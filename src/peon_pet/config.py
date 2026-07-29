"""Atlas layouts, animation config, and event mapping."""

from enum import StrEnum
from importlib.resources import files

ASSETS = files(__package__) / "assets"


class Anim(StrEnum):
    """Animation states — one per atlas row."""
    SLEEPING = 'sleeping'
    WAKING = 'waking'
    TYPING = 'typing'
    ALARMED = 'alarmed'
    CELEBRATE = 'celebrate'
    ANNOYED = 'annoyed'

# Known atlases: short name -> (filename, cols, rows, border_filename).
# border_filename is None when no border asset exists for that atlas.
ATLAS_LAYOUTS: dict[str, tuple[str, int, int, str | None]] = {
    "peon":        ("peon-atlas.png",               6, 6, None),
    "orc":         ("orc-sprite-atlas.png",         6, 6, "orc-borders.png"),
    "capybara":    ("capybara-sprite-atlas.png",    6, 6, "capybara-borders.png"),
    "hello-kitty": ("hello-kitty-sprite-atlas.png", 6, 6, "hello-kitty-borders.png"),
    "laptop-guy":  ("laptop-guy-atlas.png",          6, 4, None),
}

# Atlas row layout: anim -> (row, frames, fps, loop)
ANIM_CONFIG: dict[Anim, tuple[int, int, int, bool]] = {
    Anim.SLEEPING:  (0, 6, 3, True),
    Anim.WAKING:    (1, 6, 8, False),
    Anim.TYPING:    (2, 6, 8, False),
    Anim.ALARMED:   (3, 6, 8, False),
    Anim.CELEBRATE: (4, 6, 8, False),
    Anim.ANNOYED:   (5, 6, 8, False),
}

# OG peon-ping/Claude hook event names -> animation
EVENT_TO_ANIM: dict[str, Anim] = {
    'SessionStart':       Anim.WAKING,
    'UserPromptSubmit':   Anim.TYPING,
    'PermissionRequest':  Anim.ALARMED,
    'PreCompact':         Anim.ALARMED,
    'Stop':               Anim.CELEBRATE,
    'PostToolUseFailure': Anim.ANNOYED,
}
