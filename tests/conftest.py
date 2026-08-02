"""Shared pytest configuration and fixtures.

This file MUST be named `conftest.py` — pytest auto-loads files with that exact
name while walking up from the test directory, registering hooks and fixtures
with its plugin manager before any test is collected or imported.

"""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, cast

import pytest
from PySide6 import QtNetwork, QtWidgets


class _Stoppable(Protocol):
    def stop(self) -> None: ...


def pytest_configure() -> None:
    # render Qt offscreen for test purposes
    _ = os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _ = os.environ.setdefault("PYTEST_QT_API", "pyside6")


@pytest.fixture(autouse=True)
def isolated_xdg_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test XDG_CONFIG_HOME so Prefs() never reads the developer's real config.

    Every test that touches PetWindow or run() transitively reads the config via
    Prefs(); a developer's real `~/.config/peon-pet/config.json` (custom atlas,
    loop count, saved position) would otherwise leak in and influence the
    observed behavior. `test_prefs.py` overrides this itself with its own
    monkeypatched tmp_path -- that's fine: its explicit setenv wins, monkeypatch
    restores on teardown, and this autouse fixture reasserts on the next test.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


@pytest.fixture
def single_instance_app() -> Iterator[QtWidgets.QApplication]:
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
        obj = cast(_Stoppable | None, app.property(key))
        if obj is not None:
            # run() stashes watcher/demo here; stop so the next test is clean.
            obj.stop()


@pytest.fixture
def single_instance_server_name() -> Iterator[str]:
    """Yield a unique single-instance server name; remove registered local server it after the test."""
    import uuid

    name = f"peon-pet-test-{uuid.uuid4().hex}"
    yield name
    _ = QtNetwork.QLocalServer.removeServer(name)
