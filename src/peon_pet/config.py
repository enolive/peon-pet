"""Atlas layouts and animation config (pure rendering data).

Event -> behavior mapping lives in events.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files

ASSETS = files(__package__) / "assets"
ICONS = files(__package__) / "icons"


class Anim(StrEnum):
    """Animation states - one per atlas row."""

    SLEEPING = "sleeping"
    WAKING = "waking"
    TYPING = "typing"
    ALARMED = "alarmed"
    CELEBRATE = "celebrate"
    ANNOYED = "annoyed"


@dataclass(frozen=True, slots=True)
class AtlasLayout:
    filename: str
    cols: int
    rows: int
    border: str


@dataclass(frozen=True, slots=True)
class Rgba:
    """Float channels in 0..1 (legacy shader space)."""

    r: float
    g: float
    b: float
    a: float

    @classmethod
    def from_hex(cls, color: str, *, a: float = 1.0) -> Rgba:
        s = color.removeprefix("#")
        if len(s) != 6:
            raise ValueError(f"expected RRGGBB hex color, got {color!r}")
        try:
            r = int(s[0:2], 16) / 255.0
            g = int(s[2:4], 16) / 255.0
            b = int(s[4:6], 16) / 255.0
        except ValueError:
            raise ValueError(f"expected RRGGBB hex color, got {color!r}") from None
        return cls(r, g, b, a)


@dataclass(frozen=True, slots=True)
class FlashConfig:
    color: Rgba
    decay: float


@dataclass(frozen=True, slots=True)
class ShakeConfig:
    intensity: float
    decay: float


@dataclass(frozen=True, slots=True)
class ParticleConfig:
    count: int
    duration: float


EffectSpec = FlashConfig | ShakeConfig | ParticleConfig


@dataclass(frozen=True, slots=True, kw_only=True)
class AnimConfig:
    row: int
    frames: int
    fps: int
    loop: bool
    effects: tuple[EffectSpec, ...] = ()


# Known atlases: short name -> layout.
ATLAS_LAYOUTS: dict[str, AtlasLayout] = {
    "2b": AtlasLayout("2b-atlas.png", 6, 6, "2b-borders.png"),
    "orc": AtlasLayout("orc-sprite-atlas.png", 6, 6, "orc-borders.png"),
}

ANIM_CONFIG: dict[Anim, AnimConfig] = {
    Anim.SLEEPING: AnimConfig(row=0, frames=6, fps=3, loop=True),
    Anim.WAKING: AnimConfig(
        row=1,
        frames=6,
        fps=8,
        loop=False,
        effects=(FlashConfig(Rgba.from_hex("#66CCFF", a=0.3), 2.0),),
    ),
    Anim.TYPING: AnimConfig(row=2, frames=6, fps=8, loop=True),
    Anim.ALARMED: AnimConfig(
        row=3,
        frames=6,
        fps=8,
        loop=False,
        effects=(FlashConfig(Rgba.from_hex("#FF1A1A", a=0.5), 2.5),),
    ),
    Anim.CELEBRATE: AnimConfig(
        row=4,
        frames=6,
        fps=8,
        loop=False,
        effects=(
            FlashConfig(Rgba.from_hex("#FFCC00", a=0.5), 2.0),
            ParticleConfig(count=30, duration=1.2),
        ),
    ),
    Anim.ANNOYED: AnimConfig(
        row=5,
        frames=6,
        fps=8,
        loop=False,
        effects=(
            FlashConfig(Rgba.from_hex("#CC6600", a=0.3), 2.0),
            ShakeConfig(12.0, 8.0),
        ),
    ),
}
