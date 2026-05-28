"""RED tests — Bridge SFX : material, sfx_open, sfx_close on InteractiveEntity.

Spec: docs/game/specs/bridge-sfx-spec.md
Tests: UT-001 → UT-004
"""

import os
from unittest.mock import patch

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.display.init()

from src.entities.interactive import InteractiveEntity  # noqa: E402


def _make_bridge(
    sub_type="bridge",
    sfx="",
    sfx_open="",
    sfx_close="",
    sfx_ambient="",
    material="",
    is_on=True,
    is_passable=True,
):
    """Build a minimal bridge InteractiveEntity without disk assets."""
    group = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    with patch("src.entities.interactive.SpriteSheet") as mock_ss:
        mock_ss.return_value.valid = False
        entity = InteractiveEntity(
            pos=(100, 100),
            groups=[group],
            sub_type=sub_type,
            sprite_sheet="",
            position=0,
            depth=0,
            start_row=0,
            end_row=3,
            width=160,
            height=224,
            tiled_width=160,
            tiled_height=32,
            obstacles_group=obstacles,
            is_passable=is_passable,
            is_animated=False,
            is_on=is_on,
            halo_size=0,
            halo_color="[255, 255, 255]",
            halo_alpha=130,
            particles=False,
            particle_count=0,
            element_id="drawbridge",
            target_id=None,
            activate_from_anywhere=False,
            facing_direction=None,
            sfx=sfx,
            sfx_open=sfx_open,
            sfx_close=sfx_close,
            sfx_ambient=sfx_ambient,
            material=material,
            day_night_driven=False,
        )
    return entity


class TestBridgeSFXAttributes:
    """BRIDGE-U-001 → BRIDGE-U-006 — New properties are stored on the entity."""

    @pytest.mark.tc("BRIDGE-U-001")
    def test_sfx_open_stored_on_entity(self):
        """BRIDGE-U-001: sfx_open passed to constructor is accessible as entity.sfx_open."""
        entity = _make_bridge(sfx_open="bridge_open")
        assert entity.sfx_open == "bridge_open"

    @pytest.mark.tc("BRIDGE-U-002")
    def test_sfx_close_stored_on_entity(self):
        """BRIDGE-U-002: sfx_close passed to constructor is accessible as entity.sfx_close."""
        entity = _make_bridge(sfx_close="bridge_close")
        assert entity.sfx_close == "bridge_close"

    @pytest.mark.tc("BRIDGE-U-003")
    def test_material_stored_on_entity(self):
        """BRIDGE-U-003: material passed to constructor is accessible as entity.material."""
        entity = _make_bridge(material="wood")
        assert entity.material == "wood"

    @pytest.mark.tc("BRIDGE-U-004")
    def test_sfx_open_defaults_to_empty_string(self):
        """BRIDGE-U-004: When sfx_open is not provided, entity.sfx_open defaults to ''."""
        entity = _make_bridge()
        assert entity.sfx_open == ""

    @pytest.mark.tc("BRIDGE-U-005")
    def test_sfx_close_defaults_to_empty_string(self):
        """BRIDGE-U-005: When sfx_close is not provided, entity.sfx_close defaults to ''."""
        entity = _make_bridge()
        assert entity.sfx_close == ""

    @pytest.mark.tc("BRIDGE-U-006")
    def test_material_defaults_to_empty_string(self):
        """BRIDGE-U-006: When material is not provided, entity.material defaults to ''."""
        entity = _make_bridge()
        assert entity.material == ""

    def test_existing_sfx_still_works(self):
        """Regression: existing sfx attribute is unaffected by new attributes."""
        entity = _make_bridge(sfx="01-lever")
        assert entity.sfx == "01-lever"

    def test_all_three_properties_coexist(self):
        """All three new properties can be set simultaneously without conflict."""
        entity = _make_bridge(material="wood", sfx_open="bridge_down", sfx_close="bridge_up")
        assert entity.material == "wood"
        assert entity.sfx_open == "bridge_down"
        assert entity.sfx_close == "bridge_up"
