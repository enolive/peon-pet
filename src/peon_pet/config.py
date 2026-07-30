"""Atlas layouts and animation config (pure rendering data).

Event → behavior mapping lives in state.py.
"""

from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files

ASSETS = files(__package__) / "assets"


class Anim(StrEnum):
    """Animation states — one per atlas row."""

    SLEEPING = "sleeping"
    WAKING = "waking"
    TYPING = "typing"
    ALARMED = "alarmed"
    CELEBRATE = "celebrate"
    ANNOYED = "annoyed"


@dataclass(frozen=True, slots=True)
class AtlasLayout:
    """Sprite atlas grid layout + optional border overlay filename."""

    filename: str
    cols: int
    rows: int
    border: str | None = None


@dataclass(frozen=True, slots=True)
class AnimConfig:
    """Atlas row layout for one animation."""

    row: int
    frames: int
    fps: int
    loop: bool


# Known atlases: short name -> layout. border defaults to None when absent.
ATLAS_LAYOUTS: dict[str, AtlasLayout] = {
    "2b": AtlasLayout("2b-atlas.png", 6, 6, "2b-borders.png"),
    "peon": AtlasLayout("peon-atlas.png", 6, 6),
    "orc": AtlasLayout("orc-sprite-atlas.png", 6, 6, "orc-borders.png"),
    "capybara": AtlasLayout("capybara-sprite-atlas.png", 6, 6, "capybara-borders.png"),
    "hello-kitty": AtlasLayout(
        "hello-kitty-sprite-atlas.png", 6, 6, "hello-kitty-borders.png"
    ),
    "laptop-guy": AtlasLayout("laptop-guy-atlas.png", 6, 4),
}

# Atlas row layout: anim -> config.
ANIM_CONFIG: dict[Anim, AnimConfig] = {
    Anim.SLEEPING: AnimConfig(0, 6, 3, True),
    Anim.WAKING: AnimConfig(1, 6, 8, False),
    Anim.TYPING: AnimConfig(2, 6, 8, True),
    Anim.ALARMED: AnimConfig(3, 6, 8, False),
    Anim.CELEBRATE: AnimConfig(4, 6, 8, False),
    Anim.ANNOYED: AnimConfig(5, 6, 8, False),
}
