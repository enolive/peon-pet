"""Frameless transparent always-on-top window rendering the sprite animation."""

from __future__ import annotations

from typing import override

from PyQt6 import QtCore, QtGui, QtWidgets

from .config import ANIM_CONFIG, ASSETS, ATLAS_LAYOUTS, Anim

WIN_SIZE: int = 200
SPRITE_SIZE: int = 180  # inset like the JS (PlaneGeometry 180 in a 200 win)


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
        self.timer = QtCore.QTimer(self)
        _ = self.timer.timeout.connect(self.advance)
        # Play the initial event (or idle) once at startup.
        self.play(start_anim)

        # Bottom-left corner of the work area
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
