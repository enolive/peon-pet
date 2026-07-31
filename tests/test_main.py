"""Tests for __main__'s Qt-dependent wiring: single-instance claiming.

The pure CLI helpers live in cli.py (see test_cli.py). Only the Qt-dependent
wiring stays in __main__, and `claim_single_instance` is public so tests don't
trip `reportPrivateUsage`.
"""

from collections.abc import Generator, Iterator
from contextlib import contextmanager

import pytest
from PyQt6 import QtWidgets

from peon_pet.__main__ import claim_single_instance


@pytest.fixture
def single_instance_server_name() -> Iterator[str]:
    """Yield a unique single-instance server name; remove it after the test.

    The name is unique per test (uuid4) so claims never collide across tests.
    `QLocalServer.removeServer` is static, so teardown needs no running app.
    """
    import uuid

    from PyQt6 import QtNetwork

    name = f"peon-pet-test-{uuid.uuid4().hex}"
    yield name
    QtNetwork.QLocalServer.removeServer(name)


class TestClaimSingleInstance:
    def test_first_claim_succeeds(
        self,
        qapp: QtWidgets.QApplication,
        single_instance_server_name: str,
    ) -> None:
        with _does_not_raise():
            claim_single_instance(qapp, name=single_instance_server_name)

    def test_second_claim_on_same_name_exits(
        self,
        qapp: QtWidgets.QApplication,
        single_instance_server_name: str,
    ) -> None:
        claim_single_instance(qapp, name=single_instance_server_name)

        with pytest.raises(SystemExit) as exc:
            claim_single_instance(qapp, name=single_instance_server_name)

        assert exc.value.code == 1


@contextmanager
def _does_not_raise() -> Generator[None, None, None]:
    """Assert the block does not raise. Symmetric with `pytest.raises`.

    Neither pytest nor the stdlib provides this on Python 3.10–3.12; it's a
    hand-rolled no-op context manager whose only job is to make the intent
    read explicitly at the call site.
    """
    yield
