"""Frameless transparent always-on-top window rendering the sprite animation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import override

from PyQt6 import QtCore, QtGui, QtWidgets

from .config import ANIM_CONFIG, ASSETS, ATLAS_LAYOUTS, Anim

WIN_SIZE: int = 200
SPRITE_SIZE: int = 180  # inset like the JS (PlaneGeometry 180 in a 200 win)


def _config_path() -> Path:
    """XDG config path for user prefs (window position, etc.)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "peon-pet" / "config.json"


def _load_pos() -> QtCore.QPoint | None:
    """Read saved window position, or None if absent/invalid."""
    try:
        data = json.loads(_config_path().read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    w = data.get("window")
    if not isinstance(w, dict):
        return None
    x, y = w.get("x"), w.get("y")
    if isinstance(x, int) and isinstance(y, int):
        return QtCore.QPoint(x, y)
    return None


def _save_pos(pos: QtCore.QPoint) -> None:
    """Persist window position into the config file (merging existing keys)."""
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        data = {}
    data["window"] = {"x": pos.x(), "y": pos.y()}
    p.write_text(json.dumps(data, indent=2))


class PetWindow(QtWidgets.QWidget):
    # Class-level type declarations (assigned in __init__).
    atlas: QtGui.QPixmap
    border: QtGui.QPixmap | None
    cell_w: float
    cell_h: float
    reaction_loops: int
    anim: Anim
    row: int
    max_frames: int
    loop: bool
    remaining_loops: int
    frame: int
    timer: QtCore.QTimer
    _drag_offset: QtCore.QPoint | None

    def __init__(
            self,
            atlas: str,
            loops: int = 3,
            start_anim: Anim = Anim.SLEEPING,
    ) -> None:
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIN_SIZE, WIN_SIZE)

        # Load atlas + border assets from the configured layout.
        filename, cols, rows, border_file = ATLAS_LAYOUTS[atlas]
        self.atlas = QtGui.QPixmap(str(ASSETS / filename))
        if self.atlas.isNull():
            raise RuntimeError(f"failed to load atlas: {filename}")
        if border_file is not None:
            self.border = QtGui.QPixmap(str(ASSETS / border_file))
            if self.border.isNull():
                raise RuntimeError(f"failed to load border: {border_file}")
        else:
            self.border = None
        self.cell_w = self.atlas.width() / cols
        self.cell_h = self.atlas.height() / rows
        self.reaction_loops = loops

        self.frame = 0
        self._drag_offset = None
        self.timer = QtCore.QTimer(self)
        _ = self.timer.timeout.connect(self.advance)
        # Play the initial event (or idle) once at startup.
        self.play(start_anim)

        # Position: saved overrides the default bottom-left corner.
        saved = _load_pos()
        if saved is not None and QtWidgets.QApplication.screenAt(saved) is not None:
            self.move(saved)
        else:
            screen = QtWidgets.QApplication.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                self.move(geo.x() + 20, geo.bottom() - WIN_SIZE - 20)

    def play(self, anim: Anim) -> None:
        """Start playing `anim`. Event anims play `reaction_loops` times then return to sleeping."""
        self.anim = anim
        self.row, self.max_frames, fps, self.loop = ANIM_CONFIG[anim]
        self.remaining_loops = 0 if anim == Anim.SLEEPING else self.reaction_loops - 1
        self.frame = 0
        self.timer.setInterval(int(1000 / fps))
        if not self.timer.isActive():
            self.timer.start()

    def advance(self) -> None:
        self.frame += 1
        if self.frame >= self.max_frames:
            if self.loop:
                self.frame = 0
            else:
                if self.remaining_loops > 0:
                    self.remaining_loops -= 1
                    self.frame = 0
                else:
                    # Event finished — return to idle
                    self.play(Anim.SLEEPING)
                    self.update()
                    return
        self.update()

    @override
    def mousePressEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_offset = a0.globalPosition().toPoint() - self.frameGeometry().topLeft()
            a0.accept()

    @override
    def mouseMoveEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if (a0 is not None and self._drag_offset is not None
                and a0.buttons() & QtCore.Qt.MouseButton.LeftButton):
            self.move(a0.globalPosition().toPoint() - self._drag_offset)
            a0.accept()

    @override
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if (a0 is not None and a0.button() == QtCore.Qt.MouseButton.LeftButton
                and self._drag_offset is not None):
            self._drag_offset = None
            _save_pos(self.pos())
            a0.accept()

    @override
    def paintEvent(self, a0: QtGui.QPaintEvent | None) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, False)

        # Sprite: current cell of the atlas, scaled to SPRITE_SIZE, centered
        sx = (WIN_SIZE - SPRITE_SIZE) // 2
        sy = (WIN_SIZE - SPRITE_SIZE) // 2
        src = QtCore.QRectF(self.frame * self.cell_w, self.row * self.cell_h, self.cell_w, self.cell_h)
        p.drawPixmap(QtCore.QRectF(sx, sy, SPRITE_SIZE, SPRITE_SIZE), self.atlas, src)

        # Border: full atlas border image stretched to the window (if configured)
        if self.border is not None:
            p.drawPixmap(QtCore.QRectF(self.rect()), self.border,
                         QtCore.QRectF(0, 0, self.border.width(), self.border.height()))
