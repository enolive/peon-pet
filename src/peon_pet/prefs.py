"""User preferences from ~/.config/peon-pet/config.json.

Two categories: read-only (`atlas`, `loops` - user edits, app never writes) and
volatile (`position` - app reads on start, writes on drag).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import final

from .config import ATLAS_LAYOUTS

DEFAULT_LOOPS = 3
DEFAULT_ATLAS = "2b"


logger = logging.getLogger(__name__)


def _config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "peon-pet" / "config.json"


def _read() -> dict[str, object]:
    try:
        data = json.loads(_config_path().read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse config file. Using defaults.")
        return {}
    return data


@final
class WindowPosition:
    """Volatile window position - read on start, written on drag.

    Pure `(x, y)` ints (no Qt types); the window converts to/from QPoint.
    `current` is the snapshot from Prefs construction; `save` re-reads the file,
    merges the new position, and writes.
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
        self._atomic_write(p, json.dumps(data, indent=2))

    @staticmethod
    def _atomic_write(path: Path, data: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)


@final
class Prefs:
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
