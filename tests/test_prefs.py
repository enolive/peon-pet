"""Tests for Prefs: config resolution, validation, and position persistence."""

import json
from pathlib import Path

import pytest

from peon_pet.prefs import DEFAULT_ATLAS, DEFAULT_LOOPS, Prefs


def test_defaults_when_config_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sut = Prefs()

    assert sut.atlas == DEFAULT_ATLAS
    assert sut.loops == DEFAULT_LOOPS
    assert sut.position.current is None


def test_reads_valid_atlas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_config(tmp_path, {"atlas": "orc"})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sut = Prefs()

    assert sut.atlas == "orc"


def test_bad_atlas_name_raises_listing_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, {"atlas": "nope"})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    with pytest.raises(ValueError) as exc:
        Prefs()

    msg = str(exc.value)
    assert "nope" in msg
    assert "orc" in msg


def test_reads_loops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_config(tmp_path, {"loops": 5})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sut = Prefs()

    assert sut.loops == 5


@pytest.mark.parametrize("loops", [0, -1, "three", 1.5])
def test_loops_defaults_when_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, loops: object
) -> None:
    _write_config(tmp_path, {"loops": loops})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sut = Prefs()

    assert sut.loops == DEFAULT_LOOPS


def test_position_save_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    sut = Prefs()
    assert sut.position.current is None

    sut.position.save((123, 456))

    assert sut.position.current == (123, 456)
    re_read = Prefs()
    assert re_read.position.current == (123, 456)


def test_position_save_preserves_other_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(tmp_path, {"atlas": "orc", "loops": 5})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    sut = Prefs()

    sut.position.save((10, 20))

    re_read = Prefs()
    assert re_read.atlas == "orc"
    assert re_read.loops == 5
    assert re_read.position.current == (10, 20)


@pytest.mark.parametrize(
    "window",
    [{}, None, {"x": 1}, {"x": "1", "y": 2}],
    ids=["empty", "none", "partial", "invalid"],
)
def test_position_defaults_to_none_on_invalid_window_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, window: object
) -> None:
    _write_config(tmp_path, {"window": window})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    sut = Prefs()

    assert sut.position.current is None


def _write_config(tmp_path: Path, data: dict[str, object]) -> None:
    cfg = tmp_path / "peon-pet" / "config.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(data))
