"""Pet behavior state machine.

Translates peon-ping events into animations. Pure Python — no Qt, no timers.
It calls a single outbound callback (`on_anim_changed`) whenever the target
anim changes; the caller decides what to do with it (typically marshal to a
GUI thread via a seam signal).

Two-state model, one registry
----------------------------
Each known session is one entry in `_SessionRegistry`, carrying a per-session
state plus a last-seen timestamp:

- IDLE:   session alive, not currently working (e.g. just after SessionStart,
          or after a Stop completed the task).
- ACTIVE: session working (UserPromptSubmit / PreToolUse / PostToolUse).

`SessionStart` adds a session (IDLE); working events flip it to ACTIVE; `Stop`
flips it back to IDLE (task done, session still alive); `SessionEnd` removes it.

Base anim is TYPING if any session is ACTIVE, else SLEEPING. So after a Stop
the pet sleeps (task done) even while the session is still open — the badge
(session count) disambiguates "no session" from "idle-but-present".
"""

from __future__ import annotations

import enum
import sys
import threading
import time
from collections.abc import Callable
from typing import final

from .config import Anim


class _SessionState(enum.Enum):
    """Per-session task state."""

    IDLE = "idle"
    ACTIVE = "active"


# Events that start a session (→ added to the registry as IDLE). Only
# SessionStart; working events below mark a session ACTIVE (and alive-if-new)
# instead.
_SESSION_START_EVENTS: frozenset[str] = frozenset({"SessionStart"})

# Events that flip a session's task to ACTIVE (→ TYPING). Also marks the
# session alive if new, so a cold start mid-session recovers on the next
# tool use instead of waiting for a SessionStart we already missed.
_TASK_ACTIVE_EVENTS: frozenset[str] = frozenset(
    {
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
    }
)

# Events that flip a session's task to IDLE (→ SLEEPING). Stop completes the
# current task but does not end the session.
_TASK_IDLE_EVENTS: frozenset[str] = frozenset({"Stop"})

# Events that end a session (→ removed from registry). Only SessionEnd.
_SESSION_END_EVENTS: frozenset[str] = frozenset({"SessionEnd"})

# Peon-ping event → transient reaction anim. Events without an entry (only
# SessionEnd) have no reaction and just settle to the base anim.
EVENT_REACTION: dict[str, Anim] = {
    "SessionStart": Anim.WAKING,
    "UserPromptSubmit": Anim.TYPING,
    "PreToolUse": Anim.TYPING,
    "PermissionRequest": Anim.ALARMED,
    "PostToolUse": Anim.TYPING,
    "PostToolUseFailure": Anim.ANNOYED,
    "PreCompact": Anim.ALARMED,
    "Stop": Anim.CELEBRATE,
}

# Every event peon-pet understands (for validation / --help listing).
KNOWN_EVENTS: frozenset[str] = frozenset(EVENT_REACTION) | _SESSION_END_EVENTS


@final
class _SessionRegistry:
    """Known sessions keyed by id, each with a state and last-seen timestamp.

    No cleanup
    runs yet — the registry grows until a SessionEnd lands, so `reconcile` is
    the seam a future timer would call. However, we have a user reconcile action
    to clear everything.

    Thread-safe via `_lock` — the registry owns its own concurrency.
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
        self.on_session_count_changed: Callable[[int], None] = _noop_count

    @property
    def session_active(self) -> bool:
        return self._sessions.count > 0

    @property
    def base_anim(self) -> Anim:
        return Anim.TYPING if self._sessions.any_active else Anim.SLEEPING

    def handle_event(self, event: str, session_id: str) -> None:
        """Process a peon-ping event, emitting the appropriate anim.

        Cold start
        -----------
        The watcher replays the last peon-ping event once on startup, when the
        registry is empty, so the pet's first event for a session arrives with
        no prior `SessionStart`. A cold start is such a first event for a session
        the registry had never tracked: detected by checking `__contains__`
        *before* the update (`cold_start`).

        Working/`Stop` events also register an unknown session (alive-if-new
        recovery, so the badge isn't 0 for a cold `Stop`), so a cold start that
        lands a session in the registry — `SessionStart`, or any working/`Stop`
        event on a new session — means a session genuinely exists now. We
        announce it with `waking` regardless of the event's own reaction, so a
        cold `Stop` doesn't spuriously celebrate and a cold working event doesn't
        jump straight to `typing` without a wake.

        The exception is a cold `SessionEnd` replay: the session was never
        tracked and `discard` leaves it absent, so there's nothing to wake for
        and nothing to reflect — it falls through to `resolve_anim`, which has
        no `SessionEnd` reaction and settles to the base anim (sleeping). Live
        events for already-tracked sessions keep their normal reaction.
        """
        if event not in KNOWN_EVENTS:
            print(f"peon-pet: unknown peon-ping event {event!r}", file=sys.stderr)
            return

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

        self.on_anim_changed(anim)
        self.on_session_count_changed(self._sessions.count)

    def resolve_anim(self, event: str) -> Anim:
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


def _noop(_anim: Anim) -> None:
    pass


def _noop_count(_n: int) -> None:
    pass
