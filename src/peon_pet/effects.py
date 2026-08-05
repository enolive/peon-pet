"""Reaction-effect helpers and runtime player (flash/shake/particles)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Protocol, final

from .config import EffectSpec, FlashConfig, ParticleConfig, Rgba, ShakeConfig

_GOLD_RGB: tuple[tuple[float, float, float], ...] = (
    (1.0, 0.85, 0.0),
    (1.0, 1.0, 0.4),
    (0.9, 0.6, 0.1),
)

# Spawn band in particle space (x right, y up; origin = paint origin below).
_SPAWN_X_SPREAD = 40.0  # x in [-spread/2, +spread/2]
_SPAWN_Y_BASE = -40.0  # band center below origin
_SPAWN_Y_SPREAD = 20.0
_SPEED_MIN = 40.0
_SPEED_SPAN = 80.0
_VY_BOOST = 20.0
_GRAVITY_BASE = -60.0
_GRAVITY_SPAN = 40.0


@dataclass(frozen=True, slots=True)
class Particle:
    """One confetti speck in legacy centered coords (x right, y up, origin center)."""

    x: float
    y: float
    vx: float
    vy: float
    gravity: float
    r: float
    g: float
    b: float


@dataclass(frozen=True, slots=True)
class FlashOverlay:
    color: Rgba
    intensity: float


@dataclass(frozen=True, slots=True)
class ParticleOverlay:
    particles: tuple[Particle, ...]
    opacity: float


Overlay = FlashOverlay | ParticleOverlay


def decay_linear(value: float, dt: float, rate: float) -> float:
    return max(0.0, value - dt * rate)


def shake_offset(intensity: float, rng: random.Random) -> tuple[float, float]:
    if intensity <= 0.0:
        return 0.0, 0.0
    return (rng.random() - 0.5) * intensity, (rng.random() - 0.5) * intensity


def burst_opacity(lifetime: float, duration: float) -> float:
    if duration <= 0.0 or lifetime <= 0.0:
        return 0.0
    return min(1.0, lifetime / duration)


def particle_to_qt(
    x: float, y: float, *, origin_x: float, origin_y: float
) -> tuple[float, float]:
    """Particle space (y up) -> Qt widget pixels (y down)."""
    return origin_x + x, origin_y - y


def spawn_particles(count: int, rng: random.Random) -> list[Particle]:
    particles: list[Particle] = []
    for _ in range(count):
        angle = (rng.random() * math.pi) - math.pi / 2
        speed = _SPEED_MIN + rng.random() * _SPEED_SPAN
        r, g, b = _GOLD_RGB[rng.randrange(len(_GOLD_RGB))]
        particles.append(
            Particle(
                x=(rng.random() - 0.5) * _SPAWN_X_SPREAD,
                y=_SPAWN_Y_BASE + (rng.random() - 0.5) * _SPAWN_Y_SPREAD,
                vx=math.cos(angle) * speed,
                vy=abs(math.sin(angle)) * speed + _VY_BOOST,
                gravity=_GRAVITY_BASE - rng.random() * _GRAVITY_SPAN,
                r=r,
                g=g,
                b=b,
            )
        )
    return particles


def step_particle(particle: Particle, dt: float) -> Particle:
    return Particle(
        x=particle.x + particle.vx * dt,
        y=particle.y + particle.vy * dt,
        vx=particle.vx,
        vy=particle.vy + particle.gravity * dt,
        gravity=particle.gravity,
        r=particle.r,
        g=particle.g,
        b=particle.b,
    )


class LiveEffect(Protocol):
    def tick(self, dt: float, rng: random.Random) -> bool:
        """Advance; return True while still active."""
        ...

    def sprite_offset(self) -> tuple[float, float]: ...

    def overlay(self) -> Overlay | None: ...


@final
class _LiveFlash:
    def __init__(self, cfg: FlashConfig) -> None:
        self._color = cfg.color
        self._decay = cfg.decay
        self._intensity = cfg.color.a

    @property
    def intensity(self) -> float:
        return self._intensity

    def tick(self, dt: float, rng: random.Random) -> bool:
        _ = rng
        self._intensity = decay_linear(self._intensity, dt, self._decay)
        return self._intensity > 0.0

    @staticmethod
    def sprite_offset() -> tuple[float, float]:
        return 0.0, 0.0

    def overlay(self) -> Overlay | None:
        if self._intensity <= 0.0:
            return None
        return FlashOverlay(self._color, self._intensity)


@final
class _LiveShake:
    def __init__(self, cfg: ShakeConfig, rng: random.Random) -> None:
        self._decay = cfg.decay
        self._intensity = cfg.intensity
        self._dx, self._dy = shake_offset(self._intensity, rng)

    @property
    def intensity(self) -> float:
        return self._intensity

    def tick(self, dt: float, rng: random.Random) -> bool:
        self._intensity = decay_linear(self._intensity, dt, self._decay)
        if self._intensity <= 0.0:
            self._dx, self._dy = 0.0, 0.0
            return False
        self._dx, self._dy = shake_offset(self._intensity, rng)
        return True

    def sprite_offset(self) -> tuple[float, float]:
        return self._dx, self._dy

    @staticmethod
    def overlay() -> Overlay | None:
        return None


@final
class _LiveParticles:
    def __init__(self, cfg: ParticleConfig, rng: random.Random) -> None:
        self._particles = spawn_particles(cfg.count, rng)
        self._lifetime = cfg.duration
        self._duration = cfg.duration

    @property
    def count(self) -> int:
        return len(self._particles)

    def tick(self, dt: float, rng: random.Random) -> bool:
        _ = rng
        self._lifetime = max(0.0, self._lifetime - dt)
        self._particles = [step_particle(p, dt) for p in self._particles]
        if self._lifetime <= 0.0:
            self._particles = []
            return False
        return True

    @staticmethod
    def sprite_offset() -> tuple[float, float]:
        return 0.0, 0.0

    def overlay(self) -> Overlay | None:
        opacity = burst_opacity(self._lifetime, self._duration)
        if opacity <= 0.0 or not self._particles:
            return None
        return ParticleOverlay(tuple(self._particles), opacity)


def _spawn_live(spec: EffectSpec, rng: random.Random) -> LiveEffect:
    match spec:
        case FlashConfig() as cfg:
            return _LiveFlash(cfg)
        case ShakeConfig() as cfg:
            return _LiveShake(cfg, rng)
        case ParticleConfig() as cfg:
            return _LiveParticles(cfg, rng)


@final
class EffectPlayer:
    """Runtime bag of live effects for one anim; empty == noop."""

    def __init__(self) -> None:
        self._live: list[LiveEffect] = []
        self._rng = random.Random()

    @property
    def active(self) -> bool:
        return bool(self._live)

    def clear(self) -> None:
        self._live = []

    def arm(
        self, specs: tuple[EffectSpec, ...], *, rng: random.Random | None = None
    ) -> None:
        if rng is not None:
            self._rng = rng
        self._live = [_spawn_live(spec, self._rng) for spec in specs]

    def tick(self, dt: float) -> bool:
        self._live = [e for e in self._live if e.tick(dt, self._rng)]
        return self.active

    def sprite_offset(self) -> tuple[float, float]:
        dx = 0.0
        dy = 0.0
        for effect in self._live:
            ox, oy = effect.sprite_offset()
            dx += ox
            dy += oy
        return dx, dy

    def overlays(self) -> list[Overlay]:
        out: list[Overlay] = []
        for effect in self._live:
            overlay = effect.overlay()
            if overlay is not None:
                out.append(overlay)
        return out

    @property
    def flash_intensity(self) -> float:
        for effect in self._live:
            if isinstance(effect, _LiveFlash):
                return effect.intensity
        return 0.0

    @property
    def shake_intensity(self) -> float:
        for effect in self._live:
            if isinstance(effect, _LiveShake):
                return effect.intensity
        return 0.0

    @property
    def particle_count(self) -> int:
        for effect in self._live:
            if isinstance(effect, _LiveParticles):
                return effect.count
        return 0
