import os
from unittest.mock import MagicMock

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.config import Settings
from src.entities.base import BaseEntity
from src.map.manager import MapManager


class TestLadderMovementUnit:
    @pytest.fixture
    def setup_map_manager(self):
        """Builds a helper to create MapManager with custom tile properties."""

        def _create(tile_properties=None, tx=1, ty=1, map_w=5, map_h=5):
            tile_id = 99
            grid = [[0] * map_w for _ in range(map_h)]
            grid[ty][tx] = tile_id

            layout = MagicMock()
            layout.to_world.return_value = (tx, ty)
            layout.tile_size = 32

            tile = MagicMock()
            tile.properties = tile_properties or {}

            map_data = {
                "layers": {"layer_0": grid},
                "tiles": {tile_id: tile},
                "layer_names": {},
                "entities": [],
                "layer_order": ["layer_0"],
                "layer_order_values": {"layer_0": 0},
                "properties": {},
            }
            mm = MapManager(map_data, layout)
            mm.width = map_w
            mm.height = map_h
            return mm

        return _create

    def _make_entity_on_ladder(self, mm, movement_type="ladder"):
        """Helper: create entity at (1,1) with mocked ladder props."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm
        current_props = {
            "movement_type": movement_type,
            "walkable": True,
            "stair_direction": "ladder" if movement_type == "ladder" else "",
        }
        mm.get_vertical_move_props = MagicMock(
            side_effect=lambda x, y: current_props if (x == 1 and y == 1) else None
        )
        return entity

    def test_ut_ladder_001_horizontal_input_blocked(self, setup_map_manager):
        """UT-LADDER-001: horizontal inputs (Left/Right) are ignored on a ladder tile."""
        mm = setup_map_manager()
        entity = self._make_entity_on_ladder(mm)
        entity.direction = pygame.math.Vector2(1, 0)  # Right
        entity.start_move()

        # Should be blocked, direction reset to 0
        assert entity.direction == pygame.math.Vector2(0, 0)
        assert entity.is_moving is False

    def test_ut_ladder_002_vertical_input_allowed(self, setup_map_manager):
        """UT-LADDER-002: vertical inputs (Up/Down) are allowed on a ladder tile."""
        mm = setup_map_manager()
        entity = self._make_entity_on_ladder(mm)
        entity.direction = pygame.math.Vector2(0, -1)  # Up
        entity.start_move()

        # Should be allowed, moving to target_pos (48, 16)
        assert entity.direction == pygame.math.Vector2(0, -1)
        assert entity.target_pos == pygame.math.Vector2(48, 16)
        assert entity.is_moving is True
