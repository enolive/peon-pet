"""Polls peon-ping's .state.json and invokes a callback for new events."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import final

from .events import Event

DEFAULT_STATE_PATH = Path.home() / ".claude" / "hooks" / "peon-ping" / ".state.json"
POLL_INTERVAL_S = 0.5

logger = logging.getLogger(__name__)

# Callback shape: (event, session_id).
OnEvent = Callable[[Event, str], None]


@final
class StateWatcher:
    """The on_event callback fires on the daemon thread, so callers crossing
    into a GUI thread must marshal themselves (see __main__'s seam). peon-ping
    writes .state.json atomically (tempfile + os.replace), which breaks
    QFileSystemWatcher's inode watch, hence mtime polling."""

    def __init__(
        self,
        on_event: OnEvent,
        path: Path = DEFAULT_STATE_PATH,
        poll_interval_s: float = POLL_INTERVAL_S,
    ) -> None:
        self.path = path
        self.on_event: OnEvent = on_event
        self._poll_interval_s = poll_interval_s
        self._last_mtime: float = 0.0
        self._last_timestamp: float = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.debug("started, polling %s", self.path)

    def stop(self) -> None:
        self._stop.set()
        logger.debug("stop requested")

    def _run(self) -> None:
        # Emits the current event first so consumers sync to current reality,
        # then polls for changes.
        logger.debug("polling thread running")
        self._emit_current()
        while not self._stop.wait(self._poll_interval_s):
            self._poll()
        logger.debug("polling thread exiting")

    def _emit_current(self) -> None:
        # Records the event's timestamp so the next poll doesn't re-emit it.
        self._last_mtime = self._mtime()
        self._emit(self._read_last_active())

    def _poll(self) -> None:
        mtime = self._mtime()
        if mtime == self._last_mtime:
            return
        self._last_mtime = mtime
        last_active = self._read_last_active()
        if last_active is None:
            return
        ts = self._ts(last_active)
        if ts <= self._last_timestamp:
            logger.debug("mtime changed but timestamp not newer (%.3f)", ts)
            return
        self._last_timestamp = ts
        self._emit(last_active)

    def _emit(self, last_active: dict[str, object] | None) -> None:
        # Updates `_last_timestamp` so the next poll doesn't re-emit an older
        # event. Unknown event names or missing fields are skipped here, the
        # only place str-to-Event parsing happens.
        if last_active is None:
            return
        self._last_timestamp = self._ts(last_active)
        ev_name = _field(last_active, "event")
        sid = _field(last_active, "session_id")
        if ev_name is None:
            return
        ev = Event.from_name(ev_name)
        if ev is None:
            logger.warning("unknown peon-ping event %r", ev_name)
            return
        if sid is None:
            return
        self.on_event(ev, sid)

    @staticmethod
    def _ts(last_active: dict[str, object]) -> float:
        ts = last_active.get("timestamp", 0.0)
        return float(ts) if isinstance(ts, (int, float)) else 0.0

    def _mtime(self) -> float:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0

    def _read_last_active(self) -> dict[str, object] | None:
        try:
            with self.path.open() as f:
                st = json.load(f)
        except (OSError, ValueError):
            return None
        last_active = st.get("last_active")
        if not isinstance(last_active, dict):
            return None
        return last_active


def _field(last_active: dict[str, object], key: str) -> str | None:
    v = last_active.get(key)
    return v if isinstance(v, str) else None
