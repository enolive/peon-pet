"""Tests for PetWindow's sprite-map math, missing-row detection, and the
finished-signal boundary that the state machine depends on.
"""

import pytest
from PyQt6 import QtCore
from PyQt6.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot

from peon_pet.config import ANIM_CONFIG, Anim
from peon_pet.prefs import Prefs
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

        assert len(finished_spy) == 1
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

        assert len(finished_spy) == 0


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


def _make_prefs() -> Prefs:
    """Prefs with the default atlas and a tiny loop count for fast boundary tests."""
    # Offscreen Qt: construction without a display. Defaults suffice (atlas
    # '2b', loops 3). XDG_CONFIG_HOME is isolated by the test environment.
    return Prefs()
