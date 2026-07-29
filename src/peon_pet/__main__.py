"""Entry point: parse args, run the Qt event loop."""

from __future__ import annotations

import argparse
import signal
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from .config import ATLAS_LAYOUTS, ANIM_CONFIG, Anim, AtlasLayout
from .state import EVENT_REACTION, KNOWN_EVENTS, PetStateMachine
from .watcher import DEFAULT_STATE_PATH, StateWatcher
from .window import PetWindow


def _resolve_atlas(arg: str) -> None:
    """Validate the atlas short name, or list available and exit."""
    if arg in ATLAS_LAYOUTS:
        return
    print(f"atlas not found: {arg!r}", file=sys.stderr)
    print("available atlases (--atlas <name>):", file=sys.stderr)
    sorted_layouts = sorted(ATLAS_LAYOUTS.items())
    layout: tuple[str, AtlasLayout]
    for layout in sorted_layouts:
        name, atlas_layout = layout
        print(f"  {name:14s} {atlas_layout.cols}x{atlas_layout.rows}", file=sys.stderr)
    sys.exit(1)


def _resolve_event(arg: str, atlas_rows: int) -> str:
    """Validate an event name, or list available events and exit. Returns the name."""
    if arg == 'idle':
        return arg
    if arg not in KNOWN_EVENTS:
        print(f"event not found: {arg!r}", file=sys.stderr)
        print("available events (--event <name>):", file=sys.stderr)
        print(f"  {'idle':22s} sleeping  (row 0)", file=sys.stderr)
        name: str
        for name in sorted(KNOWN_EVENTS):
            anim = EVENT_REACTION.get(name)
            if anim is None:
                # SessionEnd — settles to sleeping, no transient reaction.
                print(f"  {name:22s} (→idle)   (row 0)", file=sys.stderr)
            else:
                row = ANIM_CONFIG[anim].row
                avail = "ok" if row < atlas_rows else "(not in this atlas)"
                print(f"  {name:22s} {anim:9s} (row {row}) {avail}", file=sys.stderr)
        sys.exit(1)
    # Row-availability check for the reaction anim (if any).
    anim = EVENT_REACTION.get(arg)
    if anim is not None:
        row = ANIM_CONFIG[anim].row
        if row >= atlas_rows:
            print(f"event {arg!r} → {anim} (row {row}) is not in this atlas ({atlas_rows} rows)", file=sys.stderr)
            sys.exit(1)
    return arg


@dataclass
class CliArgs:
    atlas: str
    event: str
    loops: int
    demo: bool
    watch: Path | None


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="peon-pet",
        description="Desktop pet that reacts to peon-ping events.",
    )
    parser.add_argument("--atlas", default="peon",
                        help="atlas short name (default: peon)")
    parser.add_argument("--event", default="idle",
                        help="event to react to on startup (default: idle)")
    parser.add_argument("--loops", type=int, default=3,
                        help="times to loop a reaction anim before returning to base (default: 3)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true",
                      help="cycle through every animation every 3s (visual QA)")
    mode.add_argument("--watch", nargs="?", const=str(DEFAULT_STATE_PATH),
                      default=None, metavar="PATH",
                      help=f"watch peon-ping .state.json at PATH and react to events (default: {DEFAULT_STATE_PATH})")
    ns = parser.parse_args(argv)
    args = CliArgs(atlas=str(ns.atlas), event=str(ns.event), loops=int(ns.loops),
                   demo=bool(ns.demo),
                   watch=Path(ns.watch) if ns.watch is not None else None)

    _resolve_atlas(args.atlas)
    rows = ATLAS_LAYOUTS[args.atlas].rows
    _resolve_event(args.event, rows)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Peon Pet")

    try:
        win = PetWindow(args.atlas, args.loops)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    win.show()

    # Ctrl-C in the terminal should exit cleanly instead of being swallowed by Qt.
    _ = signal.signal(signal.SIGINT, lambda *_: app.quit())
    # Let the Python interpreter see signals while Qt's event loop runs.
    timer = QtCore.QTimer()  # noqa: keep a reference
    timer.start(200)

    def _no_op() -> None:
        pass

    _ = timer.timeout.connect(_no_op)

    if args.demo:
        # Cycle through every animation every 3s to exercise play() at runtime.
        it = iter(cycle(Anim))
        next(it)  # skip the one already playing as start_anim

        def _cycle() -> None:
            win.play(next(it))

        demo_timer = QtCore.QTimer()
        demo_timer.start(3000)
        _ = demo_timer.timeout.connect(_cycle)
    else:
        state = PetStateMachine()
        state.anim_changed.connect(win.play)
        win.finished.connect(state.on_finished)
        if args.event != 'idle':
            state.handle_event(args.event)
        if args.watch is not None:
            watcher = StateWatcher(args.watch)
            watcher.event_triggered.connect(state.handle_event)
            watcher.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
