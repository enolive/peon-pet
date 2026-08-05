"""Reaction-effect helpers (flash decay now; particles/shake later)."""

from __future__ import annotations


def decay_flash(intensity: float, dt: float, decay: float) -> float:
    return max(0.0, intensity - dt * decay)
