"""Frameless transparent always-on-top window rendering the sprite animation."""

from __future__ import annotations

import logging
from typing import final, override

from PyQt6 import QtCore, QtGui, QtWidgets

from .config import ANIM_CONFIG, ASSETS, ATLAS_LAYOUTS, Anim
from .prefs import Prefs

_BADGE_FG_COLOR = "white"
_BADGE_BG_COLOR = "#0c6d1a"
_WIN_SIZE: int = 200
_SPRITE_SIZE: int = 180  # inset like the JS (PlaneGeometry 180 in a 200 win)

logger = logging.getLogger(__name__)


def cell_rect(frame: int, row: int, cell_w: float, cell_h: float) -> QtCore.QRectF:
    """Source rect of the sprite cell at `frame` (column), `row` in the atlas.

    Pure math over the atlas grid - no Qt application needed to construct or
    assert on the returned `QRectF` (a value type). Extracted from `paintEvent`
    so the "which sprite" math is testable without rendering.
    """
    return QtCore.QRectF(frame * cell_w, row * cell_h, cell_w, cell_h)


def missing_anims(rows: int) -> list[Anim]:
    """Anims whose configured row is at or beyond `rows` (-> fall back to row 0).

    Pure given the atlas row count; the stderr warning stays in
    `_warn_missing_anims` so this stays testable without rendering.
    """
    return [a for a in Anim if ANIM_CONFIG[a].row >= rows]


@final
class PetWindow(QtWidgets.QWidget):
    # Class-level type declarations (assigned in __init__).
    atlas: QtGui.QPixmap
    border: QtGui.QPixmap
    cell_w: float
    cell_h: float
    loops: int
    _rows: int
    anim: Anim
    row: int
    max_frames: int
    loop: bool
    frame: int
    _loops_played: int
    timer: QtCore.QTimer
    _drag_offset: QtCore.QPoint | None
    _session_count: int
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
        self.setFixedSize(_WIN_SIZE, _WIN_SIZE)

        atlas = prefs.atlas
        loops = prefs.loops
        layout = ATLAS_LAYOUTS[atlas]
        self.atlas = QtGui.QPixmap(str(ASSETS / layout.filename))
        if self.atlas.isNull():
            raise RuntimeError(f"failed to load atlas: {layout.filename}")
        border = QtGui.QPixmap(str(ASSETS / layout.border))
        if border.isNull():
            raise RuntimeError(f"failed to load border: {layout.border}")
        self.border = border
        self.cell_w = self.atlas.width() / layout.cols
        self.cell_h = self.atlas.height() / layout.rows
        self.loops = loops
        self._rows = layout.rows
        self._prefs = prefs
        self._warn_missing_anims(atlas)

        self.frame = 0
        self._loops_played = 0
        self._drag_offset = None
        self._session_count = 0
        self.timer = QtCore.QTimer(self)
        _ = self.timer.timeout.connect(self.advance)
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
            self.move(geo.x() + 20, geo.bottom() - _WIN_SIZE - 20)

    def play(self, anim: Anim, play_forever: bool = False) -> None:
        """Switch to `anim` and render it.

        Looping anims (sleeping, typing) loop forever. One-shot anims (waking,
        alarmed, etc.) play `loops` times then emit `finished`; the caller
        (state machine) decides what follows. A redundant call with the same
        anim and loop behavior is a no-op to reduce the flicker.
        """
        cfg = ANIM_CONFIG[anim]
        loop = True if play_forever else cfg.loop
        if getattr(self, "anim", None) is anim and getattr(self, "loop", None) is loop:
            return
        logger.debug("play %s%s", anim.value, " (forever)" if play_forever else "")
        self.anim = anim
        self.row = min(cfg.row, self._rows - 1)
        self.max_frames = cfg.frames
        self.loop = loop
        self.frame = 0
        self._loops_played = 0
        self.timer.setInterval(int(1000 / cfg.fps))
        if not self.timer.isActive():
            self.timer.start()

    def _warn_missing_anims(self, atlas: str) -> None:
        missing = missing_anims(self._rows)
        if not missing:
            return
        names = ", ".join(f"{a.value} (row {ANIM_CONFIG[a].row})" for a in missing)
        logger.warning(
            "atlas %r has %d row(s); %d anim(s) have no sprite and will fall back to last available row: %s",
            atlas,
            self._rows,
            len(missing),
            names,
        )

    def advance(self) -> None:
        self.frame += 1
        if self.frame >= self.max_frames:
            if self.loop:
                self.frame = 0
            else:
                self._loops_played += 1
                if self._loops_played >= self.loops:
                    # Reaction played out - hold the last frame as a fallback.
                    # In practice the synchronous finished -> state -> play(base)
                    # chain switches at this loop boundary without a freeze.
                    self.frame = self.max_frames - 1
                    self.finished.emit()
                    self.update()
                    return
                self.frame = 0
        self.update()

    def toggle_visibility(self) -> None:
        self.setVisible(not self.isVisible())

    def set_session_count(self, count: int) -> None:
        """Update the active-session badge. Only repaints if it changed."""
        if count == self._session_count:
            return
        self._session_count = count
        self.update()

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

        sx = (_WIN_SIZE - _SPRITE_SIZE) // 2
        sy = (_WIN_SIZE - _SPRITE_SIZE) // 2
        src = cell_rect(self.frame, self.row, self.cell_w, self.cell_h)
        p.drawPixmap(QtCore.QRectF(sx, sy, _SPRITE_SIZE, _SPRITE_SIZE), self.atlas, src)

        p.drawPixmap(
            QtCore.QRectF(self.rect()),
            self.border,
            QtCore.QRectF(0, 0, self.border.width(), self.border.height()),
        )

        # Badge last so it sits on top.
        if self._session_count > 0:
            self._draw_badge(p)

    def _draw_badge(self, p: QtGui.QPainter) -> None:
        # Cap at 9+ so the badge stays a fixed size.
        text = str(self._session_count) if self._session_count <= 9 else "9+"
        diameter = 22
        margin = 8
        x = _WIN_SIZE - diameter - margin
        y = margin
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(_BADGE_BG_COLOR))
        p.drawEllipse(
            QtCore.QPointF(x + diameter / 2, y + diameter / 2),
            diameter / 2,
            diameter / 2,
        )
        p.setPen(QtGui.QColor(_BADGE_FG_COLOR))
        font = QtGui.QFont("Sans", 9, QtGui.QFont.Weight.Bold)
        p.setFont(font)
        _ = p.drawText(
            QtCore.QRectF(x, y, diameter, diameter),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            text,
        )
