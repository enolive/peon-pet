"""Tests for atlas/anim config invariants."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from peon_pet.config import (
    ANIM_CONFIG,
    ATLAS_LAYOUTS,
    Anim,
    FlashConfig,
    ParticleConfig,
    Rgba,
    ShakeConfig,
)


def test_every_anim_has_a_config() -> None:
    assert set(ANIM_CONFIG) == set(Anim)


@pytest.mark.parametrize("atlas", list(ATLAS_LAYOUTS), ids=list(ATLAS_LAYOUTS))
def test_every_anim_row_fits_every_atlas(atlas: str) -> None:
    rows = ATLAS_LAYOUTS[atlas].rows
    oversize = [a for a, c in ANIM_CONFIG.items() if c.row >= rows]

    assert oversize == [], f"anims {oversize} exceed {rows} rows of atlas {atlas!r}"


def test_reaction_anims_have_flash() -> None:
    with_flash = {
        a
        for a, c in ANIM_CONFIG.items()
        if any(isinstance(e, FlashConfig) for e in c.effects)
    }

    assert with_flash == {
        Anim.WAKING,
        Anim.ALARMED,
        Anim.CELEBRATE,
        Anim.ANNOYED,
    }


def test_base_anims_have_no_effects() -> None:
    assert ANIM_CONFIG[Anim.SLEEPING].effects == ()
    assert ANIM_CONFIG[Anim.TYPING].effects == ()


def test_only_annoyed_has_shake() -> None:
    with_shake = {
        a
        for a, c in ANIM_CONFIG.items()
        if any(isinstance(e, ShakeConfig) for e in c.effects)
    }

    assert with_shake == {Anim.ANNOYED}


def test_only_celebrate_has_particles() -> None:
    with_particles = {
        a
        for a, c in ANIM_CONFIG.items()
        if any(isinstance(e, ParticleConfig) for e in c.effects)
    }

    assert with_particles == {Anim.CELEBRATE}
    particles = next(
        e for e in ANIM_CONFIG[Anim.CELEBRATE].effects if isinstance(e, ParticleConfig)
    )
    assert particles.count == 30
    assert particles.duration == 1.2


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

    @given(
        r=st.integers(min_value=0, max_value=255),
        g=st.integers(min_value=0, max_value=255),
        b=st.integers(min_value=0, max_value=255),
        a=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        use_hash=st.booleans(),
        upper=st.booleans(),
    )
    def test_valid_hex_maps_to_channels(
        self,
        r: int,
        g: int,
        b: int,
        a: float,
        use_hash: bool,
        upper: bool,
    ) -> None:
        body = f"{r:02x}{g:02x}{b:02x}"
        if upper:
            body = body.upper()
        color = f"#{body}" if use_hash else body

        sut = Rgba.from_hex(color, a=a)

        assert sut.r == pytest.approx(r / 255)
        assert sut.g == pytest.approx(g / 255)
        assert sut.b == pytest.approx(b / 255)
        assert sut.a == a
