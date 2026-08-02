"""User preferences from ~/.config/peon-pet/config.json.

Two categories: read-only (`atlas`, `loops` - user edits, app never writes) and
volatile (`position` - app reads on start, writes on drag).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import final

from pydantic import BaseModel, Field

from .config import ATLAS_LAYOUTS

DEFAULT_LOOPS = 3
DEFAULT_ATLAS = "2b"


logger = logging.getLogger(__name__)


def _config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "peon-pet" / "config.json"


def _read() -> _PrefsModel:
    try:
        raw_json = _config_path().read_text()
        data = _PrefsModel.model_validate_json(raw_json)
    except FileNotFoundError:
        return _PrefsModel.default()
    except ValueError:
        logger.warning("Failed to parse config file. Using defaults.")
        return _PrefsModel.default()
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
        data.window = _WindowPositionModel(x=pos[0], y=pos[1])
        self._atomic_write(p, data.model_dump_json(indent=2))

    @staticmethod
    def _atomic_write(path: Path, data: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            _ = f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)


@final
class Prefs:
    def __init__(self) -> None:
        data = _read()
        self.atlas = self._resolve_atlas(data)
        self.loops = data.loops
        self.position = WindowPosition(self._resolve_position(data))

    @staticmethod
    def _resolve_atlas(data: _PrefsModel) -> str:
        a = data.atlas
        if a in ATLAS_LAYOUTS:
            return a
        available = ", ".join(sorted(ATLAS_LAYOUTS))
        raise ValueError(f"config 'atlas' {a!r} is not valid; available: {available}")

    @staticmethod
    def _resolve_position(data: _PrefsModel) -> tuple[int, int] | None:
        if data.window is None:
            return None
        return data.window.x, data.window.y


class _PrefsModel(BaseModel):
    atlas: str = DEFAULT_ATLAS
    loops: int = Field(gt=0, default=DEFAULT_LOOPS, strict=True)
    window: _WindowPositionModel | None = None

    @staticmethod
    def default() -> _PrefsModel:
        return _PrefsModel(atlas=DEFAULT_ATLAS, loops=DEFAULT_LOOPS, window=None)


class _WindowPositionModel(BaseModel):
    x: int = Field(strict=True)
    y: int = Field(strict=True)
