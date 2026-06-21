"""Tests TDD pour clip_display_y_offset — TC-CDO-U-01 à TC-CDO-U-11, TC-CDO-I-01 à TC-CDO-I-03."""

import os
from unittest.mock import MagicMock

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()

from src.entities.base import BaseEntity
from src.entities.groups import CameraGroup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity():
    e = BaseEntity(pos=(160, 160))
    e.image = pygame.Surface((32, 48))
    return e


def _clip_vm(visual_y_offset: int = 8, clip_display_y_offset: int = 0):
    return {
        "clip": True,
        "visual_y_offset": visual_y_offset,
        "clip_display_y_offset": clip_display_y_offset,
        "stair_direction": "down,left",
    }


def _no_clip_vm():
    return {
        "clip": False,
        "visual_y_offset": 0,
        "clip_display_y_offset": 0,
        "stair_direction": "up,left",
    }


# ---------------------------------------------------------------------------
# TC-CDO-U-01 : Init → les 3 champs display_offset à 0.0
# ---------------------------------------------------------------------------


class TestClipDisplayOffsetInit:
    def test_TC_CDO_U_01_init_fields_zero(self):
        """TC-CDO-U-01 : Tous les champs clip_display_offset initialisés à 0."""
        e = _make_entity()
        assert e.current_stair_clip_display_offset == 0.0
        assert e.stair_start_clip_display_offset == 0.0
        assert e.stair_target_clip_display_offset == 0.0


# ---------------------------------------------------------------------------
# TC-CDO-U-02 : _init_stair_clip_properties avec tile clip + display_offset=12
# ---------------------------------------------------------------------------


class TestInitStairClipProperties:
    def test_TC_CDO_U_02_clip_tile_sets_target_display_offset(self):
        """TC-CDO-U-02 : clip=True, clip_display_y_offset=12 → stair_target_clip_display_offset=12."""
        e = _make_entity()
        vm = _clip_vm(visual_y_offset=8, clip_display_y_offset=12)
        e._init_stair_clip_properties(vm)
        assert e.stair_target_clip_display_offset == 12.0

    def test_TC_CDO_U_03_no_clip_tile_resets_target_display_offset(self):
        """TC-CDO-U-03 : clip=False → stair_target_clip_display_offset=0."""
        e = _make_entity()
        e.current_stair_clip_display_offset = 10.0
        e._init_stair_clip_properties(_no_clip_vm())
        assert e.stair_target_clip_display_offset == 0.0

    def test_TC_CDO_U_04_none_vm_resets_target_display_offset(self):
        """TC-CDO-U-04 : target_vm=None → stair_target_clip_display_offset=0."""
        e = _make_entity()
        e.current_stair_clip_display_offset = 7.0
        e._init_stair_clip_properties(None)
        assert e.stair_target_clip_display_offset == 0.0

    def test_start_preserved_as_current(self):
        """_init copie current → start avant d'affecter target."""
        e = _make_entity()
        e.current_stair_clip_display_offset = 6.0
        e._init_stair_clip_properties(_clip_vm(clip_display_y_offset=20))
        assert e.stair_start_clip_display_offset == 6.0


# ---------------------------------------------------------------------------
# TC-CDO-U-05/06 : update_stair_offset en mode idle
# ---------------------------------------------------------------------------


class TestUpdateStairOffsetIdle:
    def test_TC_CDO_U_05_idle_clip_tile_sets_current(self):
        """TC-CDO-U-05 : idle sur tile clip + display_offset=10 → current=10."""
        e = _make_entity()
        e.is_moving = False
        e._vertical_move = _clip_vm(visual_y_offset=8, clip_display_y_offset=10)
        e.update_stair_offset()
        assert e.current_stair_clip_display_offset == 10.0

    def test_TC_CDO_U_06_idle_no_clip_resets_current(self):
        """TC-CDO-U-06 : idle sur tile non-clip → current=0."""
        e = _make_entity()
        e.is_moving = False
        e.current_stair_clip_display_offset = 15.0
        e._vertical_move = _no_clip_vm()
        e.update_stair_offset()
        assert e.current_stair_clip_display_offset == 0.0

    def test_idle_no_vm_resets_current(self):
        """idle, vm=None → current=0."""
        e = _make_entity()
        e.is_moving = False
        e.current_stair_clip_display_offset = 5.0
        e._vertical_move = None
        e.update_stair_offset()
        assert e.current_stair_clip_display_offset == 0.0


# ---------------------------------------------------------------------------
# TC-CDO-U-07 : update_stair_offset en mode moving (interpolation)
# ---------------------------------------------------------------------------


class TestUpdateStairOffsetMoving:
    def test_TC_CDO_U_07_moving_50pct_interpolates(self):
        """TC-CDO-U-07 : moving à 50% → current_stair_clip_display_offset = 10 (mi-chemin 0→20)."""
        e = _make_entity()
        e.is_moving = True
        e.stair_move_distance = 32.0
        e.stair_start_clip_display_offset = 0.0
        e.stair_target_clip_display_offset = 20.0
        # 50% progress → curr_dist = 16 (half remaining)
        e.pos = pygame.math.Vector2(160, 160)
        e.target_pos = pygame.math.Vector2(160 + 32, 160)
        # Simulate 50% progress by positioning pos at midpoint
        e.pos = pygame.math.Vector2(160 + 16, 160)
        # stubs needed by the stair_offset (stair_start/target_offset)
        e.stair_start_offset = 0.0
        e.stair_target_offset = 0.0
        e.stair_start_clip = 0.0
        e.stair_target_clip = 0.0
        e.update_stair_offset()
        assert abs(e.current_stair_clip_display_offset - 10.0) < 0.01

    def test_TC_CDO_U_08_moving_zero_distance_fallback(self):
        """TC-CDO-U-08 : moving, stair_move_distance=0 → current = target."""
        e = _make_entity()
        e.is_moving = True
        e.stair_move_distance = 0.0
        e.stair_target_clip_display_offset = 16.0
        e.stair_target_offset = 0.0
        e.stair_target_clip = 0.0
        e.update_stair_offset()
        assert e.current_stair_clip_display_offset == 16.0


# ---------------------------------------------------------------------------
# TC-CDO-U-09/10/11 : groups.CameraGroup.custom_draw
# ---------------------------------------------------------------------------


class TestCustomDrawClipDisplayOffset:
    def _make_cg(self):
        cg = CameraGroup()
        cg.offset = pygame.math.Vector2(0, 0)
        return cg

    def _make_sprite(self, clip_val: float, display_offset: float):
        sprite = MagicMock()
        sprite.image = pygame.Surface((32, 48))
        sprite.rect = pygame.Rect(0, 0, 32, 48)
        sprite.depth = 1
        sprite.is_moving = False
        sprite.current_stair_clip = clip_val
        sprite.current_stair_clip_display_offset = display_offset
        sprite.current_stair_offset = 0.0
        return sprite

    def test_TC_CDO_U_09_clipped_blit_uses_display_offset(self):
        """TC-CDO-U-09 : clip=16, display_offset=8 → blit dest Y décalé de -8."""
        cg = self._make_cg()
        sprite = self._make_sprite(clip_val=16.0, display_offset=8.0)
        surface = MagicMock()
        surface.get_rect.return_value = pygame.Rect(0, 0, 800, 600)

        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            cg, "get_sorted_sprites", return_value=[sprite]
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            cg, "sprites", return_value=[sprite]
        ):
            cg.custom_draw(surface)

        assert surface.blit.called
        call_args = surface.blit.call_args
        dest = call_args[0][1]  # positional arg 1 = dest
        area = call_args[1].get("area") or (call_args[0][2] if len(call_args[0]) > 2 else None)
        # dest Y doit être décalé de -8 par rapport à la position visuelle
        assert dest[1] == -8
        # area = Rect(0, 0, 32, 48-16=32)
        assert area == pygame.Rect(0, 0, 32, 32)

    def test_TC_CDO_U_10_no_clip_display_offset_ignored(self):
        """TC-CDO-U-10 : clip=0, display_offset=8 → blit sans area, dest Y non décalé."""
        cg = self._make_cg()
        sprite = self._make_sprite(clip_val=0.0, display_offset=8.0)
        surface = MagicMock()
        surface.get_rect.return_value = pygame.Rect(0, 0, 800, 600)

        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            cg, "get_sorted_sprites", return_value=[sprite]
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            cg, "sprites", return_value=[sprite]
        ):
            cg.custom_draw(surface)

        assert surface.blit.called
        call_args = surface.blit.call_args
        # blit normal : 2 args positionnels seulement (image, dest), pas d'area
        assert len(call_args[0]) == 2
        dest = call_args[0][1]
        assert dest[1] == 0  # Y non décalé

    def test_TC_CDO_U_11_missing_attr_defaults_zero(self):
        """TC-CDO-U-11 : sprite sans current_stair_clip_display_offset → offset 0."""
        cg = self._make_cg()
        sprite = MagicMock(spec=[])  # pas d'attributs automatiques
        sprite.image = pygame.Surface((32, 32))
        sprite.rect = pygame.Rect(0, 0, 32, 32)
        sprite.depth = 1
        sprite.is_moving = False
        sprite.current_stair_clip = 8.0
        sprite.current_stair_offset = 0.0
        # current_stair_clip_display_offset absent → getattr default 0

        surface = MagicMock()
        surface.get_rect.return_value = pygame.Rect(0, 0, 800, 600)

        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            cg, "get_sorted_sprites", return_value=[sprite]
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            cg, "sprites", return_value=[sprite]
        ):
            cg.custom_draw(surface)

        assert surface.blit.called
        call_args = surface.blit.call_args
        dest = call_args[0][1]
        # Y inchangé (display_offset == 0 par défaut)
        assert dest[1] == 0


# ---------------------------------------------------------------------------
# TC-CDO-I-01/02 : manager.get_vertical_move_props (integration)
# ---------------------------------------------------------------------------


class TestManagerClipDisplayOffsetIntegration:
    def _make_manager(self, clip_display_y_offset: int | None):
        from src.map.layout import LayoutStrategy
        from src.map.manager import MapManager

        props = {
            "direction": "down,left",
            "clip": True,
            "visual_y_offset": 8,
        }
        if clip_display_y_offset is not None:
            props["clip_display_y_offset"] = clip_display_y_offset

        tile = MagicMock()
        tile.depth = 0
        tile.walkable = True
        tile.direction_flags = {"any"}
        tile.frames = None
        tile.properties = props

        layout = MagicMock(spec=LayoutStrategy)
        layout.tile_size = 32

        map_data = {
            "layers": {1: [[1]]},
            "tiles": {1: tile},
            "layer_names": {1: "ground"},
            "layer_order": [1],
            "layer_order_values": {1: 0},
            "entities": [],
            "properties": {},
        }
        return MapManager(map_data, layout)

    def test_TC_CDO_I_01_clip_tile_exposes_display_offset(self):
        """TC-CDO-I-01 : get_vertical_move_props sur tile clip → dict contient clip_display_y_offset."""
        mgr = self._make_manager(clip_display_y_offset=5)
        result = mgr.get_vertical_move_props(0, 0)
        assert result is not None
        assert "clip_display_y_offset" in result
        assert result["clip_display_y_offset"] == 5

    def test_TC_CDO_I_02_missing_property_defaults_zero(self):
        """TC-CDO-I-02 : tile sans clip_display_y_offset → default 0."""
        mgr = self._make_manager(clip_display_y_offset=None)
        result = mgr.get_vertical_move_props(0, 0)
        assert result is not None
        assert result.get("clip_display_y_offset", 0) == 0
