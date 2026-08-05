"""Reaction-effect helpers (flash/shake/particles)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

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
