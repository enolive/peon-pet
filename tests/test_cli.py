"""Tests for cli.py: arg parsing, anim resolution, event mapping, and the
log-level enum. cli.py is pure Python (no Qt).
"""

import logging
from pathlib import Path
from typing import ClassVar

import pytest

from peon_pet.cli import (
    CliArgs,
    LogLevel,
    parse_args,
    print_event_anim_mapping,
    resolve_anim,
)
from peon_pet.config import Anim
from peon_pet.events import EVENT_REACTION, Event


class TestParseArgs:
    def test_defaults_when_no_args(self) -> None:
        args = parse_args([])

        assert args == CliArgs(
            anim=None,
            demo=False,
            watch=None,
            list_events=False,
            log_level=LogLevel.WARNING,
        )

    def test_anim_name_is_parsed(self) -> None:
        args = parse_args(["--anim", "waking"])

        assert args.anim == "waking"

    _EXPECTED_LOG_LEVELS: ClassVar[list[tuple[str, LogLevel]]] = [
        ("--verbose", LogLevel.INFO),
        ("-v", LogLevel.INFO),
        ("-vv", LogLevel.DEBUG),
        ("-vvv", LogLevel.DEBUG),
        ("-vvvv", LogLevel.DEBUG),
    ]

    @pytest.mark.parametrize(
        "arg,expected",
        argvalues=_EXPECTED_LOG_LEVELS,
        ids=[arg for arg, _ in _EXPECTED_LOG_LEVELS],
    )
    def test_verbose_maps_to_expected_log_level(
        self, arg: str, expected: LogLevel
    ) -> None:
        args = parse_args([arg])

        assert args.log_level is expected

    def test_demo_flag_is_set(self) -> None:
        args = parse_args(["--demo"])

        assert args.demo is True
        assert args.watch is None

    def test_watch_defaults_to_peon_ping_state_path(self) -> None:
        args = parse_args(["--watch"])

        assert args.watch is not None
        assert args.watch.name == ".state.json"

    def test_watch_with_explicit_path(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        args = parse_args(["--watch", str(state_path)])

        assert args.watch == state_path

    def test_list_events_flag_is_set(self) -> None:
        args = parse_args(["--list-events"])

        assert args.list_events is True


class TestResolveAnim:
    def test_returns_the_anim_for_a_valid_name(self) -> None:
        assert resolve_anim("waking") == Anim.WAKING

    def test_raises_value_error_for_an_unknown_name(self) -> None:
        with pytest.raises(ValueError):
            resolve_anim("not-an-anim")


class TestPrintEventAnimMapping:
    def test_prints_every_reaction_then_session_end_settle(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_event_anim_mapping()

        out = capsys.readouterr().out
        assert "event -> anim mapping:" in out
        for event in EVENT_REACTION:
            assert event.value in out
        assert Event.SESSION_END.value in out


class TestLogLevel:
    def test_warning_maps_to_stdlib_warning(self) -> None:
        assert LogLevel.WARNING.to_stdlib() == logging.WARNING

    def test_info_maps_to_stdlib_info(self) -> None:
        assert LogLevel.INFO.to_stdlib() == logging.INFO

    def test_debug_maps_to_stdlib_debug(self) -> None:
        assert LogLevel.DEBUG.to_stdlib() == logging.DEBUG
