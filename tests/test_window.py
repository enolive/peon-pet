"""Tests for PetWindow's sprite-map math, missing-row detection, and the
finished-signal boundary that the state machine depends on.
"""

import pytest
from PySide6 import QtCore
from PySide6.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot

from peon_pet.config import ANIM_CONFIG, Anim, FlashConfig, ParticleConfig
from peon_pet.prefs import Prefs, WindowPosition
from peon_pet.window import PetWindow, cell_rect, missing_anims


class TestFinishedBoundary:
    def test_one_shot_emits_finished_once_at_boundary(self, qtbot: QtBot) -> None:
        prefs = _make_prefs()
        sut = PetWindow(prefs)
        qtbot.addWidget(sut)
        sut.play(Anim.WAKING)
        cfg = ANIM_CONFIG[Anim.WAKING]
        finished_spy = QSignalSpy(sut.finished)

        for _ in range(cfg.frames * sut.loops):
            sut.advance()

        assert finished_spy.count() == 1
        assert sut.frame == cfg.frames - 1

    def test_looping_anim_never_emits_finished(self, qtbot: QtBot) -> None:
        prefs = _make_prefs()
        sut = PetWindow(prefs)
        qtbot.addWidget(sut)
        sut.play(Anim.TYPING)  # looping
        cfg = ANIM_CONFIG[Anim.TYPING]
        finished_spy = QSignalSpy(sut.finished)

        for _ in range(cfg.frames * sut.loops):
            sut.advance()

        assert finished_spy.count() == 0


class TestSavedPosition:
    def test_restores_saved_position_on_construction(self, qtbot: QtBot) -> None:
        prefs = _make_prefs()
        prefs.position = WindowPosition((123, 456))

        sut = PetWindow(prefs)
        qtbot.addWidget(sut)

        assert sut.pos().x() == 123
        assert sut.pos().y() == 456


class TestHelperFunctions:
    @pytest.mark.parametrize(
        ("frame", "row"),
        [(0, 0), (5, 2), (3, 4)],
        ids=["top-left", "frame5-row2", "frame3-row4"],
    )
    def test_origin_scales_with_frame_and_row(self, frame: int, row: int) -> None:
        cell_w = 32.0
        cell_h = 48.0

        rect = cell_rect(frame, row, cell_w, cell_h)

        assert rect == QtCore.QRectF(frame * cell_w, row * cell_h, cell_w, cell_h)

    def test_zero_origin_for_top_left(self) -> None:
        rect = cell_rect(0, 0, 32.0, 48.0)

        assert rect.x() == 0.0
        assert rect.y() == 0.0
        assert rect.width() == 32.0
        assert rect.height() == 48.0

    def test_empty_when_all_rows_fit(self) -> None:
        assert missing_anims(6) == []

    def test_lists_anims_at_or_beyond_row_count(self) -> None:
        assert missing_anims(4) == [Anim.CELEBRATE, Anim.ANNOYED]


class TestPlayIdempotent:
    """
    Repeated events that resolve to the same anim (e.g. every PreToolUse
    during a busy session maps to TYPING) must not restart the animation -
    otherwise the sprite snaps back to frame 0 mid-cycle and visibly flashes.
    """

    def test_redundant_play_does_not_reset_frame(self, qtbot: QtBot) -> None:
        sut = PetWindow(_make_prefs())
        qtbot.addWidget(sut)
        sut.play(Anim.TYPING)
        sut.advance()
        sut.advance()
        sut.advance()
        frame_before = sut.frame

        sut.play(Anim.TYPING)

        assert sut.frame == frame_before

    def test_switching_to_a_different_anim_still_resets(self, qtbot: QtBot) -> None:
        sut = PetWindow(_make_prefs())
        qtbot.addWidget(sut)
        sut.play(Anim.TYPING)
        sut.advance()
        sut.advance()

        sut.play(Anim.ALARMED)

        assert sut.anim == Anim.ALARMED
        assert sut.frame == 0

    @pytest.mark.parametrize(
        "play_forever",
        [True, False],
    )
    def test_switching_to_a_different_overridden_loop_config_still_resets(
        self, qtbot: QtBot, play_forever: bool
    ) -> None:
        sut = PetWindow(_make_prefs())
        qtbot.addWidget(sut)
        sut.play(Anim.ALARMED, play_forever=not play_forever)
        sut.advance()
        sut.advance()

        sut.play(Anim.ALARMED, play_forever=play_forever)

        assert sut.anim == Anim.ALARMED
        assert sut.loop == play_forever
        assert sut.frame == 0


class TestEffectResetOnPlay:
    def test_switching_anim_clears_residual_effects(self, qtbot: QtBot) -> None:
        sut = PetWindow(_make_prefs())
        qtbot.addWidget(sut)
        effects = sut.effects
        sut.play(Anim.CELEBRATE, play_forever=True)
        assert effects.particle_count > 0

        sut.play(Anim.SLEEPING)

        assert not effects.active
        assert effects.sprite_offset() == (0.0, 0.0)
        assert effects.overlays() == []
        assert effects.flash_intensity == 0.0
        assert effects.shake_intensity == 0.0
        assert effects.particle_count == 0

    def test_switching_anim_rearms_destination_effects(self, qtbot: QtBot) -> None:
        sut = PetWindow(_make_prefs())
        qtbot.addWidget(sut)
        effects = sut.effects
        sut.play(Anim.ANNOYED, play_forever=True)

        sut.play(Anim.CELEBRATE, play_forever=True)

        assert effects.shake_intensity == 0.0
        flash = next(
            e for e in ANIM_CONFIG[Anim.CELEBRATE].effects if isinstance(e, FlashConfig)
        )
        assert effects.flash_intensity == pytest.approx(flash.color.a)
        particles = next(
            e
            for e in ANIM_CONFIG[Anim.CELEBRATE].effects
            if isinstance(e, ParticleConfig)
        )
        assert effects.particle_count == particles.count


def _make_prefs() -> Prefs:
    """Prefs with the default atlas and a tiny loop count for fast boundary tests."""
    # Offscreen Qt: construction without a display. Defaults suffice (atlas
    # '2b', loops 3). XDG_CONFIG_HOME is isolated by the test environment.
    return Prefs()
