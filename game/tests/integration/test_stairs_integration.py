import os
from unittest.mock import MagicMock

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.config import Settings
from src.entities.npc import NPC
from src.entities.player import Player
from src.map.manager import MapManager


class TestStairsIntegration:
    @pytest.fixture
    def setup_mini_map(self):
        """Builds a MapManager for integration tests using stair_half=True/False."""
        def _create(tile_configs: dict[tuple[int, int], dict]):
            map_w, map_h = 10, 10
            grid = [[0] * map_w for _ in range(map_h)]
            tiles = {}

            tile_id_counter = 1
            for (tx, ty), config in tile_configs.items():
                tile_id = tile_id_counter
                grid[ty][tx] = tile_id

                tile = MagicMock()
                tile.properties = config
                direction_prop = config.get("direction", "any")
                tile.direction_flags = {d.strip() for d in direction_prop.split(",")} if direction_prop else {"any"}
                tile.depth = config.get("depth", 0)
                tile.walkable = config.get("walkable", True)

                tiles[tile_id] = tile
                tile_id_counter += 1

            layout = MagicMock()
            layout.to_world.side_effect = lambda px, py: (int(px // 32), int(py // 32))
            layout.tile_size = 32

            map_data = {
                "layers": {"layer_0": grid},
                "tiles": tiles,
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

    def test_it_001_player_walk_up_right_stair(self, setup_mini_map):
        """IT-001: Walk right on a right-stair tile → diagonal target and alignment.

        Layout (right stair, 2-tile step):
          (1,1) stair_half=False  → flat entry
          (2,1) stair_half=True   → diagonal climb → target (3,0)
          (3,0) stair_half=False  → next step entry
        """
        mm = setup_mini_map({
            (1, 1): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
            (2, 1): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": 0},
            (3, 0): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
        })

        player = Player(pos=(48, 48))  # center of (1,1)
        player.speed = 100

        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        player.game = mock_game
        player.walkable_func = lambda x, y, requester=None: mm.is_walkable(int(x // 32), int(y // 32))

        # Input Right on lower-half tile → flat
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()

        assert player.direction == pygame.math.Vector2(1, 0)
        assert player.target_pos == pygame.math.Vector2(80, 48)
        assert player.is_moving is True

        player.update(0.5)
        assert player.is_moving is False
        assert player.pos == pygame.math.Vector2(80, 48)

        # Input Right on upper-half tile → diagonal
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()

        assert player.direction == pygame.math.Vector2(1, -1)
        assert player.target_pos == pygame.math.Vector2(112, 16)
        assert player.is_moving is True

        player.update(0.5)
        assert player.is_moving is False
        assert player.pos == pygame.math.Vector2(112, 16)

    def test_it_002_visual_y_offset_active_during_movement(self, setup_mini_map):
        """IT-002: visual_y_offset is accessible when on a stair tile, None after step-off."""
        mm = setup_mini_map({
            (1, 1): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
            (2, 1): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": -16},
            (3, 1): {"walkable": True},
        })

        player = Player(pos=(48, 48))
        player.speed = 100

        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        player.game = mock_game
        player.walkable_func = lambda x, y, requester=None: True

        # start_move from (1,1): stair_half=False → flat, target=(2,1)
        # _vertical_move is set to TARGET tile (2,1)'s props after start_move
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        assert player._vertical_move is not None
        assert player._vertical_move["stair_direction"] == "right"
        assert player.direction == pygame.math.Vector2(1, 0)  # flat move confirmed

        # Complete movement to (2,1)
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(80, 48)

        # start_move from (2,1): stair_half=True, target (3,0) is None → step-off flat to (3,1)
        # _vertical_move is set to TARGET tile (3,1)'s props = None (normal tile)
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        assert player.direction == pygame.math.Vector2(1, 0)    # step-off confirmed
        assert player._vertical_move is None                    # target (3,1) is normal tile
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(112, 48)

        # start_move from (3,1): normal tile → no stair interception, _vertical_move stays None
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        assert player._vertical_move is None

    def test_it_003_multi_stair_traversal(self, setup_mini_map):
        """IT-003: Multi-tile stair traversal — 2 full steps (flat+diag+flat+step-off).

        Layout (stair_half alternates per step):
          (1,3) False → flat (entry)
          (2,3) True  → diagonal → (3,2)
          (3,2) False → flat (next step entry)
          (4,2) True  → diagonal → (5,1), but target is (5,2)=normal → step-off flat
        """
        mm = setup_mini_map({
            (1, 3): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
            (2, 3): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": -16},
            (3, 2): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
            (4, 2): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": -16},
            (5, 2): {"walkable": True},
        })

        player = Player(pos=(48, 112))  # center of (1,3)
        player.speed = 100

        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        player.game = mock_game
        player.walkable_func = lambda x, y, requester=None: True

        # Step 1: flat (entry)
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(80, 112)  # (2,3)

        # Step 2: diagonal ↗
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(112, 80)  # (3,2)

        # Step 3: flat (next step entry)
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(144, 80)  # (4,2)

        # Step 4: step-off (target (5,2) is normal → forced flat)
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(176, 80)  # (5,2)

    def test_it_004_stair_walls_block_movement(self, setup_mini_map):
        """IT-004: Wall tiles surrounding stairs block movement properly."""
        mm = setup_mini_map({
            (1, 1): {"stair_direction": "right", "walkable": True, "stair_half": True, "visual_y_offset": -16},
            (2, 0): {"walkable": False},
        })

        player = Player(pos=(48, 48))
        player.speed = 100

        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        player.game = mock_game
        player.walkable_func = lambda x, y, requester=None: mm.is_walkable(int(x // 32), int(y // 32))

        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()

        assert player.is_moving is False
        assert player.pos == pygame.math.Vector2(48, 48)

    def test_it_005_npc_stair_traversal(self, setup_mini_map):
        """IT-005: NPCs traverse stairs using the same interception logic."""
        mm = setup_mini_map({
            (1, 1): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": -16},
            (2, 0): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
        })

        npc = NPC(pos=(48, 48))
        npc.speed = 100

        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        npc.game = mock_game
        npc.walkable_func = lambda x, y, requester=None: True

        npc.direction = pygame.math.Vector2(1, 0)
        npc.start_move()

        assert npc.direction == pygame.math.Vector2(1, -1)
        npc.update(0.5)
        assert npc.pos == pygame.math.Vector2(80, 16)

    def test_it_006_direction_flags_isolation(self, setup_mini_map):
        """IT-006: direction property without stair_direction does not trigger stair movement."""
        mm = setup_mini_map({
            (1, 1): {"direction": "right", "walkable": True},
            (2, 1): {"walkable": True},
        })

        player = Player(pos=(48, 48))
        player.speed = 100

        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        player.game = mock_game
        player.walkable_func = lambda x, y, requester=None: True

        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()

        assert player.direction == pygame.math.Vector2(1, 0)
        assert player.target_pos == pygame.math.Vector2(80, 48)

    def test_it_007_stair_traversal_symmetry(self, setup_mini_map):
        """IT-007: Ascent then descent returns the player to exact starting coordinates (no Y drift).

        Layout (stair_half controls direction for BOTH ascent and descent):
          (1,3) normal floor
          (2,3) stair_half=False → flat entry
          (3,3) stair_half=True  → diagonal climb/descent
          (4,2) stair_half=True  → diagonal climb/descent
          (5,2) normal floor
        """
        mm = setup_mini_map({
            (1, 3): {"walkable": True},
            (2, 3): {"stair_direction": "right", "walkable": True, "stair_half": False, "visual_y_offset": 0},
            (3, 3): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": -16},
            (4, 2): {"stair_direction": "right", "walkable": True, "stair_half": True,  "visual_y_offset": -32},
            (5, 2): {"walkable": True},
        })

        player = Player(pos=(48, 112))  # center of (1,3)
        player.speed = 100
        mock_game = MagicMock()
        mock_game.map_manager = mm
        mock_game.layout = mm.layout
        player.game = mock_game
        player.walkable_func = lambda x, y, requester=None: True

        # 1. Step onto stairs: (1,3) → (2,3)  [flat]
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(80, 112)

        # 2. Flat step on stair: (2,3) → (3,3)  [flat]
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(112, 112)

        # 3. Diagonal climb: (3,3) → (4,2)  [diag (1,-1)]
        player.direction = pygame.math.Vector2(1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(144, 80)

        # 4. Descent: (4,2) → (3,3)  [diag (-1,1)]
        player.direction = pygame.math.Vector2(-1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(112, 112)

        # 5. Flat step back: (3,3) → (2,3)  [flat]
        player.direction = pygame.math.Vector2(-1, 0)
        player.start_move()
        player.update(0.5)
        assert player.pos == pygame.math.Vector2(80, 112)

        # 6. Step off stairs: (2,3) → (1,3)  [flat]
        player.direction = pygame.math.Vector2(-1, 0)
        player.start_move()
        player.update(0.5)

        assert player.pos == pygame.math.Vector2(48, 112)   # back to start ✅
        assert getattr(player, "current_stair_offset", 0.0) == 0.0
