"""Tests for the -v / --verbose → logging-level mapping in __main__."""

import logging

from peon_pet.__main__ import _log_level


def test_default_verbosity_is_warning() -> None:
    assert _log_level(0) == logging.WARNING


def test_single_v_is_info() -> None:
    assert _log_level(1) == logging.INFO


def test_double_v_is_debug() -> None:
    assert _log_level(2) == logging.DEBUG


def test_verbosity_clamps_to_debug_past_two() -> None:
    assert _log_level(3) == logging.DEBUG
    assert _log_level(99) == logging.DEBUG
