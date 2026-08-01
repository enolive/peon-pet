"""Tests for __main__'s Qt-dependent wiring: single-instance claiming.

The pure CLI helpers live in cli.py (see test_cli.py). Only the Qt-dependent
wiring stays in __main__, and `claim_single_instance` is public so tests don't
trip `reportPrivateUsage`.
"""

import pytest
from PyQt6 import QtWidgets

from peon_pet.__main__ import claim_single_instance
from tests.assertions import does_not_raise


def test_first_claim_succeeds(
    qapp: QtWidgets.QApplication,
    single_instance_server_name: str,
) -> None:
    with does_not_raise():
        claim_single_instance(qapp, name=single_instance_server_name)


def test_second_claim_on_same_name_exits(
    qapp: QtWidgets.QApplication,
    single_instance_server_name: str,
) -> None:
    claim_single_instance(qapp, name=single_instance_server_name)

    with pytest.raises(SystemExit) as exc:
        claim_single_instance(qapp, name=single_instance_server_name)

    assert exc.value.code == 1
