"""Tests for atlas/anim config invariants."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from peon_pet.config import (
    ANIM_CONFIG,
    ATLAS_LAYOUTS,
    Anim,
    FlashConfig,
    ParticleConfig,
    Rgb,
    Rgba,
    ShakeConfig,
)

_color_byte: SearchStrategy[int] = st.integers(min_value=0, max_value=255)
_alpha: SearchStrategy[float] = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)
_rgb: SearchStrategy[Rgb] = st.builds(Rgb, r=_color_byte, g=_color_byte, b=_color_byte)


@st.composite
def _hex_colors(draw: st.DrawFn) -> tuple[Rgb, str]:
    rgb = draw(_rgb)
    use_hash = draw(st.booleans())
    upper = draw(st.booleans())
    body = f"{rgb.r:02x}{rgb.g:02x}{rgb.b:02x}"
    if upper:
        body = body.upper()
    text = f"#{body}" if use_hash else body
    return rgb, text


def test_every_anim_has_a_config() -> None:
    assert set(ANIM_CONFIG) == set(Anim)


@pytest.mark.parametrize("atlas", list(ATLAS_LAYOUTS), ids=list(ATLAS_LAYOUTS))
def test_every_anim_row_fits_every_atlas(atlas: str) -> None:
    rows = ATLAS_LAYOUTS[atlas].rows
    oversize = [a for a, c in ANIM_CONFIG.items() if c.row >= rows]

    assert oversize == [], f"anims {oversize} exceed {rows} rows of atlas {atlas!r}"


def test_reaction_anims_have_flash() -> None:
    with_flash = _filter_anims_by_effect(FlashConfig)

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
    with_shake = _filter_anims_by_effect(ShakeConfig)

    assert with_shake == {Anim.ANNOYED}


def test_only_celebrate_has_particles() -> None:
    with_particles = _filter_anims_by_effect(ParticleConfig)

    assert with_particles == {Anim.CELEBRATE}


class TestRgbFromHex:
    def test_parses_hash_prefixed_rgb(self) -> None:
        sut = Rgb.from_hex("#66CCFF")

        assert sut == Rgb(0x66, 0xCC, 0xFF)

    def test_parses_without_hash(self) -> None:
        sut = Rgb.from_hex("FFCC00")

        assert sut == Rgb(0xFF, 0xCC, 0x00)

    def test_rejects_bad_length(self) -> None:
        with pytest.raises(ValueError, match="RRGGBB"):
            _ = Rgb.from_hex("#FFF")

    @pytest.mark.parametrize(
        argnames="value", argvalues=["bullshit", "", "#GGHHII", "GGHHII"]
    )
    def test_rejects_non_hex(self, value: str) -> None:
        with pytest.raises(ValueError):
            _ = Rgb.from_hex(value)

    @given(case=_hex_colors())
    def test_valid_hex_maps_to_channels(self, case: tuple[Rgb, str]) -> None:
        rgb, color = case

        assert Rgb.from_hex(color) == rgb


class TestRgba:
    @given(case=_hex_colors(), a=_alpha)
    def test_from_hex_maps_rgb_and_alpha(self, case: tuple[Rgb, str], a: float) -> None:
        rgb, color = case

        sut = Rgba.from_hex(color, a=a)

        assert sut.rgb == rgb
        assert sut.a == a

    @given(rgb=_rgb, a=_alpha)
    def test_from_rgb_preserves_parts(self, rgb: Rgb, a: float) -> None:
        sut = Rgba.from_rgb(rgb, a=a)

        assert sut.rgb is rgb
        assert sut.a == a

    @given(case=_hex_colors())
    def test_default_alpha_is_opaque(self, case: tuple[Rgb, str]) -> None:
        _, color = case

        assert Rgba.from_hex(color).a == 1.0


def _filter_anims_by_effect(config: type) -> set[Anim]:
    return {
        a
        for a, c in ANIM_CONFIG.items()
        if any(isinstance(e, config) for e in c.effects)
    }
