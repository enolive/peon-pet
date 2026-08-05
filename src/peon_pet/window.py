"""Frameless transparent always-on-top window rendering the sprite animation."""

from __future__ import annotations

import logging
from typing import final, override

from PySide6 import QtCore, QtGui, QtWidgets

from .config import ANIM_CONFIG, ASSETS, ATLAS_LAYOUTS, Anim, FlashConfig
from .effects import decay_flash
from .prefs import Prefs

_BADGE_FG_COLOR = "white"
_BADGE_BG_COLOR = "#0c6d1a"
_WIN_SIZE: int = 200
_SPRITE_SIZE: int = 180  # inset like the JS (PlaneGeometry 180 in a 200 win)
_EFFECT_INTERVAL_MS = 16  # ~60fps while a flash (etc.) is live

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
    # Emitted when a one-shot anim has played `loops` times. The state machine
    # reacts to this by switching to the base anim.
    finished = QtCore.Signal()

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
        self._atlas = QtGui.QPixmap(str(ASSETS / layout.filename))
        if self._atlas.isNull():
            raise RuntimeError(f"failed to load atlas: {layout.filename}")
        border = QtGui.QPixmap(str(ASSETS / layout.border))
        if border.isNull():
            raise RuntimeError(f"failed to load border: {layout.border}")
        self._border = border
        self._cell_w = self._atlas.width() / layout.cols
        self._cell_h = self._atlas.height() / layout.rows
        self._loops = loops
        self._anim: Anim | None = None
        self._loop: bool | None = None
        self._rows = layout.rows
        self._prefs = prefs
        self._warn_missing_anims(atlas)
        self._frame = 0
        self._loops_played = 0
        self._drag_offset: QtCore.QPoint | None = None
        self._session_count = 0
        self._flash: FlashConfig | None = None
        self._flash_intensity = 0.0
        self._timer = QtCore.QTimer(self)
        _ = self._timer.timeout.connect(self.advance)
        self._effect_timer = QtCore.QTimer(self)
        _ = self._effect_timer.timeout.connect(self._tick_effects)
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

    @property
    def anim(self) -> Anim | None:
        return self._anim

    @property
    def loops(self) -> int:
        return self._loops

    @property
    def loop(self) -> bool | None:
        return self._loop

    @property
    def frame(self) -> int:
        return self._frame

    def _move_default(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen()
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
        if self._anim is anim and self._loop is loop:
            return
        logger.debug("play %s%s", anim.value, " (forever)" if play_forever else "")
        self._anim = anim
        self._row = min(cfg.row, self._rows - 1)
        self._max_frames = cfg.frames
        self._loop = loop
        self._frame = 0
        self._loops_played = 0
        self._timer.setInterval(int(1000 / cfg.fps))
        if not self._timer.isActive():
            self._timer.start()
        self._arm_flash(cfg.flash)

    def _arm_flash(self, flash: FlashConfig | None) -> None:
        if flash is None:
            return
        self._flash = flash
        self._flash_intensity = flash.color.a
        if not self._effect_timer.isActive():
            self._effect_timer.start(_EFFECT_INTERVAL_MS)

    def _tick_effects(self) -> None:
        if self._flash is None or self._flash_intensity <= 0.0:
            self._flash_intensity = 0.0
            self._effect_timer.stop()
            return
        dt = _EFFECT_INTERVAL_MS / 1000.0
        self._flash_intensity = decay_flash(
            self._flash_intensity, dt, self._flash.decay
        )
        if self._flash_intensity <= 0.0:
            self._effect_timer.stop()
        self.update()

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
        self._frame += 1
        if self._frame >= self._max_frames:
            if self._loop:
                self._frame = 0
            else:
                self._loops_played += 1
                if self._loops_played >= self._loops:
                    # Reaction played out - hold the last frame as a fallback.
                    # In practice the synchronous finished -> state -> play(base)
                    # chain switches at this loop boundary without a freeze.
                    self._frame = self._max_frames - 1
                    self.finished.emit()
                    self.update()
                    return
                self._frame = 0
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
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    @override
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            self._drag_offset is not None
            and event.buttons() & QtCore.Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    @override
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and self._drag_offset is not None
        ):
            self._drag_offset = None
            self._prefs.position.save((self.pos().x(), self.pos().y()))
            event.accept()

    @override
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        _ = event
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, False)

        sx = (_WIN_SIZE - _SPRITE_SIZE) // 2
        sy = (_WIN_SIZE - _SPRITE_SIZE) // 2
        src = cell_rect(self._frame, self._row, self._cell_w, self._cell_h)
        p.drawPixmap(
            QtCore.QRectF(sx, sy, _SPRITE_SIZE, _SPRITE_SIZE), self._atlas, src
        )

        p.drawPixmap(
            QtCore.QRectF(self.rect()),
            self._border,
            QtCore.QRectF(0, 0, self._border.width(), self._border.height()),
        )

        # Flash above border (legacy z-order); badge stays on top.
        if self._flash is not None and self._flash_intensity > 0.0:
            c = self._flash.color
            color = QtGui.QColor.fromRgbF(c.r, c.g, c.b, self._flash_intensity)
            p.fillRect(self.rect(), color)

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
