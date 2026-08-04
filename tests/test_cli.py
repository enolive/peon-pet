"""Tests for cli.py: arg parsing, anim resolution, event mapping, and the
log-level enum. cli.py is pure Python (no Qt).
"""

import logging
from pathlib import Path
from typing import ClassVar
from unittest.mock import Mock, call, patch

import pytest

from peon_pet import __version__
from peon_pet.cli import (
    INSTALL_SH_URL,
    LogLevel,
    parse_args,
    print_event_anim_mapping,
    resolve_anim,
)
from peon_pet.config import Anim
from peon_pet.events import EVENT_REACTION, Event
from peon_pet.watcher import DEFAULT_STATE_PATH


class TestVersion:
    def test_package_version_matches_metadata(self) -> None:
        from importlib.metadata import version

        assert __version__ == version("peon-pet")

    def test_cli_version_flag_prints_version_and_exits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _ = parse_args(["--version"])

        assert exc_info.value.code == 0
        assert __version__ in capsys.readouterr().out


class TestListEventsFlag:
    def test_prints_mapping_and_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _ = parse_args(["--list-events"])

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "event -> anim mapping:" in out
        for event in EVENT_REACTION:
            assert event.value in out
        assert Event.SESSION_END.value in out


class TestUpdate:
    def test_update_flag_curls_install_sh_then_pipes_to_bash(self) -> None:
        script = b"#!/bin/bash\necho hi\n"
        with patch("peon_pet.cli.subprocess.run") as run:
            run.return_value = Mock(stdout=script)

            with pytest.raises(SystemExit) as exc_info:
                _ = parse_args(["--update"])

            assert exc_info.value.code == 0
            assert run.call_args_list == [
                call(
                    ["curl", "-fsSL", INSTALL_SH_URL], check=True, capture_output=True
                ),
                call(["bash"], input=script, check=True),
            ]


class TestParseArgs:
    def test_defaults_to_watch_when_no_args(self) -> None:
        args = parse_args([])

        assert args.watch == DEFAULT_STATE_PATH
        assert args.demo is False
        assert args.anim is None
        assert args.log_level is LogLevel.WARNING

    def test_defaults_to_watch_with_only_verbose(self) -> None:
        args = parse_args(["-v"])

        assert args.watch is not None
        assert args.watch.name == ".state.json"
        assert args.log_level is LogLevel.INFO

    def test_anim_name_is_parsed(self) -> None:
        args = parse_args(["--anim", "waking"])

        assert args.anim == "waking"
        assert args.watch is None

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

    def test_watch_flag_uses_peon_ping_state_path(self) -> None:
        args = parse_args(["--watch"])

        assert args.watch is not None
        assert args.watch.name == ".state.json"

    def test_watch_with_explicit_path(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".state.json"
        args = parse_args(["--watch", str(state_path)])

        assert args.watch == state_path


class TestResolveAnim:
    def test_returns_the_anim_for_a_valid_name(self) -> None:
        assert resolve_anim("waking") == Anim.WAKING

    def test_raises_value_error_for_an_unknown_name(self) -> None:
        with pytest.raises(ValueError):
            _ = resolve_anim("not-an-anim")


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
