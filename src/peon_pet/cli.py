"""CLI helpers: arg parsing, anim resolution, event listing, log-level mapping.

Pure Python (no Qt) so `__main__` can keep the untestable Qt wiring and these
helpers stay unit-testable. Public so tests don't trip `reportPrivateUsage` by
reaching across a private-import boundary.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import override

from pydantic import BaseModel

from . import __version__
from .config import ANIM_CONFIG, Anim
from .events import EVENT_REACTION, Event
from .watcher import DEFAULT_STATE_PATH

INSTALL_SH_URL = (
    "https://github.com/enolive/peon-pet/releases/latest/download/install.sh"
)


class LogLevel(StrEnum):
    """Meaningful log levels for the CLI, decoupled from stdlib's numeric magic."""

    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

    def to_stdlib(self) -> int:
        """Map to the stdlib `logging` level at the boundary."""
        return _STDLIB_LEVEL[self]


_STDLIB_LEVEL: Mapping[LogLevel, int] = {
    LogLevel.WARNING: logging.WARNING,
    LogLevel.INFO: logging.INFO,
    LogLevel.DEBUG: logging.DEBUG,
}


class CliArgs(BaseModel):
    anim: str | None = None
    demo: bool = False
    watch: Path | None = None
    verbose: int = 0

    @property
    def log_level(self) -> LogLevel:
        if self.verbose == 0:
            return LogLevel.WARNING
        if self.verbose == 1:
            return LogLevel.INFO
        return LogLevel.DEBUG


def parse_args(argv: Sequence[str] | None) -> CliArgs:
    parser = argparse.ArgumentParser(
        prog="peon-pet",
        description="Desktop pet that reacts to peon-ping events.",
    )
    _ = parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    _ = parser.add_argument(
        "--update",
        nargs=0,
        action=_UpdateAction,
        dest=argparse.SUPPRESS,
        help="download and run the latest install.sh from GitHub Releases",
    )
    _ = parser.add_argument(
        "--anim",
        default=None,
        help="anim to play on startup; takes precedence over --watch and --demo",
    )
    mode = parser.add_mutually_exclusive_group()
    _ = mode.add_argument(
        "--demo",
        action="store_true",
        help="cycle through every animation every 3s (visual QA)",
    )
    _ = mode.add_argument(
        "--list-events",
        nargs=0,
        action=_ListEventsAction,
        dest=argparse.SUPPRESS,
        help="list all known events and their mappings to anims and exit",
    )
    _ = parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (-v info, -vv debug)",
    )
    _ = mode.add_argument(
        "--watch",
        nargs="?",
        const=str(DEFAULT_STATE_PATH),
        default=None,
        metavar="PATH",
        help=(
            "watch peon-ping .state.json at PATH and react to events "
            f"(default mode; PATH defaults to {DEFAULT_STATE_PATH})"
        ),
    )
    ns = parser.parse_args(argv)
    cli_args = CliArgs.model_validate(vars(ns))
    no_mode_given = (
        cli_args.watch is None and not cli_args.demo and cli_args.anim is None
    )
    if no_mode_given:
        cli_args = cli_args.model_copy(update={"watch": DEFAULT_STATE_PATH})
    return cli_args


def resolve_anim(arg: str) -> Anim:
    """Resolve an anim name, or raise ValueError listing available anims."""
    try:
        return Anim(arg)
    except ValueError:
        available = ", ".join(f"{a.value} (row {ANIM_CONFIG[a].row})" for a in Anim)
        raise ValueError(f"anim not found: {arg!r}; available: {available}") from None


def print_event_anim_mapping() -> None:
    print("event -> anim mapping:")
    for event in EVENT_REACTION:
        anim = EVENT_REACTION[event]
        print(f"  {event:22s} -> {anim.value}")
    # SessionEnd has no transient reaction: it removes the session and settles
    # to the base anim (SLEEPING if none remain, else TYPING).
    print(f"  {Event.SESSION_END.value:22s} -> (settle to base: sleeping / typing)")


def run_update() -> None:
    script = subprocess.run(
        ["curl", "-fsSL", INSTALL_SH_URL],
        check=True,
        capture_output=True,
    )
    _ = subprocess.run(["bash"], input=script.stdout, check=True)


class _ListEventsAction(argparse.Action):
    @override
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        print_event_anim_mapping()
        parser.exit(0)


class _UpdateAction(argparse.Action):
    @override
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        run_update()
        parser.exit(0)
