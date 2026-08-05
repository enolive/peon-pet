"""Tests for reaction-effect pure helpers."""

import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from peon_pet.effects import decay_linear, shake_offset


class TestDecayLinear:
    def test_subtracts_dt_times_rate(self) -> None:
        assert decay_linear(0.5, dt=0.1, rate=2.0) == pytest.approx(0.3)

    def test_clamps_at_zero(self) -> None:
        assert decay_linear(0.1, dt=1.0, rate=2.0) == 0.0

    def test_zero_stays_zero(self) -> None:
        assert decay_linear(0.0, dt=0.1, rate=2.0) == 0.0

    @given(
        value=st.floats(
            min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
        ),
        dt=st.floats(
            min_value=1e-3, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        rate=st.floats(
            min_value=1e-3, max_value=1_000.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_result_stays_in_range(self, value: float, dt: float, rate: float) -> None:
        result = decay_linear(value, dt, rate)

        assert 0.0 <= result <= value

    @given(
        value=st.floats(
            min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
        ),
        rate=st.floats(
            min_value=1e-3, max_value=1_000.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_large_enough_step_reaches_zero_and_stays(
        self, value: float, rate: float
    ) -> None:
        dt = (value / rate) + 1.0

        assert decay_linear(value, dt, rate) == 0.0
        assert decay_linear(0.0, dt, rate) == 0.0


class TestShakeOffset:
    def test_zero_intensity_is_origin(self) -> None:
        assert shake_offset(0.0, random.Random(0)) == (0.0, 0.0)

    @given(
        intensity=st.floats(
            min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
        ),
        seed=st.integers(min_value=0, max_value=2**32 - 1),
    )
    def test_stays_within_plus_minus_half_intensity(
        self, intensity: float, seed: int
    ) -> None:
        dx, dy = shake_offset(intensity, random.Random(seed))
        half = intensity / 2.0

        assert -half <= dx <= half
        assert -half <= dy <= half

    @given(
        intensity=st.floats(
            min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
        ),
        seed=st.integers(min_value=0, max_value=2**32 - 1),
    )
    def test_deterministic_with_seeded_rng(self, intensity: float, seed: int) -> None:
        a = shake_offset(intensity, random.Random(seed))
        b = shake_offset(intensity, random.Random(seed))

        assert a == b
