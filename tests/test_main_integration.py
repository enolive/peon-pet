"""Integration tests of the wired --watch chain: watcher -> state -> seam -> window.

These exercise the full `run(app, ...])` path end-to-end with
offscreen Qt, no display, and no real peon-ping.
"""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from PySide6 import QtWidgets
from pytestqt.qtbot import QtBot

from peon_pet.__main__ import run
from peon_pet.cli import parse_args
from peon_pet.config import Anim
from peon_pet.window import PetWindow

POLL_INTERVAL_SECONDS = 0.05
TIMEOUT_MS = 5000


class TestWatchIntegration:
    def test_reacts_to_a_full_session_lifecycle(
        self,
        single_instance_app: QtWidgets.QApplication,
        qtbot: QtBot,
        tmp_path: Path,
        single_instance_server_name: str,
    ) -> None:
        state_path = tmp_path / ".state.json"
        # No pre-seeded file -> genuinely cold first event.
        win = _run(
            single_instance_app,
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
        single_instance_app: QtWidgets.QApplication,
        qtbot: QtBot,
        tmp_path: Path,
        single_instance_server_name: str,
    ) -> None:
        state_path = tmp_path / ".state.json"
        # Pre-seed a Stop: a cold start on an event that registers the session
        # announces WAKING (not CELEBRATE) — the cold-start override.
        _write_state(state_path, "Stop", "s1", 1.0)
        win = _run(
            single_instance_app,
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
        single_instance_app: QtWidgets.QApplication,
        qtbot: QtBot,
        single_instance_server_name: str,
    ) -> None:
        # No pre-seeded file -> genuinely cold first event.
        win = _run(
            single_instance_app,
            ["--anim", "annoyed"],
            single_instance_name=single_instance_server_name,
        )
        qtbot.addWidget(win)

        qtbot.waitUntil(lambda: win.anim == Anim.ANNOYED, timeout=TIMEOUT_MS)

        assert win.anim == Anim.ANNOYED

    def test_bad_anim_raises_error(
        self,
        single_instance_app: QtWidgets.QApplication,
        single_instance_server_name: str,
    ) -> None:
        with pytest.raises(ValueError):
            _ = _run(
                single_instance_app,
                ["--anim", "bogus"],
                single_instance_name=single_instance_server_name,
            )

        assert PetWindow not in single_instance_app.topLevelWidgets(), (
            "application should close instantly"
        )


class TestDemoIntegration:
    def test_plays_demo_in_cycle(
        self,
        single_instance_app: QtWidgets.QApplication,
        qtbot: QtBot,
        single_instance_server_name: str,
    ) -> None:
        win = _run(
            single_instance_app,
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


def _run(
    app: QtWidgets.QApplication,
    argv: Sequence[str],
    *,
    single_instance_name: str,
    poll_interval_s: float = POLL_INTERVAL_SECONDS,
) -> PetWindow:
    return run(
        app,
        parse_args(argv),
        single_instance_name=single_instance_name,
        poll_interval_s=poll_interval_s,
    )


def _write_state(path: Path, event: str, sid: str, ts: float) -> None:
    _ = path.write_text(
        json.dumps(
            {"last_active": {"event": event, "session_id": sid, "timestamp": ts}}
        )
    )
