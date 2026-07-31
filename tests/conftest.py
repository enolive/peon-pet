"""Shared pytest configuration and fixtures.

This file MUST be named `conftest.py` — pytest auto-loads files with that exact
name while walking up from the test directory, registering hooks and fixtures
with its plugin manager before any test is collected or imported.

"""

import os


def pytest_configure() -> None:
    # render Qt headless for test purposes
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
