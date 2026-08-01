"""Shared pytest configuration and fixtures.

This file MUST be named `conftest.py` — pytest auto-loads files with that exact
name while walking up from the test directory, registering hooks and fixtures
with its plugin manager before any test is collected or imported.

"""

import os
from collections.abc import Iterator

import pytest


def pytest_configure() -> None:
    # render Qt offscreen for test purposes
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def single_instance_server_name() -> Iterator[str]:
    """Yield a unique single-instance server name; remove it after the test.

    The name is unique per test (uuid4) so claims never collide across tests.
    `QLocalServer.removeServer` is static, so teardown needs no running app.
    Shared by the single-instance unit tests and the --watch integration test.
    """
    import uuid

    from PyQt6 import QtNetwork

    name = f"peon-pet-test-{uuid.uuid4().hex}"
    yield name
    QtNetwork.QLocalServer.removeServer(name)
