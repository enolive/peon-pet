"""Reaction-effect helpers (flash/shake decay + offsets; particles later)."""

from __future__ import annotations

import random


def decay_linear(value: float, dt: float, rate: float) -> float:
    return max(0.0, value - dt * rate)


def shake_offset(intensity: float, rng: random.Random) -> tuple[float, float]:
    if intensity <= 0.0:
        return (0.0, 0.0)
    return ((rng.random() - 0.5) * intensity, (rng.random() - 0.5) * intensity)
