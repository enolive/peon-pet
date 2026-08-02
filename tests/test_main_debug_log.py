"""Test for the -vv debug-log file written by `_configure_logging`."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PyQt6 import QtWidgets
from pytestqt.qtbot import QtBot

from peon_pet.__main__ import DEBUG_LOG_REL, run
from tests.assertions import wait_until

TIMEOUT_S = 5.0


@pytest.fixture
def app() -> Iterator[QtWidgets.QApplication]:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert isinstance(app, QtWidgets.QApplication)
    yield app
    for key in ("peon_pet_watcher", "peon_pet_demo"):
        obj = app.property(key)
        if obj is not None:
            obj.stop()


def test_vv_writes_debug_records_to_state_dir(
    app: QtWidgets.QApplication,
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    single_instance_server_name: str,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    log_path = tmp_path / DEBUG_LOG_REL

    win = run(
        app,
        ["--anim", "annoyed", "-vv"],
        single_instance_name=single_instance_server_name,
    )
    qtbot.addWidget(win)

    assert wait_until(lambda: "annoyed" in _read(log_path), timeout_s=TIMEOUT_S)
    text = _read(log_path)
    assert " DEBUG " in text, f"no DEBUG records in log:\n{text}"


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""
