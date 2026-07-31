"""Tests for StateWatcher's str→Event parsing at the read boundary."""

import json
import os
from pathlib import Path

from peon_pet.state import Event
from peon_pet.watcher import StateWatcher


def test_emits_typed_event_for_known_name(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    sut = WatcherDriver(state_path)

    sut.emit_current()

    assert sut.seen == [(Event.SESSION_START, "s1")]


def test_unknown_event_name_is_skipped(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "NotARealEvent", "s1", 1.0)
    sut = WatcherDriver(state_path)

    sut.emit_current()

    assert sut.seen == []


def test_missing_event_field_is_skipped(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, None, "s1", 1.0)
    sut = WatcherDriver(state_path)

    sut.emit_current()

    assert sut.seen == []


def test_poll_does_not_reemit_when_mtime_unchanged(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    sut = WatcherDriver(state_path)
    sut.emit_current()
    assert sut.seen == [(Event.SESSION_START, "s1")]
    sut.seen.clear()

    sut.poll()

    assert sut.seen == []


def test_poll_suppresses_when_mtime_changed_but_timestamp_equal(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    _set_mtime(state_path, 1000.0)
    sut = WatcherDriver(state_path)
    sut.emit_current()
    assert sut.seen == [(Event.SESSION_START, "s1")]
    sut.seen.clear()
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    _set_mtime(state_path, 2000.0)

    sut.poll()

    assert sut.seen == []


def test_poll_emits_when_mtime_and_timestamp_newer(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    _set_mtime(state_path, 1000.0)
    sut = WatcherDriver(state_path)
    sut.emit_current()
    assert sut.seen == [(Event.SESSION_START, "s1")]
    sut.seen.clear()
    _write_state_to_file(state_path, "UserPromptSubmit", "s1", 2.0)
    _set_mtime(state_path, 2000.0)

    sut.poll()

    assert sut.seen == [(Event.USER_PROMPT_SUBMIT, "s1")]


def test_poll_skips_malformed_json_without_crash(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    _set_mtime(state_path, 1000.0)
    sut = WatcherDriver(state_path)
    sut.emit_current()
    sut.seen.clear()
    state_path.write_text("{not json")
    _set_mtime(state_path, 2000.0)

    sut.poll()

    assert sut.seen == []


def test_poll_skips_missing_file_without_crash(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
    _set_mtime(state_path, 1000.0)
    sut = WatcherDriver(state_path)
    sut.emit_current()
    sut.seen.clear()
    state_path.unlink()

    sut.poll()

    assert sut.seen == []


def test_emit_current_on_missing_file_does_not_crash(tmp_path: Path) -> None:
    state_path = tmp_path / ".state.json"
    sut = WatcherDriver(state_path)

    sut.emit_current()

    assert sut.seen == []


def _write_state_to_file(path: Path, event: object, sid: object, ts: float) -> None:
    path.write_text(
        json.dumps(
            {"last_active": {"event": event, "session_id": sid, "timestamp": ts}}
        )
    )


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


class WatcherDriver:
    """Drives a StateWatcher's polling steps synchronously, without its thread.

    StateWatcher's public API is `start()` / `stop()` — a daemon thread that
    polls every POLL_INTERVAL_S. Driving that in tests means sleeping and
    racing the scheduler: flaky and slow, and it tests the threading wrapper
    rather than the logic with real bugs.

    Instead we drive the two synchronous steps the thread performs — the
    initial sync (`_emit_current`) and one poll tick (`_poll`) — directly.
    These are private methods, so this is deliberately testing internal API:
    the mtime/timestamp suppression logic is the whole point and has no other
    entry point. Centralizing the calls here keeps the internal-API use to a
    single seam (this class) rather than scattering `w._poll()` / `_emit_current()`
    across every test, which made the smell pervasive and unreviewable.
    """

    _watcher: StateWatcher

    def __init__(self, path: Path) -> None:
        self.seen: list[tuple[Event, str]] = []
        self._watcher = StateWatcher(
            path, on_event=lambda e, s: self.seen.append((e, s))
        )

    def emit_current(self) -> None:
        """Act: the watcher's initial sync (one `_emit_current`)."""
        self._watcher._emit_current()  # pyright: ignore[reportPrivateUsage]

    def poll(self) -> None:
        """Act: one polling tick (one `_poll`)."""
        self._watcher._poll()  # pyright: ignore[reportPrivateUsage]
