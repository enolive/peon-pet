"""Tests for atlas/anim config invariants."""

import pytest

from peon_pet.config import ANIM_CONFIG, ATLAS_LAYOUTS, Anim


def test_every_anim_has_a_config() -> None:
    assert set(ANIM_CONFIG) == set(Anim)


@pytest.mark.parametrize("atlas", list(ATLAS_LAYOUTS), ids=list(ATLAS_LAYOUTS))
def test_every_anim_row_fits_every_atlas(atlas: str) -> None:
    rows = ATLAS_LAYOUTS[atlas].rows
    oversize = [a for a, c in ANIM_CONFIG.items() if c.row >= rows]

    assert oversize == [], f"anims {oversize} exceed {rows} rows of atlas {atlas!r}"
