"""Tests for cli.py: arg parsing, anim resolution, event mapping, and the
log-level mapping. cli.py is pure Python (no Qt).
"""

import logging
from pathlib import Path

import pytest

from peon_pet.cli import (
    CliArgs,
    log_level,
    parse_args,
    print_event_anim_mapping,
    resolve_anim,
)
from peon_pet.config import Anim
from peon_pet.state import EVENT_REACTION, Event


class TestParseArgs:
    def test_defaults_when_no_args(self) -> None:
        args = parse_args([])

        assert args == CliArgs(
            anim=None, demo=False, watch=None, list_events=False, verbose=0
        )

    def test_anim_name_is_parsed(self) -> None:
        args = parse_args(["--anim", "waking"])

        assert args.anim == "waking"

    def test_verbose_count_accumulates(self) -> None:
        args = parse_args(["-v", "-v"])

        assert args.verbose == 2

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
        assert "event → anim mapping:" in out
        for event in EVENT_REACTION:
            assert event.value in out
        assert Event.SESSION_END.value in out


class TestLogLevel:
    def test_default_verbosity_is_warning(self) -> None:
        assert log_level(0) == logging.WARNING

    def test_single_v_is_info(self) -> None:
        assert log_level(1) == logging.INFO

    def test_double_v_is_debug(self) -> None:
        assert log_level(2) == logging.DEBUG

    def test_verbosity_clamps_to_debug_past_two(self) -> None:
        assert log_level(3) == logging.DEBUG
        assert log_level(99) == logging.DEBUG
