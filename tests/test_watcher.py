"""Tests for StateWatcher's str->Event parsing at the read boundary."""

import json
import os
import time
from pathlib import Path
from types import TracebackType
from typing import Self

from peon_pet.events import Event
from peon_pet.watcher import StateWatcher
from tests.assertions import wait_until


class TestThread:
    def test_start_emits_current_then_polls_new_events(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        with WatcherDriver(path=state_path, poll_interval_s=0.05) as sut:
            sut.start()
            assert wait_until(lambda: sut.seen == [(Event.SESSION_START, "s1")])

            _write_state_to_file(state_path, "UserPromptSubmit", "s1", 2.0)

            assert wait_until(
                lambda: (
                    sut.seen
                    == [(Event.SESSION_START, "s1"), (Event.USER_PROMPT_SUBMIT, "s1")]
                )
            )

    def test_stop_halts_consumption(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        sut = WatcherDriver(path=state_path, poll_interval_s=0.05)
        sut.start()
        assert wait_until(lambda: sut.seen == [(Event.SESSION_START, "s1")])

        sut.stop()
        _write_state_to_file(state_path, "UserPromptSubmit", "s1", 2.0)

        # wait a few cycles to assure no more events are emitted
        time.sleep(0.2)
        assert sut.seen == [(Event.SESSION_START, "s1")]


class TestTick:
    def test_tick_fires_on_each_poll_interval_without_state_change(
        self, tmp_path: Path
    ) -> None:
        state_path = tmp_path / ".state.json"
        with WatcherDriver(path=state_path, poll_interval_s=0.05) as sut:
            sut.start()

            assert wait_until(lambda: sut.ticks >= 2)

    def test_tick_fires_even_when_events_also_fire(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        with WatcherDriver(path=state_path, poll_interval_s=0.05) as sut:
            sut.start()
            assert wait_until(lambda: sut.seen == [(Event.SESSION_START, "s1")])

            _write_state_to_file(state_path, "UserPromptSubmit", "s1", 2.0)

            assert wait_until(
                lambda: (
                    Event.USER_PROMPT_SUBMIT in {e for e, _ in sut.seen}
                    and sut.ticks >= 1
                )
            )

    def test_stop_halts_any_further_ticks(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        sut = WatcherDriver(path=state_path, poll_interval_s=0.05)
        sut.start()
        assert wait_until(lambda: sut.ticks >= 1)

        sut.stop()
        frozen = sut.ticks
        # wait a few cycles to ensure no more ticks are emitted
        time.sleep(0.2)

        assert sut.ticks == frozen

    def test_tick_not_called_during_initial_emit(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        with WatcherDriver(path=state_path, poll_interval_s=1.0) as sut:
            sut.start()
            assert wait_until(lambda: sut.seen == [(Event.SESSION_START, "s1")])

            time.sleep(0.1)

            assert sut.ticks == 0


class TestReadBoundary:
    def test_emits_typed_event_for_known_name(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        sut = WatcherDriver(state_path)

        sut.emit_current()

        assert sut.seen == [(Event.SESSION_START, "s1")]

    def test_missing_session_id_is_skipped(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", None, 1.0)
        sut = WatcherDriver(state_path)

        sut.emit_current()

        assert sut.seen == []

    def test_unknown_event_name_is_skipped(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "NotARealEvent", "s1", 1.0)
        sut = WatcherDriver(state_path)

        sut.emit_current()

        assert sut.seen == []

    def test_missing_event_field_is_skipped(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, None, "s1", 1.0)
        sut = WatcherDriver(state_path)

        sut.emit_current()

        assert sut.seen == []

    def test_state_file_without_last_active_is_skipped(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _ = state_path.write_text("{}")
        sut = WatcherDriver(state_path)

        sut.emit_current()

        assert sut.seen == []

    def test_emit_current_on_missing_file_does_not_crash(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        sut = WatcherDriver(state_path)

        sut.emit_current()

        assert sut.seen == []


class TestPoll:
    def test_does_not_reemit_when_mtime_unchanged(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        sut = WatcherDriver(state_path)
        sut.emit_current()
        assert sut.seen == [(Event.SESSION_START, "s1")]
        sut.seen.clear()

        sut.poll()

        assert sut.seen == []

    def test_does_not_reemit_when_mtime_is_in_the_past(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        _set_mtime(state_path, 2000.0)
        sut = WatcherDriver(state_path)
        sut.emit_current()
        assert sut.seen == [(Event.SESSION_START, "s1")]
        sut.seen.clear()
        _write_state_to_file(state_path, "SessionStart", "s1", 2.0)
        # if for any reasons the mtime is now in the past, it might be corrupt. ignore it
        _set_mtime(state_path, 1000.0)

        sut.poll()

        assert sut.seen == []

    def test_suppresses_when_mtime_changed_but_timestamp_equal(
        self, tmp_path: Path
    ) -> None:
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

    def test_emits_when_mtime_and_timestamp_newer(self, tmp_path: Path) -> None:
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

    def test_skips_malformed_json_without_crash(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        _set_mtime(state_path, 1000.0)
        sut = WatcherDriver(state_path)
        sut.emit_current()
        sut.seen.clear()
        _ = state_path.write_text("{not json")
        _set_mtime(state_path, 2000.0)

        sut.poll()

        assert sut.seen == []

    def test_skips_json_that_is_not_dict_without_crash(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        _set_mtime(state_path, 1000.0)
        sut = WatcherDriver(state_path)
        sut.emit_current()
        sut.seen.clear()
        _ = state_path.write_text("42")
        _set_mtime(state_path, 2000.0)

        sut.poll()

        assert sut.seen == []

    def test_skips_missing_file_without_crash(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        _write_state_to_file(state_path, "SessionStart", "s1", 1.0)
        _set_mtime(state_path, 1000.0)
        sut = WatcherDriver(state_path)
        sut.emit_current()
        sut.seen.clear()
        state_path.unlink()

        sut.poll()

        assert sut.seen == []


def _write_state_to_file(path: Path, event: object, sid: str | None, ts: float) -> None:
    _ = path.write_text(
        json.dumps(
            {"last_active": {"event": event, "session_id": sid, "timestamp": ts}}
        )
    )


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


class WatcherDriver:
    """Drives a StateWatcher.

    Thread-level tests (TestThread, TestWatcherTick) use start/stop on the same
    driver and record `on_tick` via `ticks`.

    Other tests are using its internal api via poll/emit_current in order to be able
    to test its behavior synchronously.

    Implements a context manager to stop the watcher after its usage and get rid of
    weird try finally blocks for stopping it.
    """

    _watcher: StateWatcher

    ticks: int

    def __init__(self, path: Path, poll_interval_s: float = 0.05) -> None:
        self.seen: list[tuple[Event, str]] = []
        self.ticks = 0
        self._watcher = StateWatcher(
            path=path,
            on_event=lambda e, s: self.seen.append((e, s)),
            on_tick=self._on_tick,
            poll_interval_s=poll_interval_s,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    def _on_tick(self) -> None:
        self.ticks += 1

    def start(self) -> None:
        self._watcher.start()

    def stop(self) -> None:
        self._watcher.stop()

    def emit_current(self) -> None:
        """Act: the watcher's initial sync (one `_emit_current`)."""
        # noinspection protected-member
        self._watcher._emit_current()  # pyright: ignore[reportPrivateUsage]

    def poll(self) -> None:
        """Act: one polling tick (one `_poll`)."""
        # noinspection protected-member
        self._watcher._poll()  # pyright: ignore[reportPrivateUsage]
