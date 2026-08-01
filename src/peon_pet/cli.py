"""CLI helpers: arg parsing, anim resolution, event listing, log-level mapping.

Pure Python (no Qt) so `__main__` can keep the untestable Qt wiring and these
helpers stay unit-testable. Public so tests don't trip `reportPrivateUsage` by
reaching across a private-import boundary.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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


@dataclass
class CliArgs:
    """Parsed CLI args; the seam `main` consumes."""

    anim: str | None
    demo: bool
    watch: Path | None
    list_events: bool
    log_level: LogLevel


def parse_args(argv: Sequence[str] | None) -> CliArgs:
    parser = argparse.ArgumentParser(
        prog="peon-pet",
        description="Desktop pet that reacts to peon-ping events.",
    )
    parser.add_argument("--anim", default=None, help="anim to play on startup")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--demo",
        action="store_true",
        help="cycle through every animation every 3s (visual QA)",
    )
    mode.add_argument(
        "--list-events",
        default=False,
        action="store_true",
        help="list all known events and their mappings to anims and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (-v info, -vv debug)",
    )
    mode.add_argument(
        "--watch",
        nargs="?",
        const=str(DEFAULT_STATE_PATH),
        default=None,
        metavar="PATH",
        help=f"watch peon-ping .state.json at PATH and react to events (default: {DEFAULT_STATE_PATH})",
    )
    ns = parser.parse_args(argv)
    # Map the -v count to a meaningful level: 0 -> WARNING, 1 -> INFO, >=2 -> DEBUG.
    level = (
        LogLevel.DEBUG
        if ns.verbose >= 2
        else LogLevel.INFO
        if ns.verbose >= 1
        else LogLevel.WARNING
    )
    return CliArgs(
        anim=str(ns.anim) if ns.anim is not None else None,
        demo=bool(ns.demo),
        watch=Path(ns.watch) if ns.watch is not None else None,
        list_events=bool(ns.list_events),
        log_level=level,
    )


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
