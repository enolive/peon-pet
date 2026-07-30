"""Frameless transparent always-on-top window rendering the sprite animation."""

from __future__ import annotations

from typing import final, override

from PyQt6 import QtCore, QtGui, QtWidgets

from .config import ANIM_CONFIG, ASSETS, ATLAS_LAYOUTS, Anim
from .prefs import Prefs

WIN_SIZE: int = 200
SPRITE_SIZE: int = 180  # inset like the JS (PlaneGeometry 180 in a 200 win)


@final
class PetWindow(QtWidgets.QWidget):
    # Class-level type declarations (assigned in __init__).
    atlas: QtGui.QPixmap
    border: QtGui.QPixmap | None
    cell_w: float
    cell_h: float
    loops: int
    anim: Anim
    row: int
    max_frames: int
    loop: bool
    frame: int
    _loops_played: int
    timer: QtCore.QTimer
    _drag_offset: QtCore.QPoint | None
    _prefs: Prefs

    # Emitted when a one-shot anim has played `loops` times. The state machine
    # reacts to this by switching to the base anim.
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        prefs: Prefs,
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

        atlas = prefs.atlas
        loops = prefs.loops
        # Load atlas + border assets from the configured layout.
        layout = ATLAS_LAYOUTS[atlas]
        self.atlas = QtGui.QPixmap(str(ASSETS / layout.filename))
        if self.atlas.isNull():
            raise RuntimeError(f"failed to load atlas: {layout.filename}")
        if layout.border is not None:
            border = QtGui.QPixmap(str(ASSETS / layout.border))
            if border.isNull():
                raise RuntimeError(f"failed to load border: {layout.border}")
            self.border = border
        else:
            self.border = None
        self.cell_w = self.atlas.width() / layout.cols
        self.cell_h = self.atlas.height() / layout.rows
        self.loops = loops
        self._prefs = prefs

        self.frame = 0
        self._loops_played = 0
        self._drag_offset = None
        self.timer = QtCore.QTimer(self)
        _ = self.timer.timeout.connect(self.advance)
        # Play the initial event (or idle) once at startup.
        self.play(start_anim)

        # Position: saved overrides the default bottom-left corner.
        saved = prefs.position.current
        if saved is not None:
            pt = QtCore.QPoint(*saved)
            if QtWidgets.QApplication.screenAt(pt) is not None:
                self.move(pt)
            else:
                self._move_default()
        else:
            self._move_default()

    def _move_default(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.x() + 20, geo.bottom() - WIN_SIZE - 20)

    def play(self, anim: Anim, play_forever: bool = False) -> None:
        """Switch to `anim` and render it.

        Looping anims (sleeping, typing) loop forever. One-shot anims
        (waking, alarmed, …) play `loops` times, then emit `finished` — the
        caller (state machine) decides what follows. Never self-switches.
        """
        self.anim = anim
        cfg = ANIM_CONFIG[anim]
        loop: bool
        if play_forever:
            loop = True
        else:
            loop = cfg.loop
        self.row, self.max_frames, fps, self.loop = (
            cfg.row,
            cfg.frames,
            cfg.fps,
            loop,
        )
        self.frame = 0
        self._loops_played = 0
        self.timer.setInterval(int(1000 / fps))
        if not self.timer.isActive():
            self.timer.start()

    def advance(self) -> None:
        self.frame += 1
        if self.frame >= self.max_frames:
            if self.loop:
                self.frame = 0
            else:
                self._loops_played += 1
                if self._loops_played >= self.loops:
                    # Reaction played out — hold the last frame as a fallback.
                    # In practice the synchronous finished → state → play(base)
                    # chain switches at this loop boundary without a freeze.
                    self.frame = self.max_frames - 1
                    self.finished.emit()
                    self.update()
                    return
                self.frame = 0
        self.update()

    def toggle_visibility(self) -> None:
        self.setVisible(not self.isVisible())

    @override
    def mousePressEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_offset = (
                a0.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            a0.accept()

    @override
    def mouseMoveEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if (
            a0 is not None
            and self._drag_offset is not None
            and a0.buttons() & QtCore.Qt.MouseButton.LeftButton
        ):
            self.move(a0.globalPosition().toPoint() - self._drag_offset)
            a0.accept()

    @override
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if (
            a0 is not None
            and a0.button() == QtCore.Qt.MouseButton.LeftButton
            and self._drag_offset is not None
        ):
            self._drag_offset = None
            self._prefs.position.save((self.pos().x(), self.pos().y()))
            a0.accept()

    @override
    def paintEvent(self, a0: QtGui.QPaintEvent | None) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, False)

        # Sprite: current cell of the atlas, scaled to SPRITE_SIZE, centered
        sx = (WIN_SIZE - SPRITE_SIZE) // 2
        sy = (WIN_SIZE - SPRITE_SIZE) // 2
        src = QtCore.QRectF(
            self.frame * self.cell_w, self.row * self.cell_h, self.cell_w, self.cell_h
        )
        p.drawPixmap(QtCore.QRectF(sx, sy, SPRITE_SIZE, SPRITE_SIZE), self.atlas, src)

        # Border: full atlas border image stretched to the window (if configured)
        if self.border is not None:
            p.drawPixmap(
                QtCore.QRectF(self.rect()),
                self.border,
                QtCore.QRectF(0, 0, self.border.width(), self.border.height()),
            )
