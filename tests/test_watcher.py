"""Tests for StateWatcher's str→Event parsing at the read boundary."""

import json
from pathlib import Path

from peon_pet.state import Event
from peon_pet.watcher import StateWatcher


def test_emits_typed_event_for_known_name(tmp_path: Path) -> None:
    state = tmp_path / ".state.json"
    _write_state_to_file(state, "SessionStart", "s1", 1.0)

    seen = _emit_and_collect(state)

    assert seen == [(Event.SESSION_START, "s1")]


def test_unknown_event_name_is_skipped(tmp_path: Path) -> None:
    state = tmp_path / ".state.json"
    _write_state_to_file(state, "NotARealEvent", "s1", 1.0)

    seen = _emit_and_collect(state)

    assert seen == []


def test_missing_event_field_is_skipped(tmp_path: Path) -> None:
    state = tmp_path / ".state.json"
    _write_state_to_file(state, None, "s1", 1.0)

    seen = _emit_and_collect(state)

    assert seen == []


def _write_state_to_file(path: Path, event: object, sid: object, ts: float) -> None:
    path.write_text(
        json.dumps(
            {"last_active": {"event": event, "session_id": sid, "timestamp": ts}}
        )
    )


def _emit_and_collect(path: Path) -> list[tuple[Event, str]]:
    seen: list[tuple[Event, str]] = []
    w = StateWatcher(path, on_event=lambda e, s: seen.append((e, s)))
    # TODO: potential code smell: we use the internal api here to like as the subject under test
    #   review this after tests in watcher are done
    w._emit_current()
    return seen
