"""User preferences from ~/.config/peon-pet/config.json.

Owns the config file and the resolution/validation of its values. Two clearly
separated categories:

- Read-only:   `atlas`, `loops`. User edits the file; the app never writes these.
- Volatile:    `position` (window position). App reads on start, writes on drag.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import final

from .config import ATLAS_LAYOUTS

DEFAULT_LOOPS = 3
DEFAULT_ATLAS = "orc"


def _config_path() -> Path:
    """XDG config path for user prefs."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "peon-pet" / "config.json"


def _read() -> dict[str, object]:
    """Load the config file."""
    try:
        data = json.loads(_config_path().read_text())
    except FileNotFoundError:
        return {}
    return data


@final
class WindowPosition:
    """Volatile window position — read on start, written on drag.

    Pure data: `(x, y)` ints, no Qt types. The window converts to/from
    QPoint. `current` reads from the snapshot taken at Prefs construction.
    `save` re-reads the file (in case it changed), merges the new position,
    writes.
    """

    def __init__(self, position: tuple[int, int] | None) -> None:
        self.position = position

    @property
    def current(self) -> tuple[int, int] | None:
        return self.position

    def save(self, pos: tuple[int, int]) -> None:
        self.position = pos
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = _read()
        data["window"] = {"x": pos[0], "y": pos[1]}
        p.write_text(json.dumps(data, indent=2))


@final
class Prefs:
    """Owns the config file. Read-only settings are resolved+validated here."""

    def __init__(self) -> None:
        data = _read()
        self.atlas = self._resolve_atlas(data)
        self.loops = self._resolve_loops(data)
        self.position = WindowPosition(self._resolve_position(data))

    @staticmethod
    def _resolve_atlas(data: dict[str, object]) -> str:
        a = data.get("atlas")
        if isinstance(a, str) and a in ATLAS_LAYOUTS:
            return a
        if a is None:
            return DEFAULT_ATLAS
        available = ", ".join(sorted(ATLAS_LAYOUTS))
        raise ValueError(f"config 'atlas' {a!r} is not valid; available: {available}")

    @staticmethod
    def _resolve_loops(data: dict[str, object]) -> int:
        l = data.get("loops")
        if isinstance(l, int) and l > 0:
            return l
        return DEFAULT_LOOPS

    @staticmethod
    def _resolve_position(data: dict[str, object]) -> tuple[int, int] | None:
        w = data.get("window")
        if not isinstance(w, dict):
            return None
        x, y = w.get("x"), w.get("y")
        if isinstance(x, int) and isinstance(y, int):
            return x, y
        return None
