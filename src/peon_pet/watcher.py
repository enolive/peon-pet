"""Polls peon-ping's .state.json and invokes a callback for new events."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import final

from pydantic import BaseModel

from .events import Event

DEFAULT_STATE_PATH = Path.home() / ".claude" / "hooks" / "peon-ping" / ".state.json"
POLL_INTERVAL_S = 0.5

logger = logging.getLogger(__name__)

# Callback shape: (event, session_id).
OnEvent = Callable[[Event, str], None]
OnTick = Callable[[], None]


def _noop() -> None:
    pass


@final
class StateWatcher:
    """The on_event callback fires on the daemon thread, so callers crossing
    into a GUI thread must marshal themselves (see __main__'s seam). peon-ping
    writes .state.json atomically (tempfile + os.replace), which breaks
    QFileSystemWatcher's inode watch, hence mtime polling.

    After each poll wait, `on_tick` runs (even when the file did not change) so
    consumers can expire stale state. It is not called during the initial
    `_emit_current` sync. `stop` joins the poll thread.
    """

    def __init__(
        self,
        on_event: OnEvent,
        path: Path = DEFAULT_STATE_PATH,
        poll_interval_s: float = POLL_INTERVAL_S,
        on_tick: OnTick | None = None,
    ) -> None:
        self.path = path
        self.on_event: OnEvent = on_event
        self.on_tick: OnTick = on_tick if on_tick is not None else _noop
        self._poll_interval_s = poll_interval_s
        self._last_mtime: float = 0.0
        """keeps track of the last modification time of the state file"""
        self._last_timestamp: float = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.debug("started, polling %s", self.path)

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout_s)
            self._thread = None
        logger.debug("stop requested")

    def _run(self) -> None:
        # Emits the current event first so consumers sync to current reality,
        # then polls for changes. on_tick runs only after each wait, not on the
        # initial emit.
        logger.debug("polling thread running")
        self._emit_current()
        while not self._stop.wait(self._poll_interval_s):
            self._poll()
            self.on_tick()
        logger.debug("polling thread exiting")

    def _emit_current(self) -> None:
        # Records the event's timestamp so the next poll doesn't re-emit it.
        self._last_mtime = self._current_mtime()
        self._emit(self._read_last_active())

    def _poll(self) -> None:
        current_mtime = self._current_mtime()
        if current_mtime <= self._last_mtime:
            return
        self._last_mtime = current_mtime
        last_active = self._read_last_active()
        if last_active is None:
            return
        ts = last_active.timestamp
        if ts <= self._last_timestamp:
            logger.debug("mtime changed but timestamp not newer (%.3f)", ts)
            return
        self._last_timestamp = ts
        self._emit(last_active)

    def _emit(self, last_active: _LastActive | None) -> None:
        # Updates `_last_timestamp` so the next poll doesn't re-emit an older
        # event. Unknown event names or missing fields are skipped here, the
        # only place str-to-Event parsing happens.
        if last_active is None:
            return
        self._last_timestamp = last_active.timestamp
        ev_name = last_active.event
        sid = last_active.session_id
        ev = Event.from_name(ev_name)
        if ev is None:
            logger.warning("unknown peon-ping event %r", ev_name)
            return
        self.on_event(ev, sid)

    def _current_mtime(self) -> float:
        """
        reads the current modification time of the state file.
        used as a quick probe before reading its contents.
        """
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0

    def _read_last_active(self) -> _LastActive | None:
        try:
            raw_json = self.path.read_text()
            data = _SessionState.model_validate_json(raw_json)
        except (OSError, ValueError):
            return None
        return data.last_active


class _SessionState(BaseModel):
    last_active: _LastActive


class _LastActive(BaseModel):
    event: str
    session_id: str
    timestamp: float
