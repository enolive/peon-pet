"""Pet behavior state machine - translates peon-ping events into anims.

Pure Python, no Qt: emits via callbacks; the caller marshals to the GUI thread.
Two-state model: each known session is IDLE or ACTIVE. Base anim is TYPING if
any session is ACTIVE, else SLEEPING, so after a Stop the pet sleeps even while
the session is still open; the badge (session count) disambiguates "no session"
from "idle-but-present".
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
    IDLE = "idle"
    ACTIVE = "active"


# Events that start a session (-> added to the registry as IDLE). Only
# SessionStart; working events below mark a session ACTIVE (and alive-if-new)
# instead.
_SESSION_START_EVENTS: frozenset[Event] = frozenset({Event.SESSION_START})

# Events that flip a session's task to ACTIVE (-> TYPING). Also marks the
# session alive if new, so a cold start mid-session recovers on the next
# tool use instead of waiting for a SessionStart we already missed.
_TASK_ACTIVE_EVENTS: frozenset[Event] = frozenset(
    {
        Event.USER_PROMPT_SUBMIT,
        Event.PRE_TOOL_USE,
        Event.POST_TOOL_USE,
    }
)

# Events that flip a session's task to IDLE (-> SLEEPING). Stop completes the
# current task but does not end the session.
_TASK_IDLE_EVENTS: frozenset[Event] = frozenset({Event.STOP})

# Events that end a session (-> removed from registry). Only SessionEnd.
_SESSION_END_EVENTS: frozenset[Event] = frozenset({Event.SESSION_END})


@final
class _SessionRegistry:
    """Grows until a SessionEnd lands; no cleanup timer yet."""

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[_SessionState, float]] = {}
        self._lock = threading.Lock()

    def apply(self, event: Event, session_id: str) -> tuple[bool, bool, int]:
        # Apply one event to the registry and return (cold_start, added, count)
        # under a single lock so callers can decide an anim and emit a count from
        # the same snapshot that can't be torn by a concurrent clear()/on_finished().
        # `added` is post-mutation membership: False for SessionEnd (it removes)
        # and for events that keep a known session (set_active/set_idle refresh
        # but don't add).
        with self._lock:
            cold_start = session_id not in self._sessions
            if event in _SESSION_START_EVENTS:
                self._add(cold_start, session_id)
            elif event in _TASK_ACTIVE_EVENTS:
                self._set_active(session_id)
            elif event in _TASK_IDLE_EVENTS:
                self._set_idle(session_id)
            elif event in _SESSION_END_EVENTS:
                self._discard(session_id)
            added = session_id in self._sessions
            return cold_start, added, len(self._sessions)

    def _add(self, cold_start: bool, session_id: str):
        # Create-only: a redundant SessionStart for a known session must
        # not downgrade it (an ACTIVE session mid-task would otherwise
        # flip to IDLE, and on_finished would settle to SLEEPING while
        # the session is still running). Refresh last-seen either way.
        if cold_start:
            self._set_idle(session_id)
        else:
            state, _ = self._sessions[session_id]
            self._sessions[session_id] = (state, time.time())

    def _set_idle(self, session_id: str):
        self._sessions[session_id] = (_SessionState.IDLE, time.time())

    def _set_active(self, session_id: str):
        self._sessions[session_id] = (_SessionState.ACTIVE, time.time())

    def _discard(self, session_id: str):
        _ = self._sessions.pop(session_id, None)

    @property
    def count(self) -> int:
        # The badge value.
        with self._lock:
            return len(self._sessions)

    @property
    def any_active(self) -> bool:
        # Drives the base anim (TYPING when True).
        with self._lock:
            return any(
                state is _SessionState.ACTIVE for state, _ in self._sessions.values()
            )

    def clear(self) -> bool:
        with self._lock:
            had_any = bool(self._sessions)
            self._sessions.clear()
            return had_any


@final
class PetStateMachine:
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
        cold_start, added, count = self._sessions.apply(event, session_id)
        if cold_start and added:
            # Cold start: the watcher replayed the last peon-ping event on an
            # unknown session. Override the reaction to WAKING so a cold Stop
            # doesn't spuriously celebrate and a cold working event doesn't skip
            # the wake. A cold SessionEnd (nothing to wake) settles to base.
            anim = Anim.WAKING
        else:
            anim = self.resolve_anim(event)

        logger.debug(
            "event=%s sid=%s cold=%s -> anim=%s count=%d",
            event,
            session_id,
            cold_start,
            anim,
            count,
        )

        self.on_anim_changed(anim)
        self.on_session_count_changed(count)

    def resolve_anim(self, event: Event) -> Anim:
        reaction = EVENT_REACTION.get(event)
        anim = self.base_anim if reaction is None else reaction
        return anim

    def on_finished(self) -> None:
        self.on_anim_changed(self.base_anim)

    def clear(self) -> None:
        if self._sessions.clear():
            self.on_anim_changed(self.base_anim)
        self.on_session_count_changed(self._sessions.count)


def _noop(*_a: object) -> None:
    pass
