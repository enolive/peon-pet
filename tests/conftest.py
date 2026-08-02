"""Shared pytest configuration and fixtures.

This file MUST be named `conftest.py` — pytest auto-loads files with that exact
name while walking up from the test directory, registering hooks and fixtures
with its plugin manager before any test is collected or imported.

"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


def pytest_configure() -> None:
    # render Qt offscreen for test purposes
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
def single_instance_server_name() -> Iterator[str]:
    """Yield a unique single-instance server name; remove registered local server it after the test."""
    import uuid

    from PyQt6 import QtNetwork

    name = f"peon-pet-test-{uuid.uuid4().hex}"
    yield name
    QtNetwork.QLocalServer.removeServer(name)
