"""Atlas layouts, animation config, and event mapping."""

from importlib.resources import files

ASSETS = files(__package__) / "assets"

# Known atlases: short name -> (filename, cols, rows). Add new atlases here.
ATLAS_LAYOUTS = {
    "peon":        ("peon-atlas.png",               6, 6),
    "orc":         ("orc-sprite-atlas.png",         6, 6),
    "capybara":    ("capybara-sprite-atlas.png",    6, 6),
    "hello-kitty": ("hello-kitty-sprite-atlas.png", 6, 6),
    "laptop-guy":  ("laptop-guy-atlas.png",          6, 4),
}

# Atlas row layout: anim name -> (row, frames, fps, loop)
ANIM_CONFIG = {
    'sleeping':  (0, 6, 3, True),
    'waking':    (1, 6, 8, False),
    'typing':    (2, 6, 8, False),
    'alarmed':   (3, 6, 8, False),
    'celebrate': (4, 6, 8, False),
    'annoyed':   (5, 6, 8, False),
}

# OG peon-ping/Claude hook event names -> animation
EVENT_TO_ANIM = {
    'SessionStart':       'waking',
    'UserPromptSubmit':   'typing',
    'PermissionRequest':  'alarmed',
    'PreCompact':         'alarmed',
    'Stop':               'celebrate',
    'PostToolUseFailure': 'annoyed',
}
