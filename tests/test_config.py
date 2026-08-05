"""Tests for atlas/anim config invariants."""

import pytest

from peon_pet.config import ANIM_CONFIG, ATLAS_LAYOUTS, Anim, AnimConfig, Rgba


def test_every_anim_has_a_config() -> None:
    assert set(ANIM_CONFIG) == set(Anim)


@pytest.mark.parametrize("atlas", list(ATLAS_LAYOUTS), ids=list(ATLAS_LAYOUTS))
def test_every_anim_row_fits_every_atlas(atlas: str) -> None:
    rows = ATLAS_LAYOUTS[atlas].rows
    oversize = [a for a, c in ANIM_CONFIG.items() if c.row >= rows]

    assert oversize == [], f"anims {oversize} exceed {rows} rows of atlas {atlas!r}"


def test_reaction_anims_have_flash() -> None:
    with_flash = {a for a, c in ANIM_CONFIG.items() if c.flash is not None}

    assert with_flash == {
        Anim.WAKING,
        Anim.ALARMED,
        Anim.CELEBRATE,
        Anim.ANNOYED,
    }


def test_base_anims_have_no_flash() -> None:
    assert ANIM_CONFIG[Anim.SLEEPING].flash is None
    assert ANIM_CONFIG[Anim.TYPING].flash is None


class TestRgbaFromHex:
    def test_parses_hash_prefixed_rgb(self) -> None:
        sut = Rgba.from_hex("#66CCFF", a=0.3)

        assert sut.r == pytest.approx(0x66 / 255)
        assert sut.g == pytest.approx(0xCC / 255)
        assert sut.b == pytest.approx(0xFF / 255)
        assert sut.a == 0.3

    def test_parses_without_hash(self) -> None:
        sut = Rgba.from_hex("FFCC00", a=0.5)

        assert sut.r == pytest.approx(1.0)
        assert sut.g == pytest.approx(0xCC / 255)
        assert sut.b == pytest.approx(0.0)
        assert sut.a == 0.5

    def test_default_alpha_is_opaque(self) -> None:
        sut = Rgba.from_hex("#FFFFFF")

        assert sut.a == 1.0

    def test_rejects_bad_length(self) -> None:
        with pytest.raises(ValueError, match="RRGGBB"):
            _ = Rgba.from_hex("#FFF")

    @pytest.mark.parametrize(
        argnames="value", argvalues=["bullshit", "", "#GGHHII", "GGHHII"]
    )
    def test_rejects_non_hex(self, value: str) -> None:
        with pytest.raises(ValueError):
            _ = Rgba.from_hex(value)
