"""Entry point: parse args, run the Qt event loop."""

from __future__ import annotations

import argparse
import signal
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from PyQt6 import QtCore, QtWidgets

from .config import ATLAS_LAYOUTS, ANIM_CONFIG, EVENT_TO_ANIM, Anim
from .window import PetWindow


def _resolve_atlas(arg: str) -> None:
    """Validate the atlas short name, or list available and exit."""
    if arg in ATLAS_LAYOUTS:
        return
    print(f"atlas not found: {arg!r}", file=sys.stderr)
    print("available atlases (--atlas <name>):", file=sys.stderr)
    sorted_layouts = sorted(ATLAS_LAYOUTS.items())
    layout: tuple[str, tuple[str, int, int, str | None]]
    for layout in sorted_layouts:
        name, (_, cols, rows, _) = layout
        print(f"  {name:14s} {cols}x{rows}", file=sys.stderr)
    sys.exit(1)


def _resolve_event(arg: str, atlas_rows: int) -> Anim:
    """Resolve an event name to an anim, or list available and exit."""
    if arg == 'idle':
        anim = Anim.SLEEPING
    elif arg in EVENT_TO_ANIM:
        anim = EVENT_TO_ANIM[arg]
    else:
        print(f"event not found: {arg!r}", file=sys.stderr)
        print("available events (--event <name>):", file=sys.stderr)
        print(f"  {'idle':22s} sleeping  (row 0)", file=sys.stderr)
        name: str
        for name in sorted(EVENT_TO_ANIM):
            anim_name = EVENT_TO_ANIM[name]
            row = ANIM_CONFIG[anim_name][0]
            avail = "ok" if row < atlas_rows else "(not in this atlas)"
            print(f"  {name:22s} {anim_name:9s} (row {row}) {avail}", file=sys.stderr)
        sys.exit(1)
    row = ANIM_CONFIG[anim][0]
    if row >= atlas_rows:
        print(f"event {arg!r} → {anim} (row {row}) is not in this atlas ({atlas_rows} rows)", file=sys.stderr)
        sys.exit(1)
    return anim


@dataclass
class CliArgs:
    atlas: str
    event: str
    loops: int


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="peon-pet",
        description="Desktop pet that reacts to peon-ping events.",
    )
    parser.add_argument("--atlas", default="peon",
                        help="atlas short name (default: peon)")
    parser.add_argument("--event", default="idle",
                        help="event to play on startup, then return to idle (default: idle)")
    parser.add_argument("--loops", type=int, default=3,
                        help="times to play an event anim before idle (default: 3)")
    ns = parser.parse_args(argv)
    args = CliArgs(atlas=str(ns.atlas), event=str(ns.event), loops=int(ns.loops))

    _resolve_atlas(args.atlas)
    _, _, rows, _ = ATLAS_LAYOUTS[args.atlas]
    start_anim = _resolve_event(args.event, rows)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Peon Pet")

    try:
        win = PetWindow(args.atlas, args.loops, start_anim)
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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
