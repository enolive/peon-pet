"""Pet behavior state machine.

Translates peon-ping events into animations. Pure Python — no Qt, no timers.
It calls a single outbound callback (`on_anim_changed`) whenever the target
anim changes; the caller decides what to do with it (typically marshal to a
GUI thread via a seam signal).

Session model
-------------
- IDLE:    no session active — base anim is SLEEPING.
- WORKING: at least one session is active — base anim is TYPING.

SessionStart / working events (tool use, prompt submit) add the session to
the active set; Stop / SessionEnd remove *that session only*. Each session's
last-seen timestamp is recorded (local `time.time()`), so a future staleness
sweep can reap sessions whose end event was lost. Multiple concurrent agents
are tracked correctly: one session finishing does not zero the liveness flag
for the others.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from typing import final

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
    'SessionStart': Anim.WAKING,
    'UserPromptSubmit': Anim.TYPING,
    'PreToolUse': Anim.TYPING,
    'PostToolUse': Anim.TYPING,
    'PermissionRequest': Anim.ALARMED,
    'PreCompact': Anim.ALARMED,
    'PostToolUseFailure': Anim.ANNOYED,
    'Stop': Anim.CELEBRATE,
}

# Every event peon-pet understands (for validation / --help listing).
KNOWN_EVENTS: frozenset[str] = frozenset(EVENT_REACTION) | _SESSION_END_EVENTS


@final
class _SessionRegistry:
    """Active sessions keyed by id, with last-seen timestamps.

    Timestamps are local `time.time()` readings taken when a session touches
    the registry. They enable a future staleness sweep to reap sessions whose
    end event was lost. No cleanup runs yet — the registry grows until a
    Stop/SessionEnd lands, so `reconcile` is the seam a future timer would call.

    Thread-safe via `_lock` — the registry owns its own concurrency because the
    lock guards its `sessions` dict. Callers (`PetStateMachine.handle_event`,
    `on_finished`, future `reconcile`) don't take the lock; they call these
    methods, which do. Reads via `active` also take the lock so they observe a
    consistent snapshot.
    """

    def __init__(self) -> None:
        self.sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, session_id: str) -> None:
        with self._lock:
            self.sessions[session_id] = time.time()

    def discard(self, session_id: str) -> None:
        with self._lock:
            self.sessions.pop(session_id, None)

    @property
    def active(self) -> bool:
        with self._lock:
            return bool(self.sessions)

    def clear(self) -> bool:
        with self._lock:
            was_active = bool(self.sessions)
            self.sessions.clear()
            return was_active


@final
class PetStateMachine:
    """Owns the active-session registry and emits anim transitions via callback.

    - Base anim is SLEEPING when the registry is empty, TYPING otherwise.
    - `handle_event` updates the registry then calls `on_anim_changed` with
      either the transient reaction anim or, for SessionEnd, the base anim.
    - `on_finished` is called by the window when a one-shot reaction has played
      out `loops` times; it calls `on_anim_changed` with the base anim to settle.

    Thread-safe via `_lock`: `handle_event` is driven from the watcher's daemon
    thread, `on_finished` from the GUI thread (via window.finished). The lock
    lives on the registry — `handle_event` and `on_finished` call registry
    methods that lock internally, and read `base_anim` (which goes through the
    registry's locked `active`). The `on_anim_changed` callback fires after the
    registry method returns (lock released), so a callback that re-entered state
    wouldn't deadlock.
    """

    def __init__(self) -> None:
        self._sessions = _SessionRegistry()
        self.on_anim_changed: Callable[[Anim], None] = _noop

    @property
    def session_active(self) -> bool:
        return self._sessions.active

    @property
    def base_anim(self) -> Anim:
        return Anim.TYPING if self._sessions.active else Anim.SLEEPING

    def handle_event(self, event: str, session_id: str) -> None:
        """Process a peon-ping event, emitting the appropriate anim."""
        if event not in KNOWN_EVENTS:
            print(f"peon-pet: unknown peon-ping event {event!r}", file=sys.stderr)
            return

        # Update the active-session registry first — it determines the base
        # anim reactions return to. End events remove only the emitting session.
        # The registry's methods lock internally.
        if event in _SESSION_ACTIVE_EVENTS:
            self._sessions.add(session_id)
        elif event in _SESSION_END_EVENTS:
            self._sessions.discard(session_id)

        # Decide the anim to emit. (Mutation and this read are both locked at the
        # registry level, not as one atomic op across both — a concurrent event
        # could land between them. That's benign: the window plays this anim and
        # the next event overrides, same as any event-driven UI.)
        reaction = EVENT_REACTION.get(event)
        anim = self.base_anim if reaction is None else reaction

        # Emit outside the lock — the callback (a Qt signal emit) is non-blocking,
        # and not holding the lock means a callback that re-entered state wouldn't deadlock.
        self.on_anim_changed(anim)

    def on_finished(self) -> None:
        """Called when the window finishes playing a transient reaction."""
        self.on_anim_changed(self.base_anim)

    def clear(self) -> None:
        """Reset the state to idle."""
        if self._sessions.clear():
            self.on_anim_changed(self.base_anim)


def _noop(_anim: Anim) -> None:
    pass
