"""Integration tests of the wired --watch chain: watcher → state → seam → window.

These exercise the full `run(app, ["--watch", ...])` path end-to-end with
offscreen Qt, no display, and no real peon-ping. `run` wires the app (window,
watcher, tray) for the parsed args and returns the window — it receives the
`QApplication` rather than constructing one, and does NOT call `app.exec()`, so
the test owns the event loop.

We drive it with `qtbot.waitUntil`, not `app.exec()` + `QTimer.singleShot`: the
watcher runs a daemon thread that emits a GUI-bound Qt signal across threads,
and `qtbot.waitUntil` pumps the event loop (via `processEvents`) until the
queued `win.play` lands and `win.anim` flips. This reads top-to-bottom as one
write + one wait per step — no nested continuations. (The earlier segfault here
was a lifetime bug — `seam`/`state`/`watcher` GC'd while the worker thread still
emitted — now fixed by parenting them to the app; and the watcher is stopped on
`app.aboutToQuit` so its thread doesn't leak into the next test.)

`run`'s `poll_interval_s` is injected (default 0.5s in production) so the tests
run fast and don't duplicate the interval knowledge. The single-instance
collision is skipped via the injectable name. A private `app` fixture
creates/destroys a `QApplication` per test so the watcher from one test can't
leak into the next.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PyQt6 import QtWidgets
from pytestqt.qtbot import QtBot

from peon_pet.__main__ import run
from peon_pet.config import Anim

POLL_INTERVAL_SECONDS = 0.05
TIMEOUT_MS = 5000


@pytest.fixture
def app() -> Iterator[QtWidgets.QApplication]:
    """Yield the shared QApplication for one test, stopping that test's background
    thread (watcher or demo) after.

    The QApplication is a singleton: the first test to request this fixture
    creates it (and `qapp`/`qtbot` reuse `QApplication.instance()` ever after), so
    there's exactly one app for the whole session — no double-app segfault, no
    deletion (deleting a `QApplication` that `qtbot`'s session state still
    references crashes).

    The watcher/demo run daemon threads that emit a GUI-bound signal across
    threads; `run` stops neither on its own (in production the process exit kills
    them; in tests they'd leak into the next test and segfault on the next `run`).
    So the fixture stops whichever `run` stashed on the app explicitly.
    """
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert isinstance(app, QtWidgets.QApplication)
    yield app
    for key in ("peon_pet_watcher", "peon_pet_demo"):
        obj = app.property(key)
        if obj is not None:
            obj.stop()


class TestWatchIntegration:
    def test_reacts_to_a_full_session_lifecycle(
        self,
        app: QtWidgets.QApplication,
        qtbot: QtBot,
        tmp_path: Path,
        single_instance_server_name: str,
    ) -> None:
        state_path = tmp_path / ".state.json"
        # No pre-seeded file → genuinely cold first event.
        win = run(
            app,
            ["--watch", str(state_path)],
            single_instance_name=single_instance_server_name,
            poll_interval_s=POLL_INTERVAL_SECONDS,
        )
        qtbot.addWidget(win)

        _write_state(state_path, "SessionStart", "s1", 1.0)
        qtbot.waitUntil(lambda: win.anim == Anim.WAKING, timeout=TIMEOUT_MS)
        _write_state(state_path, "UserPromptSubmit", "s1", 2.0)
        qtbot.waitUntil(lambda: win.anim == Anim.TYPING, timeout=TIMEOUT_MS)
        _write_state(state_path, "Stop", "s1", 3.0)
        qtbot.waitUntil(lambda: win.anim == Anim.CELEBRATE, timeout=TIMEOUT_MS)
        _write_state(state_path, "SessionEnd", "s1", 4.0)
        qtbot.waitUntil(lambda: win.anim == Anim.SLEEPING, timeout=TIMEOUT_MS)

        assert win.anim == Anim.SLEEPING

    def test_reacts_to_a_cold_start_session(
        self,
        app: QtWidgets.QApplication,
        qtbot: QtBot,
        tmp_path: Path,
        single_instance_server_name: str,
    ) -> None:
        state_path = tmp_path / ".state.json"
        # Pre-seed a Stop: a cold start on an event that registers the session
        # announces WAKING (not CELEBRATE) — the cold-start override.
        _write_state(state_path, "Stop", "s1", 1.0)
        win = run(
            app,
            ["--watch", str(state_path)],
            single_instance_name=single_instance_server_name,
            poll_interval_s=POLL_INTERVAL_SECONDS,
        )
        qtbot.addWidget(win)

        qtbot.waitUntil(lambda: win.anim == Anim.WAKING, timeout=TIMEOUT_MS)
        _write_state(state_path, "UserPromptSubmit", "s1", 2.0)
        qtbot.waitUntil(lambda: win.anim == Anim.TYPING, timeout=TIMEOUT_MS)
        _write_state(state_path, "SessionEnd", "s1", 3.0)
        qtbot.waitUntil(lambda: win.anim == Anim.SLEEPING, timeout=TIMEOUT_MS)

        assert win.anim == Anim.SLEEPING


class TestAnimIntegration:
    def test_plays_desired_animation(
        self,
        app: QtWidgets.QApplication,
        qtbot: QtBot,
        single_instance_server_name: str,
    ) -> None:
        # No pre-seeded file → genuinely cold first event.
        win = run(
            app,
            ["--anim", "annoyed"],
            single_instance_name=single_instance_server_name,
        )
        qtbot.addWidget(win)

        qtbot.waitUntil(lambda: win.anim == Anim.ANNOYED, timeout=TIMEOUT_MS)

        assert win.anim == Anim.ANNOYED


class TestDemoIntegration:
    def test_plays_demo_in_cycle(
        self,
        app: QtWidgets.QApplication,
        qtbot: QtBot,
        single_instance_server_name: str,
    ) -> None:
        win = run(
            app,
            ["--demo"],
            single_instance_name=single_instance_server_name,
            poll_interval_s=POLL_INTERVAL_SECONDS,
        )
        qtbot.addWidget(win)

        qtbot.waitUntil(lambda: win.anim == Anim.SLEEPING, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: win.anim == Anim.WAKING, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: win.anim == Anim.TYPING, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: win.anim == Anim.ALARMED, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: win.anim == Anim.CELEBRATE, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: win.anim == Anim.ANNOYED, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: win.anim == Anim.SLEEPING, timeout=TIMEOUT_MS)

        assert win.anim == Anim.SLEEPING


def _write_state(path: Path, event: str, sid: str, ts: float) -> None:
    path.write_text(
        json.dumps(
            {"last_active": {"event": event, "session_id": sid, "timestamp": ts}}
        )
    )
