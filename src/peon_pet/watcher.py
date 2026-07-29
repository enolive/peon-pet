"""Polls peon-ping's .state.json and emits (event, session_id) signals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import final

from PyQt6 import QtCore

DEFAULT_STATE_PATH = Path.home() / ".claude" / "hooks" / "peon-ping" / ".state.json"
POLL_INTERVAL_MS = 500


@final
class StateWatcher(QtCore.QObject):
    """Polls peon-ping's state file (mtime-based) and emits event_triggered(str, str).

    Emits (raw event name, session id); the state machine decides what to do
    with them. The session id lets the state machine track multiple concurrent
    sessions without one session's Stop zeroing the liveness flag for the others.

    peon-ping writes .state.json atomically (tempfile + os.replace), which breaks
    QFileSystemWatcher's inode-based watch — so we poll mtime instead.
    """

    event_triggered = QtCore.pyqtSignal(str, str)

    def __init__(self, path: Path = DEFAULT_STATE_PATH, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.path = path
        self._last_mtime: float = 0.0
        self._last_timestamp: float = 0.0
        self._timer = QtCore.QTimer(self)
        _ = self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        """Begin polling. Emits the current event (if any) so the state machine
        syncs to current reality, then polls for changes."""
        self._emit_current()
        self._timer.start(POLL_INTERVAL_MS)

    def stop(self) -> None:
        self._timer.stop()

    def _emit_current(self) -> None:
        """Emit the current event and record its timestamp so the next poll
        doesn't re-emit it."""
        self._last_mtime = self._mtime()
        last_active = self._read_last_active()
        if last_active is None:
            return
        ts = self._ts(last_active)
        self._last_timestamp = ts
        ev = _field(last_active, "event")
        sid = _field(last_active, "session_id")
        if ev is None or sid is None:
            return
        self.event_triggered.emit(ev, sid)

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
            return
        self._last_timestamp = ts
        ev = _field(last_active, "event")
        sid = _field(last_active, "session_id")
        if ev is None or sid is None:
            return
        self.event_triggered.emit(ev, sid)

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
        """Read last_active from the state file, or None on any error."""
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
