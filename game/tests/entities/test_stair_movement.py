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
            # Add width/height mocks as used by start_move
            mm.width = map_w
            mm.height = map_h
            return mm
        return _create

    def test_ut_001_get_vertical_move_props_stair_right(self, setup_map_manager):
        """UT-001: get_vertical_move_props(tx, ty) returns properties for right stair."""
        mm = setup_map_manager({"stair_direction": "right", "movement_type": "stair", "visual_y_offset": -12})
        props = mm.get_vertical_move_props(1, 1)
        assert props == {
            "stair_direction": "right",
            "movement_type": "stair",
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

    def test_ut_005_start_move_stair_right_input_right(self, setup_map_manager):
        """UT-005: Input (1, 0) on right stair -> direction (1, -1), target_pos y decreased."""
        entity = BaseEntity(pos=(48, 48))  # Center of tile (1,1) at 32x32 size (16+32, 16+32)
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "right"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(1, -1)
        assert entity.target_pos == pygame.math.Vector2(80, 16)
        assert entity.is_moving is True

    def test_ut_006_start_move_stair_right_input_left(self, setup_map_manager):
        """UT-006: Input (-1, 0) on right stair -> direction (-1, 1), target_pos y increased."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "right"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, 1)
        assert entity.target_pos == pygame.math.Vector2(16, 80)
        assert entity.is_moving is True

    def test_ut_007_start_move_stair_right_input_vertical(self, setup_map_manager):
        """UT-007: Input (0, -1) (Up) on right stair -> is_moving remains False, direction reset to (0,0)."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "right"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(0, -1)
        entity.start_move()

        assert entity.is_moving is False
        assert entity.direction == pygame.math.Vector2(0, 0)

    def test_ut_008_start_move_stair_right_input_diagonal_unmapped(self, setup_map_manager):
        """UT-008: Input (1, 1) on right stair -> is_moving remains False, direction reset to (0,0)."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "right"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(1, 1)
        entity.start_move()

        assert entity.is_moving is False
        assert entity.direction == pygame.math.Vector2(0, 0)

    def test_ut_009_start_move_stair_left_input_left(self, setup_map_manager):
        """UT-009: Input (-1, 0) on left stair -> direction (-1, -1), target_pos y decreased."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "left"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(-1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(-1, -1)
        assert entity.target_pos == pygame.math.Vector2(16, 16)
        assert entity.is_moving is True

    def test_ut_010_start_move_stair_left_input_right(self, setup_map_manager):
        """UT-010: Input (1, 0) on left stair -> direction (1, 1), target_pos y increased."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "left"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.direction == pygame.math.Vector2(1, 1)
        assert entity.target_pos == pygame.math.Vector2(80, 80)
        assert entity.is_moving is True

    def test_ut_011_start_move_normal_tile(self, setup_map_manager):
        """UT-011: Entity on normal tile -> _vertical_move is None, movement is normal orthogonal."""
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
        """UT-012: Entity leaves stair to normal tile -> _vertical_move becomes None, offset 0."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm_stair = setup_map_manager({"stair_direction": "right"})
        mm_stair.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm_stair

        # Step 1: on stair
        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()
        assert entity._vertical_move is not None

        # Step 2: reached target, move again, but now map returns None (normal tile)
        entity.pos = pygame.math.Vector2(entity.target_pos)
        entity.is_moving = False
        mm_normal = setup_map_manager({"walkable": True})
        mm_normal.get_direction_flags = MagicMock(return_value=["any"])
        entity.game.map_manager = mm_normal

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()
        assert entity._vertical_move is None

    def test_ut_013_target_not_walkable(self, setup_map_manager):
        """UT-013: walkable_func returns False -> target_pos resets, is_moving is False."""
        entity = BaseEntity(pos=(48, 48))
        entity.speed = 200
        mm = setup_map_manager({"stair_direction": "right"})
        mm.get_direction_flags = MagicMock(return_value=["any"])
        entity.game = MagicMock()
        entity.game.map_manager = mm
        entity.walkable_func = lambda x, y, requester=None: False

        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()

        assert entity.is_moving is False
        assert entity.target_pos == entity.pos

    def test_ut_014_rendering_offset_active(self):
        """UT-014: Entity with active _vertical_move draws with Y offset."""
        # This will be verified in custom_draw integration/unit test, or we mock sprite drawing.
        # Let's mock a CameraGroup and a Sprite.
        from src.entities.groups import CameraGroup
        
        # We need a headless display to do this, conftest handles it
        group = CameraGroup()
        sprite = BaseEntity(pos=(100, 100))
        sprite.image = pygame.Surface((32, 32))
        sprite._vertical_move = {"visual_y_offset": -12}
        
        # Mock surface to blit on
        surface = MagicMock()
        group.offset = pygame.math.Vector2(0, 0)
        
        with patch.object(surface, 'blit') as mock_blit:
            group.custom_draw(surface)
            # The custom_draw method draws all sprites in the group.
            # We must add sprite to group first.
            group.add(sprite)
            # Clear mock
            mock_blit.reset_mock()
            group.custom_draw(surface)
            
            assert mock_blit.called
            # The position blitted should be visual_rect.topleft + offset + visual_y_offset.
            # sprite.rect is center=(100, 100) -> top_left = (100 - 16, 100 - 16) = (84, 84)
            # with visual_y_offset = -12 -> (84, 84 - 12) = (84, 72)
            # Let's extract the position argument.
            call_args = mock_blit.call_args[0]
            # call_args[1] is the offset_pos
            dest_pos = call_args[1]
            assert dest_pos[1] == 72

    def test_ut_015_rendering_offset_inactive(self):
        """UT-015: Entity with _vertical_move=None draws without Y offset."""
        from src.entities.groups import CameraGroup
        group = CameraGroup()
        sprite = BaseEntity(pos=(100, 100))
        sprite.image = pygame.Surface((32, 32))
        sprite._vertical_move = None
        group.add(sprite)
        
        surface = MagicMock()
        group.offset = pygame.math.Vector2(0, 0)
        
        with patch.object(surface, 'blit') as mock_blit:
            group.custom_draw(surface)
            dest_pos = mock_blit.call_args[0][1]
            assert dest_pos[1] == 84  # 100 - 16

    def test_ut_016_vertical_move_map_config(self):
        """UT-016: VERTICAL_MOVE_MAP is defined with correct stair translations."""
        from src.config import Settings
        # Check that Settings has VERTICAL_MOVE_MAP and it is correct
        assert hasattr(Settings, "VERTICAL_MOVE_MAP")
        assert Settings.VERTICAL_MOVE_MAP[((1, 0), "right")] == (1, -1)
        assert Settings.VERTICAL_MOVE_MAP[((-1, 0), "right")] == (-1, 1)
        assert Settings.VERTICAL_MOVE_MAP[((1, 0), "left")] == (1, 1)
        assert Settings.VERTICAL_MOVE_MAP[((-1, 0), "left")] == (-1, -1)
