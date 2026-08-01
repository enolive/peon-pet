"""Integration tests of the wired --watch chain: watcher → state → seam → window.

These exercise the full `run(app, ...])` path end-to-end with
offscreen Qt, no display, and no real peon-ping.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PyQt6 import QtWidgets
from pytestqt.qtbot import QtBot

from peon_pet.__main__ import run
from peon_pet.config import Anim
from peon_pet.window import PetWindow

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

    def test_bad_anim_raises_error(
        self,
        app: QtWidgets.QApplication,
        single_instance_server_name: str,
    ) -> None:
        with pytest.raises(ValueError):
            run(
                app,
                ["--anim", "bogus"],
                single_instance_name=single_instance_server_name,
            )

        assert PetWindow not in app.topLevelWidgets(), (
            "application should close instantly"
        )


class TestListEvents:
    def test_list_events_and_exits_immediately(
        self,
        app: QtWidgets.QApplication,
        single_instance_server_name: str,
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            run(
                app, ["--list-events"], single_instance_name=single_instance_server_name
            )

        assert exc.value.code == 0
        assert PetWindow not in app.topLevelWidgets(), (
            "application should close instantly"
        )


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
