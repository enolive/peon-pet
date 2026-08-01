"""Tests for the Event enum and its str->Event parsing."""

import pytest

from peon_pet.events import EVENT_REACTION, KNOWN_EVENTS, Event


@pytest.mark.parametrize("name", [e.value for e in Event])
def test_from_name_round_trips_known(name: str) -> None:
    assert Event.from_name(name) is not None


def test_from_name_returns_none_for_unknown() -> None:
    assert Event.from_name("NotARealEvent") is None


def test_from_name_returns_none_for_empty() -> None:
    assert Event.from_name("") is None


def test_every_event_is_known() -> None:
    assert set(Event) <= KNOWN_EVENTS


def test_session_end_has_no_transient_reaction() -> None:
    assert Event.SESSION_END not in EVENT_REACTION
