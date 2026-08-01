"""Atlas layouts and animation config (pure rendering data).

Event -> behavior mapping lives in events.py.
"""

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
class AnimConfig:
    row: int
    frames: int
    fps: int
    loop: bool


# Known atlases: short name -> layout.
ATLAS_LAYOUTS: dict[str, AtlasLayout] = {
    "2b": AtlasLayout("2b-atlas.png", 6, 6, "2b-borders.png"),
    "orc": AtlasLayout("orc-sprite-atlas.png", 6, 6, "orc-borders.png"),
}

ANIM_CONFIG: dict[Anim, AnimConfig] = {
    Anim.SLEEPING: AnimConfig(0, 6, 3, True),
    Anim.WAKING: AnimConfig(1, 6, 8, False),
    Anim.TYPING: AnimConfig(2, 6, 8, True),
    Anim.ALARMED: AnimConfig(3, 6, 8, False),
    Anim.CELEBRATE: AnimConfig(4, 6, 8, False),
    Anim.ANNOYED: AnimConfig(5, 6, 8, False),
}
