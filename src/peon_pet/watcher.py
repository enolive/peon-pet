"""Polls peon-ping's .state.json and emits Anim signals for new events."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import final

from PyQt6 import QtCore

from .config import EVENT_TO_ANIM, Anim

DEFAULT_STATE_PATH = Path.home() / ".claude" / "hooks" / "peon-ping" / ".state.json"
POLL_INTERVAL_MS = 500


@final
class StateWatcher(QtCore.QObject):
    """Polls peon-ping's state file (mtime-based) and emits event_triggered(Anim).

    peon-ping writes .state.json atomically (tempfile + os.replace), which breaks
    QFileSystemWatcher's inode-based watch — so we poll mtime instead.
    """

    event_triggered = QtCore.pyqtSignal(Anim)

    def __init__(self, path: Path = DEFAULT_STATE_PATH, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.path = path
        self._last_mtime: float = 0.0
        self._last_timestamp: float = 0.0
        self._timer = QtCore.QTimer(self)
        _ = self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        """Begin polling. Snapshots the current state without emitting."""
        self._snapshot()
        self._timer.start(POLL_INTERVAL_MS)

    def stop(self) -> None:
        self._timer.stop()

    def _snapshot(self) -> None:
        """Record current mtime + last_active timestamp without emitting."""
        self._last_mtime = self._mtime()
        last_active = self._read_last_active()
        if last_active is not None:
            self._last_timestamp = self._ts(last_active)

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
        event = last_active.get("event")
        if not isinstance(event, str):
            return
        anim = EVENT_TO_ANIM.get(event)
        if anim is None:
            print(f"peon-pet: unknown peon-ping event {event!r}", file=sys.stderr)
            return
        self.event_triggered.emit(anim)

    def _ts(self, last_active: dict[str, object]) -> float:
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
