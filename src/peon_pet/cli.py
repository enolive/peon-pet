"""CLI helpers: arg parsing, anim resolution, event listing, log-level mapping.

Pure Python (no Qt) so `__main__` can keep the untestable Qt wiring and these
helpers stay unit-testable. Public so tests don't trip `reportPrivateUsage` by
reaching across a private-import boundary.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from .config import ANIM_CONFIG, Anim
from .events import EVENT_REACTION, Event
from .watcher import DEFAULT_STATE_PATH


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
    list_events: bool = False
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
        default=False,
        action="store_true",
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
        help=f"watch peon-ping .state.json at PATH and react to events (default: {DEFAULT_STATE_PATH})",
    )
    ns = parser.parse_args(argv)
    cli_args = CliArgs.model_validate(vars(ns))
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
