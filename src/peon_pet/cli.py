"""CLI helpers for peon-pet: arg parsing, anim resolution, event listing,
and the log-level mapping.

Pure Python — no Qt. `__main__` imports these and keeps the Qt-dependent
wiring (single-instance claiming, event loop) that can't be unit-tested here.
Public so tests don't reach across a private-import boundary (which would
trip `reportPrivateUsage`).
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import ANIM_CONFIG, Anim
from .events import EVENT_REACTION, Event
from .watcher import DEFAULT_STATE_PATH

_LOG_LEVELS: tuple[int, int, int] = (logging.WARNING, logging.INFO, logging.DEBUG)


@dataclass
class CliArgs:
    """Parsed CLI args — the seam `main` consumes."""

    anim: str | None
    demo: bool
    watch: Path | None
    list_events: bool
    verbose: int


def parse_args(argv: Sequence[str] | None) -> CliArgs:
    """Parse CLI args into a CliArgs dataclass."""
    parser = argparse.ArgumentParser(
        prog="peon-pet",
        description="Desktop pet that reacts to peon-ping events.",
    )
    parser.add_argument("--anim", default=None, help="anim to play on startup")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (-v info, -vv debug)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--demo",
        action="store_true",
        help="cycle through every animation every 3s (visual QA)",
    )
    mode.add_argument(
        "--watch",
        nargs="?",
        const=str(DEFAULT_STATE_PATH),
        default=None,
        metavar="PATH",
        help=f"watch peon-ping .state.json at PATH and react to events (default: {DEFAULT_STATE_PATH})",
    )
    mode.add_argument(
        "--list-events",
        default=False,
        action="store_true",
        help="list all known events and their mappings to anims and exit",
    )
    ns = parser.parse_args(argv)
    return CliArgs(
        anim=str(ns.anim) if ns.anim is not None else None,
        demo=bool(ns.demo),
        watch=Path(ns.watch) if ns.watch is not None else None,
        list_events=bool(ns.list_events),
        verbose=int(ns.verbose),
    )


def resolve_anim(arg: str) -> Anim:
    """Resolve an anim name, or raise ValueError listing available anims."""
    try:
        return Anim(arg)
    except ValueError:
        available = ", ".join(f"{a.value} (row {ANIM_CONFIG[a].row})" for a in Anim)
        raise ValueError(f"anim not found: {arg!r}; available: {available}") from None


def print_event_anim_mapping() -> None:
    """Print the peon-ping event → anim mapping to stdout for reference."""
    print("event → anim mapping:")
    for event in EVENT_REACTION:
        anim = EVENT_REACTION[event]
        print(f"  {event:22s} → {anim.value}")
    # SessionEnd has no transient reaction — it removes the session and settles
    # to the base anim (SLEEPING if none remain, else TYPING).
    print(f"  {Event.SESSION_END.value:22s} → (settle to base: sleeping / typing)")


def log_level(verbosity: int) -> int:
    """Map a -v count to a logging level, clamped to DEBUG."""
    return _LOG_LEVELS[min(verbosity, len(_LOG_LEVELS) - 1)]
