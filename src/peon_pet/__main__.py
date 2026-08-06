"""Entry point: parse args, build the Qt app, run the event loop."""

from __future__ import annotations

import logging
import os
import signal
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final, cast, final

from PySide6 import QtCore, QtNetwork, QtWidgets

from .cli import (
    CliArgs,
    LogLevel,
    parse_args,
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

# Relative path under $XDG_STATE_HOME (or ~/.local/state) for the -vv debug log.
# Root is dynamic; only the app-relative tail is a constant worth sharing with tests.
DEBUG_LOG_REL = Path("peon-pet") / "peon-pet-debug.log"

# App properties where run() stashes the live background worker. Production
# joins via aboutToQuit; tests call stop_background_threads on the same keys.
PROP_DEMO: Final = "peon_pet_demo"
PROP_WATCHER: Final = "peon_pet_watcher"
_BACKGROUND_PROPS: Final = (PROP_WATCHER, PROP_DEMO)


def main(
    argv: Sequence[str] | None = None,
    *,
    single_instance_name: str = "peon-pet",
    poll_interval_s: float = POLL_INTERVAL_S,
) -> None:
    try:
        # args are parsed before the Qt loop to avoid useless initialization in case something goes wrong
        # or the action is an immediate exit (such as --version)
        args = parse_args(argv)
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("Peon Pet")
        # prevent quitting on last window closed which will quit the app after the about dialog.
        app.setQuitOnLastWindowClosed(False)
        _win = run(
            app,
            args,
            single_instance_name=single_instance_name,
            poll_interval_s=poll_interval_s,
        )
        sys.exit(app.exec())
    except (RuntimeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def run(
    app: QtWidgets.QApplication,
    args: CliArgs,
    *,
    single_instance_name: str = "peon-pet",
    poll_interval_s: float = POLL_INTERVAL_S,
) -> PetWindow:
    """
    Testable version of `main` that returns the window instead of blocking on
    `app.exec()`.
    """
    _configure_logging(args)
    logger.debug("args=%s", args)

    prefs = Prefs()
    claim_single_instance(app, name=single_instance_name)

    win = PetWindow(prefs)
    win.show()

    tray = TrayIcon(app)
    _ = tray.on_toggle_visibility.connect(win.toggle_visibility)
    tray.show()

    # Ctrl-C in the terminal should exit cleanly instead of being swallowed by Qt.
    quit_app: Callable[..., None] = lambda *_: app.quit()
    _ = signal.signal(signal.SIGINT, quit_app)
    timer = QtCore.QTimer()
    timer.start(200)
    _ = timer.timeout.connect(lambda: None)

    # Demo/watcher emit Qt signals from a daemon thread. Stash on the app and
    # join on aboutToQuit so they cannot touch the seam after Qt destroys it
    # (Ctrl-C otherwise races into RuntimeError: Signal source has been deleted).
    # Same stash keys the test harness uses via stop_background_threads.
    if args.demo:
        logger.info("demo mode")
        seam = _Seam(parent=app)
        play: Callable[[Anim], None] = lambda a: win.play(a, True)
        _ = seam.anim_changed.connect(play)
        demo = Demo(on_anim_changed=seam.anim_changed.emit, interval_s=poll_interval_s)
        _ = app.setProperty(PROP_DEMO, demo)
        demo.start()
    elif args.anim:
        anim = resolve_anim(args.anim)
        logger.info("playing %s on startup", anim.value)
        win.play(anim, True)
    elif args.watch:
        state = PetStateMachine()
        logger.info("watching %s", args.watch)
        seam = _Seam(parent=app)
        state.on_anim_changed = seam.anim_changed.emit
        state.on_session_count_changed = seam.session_count_changed.emit
        _ = seam.anim_changed.connect(win.play)
        _ = seam.session_count_changed.connect(win.set_session_count)
        _ = win.finished.connect(state.on_finished)
        _ = tray.on_reset_to_idle.connect(state.clear)
        watcher = StateWatcher(
            path=args.watch,
            poll_interval_s=poll_interval_s,
            on_event=state.handle_event,
            on_tick=state.purge_expired,
        )
        _ = app.setProperty(PROP_WATCHER, watcher)
        watcher.start()

    _ = app.aboutToQuit.connect(lambda: stop_background_threads(app))

    return win


def stop_background_threads(app: QtWidgets.QApplication) -> None:
    """Join demo/watcher stashed on the app, if any. Idempotent."""
    for key in _BACKGROUND_PROPS:
        obj = cast(Demo | StateWatcher | None, app.property(key))
        if obj is not None:
            obj.stop()


def claim_single_instance(app: QtWidgets.QApplication, name: str = "peon-pet") -> None:
    """Exit if another peon-pet is running; otherwise claim the instance slot.

    Uses a Qt local server: a second launch connects to the first's socket and
    bails out. `name` is injectable so tests can claim a unique server and avoid
    colliding with each other or a real running instance.
    """
    socket = QtNetwork.QLocalSocket()
    socket.connectToServer(name)
    if socket.waitForConnected(100):
        print("peon-pet is already running.", file=sys.stderr)
        sys.exit(1)
    socket.close()
    # Clear any stale socket left by a crashed previous run before we listen.
    _ = QtNetwork.QLocalServer.removeServer(name)
    if not QtNetwork.QLocalServer(app).listen(name):
        print("ERROR: could not start single-instance server", file=sys.stderr)
        sys.exit(1)


def _configure_logging(args: CliArgs):
    logging.basicConfig(
        level=args.log_level.to_stdlib(),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    # At DEBUG (-vv), also log to a file for post-hoc analysis of intermittent
    # glitches. XDG state dir; append across runs to keep history.
    if args.log_level is LogLevel.DEBUG:
        xdg_state = os.environ.get("XDG_STATE_HOME") or str(
            Path.home() / ".local" / "state"
        )
        log_path = Path(xdg_state) / DEBUG_LOG_REL
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
        logger.info("logging to %s", log_path)


@final
class _Seam(QtCore.QObject):
    """Bridges the state machine's plain callbacks to Qt's signal-slot wiring.

    `PetStateMachine` exposes `on_anim_changed` / `on_session_count_changed`
    as plain `Callable`s so the state logic stays Qt-free. They can't be
    `connect()`-ed to Qt slots directly, so this holds the corresponding
    signals; cross-thread marshaling itself is `Qt.AutoConnection`'s job
    (sender emitted from the watcher daemon thread, receivers on the GUI
    thread).
    """

    anim_changed = QtCore.Signal(Anim)
    session_count_changed = QtCore.Signal(int)


if __name__ == "__main__":
    main()
