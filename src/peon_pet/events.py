"""Peon-ping event vocabulary - the `Event` enum and its reaction mapping."""

from __future__ import annotations

from enum import StrEnum

from .config import Anim


class Event(StrEnum):
    """Peon-ping hook events (the OG names) that the pet reacts to."""

    SESSION_START = "SessionStart"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    PERMISSION_REQUEST = "PermissionRequest"
    PRE_COMPACT = "PreCompact"
    STOP = "Stop"
    SESSION_END = "SessionEnd"

    @staticmethod
    def from_name(name: str) -> Event | None:
        """Parse a peon-ping event name, or None if unknown."""
        try:
            return Event(name)
        except ValueError:
            return None


# Peon-ping event -> transient reaction anim. Events without an entry (only
# SessionEnd) have no reaction and just settle to the base anim.
EVENT_REACTION: dict[Event, Anim] = {
    Event.SESSION_START: Anim.WAKING,
    Event.USER_PROMPT_SUBMIT: Anim.TYPING,
    Event.PRE_TOOL_USE: Anim.TYPING,
    Event.PERMISSION_REQUEST: Anim.ALARMED,
    Event.POST_TOOL_USE: Anim.TYPING,
    Event.POST_TOOL_USE_FAILURE: Anim.ANNOYED,
    Event.PRE_COMPACT: Anim.ALARMED,
    Event.STOP: Anim.CELEBRATE,
}

# Every event peon-pet understands (for validation / --list-events listing).
# SessionEnd has no transient reaction, so it's not in EVENT_REACTION.
KNOWN_EVENTS: frozenset[Event] = frozenset(EVENT_REACTION) | {Event.SESSION_END}
