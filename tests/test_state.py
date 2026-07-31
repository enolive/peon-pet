"""Tests for PetStateMachine's typed event handling."""

import pytest

from peon_pet.config import Anim
from peon_pet.state import EVENT_REACTION, Event, PetStateMachine

# Cold-start: the watcher replays the last peon-ping event once on startup with
# an empty registry. A cold event that registers a session announces `waking`
# regardless of its own reaction; a cold SessionEnd (nothing to wake) settles to
# the base anim (sleeping).
_COLD_START_CASES: list[Event] = [
    Event.SESSION_START,
    Event.USER_PROMPT_SUBMIT,
    Event.PRE_TOOL_USE,
    Event.POST_TOOL_USE,
    Event.STOP,
]


@pytest.mark.parametrize(
    "event",
    _COLD_START_CASES,
)
def test_cold_start_from_regular_event_results_win_waking(event: Event) -> None:
    sm, anims, counts = _wire_state_machine_with_recording_callbacks()

    sm.handle_event(event, "s1")

    assert anims == [Anim.WAKING]
    assert counts == [1], "because we expect a session to be added"


def test_cold_start_from_session_end_results_in_sleeping() -> None:
    sm, anims, counts = _wire_state_machine_with_recording_callbacks()

    sm.handle_event(Event.SESSION_END, "s1")

    assert anims == [Anim.SLEEPING]
    assert counts == [0], "because we expect that no session was added"


@pytest.mark.parametrize(
    ("event", "anim"),
    [(e, EVENT_REACTION[e]) for e in EVENT_REACTION],
)
def test_warm_event_emits_its_reaction(event: Event, anim: Anim) -> None:
    sm, anims, _counts = _wire_state_machine_with_recording_callbacks()
    sm.handle_event(Event.SESSION_START, "s1")  # warm the session (IDLE)
    anims.clear()

    sm.handle_event(event, "s1")

    assert anims == [anim]


def test_working_event_flips_active_and_emits_typing() -> None:
    sm, anims, _counts = _wire_state_machine_with_recording_callbacks()
    sm.handle_event(Event.SESSION_START, "s1")  # IDLE
    anims.clear()

    sm.handle_event(Event.USER_PROMPT_SUBMIT, "s1")  # → ACTIVE

    assert anims == [Anim.TYPING]
    assert sm.base_anim == Anim.TYPING


def test_stop_flips_idle_celebrates_then_sleeps() -> None:
    sm, anims, _counts = _wire_state_machine_with_recording_callbacks()
    sm.handle_event(Event.SESSION_START, "s1")
    sm.handle_event(Event.USER_PROMPT_SUBMIT, "s1")  # ACTIVE
    anims.clear()

    sm.handle_event(Event.STOP, "s1")  # → IDLE, reaction CELEBRATE

    assert anims == [Anim.CELEBRATE]
    assert sm.base_anim == Anim.SLEEPING
    anims.clear()

    sm.on_finished()

    assert anims == [Anim.SLEEPING]


def test_on_finished_settles_to_typing_when_a_session_is_active() -> None:
    sm, anims, _counts = _wire_state_machine_with_recording_callbacks()
    sm.handle_event(Event.SESSION_START, "s1")
    sm.handle_event(Event.USER_PROMPT_SUBMIT, "s1")  # ACTIVE
    sm.handle_event(Event.PERMISSION_REQUEST, "s1")  # one-shot ALARMED
    sm.handle_event(Event.POST_TOOL_USE, "s1")  # one-shot ALARMED
    anims.clear()

    sm.on_finished()

    assert anims == [Anim.TYPING]


def test_session_end_removes_session_and_settles_to_sleeping() -> None:
    sm, anims, counts = _wire_state_machine_with_recording_callbacks()
    sm.handle_event(Event.SESSION_START, "s1")

    assert sm.session_active
    counts.clear()
    anims.clear()

    sm.handle_event(Event.SESSION_END, "s1")

    assert counts == [0], "because an ending session does not add to the session count"
    assert anims == [Anim.SLEEPING]
    assert not sm.session_active
    assert sm.base_anim == Anim.SLEEPING


def test_clear_emits_only_when_a_session_was_known() -> None:
    sm, anims, counts = _wire_state_machine_with_recording_callbacks()
    sm.handle_event(Event.SESSION_START, "s1")
    anims.clear()
    counts.clear()

    sm.clear()

    assert anims == [Anim.SLEEPING]
    assert counts == [0]
    assert not sm.session_active


def test_clear_on_empty_emits_count_but_no_anim() -> None:
    sm, anims, counts = _wire_state_machine_with_recording_callbacks()

    sm.clear()

    assert anims == []
    assert counts == [0]


def test_resolve_anim_falls_back_to_base_for_session_end() -> None:
    sm, _anims, _counts = _wire_state_machine_with_recording_callbacks()

    # Empty registry → base SLEEPING; SessionEnd has no reaction entry.
    assert sm.resolve_anim(Event.SESSION_END) == Anim.SLEEPING

    sm.handle_event(Event.SESSION_START, "s1")
    sm.handle_event(Event.USER_PROMPT_SUBMIT, "s1")  # ACTIVE → base TYPING

    assert sm.resolve_anim(Event.SESSION_END) == Anim.TYPING


def _wire_state_machine_with_recording_callbacks() -> tuple[
    PetStateMachine, list[Anim], list[int]
]:
    """Wire a state machine with recording callbacks; return (sm, anims, counts)."""
    anims: list[Anim] = []
    counts: list[int] = []
    sm = PetStateMachine()
    sm.on_anim_changed = anims.append
    sm.on_session_count_changed = counts.append
    return sm, anims, counts
