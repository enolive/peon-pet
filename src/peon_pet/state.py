"""Pet behavior state machine — translates peon-ping events into anims.
Pure Python, no Qt: emits via callbacks; the caller marshals to the GUI thread.

Two-state model: each known session is IDLE or ACTIVE. Base anim is TYPING if
any session is ACTIVE, else SLEEPING — so after a Stop the pet sleeps even
while the session is still open, and the badge (session count) disambiguates
"no session" from "idle-but-present".
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from collections.abc import Callable
from typing import final

from .config import Anim
from .events import EVENT_REACTION, Event

logger = logging.getLogger(__name__)


class _SessionState(enum.Enum):
    """Per-session task state."""

    IDLE = "idle"
    ACTIVE = "active"


# Events that start a session (→ added to the registry as IDLE). Only
# SessionStart; working events below mark a session ACTIVE (and alive-if-new)
# instead.
_SESSION_START_EVENTS: frozenset[Event] = frozenset({Event.SESSION_START})

# Events that flip a session's task to ACTIVE (→ TYPING). Also marks the
# session alive if new, so a cold start mid-session recovers on the next
# tool use instead of waiting for a SessionStart we already missed.
_TASK_ACTIVE_EVENTS: frozenset[Event] = frozenset(
    {
        Event.USER_PROMPT_SUBMIT,
        Event.PRE_TOOL_USE,
        Event.POST_TOOL_USE,
    }
)

# Events that flip a session's task to IDLE (→ SLEEPING). Stop completes the
# current task but does not end the session.
_TASK_IDLE_EVENTS: frozenset[Event] = frozenset({Event.STOP})

# Events that end a session (→ removed from registry). Only SessionEnd.
_SESSION_END_EVENTS: frozenset[Event] = frozenset({Event.SESSION_END})


@final
class _SessionRegistry:
    """Known sessions keyed by id, each with a state and last-seen timestamp.

    No cleanup runs yet — the registry grows until a SessionEnd lands, so
    `reconcile` is the seam a future timer would call. (There's a user action to
    clear everything.) Thread-safe via `_lock`.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[_SessionState, float]] = {}
        self._lock = threading.Lock()

    def add(self, session_id: str) -> None:
        """Mark a session alive (IDLE). Touches its last-seen timestamp."""
        with self._lock:
            self._sessions[session_id] = (_SessionState.IDLE, time.time())

    def set_active(self, session_id: str) -> None:
        """Flip a session's task to ACTIVE. Marks it alive if new."""
        with self._lock:
            self._sessions[session_id] = (_SessionState.ACTIVE, time.time())

    def set_idle(self, session_id: str) -> None:
        """Flip a session's task to IDLE (task done, session still alive).

        Registers the session if unknown: a cold-start replay of e.g. `Stop`
        must still track the session (the watcher saw it), so the badge reflects
        it.
        """
        with self._lock:
            self._sessions[session_id] = (_SessionState.IDLE, time.time())

    def discard(self, session_id: str) -> None:
        """Remove a session (SessionEnd)."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def __contains__(self, session_id: str) -> bool:
        """Whether a session is currently known. Used by the state machine to
        detect a cold-start replay of a stale event."""
        with self._lock:
            return session_id in self._sessions

    @property
    def count(self) -> int:
        """Number of known (alive) sessions — the badge value."""
        with self._lock:
            return len(self._sessions)

    @property
    def any_active(self) -> bool:
        """Whether any session is ACTIVE — drives the base anim (TYPING)."""
        with self._lock:
            return any(
                state is _SessionState.ACTIVE for state, _ in self._sessions.values()
            )

    def clear(self) -> bool:
        """Wipe all sessions. Returns whether any were known (for emit-on-change)."""
        with self._lock:
            had_any = bool(self._sessions)
            self._sessions.clear()
            return had_any


@final
class PetStateMachine:
    """
    State machine that transfers session state and
    gets the overall state for playing the correct animations.
    """

    def __init__(self) -> None:
        self._sessions = _SessionRegistry()
        self.on_anim_changed: Callable[[Anim], None] = _noop
        self.on_session_count_changed: Callable[[int], None] = _noop

    @property
    def session_active(self) -> bool:
        return self._sessions.count > 0

    @property
    def base_anim(self) -> Anim:
        return Anim.TYPING if self._sessions.any_active else Anim.SLEEPING

    def handle_event(self, event: Event, session_id: str) -> None:
        """Process a peon-ping event, emitting the appropriate anim.

        On a cold start (first event for an unknown session), the reaction is
        overridden to `WAKING` regardless of the event's own reaction — so a cold
        `Stop` doesn't spuriously celebrate and a cold working event doesn't
        skip the wake. A cold `SessionEnd` (nothing to wake) settles to base.
        """
        cold_start = session_id not in self._sessions

        # Update the single registry — liveness and task state together.
        if event in _SESSION_START_EVENTS:
            self._sessions.add(session_id)
        elif event in _TASK_ACTIVE_EVENTS:
            self._sessions.set_active(session_id)
        elif event in _TASK_IDLE_EVENTS:
            self._sessions.set_idle(session_id)
        elif event in _SESSION_END_EVENTS:
            self._sessions.discard(session_id)

        was_session_added = session_id in self._sessions
        if cold_start and was_session_added:
            anim = Anim.WAKING
        else:
            anim = self.resolve_anim(event)

        logger.debug(
            "event=%s sid=%s cold=%s → anim=%s count=%d",
            event,
            session_id,
            cold_start,
            anim,
            self._sessions.count,
        )

        self.on_anim_changed(anim)
        self.on_session_count_changed(self._sessions.count)

    def resolve_anim(self, event: Event) -> Anim:
        """
        Transforms the given event into an animation.
        Falls back to base anim which depends on the overall session state.
        """
        reaction = EVENT_REACTION.get(event)
        anim = self.base_anim if reaction is None else reaction
        return anim

    def on_finished(self) -> None:
        """Called when the window finishes playing a transient reaction."""
        self.on_anim_changed(self.base_anim)

    def clear(self) -> None:
        """Reset the state to idle."""
        if self._sessions.clear():
            self.on_anim_changed(self.base_anim)
        self.on_session_count_changed(self._sessions.count)


def _noop(*_a: object) -> None:
    pass
