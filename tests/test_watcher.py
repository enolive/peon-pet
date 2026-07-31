"""Tests for StateWatcher's str→Event parsing at the read boundary."""

import json
from pathlib import Path

from peon_pet.state import Event
from peon_pet.watcher import StateWatcher


def _write_state(path: Path, event: object, sid: object, ts: float) -> None:
    path.write_text(
        json.dumps(
            {"last_active": {"event": event, "session_id": sid, "timestamp": ts}}
        )
    )


def _emit_and_collect(path: Path) -> list[tuple[Event, str]]:
    seen: list[tuple[Event, str]] = []
    w = StateWatcher(path, on_event=lambda e, s: seen.append((e, s)))
    w._emit_current()
    return seen


def test_emits_typed_event_for_known_name(tmp_path: Path) -> None:
    state = tmp_path / ".state.json"
    _write_state(state, "SessionStart", "s1", 1.0)
    assert _emit_and_collect(state) == [(Event.SESSION_START, "s1")]


def test_unknown_event_name_is_skipped(tmp_path: Path) -> None:
    state = tmp_path / ".state.json"
    _write_state(state, "NotARealEvent", "s1", 1.0)
    assert _emit_and_collect(state) == []


def test_missing_event_field_is_skipped(tmp_path: Path) -> None:
    state = tmp_path / ".state.json"
    _write_state(state, None, "s1", 1.0)
    assert _emit_and_collect(state) == []
