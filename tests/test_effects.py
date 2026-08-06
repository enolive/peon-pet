"""Tests for reaction-effect pure helpers."""

import math
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from peon_pet.config import FlashConfig, ParticleConfig, Rgb, Rgba, ShakeConfig
from peon_pet.effects import (
    EffectPlayer,
    FlashOverlay,
    Particle,
    ParticleOverlay,
    burst_opacity,
    decay_linear,
    shake_offset,
    spawn_particles,
    step_particle,
)


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


class TestBurstOpacity:
    def test_full_at_start(self) -> None:
        assert burst_opacity(lifetime=1.2, duration=1.2) == 1.0

    def test_zero_when_spent(self) -> None:
        assert burst_opacity(lifetime=0.0, duration=1.2) == 0.0

    @given(
        lifetime=st.floats(
            min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
        duration=st.floats(
            min_value=1e-3, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_stays_in_unit_interval(self, lifetime: float, duration: float) -> None:
        assert 0.0 <= burst_opacity(lifetime, duration) <= 1.0


class TestParticles:
    counts: SearchStrategy[int] = st.integers(min_value=1, max_value=1000)

    @given(count=counts)
    def test_spawn_count_does_not_depend_on_seed(self, count: int) -> None:
        r = random.Random()

        assert len(spawn_particles(count, r)) == count

    def test_step_applies_velocity_and_gravity(self) -> None:
        p = Particle(
            x=0.0,
            y=0.0,
            vx=10.0,
            vy=20.0,
            gravity=-50.0,
            color=Rgb(255, 255, 0),
        )

        got = step_particle(p, dt=0.1)

        assert got.x == pytest.approx(1.0)
        assert got.y == pytest.approx(2.0)
        assert got.vy == pytest.approx(15.0)

    @given(count=counts, seed=st.floats(min_value=0.0, max_value=2**32 - 1))
    def test_spawn_deterministic_with_seed(self, count: int, seed: int) -> None:
        particles1 = spawn_particles(count, random.Random(seed))
        particles2 = spawn_particles(count, random.Random(seed))

        assert particles1 == particles2

    @given(
        dt=st.floats(
            min_value=0.0, max_value=0.1, allow_nan=False, allow_infinity=False
        ),
    )
    def test_step_keeps_finite_state(self, dt: float) -> None:
        particles = spawn_particles(8, random.Random())

        for p in particles:
            got = step_particle(p, dt)
            assert math.isfinite(got.x)
            assert math.isfinite(got.y)
            assert math.isfinite(got.vy)


class TestEffectPlayer:
    def test_empty_arm_is_inactive(self) -> None:
        sut = EffectPlayer()

        sut.arm(())

        assert not sut.active
        assert sut.sprite_offset() == (0.0, 0.0)
        assert sut.overlays() == []

    def test_arm_replaces_previous_effects(self) -> None:
        sut = EffectPlayer()
        sut.arm(
            (ShakeConfig(12.0, 8.0),),
            rng=random.Random(0),
        )
        assert sut.shake_intensity > 0.0

        sut.arm(
            (FlashConfig(Rgba.from_hex("#FFCC00", a=0.5), 2.0),),
            rng=random.Random(0),
        )

        assert sut.shake_intensity == 0.0
        assert sut.flash_intensity == pytest.approx(0.5)

    def test_tick_expires_flash(self) -> None:
        sut = EffectPlayer()
        sut.arm((FlashConfig(Rgba.from_hex("#FFFFFF", a=0.5), 10.0),))

        assert sut.tick(dt=1.0) is False
        assert not sut.active

    def test_overlays_include_flash_and_particles(self) -> None:
        sut = EffectPlayer()
        sut.arm(
            (
                FlashConfig(Rgba.from_hex("#FFCC00", a=0.5), 2.0),
                ParticleConfig(count=5, duration=1.2),
            ),
            rng=random.Random(0),
        )

        kinds = {type(o) for o in sut.overlays()}

        assert kinds == {FlashOverlay, ParticleOverlay}
        assert sut.particle_count == 5
