"""Tests for PetStateMachine's typed event handling."""

from peon_pet.config import Anim
from peon_pet.state import Event, PetStateMachine


def test_cold_session_start_emits_waking() -> None:
    anims: list[Anim] = []
    counts: list[int] = []
    sm = PetStateMachine()
    sm.on_anim_changed = anims.append
    sm.on_session_count_changed = counts.append
    sm.handle_event(Event.SESSION_START, "s1")
    assert anims == [Anim.WAKING]
    assert counts == [1]
