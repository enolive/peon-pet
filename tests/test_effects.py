"""Tests for reaction-effect pure helpers."""

import pytest

from peon_pet.effects import decay_flash


class TestDecayFlash:
    def test_subtracts_dt_times_decay(self) -> None:
        assert decay_flash(0.5, dt=0.1, decay=2.0) == pytest.approx(0.3)

    def test_clamps_at_zero(self) -> None:
        assert decay_flash(0.1, dt=1.0, decay=2.0) == 0.0

    def test_zero_stays_zero(self) -> None:
        assert decay_flash(0.0, dt=0.1, decay=2.0) == 0.0
