"""Entry point: parse args, build the Qt app, run the event loop.

`run` wires the app and returns the window without calling `app.exec()`; `main`
creates the app, calls `run`, then blocks on `app.exec()`. The split keeps the
wired chain testable: tests pass a per-test app fixture into `run(...)` and
drive the event loop themselves instead of fighting a blocking `app.exec()`.
"""

from __future__ import annotations

import logging
import signal
import sys
from collections.abc import Sequence
from typing import final

from PyQt6 import QtCore, QtWidgets

from .cli import (
    log_level,
    parse_args,
    print_event_anim_mapping,
    resolve_anim,
)
from .config import Anim
from .demo import Demo
from .prefs import Prefs
from .state import PetStateMachine
from .tray import TrayIcon
from .watcher import POLL_INTERVAL_S, StateWatcher
from .window import PetWindow

logger = logging.getLogger(__name__)


def main(
    argv: Sequence[str] | None = None,
    *,
    single_instance_name: str = "peon-pet",
    poll_interval_s: float = POLL_INTERVAL_S,
) -> None:
    """Build the app and block on its event loop. Errors from run() are printed
    to stderr and exit(1) is called."""
    try:
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("Peon Pet")
        _win = run(
            app,
            argv,
            single_instance_name=single_instance_name,
            poll_interval_s=poll_interval_s,
        )
        sys.exit(app.exec())
    except (RuntimeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def run(
    app: QtWidgets.QApplication,
    argv: Sequence[str] | None = None,
    *,
    single_instance_name: str = "peon-pet",
    poll_interval_s: float = POLL_INTERVAL_S,
) -> PetWindow:
    """Wire window/watcher/tray for the parsed args and return the window.

    Receives the `QApplication` (created by `main`, or a per-test fixture) so
    tests can own the app's lifecycle and avoid two QApplications coexisting.
    Does NOT call `app.exec()`; `main` does that.
    """
    args = parse_args(argv)

    logging.basicConfig(
        level=log_level(args.verbose),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logger.debug("args=%s", args)

    if args.list_events:
        print_event_anim_mapping()
        sys.exit(0)

    prefs = Prefs()
    claim_single_instance(app, name=single_instance_name)

    win = PetWindow(prefs)
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
        seam = _Seam(parent=app)
        seam.anim_changed.connect(lambda a: win.play(a, True))
        demo = Demo(on_anim_changed=seam.anim_changed.emit, interval_s=poll_interval_s)
        app.setProperty("peon_pet_demo", demo)
        demo.start()
    elif args.anim:
        anim = resolve_anim(args.anim)
        logger.info("playing %s on startup", anim.value)
        win.play(anim, True)
    elif args.watch:
        logger.info("watching %s", args.watch)
        # we need to marshal state events onto the GUI thread.
        seam = _Seam(parent=app)
        state.on_anim_changed = seam.anim_changed.emit
        state.on_session_count_changed = seam.session_count_changed.emit
        seam.anim_changed.connect(win.play)
        seam.session_count_changed.connect(win.set_session_count)
        win.finished.connect(state.on_finished)
        tray.on_reset_to_idle.connect(state.clear)
        watcher = StateWatcher(
            path=args.watch,
            poll_interval_s=poll_interval_s,
            on_event=state.handle_event,
        )
        # expose the watcher for testing so we can stop it after each integration test
        app.setProperty("peon_pet_watcher", watcher)
        watcher.start()

    return win


@final
class _Seam(QtCore.QObject):
    """Marshals state-machine anim changes onto the GUI thread.

    The state machine runs on the watcher's daemon thread; its only GUI-thread
    requirement is that `win.play` runs on the GUI thread, so the seam sits at
    the state->window boundary, not at watcher->state.
    """

    anim_changed = QtCore.pyqtSignal(Anim)
    session_count_changed = QtCore.pyqtSignal(int)


def claim_single_instance(app: QtWidgets.QApplication, name: str = "peon-pet") -> None:
    """Exit if another peon-pet is running; otherwise claim the instance slot.

    Uses a Qt local server: a second launch connects to the first's socket and
    bails out. `name` is injectable so tests can claim a unique server and avoid
    colliding with each other or a real running instance.
    """
    from PyQt6 import QtNetwork

    socket = QtNetwork.QLocalSocket()
    socket.connectToServer(name)
    if socket.waitForConnected(100):
        print("peon-pet is already running.", file=sys.stderr)
        sys.exit(1)
    socket.close()
    # Clear any stale socket left by a crashed previous run before we listen.
    QtNetwork.QLocalServer.removeServer(name)
    if not QtNetwork.QLocalServer(app).listen(name):
        print("ERROR: could not start single-instance server", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
