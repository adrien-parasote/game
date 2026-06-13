import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.config import Settings
from src.entities.base import BaseEntity
from src.map.manager import MapManager


class TestStairMovementUnit:
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

    def test_ut_001_get_vertical_move_props_stair_right(self, setup_map_manager):
        """UT-001: get_vertical_move_props(tx, ty) returns properties for right stair."""
        mm = setup_map_manager({
            "stair_direction": "right",
            "movement_type": "stair",
            "visual_y_offset": -12,
            "stair_half": False,
        })
        props = mm.get_vertical_move_props(1, 1)
        assert props == {
            "stair_direction": "right",
            "movement_type": "stair",
            "stair_half": False,
            "visual_y_offset": -12,
        }

    def test_ut_002_get_vertical_move_props_none_on_normal_tile(self, setup_map_manager):
        """UT-002: get_vertical_move_props(tx, ty) returns None on a tile without stair_direction."""
        mm = setup_map_manager({"walkable": True})
        props = mm.get_vertical_move_props(1, 1)
        assert props is None

    def test_ut_003_get_vertical_move_props_out_of_bounds(self, setup_map_manager):
        """UT-003: get_vertical_move_props(-1, 0) returns None (bounds check)."""
        mm = setup_map_manager({"stair_direction": "right"})
        props = mm.get_vertical_move_props(-1, 0)
        assert props is None

    def test_ut_004_get_vertical_move_props_no_stair_confusion(self, setup_map_manager):
        """UT-004: get_vertical_move_props(tx, ty) returns None if direction is set but not stair_direction."""
        mm = setup_map_manager({"direction": "right"})
        props = mm.get_vertical_move_props(1, 1)
        assert props is None

    def _make_entity_on_stair(self, mm, stair_dir, stair_half, visual_y_offset=0):
        """Helper: create entity at (1,1) with mocked stair props."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm
        # Default: current tile is stair, target tiles return None (flat floor)
        current_props = {
            "stair_direction": stair_dir,
            "movement_type": "stair",
            "stair_half": stair_half,
            "visual_y_offset": visual_y_offset,
        }
        mm.get_vertical_move_props = MagicMock(side_effect=lambda x, y: (
            current_props if (x == 1 and y == 1) else None
        ))
        return entity

    # ── UT-005a: right stair, lower half (stair_half=False), input right ─────────
    def test_ut_005a_right_stair_lower_half_input_right(self, setup_map_manager):
        """UT-005a: stair_half=False + input (1,0) on right stair → flat (1,0)."""
        mm = setup_map_manager()
        entity = self._make_entity_on_stair(mm, "right", False)
        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(1, 0)
        assert entity.target_pos == pygame.math.Vector2(80, 48)
        assert entity.is_moving is True

    # ── UT-005b: right stair, upper half (stair_half=True), input right ──────────
    def test_ut_005b_right_stair_upper_half_input_right(self, setup_map_manager):
        """UT-005b: stair_half=True + input (1,0) on right stair → diagonal (1,-1)."""
        mm = setup_map_manager()
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        # Current tile: stair_half=True; target (2,0) is also a stair
        current_props = {"stair_direction": "right", "movement_type": "stair", "stair_half": True, "visual_y_offset": -16}
        target_props  = {"stair_direction": "right", "movement_type": "stair", "stair_half": False, "visual_y_offset": 0}
        mm.get_vertical_move_props = MagicMock(side_effect=lambda x, y: (
            current_props if (x == 1 and y == 1) else
            target_props  if (x == 2 and y == 0) else None
        ))

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(1, -1)
        assert entity.target_pos == pygame.math.Vector2(80, 16)
        assert entity.is_moving is True

    # ── UT-006a: right stair, upper half, input left → step-off flat ─────────────
    def test_ut_006a_right_stair_upper_half_input_left_stepoff(self, setup_map_manager):
        """UT-006a: stair_half=True + input (-1,0) on right stair + target is flat → flat (-1,0)."""
        mm = setup_map_manager()
        entity = self._make_entity_on_stair(mm, "right", True)
        # Target (0,1) returns None (flat floor) → step-off rule
        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, 0)
        assert entity.target_pos == pygame.math.Vector2(16, 48)
        assert entity.is_moving is True

    # ── UT-006b: right stair, lower half, input left → diagonal ───────────
    def test_ut_006b_right_stair_lower_half_input_left_diagonal(self, setup_map_manager):
        """UT-006b: stair_half=False + input (-1,0) on right stair → diagonal (-1,1)."""
        mm = setup_map_manager()
        current_props = {"stair_direction": "right", "movement_type": "stair", "stair_half": False, "visual_y_offset": 0}
        target_props  = {"stair_direction": "right", "movement_type": "stair", "stair_half": True, "visual_y_offset": -16}
        mm.get_vertical_move_props = MagicMock(side_effect=lambda x, y: (
            current_props if (x == 1 and y == 1) else
            target_props  if (x == 0 and y == 2) else None
        ))
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, 1)
        assert entity.target_pos == pygame.math.Vector2(16, 80)
        assert entity.is_moving is True

    def test_ut_007_start_move_stair_right_input_vertical(self, setup_map_manager):
        """UT-007: Input (0,-1) Up on right stair → is_moving False, direction reset."""
        mm = setup_map_manager()
        entity = self._make_entity_on_stair(mm, "right", True)
        entity.direction = pygame.math.Vector2(0, -1)
        entity.start_move()

        assert entity.is_moving is False
        assert entity.direction == pygame.math.Vector2(0, 0)

    def test_ut_008_start_move_stair_right_input_diagonal_unmapped(self, setup_map_manager):
        """UT-008: Input (1,1) on right stair → is_moving True because dy is ignored."""
        mm = setup_map_manager()
        entity = self._make_entity_on_stair(mm, "right", True)
        entity.direction = pygame.math.Vector2(1, 1)
        entity.start_move()
    
        assert entity.is_moving is True
        assert entity.direction == pygame.math.Vector2(1, 0)

    # ── UT-009a: left stair, upper half, input left → step-off flat ──────────────
    def test_ut_009a_left_stair_upper_half_input_left_stepoff(self, setup_map_manager):
        """UT-009a: stair_half=True + input (-1,0) on left stair + target flat → flat (-1,0)."""
        mm = setup_map_manager()
        entity = self._make_entity_on_stair(mm, "left", True)
        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, 0)
        assert entity.target_pos == pygame.math.Vector2(16, 48)
        assert entity.is_moving is True

    # ── UT-009b: left stair, lower half, input left → flat (already at bottom entry) ──
    def test_ut_009b_left_stair_lower_half_input_left_flat(self, setup_map_manager):
        """UT-009b: stair_half=False + input (-1,0) on left stair = bottom entry → flat (-1,0)."""
        mm = setup_map_manager()
        entity = self._make_entity_on_stair(mm, "left", False)
        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, 0)
        assert entity.target_pos == pygame.math.Vector2(16, 48)
        assert entity.is_moving is True

    # ── UT-010a: left stair, lower half, input right → diagonal (1,1) ─────────────
    def test_ut_010a_left_stair_lower_half_input_right_diagonal(self, setup_map_manager):
        """UT-010a: stair_half=False + input (1,0) on left stair → diagonal (1,1)."""
        mm = setup_map_manager()
        current_props = {"stair_direction": "left", "movement_type": "stair", "stair_half": False, "visual_y_offset": 0}
        target_props  = {"stair_direction": "left", "movement_type": "stair", "stair_half": True, "visual_y_offset": -16}
        mm.get_vertical_move_props = MagicMock(side_effect=lambda x, y: (
            current_props if (x == 1 and y == 1) else
            target_props  if (x == 2 and y == 2) else None
        ))
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(1, 1)
        assert entity.target_pos == pygame.math.Vector2(80, 80)
        assert entity.is_moving is True

    # ── UT-010b: left stair, upper half, input right → flat (1,0) ───────────
    def test_ut_010b_left_stair_upper_half_input_right_flat(self, setup_map_manager):
        """UT-010b: stair_half=True + input (1,0) on left stair → flat (1,0)."""
        mm = setup_map_manager()
        current_props = {"stair_direction": "left", "movement_type": "stair", "stair_half": True, "visual_y_offset": -16}
        target_props  = {"stair_direction": "left", "movement_type": "stair", "stair_half": False, "visual_y_offset": 0}
        mm.get_vertical_move_props = MagicMock(side_effect=lambda x, y: (
            current_props if (x == 1 and y == 1) else
            target_props  if (x == 2 and y == 1) else None
        ))
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(1, 0)
        assert entity.target_pos == pygame.math.Vector2(80, 48)
        assert entity.is_moving is True

    def test_ut_011_start_move_normal_tile(self, setup_map_manager):
        """UT-011: Entity on normal tile → _vertical_move is None, movement is orthogonal."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"walkable": True})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity._vertical_move is None
        assert entity.direction == pygame.math.Vector2(1, 0)
        assert entity.target_pos == pygame.math.Vector2(80, 48)
        assert entity.is_moving is True

    def test_ut_012_transition_stair_to_normal(self, setup_map_manager):
        """UT-012: stair_half=True + input (-1,0) + next tile is normal floor → step-off flat."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager()
        mm.get_direction_flags = MagicMock(return_value=["any"])

        # Current tile is stair (upper half); target (0,1) is normal floor (None)
        mm.get_vertical_move_props = MagicMock(side_effect=lambda x, y: (
            {"stair_direction": "right", "movement_type": "stair", "stair_half": True, "visual_y_offset": -16}
            if (x == 1 and y == 1) else None
        ))

        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, 0)
        assert entity.target_pos == pygame.math.Vector2(16, 48)
        assert entity.is_moving is True

    def test_ut_013_target_not_walkable(self, setup_map_manager):
        """UT-013: walkable_func returns False → target_pos resets, is_moving is False."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager()
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm
        mm.get_vertical_move_props = MagicMock(return_value={
            "stair_direction": "right", "movement_type": "stair",
            "stair_half": True, "visual_y_offset": -16,
        })
        entity.walkable_func = lambda x, y, requester=None: False

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.is_moving is False
        assert entity.target_pos == entity.pos

    def test_ut_014_interpolation(self):
        """UT-014: Interpolation updates current_stair_offset smoothly during movement."""
        entity = BaseEntity(pos=(48, 48))
        entity.is_moving = True
        entity.stair_start_offset = 0.0
        entity.stair_target_offset = -16.0
        entity.stair_move_distance = 32.0
        entity.target_pos = pygame.math.Vector2(80, 48)

        entity.pos = pygame.math.Vector2(64, 48)
        entity.update_stair_offset()
        assert entity.current_stair_offset == pytest.approx(-8.0)

        entity.pos = pygame.math.Vector2(80, 48)
        entity.update_stair_offset()
        assert entity.current_stair_offset == pytest.approx(-16.0)

    def test_ut_015_rendering_offset(self):
        """UT-015: CameraGroup.custom_draw() applies current_stair_offset to render coordinates."""
        from src.entities.groups import CameraGroup

        group = CameraGroup()
        sprite = BaseEntity(pos=(100, 100))
        sprite.image = pygame.Surface((32, 32))
        sprite.current_stair_offset = -16.0
        group.add(sprite)

        surface = MagicMock()
        group.offset = pygame.math.Vector2(0, 0)

        with patch.object(surface, 'blit') as mock_blit:
            group.custom_draw(surface)
            assert mock_blit.called
            dest_pos = mock_blit.call_args[0][1]
            assert dest_pos[1] == 68

    def test_ut_016_vertical_move_map_config(self):
        """UT-016: VERTICAL_MOVE_MAP is defined with correct stair translations."""
        assert hasattr(Settings, "VERTICAL_MOVE_MAP")
        assert Settings.VERTICAL_MOVE_MAP[((1, 0), "right")] == (1, -1)
        assert Settings.VERTICAL_MOVE_MAP[((-1, 0), "right")] == (-1, 1)
        assert Settings.VERTICAL_MOVE_MAP[((1, 0), "left")] == (1, 1)
        assert Settings.VERTICAL_MOVE_MAP[((-1, 0), "left")] == (-1, -1)
