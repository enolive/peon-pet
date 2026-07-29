"""Pet behavior state machine.

Translates peon-ping events into animations. Purely reactive: it owns no
timers. The window owns animation timing (looping, one-shot duration) and
emits `finished` when a transient reaction has played out; this machine then
emits the current base anim.

Session model
-------------
- IDLE:    no session active — base anim is SLEEPING.
- WORKING: a session is running — base anim is TYPING.

SessionStart / working events (tool use, prompt submit) mark the session
active; SessionEnd marks it idle. Stop is *not* a session end — it's just a
task-complete reaction, so the pet returns to typing (not sleeping) afterwards.
"""

from __future__ import annotations

import sys
from typing import final

from PyQt6 import QtCore

from .config import Anim

# Events that mark a session as active (→ WORKING). The working events are
# included so a cold start mid-session recovers on the next tool use instead of
# waiting for a SessionStart we already missed.
_SESSION_ACTIVE_EVENTS: frozenset[str] = frozenset({
    'SessionStart',
    'UserPromptSubmit',
    'PreToolUse',
    'PostToolUse',
})

# Events that end a session (→ IDLE).
_SESSION_END_EVENTS: frozenset[str] = frozenset({'SessionEnd', 'Stop'})

# Peon-ping event → transient reaction anim. Events without an entry (only
# SessionEnd) have no reaction and just settle to the base anim.
EVENT_REACTION: dict[str, Anim] = {
    'SessionStart':       Anim.WAKING,
    'UserPromptSubmit':   Anim.TYPING,
    'PreToolUse':         Anim.TYPING,
    'PostToolUse':        Anim.TYPING,
    'PermissionRequest':  Anim.ALARMED,
    'PreCompact':         Anim.ALARMED,
    'PostToolUseFailure': Anim.ANNOYED,
    'Stop':               Anim.CELEBRATE,
}

# Every event peon-pet understands (for validation / --help listing).
KNOWN_EVENTS: frozenset[str] = frozenset(EVENT_REACTION) | _SESSION_END_EVENTS


@final
class PetStateMachine(QtCore.QObject):
    """Owns session liveness and emits anim transitions for the window.

    - Base anim is SLEEPING when idle, TYPING when a session is active.
    - A transient reaction is emitted on its event; the window plays it
      `loops` times, then emits `finished`, which routes back here to settle on
      the base anim.
    - Events whose reaction equals the base anim (e.g. UserPromptSubmit while
      working → typing) skip the finished round-trip — they just play the base.
    """

    anim_changed = QtCore.pyqtSignal(Anim)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.session_active: bool = False

    @property
    def base_anim(self) -> Anim:
        return Anim.TYPING if self.session_active else Anim.SLEEPING

    def handle_event(self, event: str) -> None:
        """Process a peon-ping event, emitting the appropriate anim."""
        if event not in KNOWN_EVENTS:
            print(f"peon-pet: unknown peon-ping event {event!r}", file=sys.stderr)
            return

        # Update session mode first — it determines the base anim reactions return to.
        if event in _SESSION_ACTIVE_EVENTS:
            self.session_active = True
        elif event in _SESSION_END_EVENTS:
            self.session_active = False

        reaction = EVENT_REACTION.get(event)
        # No transient reaction (SessionEnd) — settle straight to the base anim.
        if reaction is None:
            self.anim_changed.emit(self.base_anim)
            return

        # Transient reaction — the window plays it `loops` times, then emits
        # `finished`, which routes back here to settle on the base anim.
        self.anim_changed.emit(reaction)

    def on_finished(self) -> None:
        """Called when the window finishes playing a transient reaction."""
        self.anim_changed.emit(self.base_anim)
