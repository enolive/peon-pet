"""Entry point: parse args, run the Qt event loop."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import final

from PyQt6 import QtCore, QtWidgets

from .config import ANIM_CONFIG, Anim
from .demo import Demo
from .prefs import Prefs
from .state import EVENT_REACTION, Event, PetStateMachine
from .tray import TrayIcon
from .watcher import DEFAULT_STATE_PATH, StateWatcher
from .window import PetWindow

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> None:
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
    args = CliArgs(
        anim=str(ns.anim) if ns.anim is not None else None,
        demo=bool(ns.demo),
        watch=Path(ns.watch) if ns.watch is not None else None,
        list_events=bool(ns.list_events),
        verbose=int(ns.verbose),
    )

    logging.basicConfig(
        level=_log_level(args.verbose),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logger.debug("args=%s", args)

    if args.list_events:
        _print_event_anim_mapping()
        sys.exit(0)

    try:
        prefs = Prefs()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Peon Pet")
    _claim_single_instance(app)

    try:
        win = PetWindow(prefs)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    win.show()

    tray = TrayIcon(app)
    tray.on_toggle_visibility.connect(win.toggle_visibility)
    tray.show()

    # Ctrl-C in the terminal should exit cleanly instead of being swallowed by Qt.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    timer = QtCore.QTimer()
    timer.start(200)

    def _no_op() -> None:
        pass

    timer.timeout.connect(_no_op)

    state = PetStateMachine()

    if args.demo:
        logger.info("demo mode")
        # we need to marshal state events onto the GUI thread.
        seam = _Seam()
        seam.anim_changed.connect(lambda a: win.play(a, True))
        demo = Demo()
        demo.on_anim_changed = seam.anim_changed.emit
        demo.start()
    elif args.anim:
        anim = _resolve_anim(args.anim)
        logger.info("playing %s on startup", anim.value)
        win.play(anim, True)
    elif args.watch:
        logger.info("watching %s", args.watch)
        # we need to marshal state events onto the GUI thread.
        seam = _Seam()
        state.on_anim_changed = seam.anim_changed.emit
        state.on_session_count_changed = seam.session_count_changed.emit
        seam.anim_changed.connect(win.play)
        seam.session_count_changed.connect(win.set_session_count)
        win.finished.connect(state.on_finished)
        tray.on_reset_to_idle.connect(state.clear)
        watcher = StateWatcher(args.watch)
        watcher.on_event = state.handle_event
        watcher.start()

    sys.exit(app.exec())


@final
class _Seam(QtCore.QObject):
    """Marshals state-machine anim changes onto the GUI thread.

    The state machine runs on the watcher's daemon thread (and is also touched
    from the GUI thread via window.finished). Its only GUI-thread requirement is
    that `win.play` runs on the GUI thread — so the seam sits at the state→window
    boundary, not at watcher→state. Created on the GUI thread.
    """

    anim_changed = QtCore.pyqtSignal(Anim)
    session_count_changed = QtCore.pyqtSignal(int)


def _print_event_anim_mapping() -> None:
    """Print the peon-ping event → anim mapping to stdout for reference."""
    print("event → anim mapping:")
    for event in EVENT_REACTION:
        anim = EVENT_REACTION[event]
        print(f"  {event:22s} → {anim.value}")
    # SessionEnd has no transient reaction — it removes the session and settles
    # to the base anim (SLEEPING if none remain, else TYPING).
    print(f"  {Event.SESSION_END.value:22s} → (settle to base: sleeping / typing)")


def _resolve_anim(arg: str) -> Anim:
    """Resolve an anim name, or list available anims and exit."""
    try:
        return Anim(arg)
    except ValueError:
        print(f"anim not found: {arg!r}", file=sys.stderr)
        print("available anims (--anim <name>):", file=sys.stderr)
        for a in Anim:
            print(f"  {a.value:9s} (row {ANIM_CONFIG[a].row})", file=sys.stderr)
        sys.exit(1)


def _claim_single_instance(app: QtWidgets.QApplication) -> None:
    """Exit if another peon-pet is running; otherwise claim the instance slot.

    Qt local server is the portable single-instance primitive: a second launch
    connects to the first's socket and bails out. `removeServer` clears any stale
    socket left by a crashed previous run before we listen. The server is
    parented to `app` so it outlives this function call.
    """
    from PyQt6 import QtNetwork

    socket = QtNetwork.QLocalSocket()
    socket.connectToServer("peon-pet")
    if socket.waitForConnected(100):
        print("peon-pet is already running.", file=sys.stderr)
        sys.exit(0)
    socket.close()
    QtNetwork.QLocalServer.removeServer("peon-pet")
    if not QtNetwork.QLocalServer(app).listen("peon-pet"):
        print("ERROR: could not start single-instance server", file=sys.stderr)
        sys.exit(1)


_LOG_LEVELS: tuple[int, int, int] = (logging.WARNING, logging.INFO, logging.DEBUG)


def _log_level(verbosity: int) -> int:
    """Map a -v count to a logging level, clamped to DEBUG."""
    return _LOG_LEVELS[min(verbosity, len(_LOG_LEVELS) - 1)]


@dataclass
class CliArgs:
    anim: str | None
    demo: bool
    watch: Path | None
    list_events: bool
    verbose: int


if __name__ == "__main__":
    main()
