import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.render_manager import RenderManager

@pytest.fixture
def dummy_game():
    game = MagicMock()
    game.screen = pygame.Surface((800, 600))
    game.tile_size = 32
    game.map_manager = MagicMock()
    game.map_manager.layer_order = [1, 2]
    game.map_manager.layers = {1: [[100, 0], [0, 0]], 2: [[0, 0], [0, 101]]}
    game.map_manager.tiles = {100: MagicMock(), 101: MagicMock()}
    game.visible_sprites = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.visible_sprites.get_sorted_sprites.return_value = []
    return game

@pytest.mark.tc("TC-RPERF-U-008")
def test_update_animated_tile_cache_uses_layer_map(dummy_game):
    """TC-RPERF-U-008: _update_animated_tile_cache uses _anim_tile_layer_map."""
    dummy_game.map_manager._anim_tile_layer_map = {(0, 0): 1, (1, 1): 2}
    
    # Mock get_visible_animated_chunks to return the two animated tiles
    dummy_game.map_manager.get_visible_animated_chunks.return_value = [
        (0, 0, 100, 0),  # px, py, tile_id, depth
        (32, 32, 101, 0)
    ]
    
    rm = RenderManager(dummy_game)
    rm._update_animated_tile_cache(pygame.math.Vector2(0, 0))
    
    assert len(rm._frame_anim_by_layer[1]) == 1
    assert rm._frame_anim_by_layer[1][0] == (0, 0, 100, 0)
    assert len(rm._frame_anim_by_layer[2]) == 1
    assert rm._frame_anim_by_layer[2][0] == (32, 32, 101, 0)

@pytest.mark.tc("TC-RPERF-U-009")
def test_update_animated_tile_cache_ignores_unknown(dummy_game):
    """TC-RPERF-U-009: Unknown animated tile is ignored without crash."""
    dummy_game.map_manager._anim_tile_layer_map = {}
    
    dummy_game.map_manager.get_visible_animated_chunks.return_value = [
        (0, 0, 999, 0),
    ]
    
    rm = RenderManager(dummy_game)
    rm._update_animated_tile_cache(pygame.math.Vector2(0, 0))
    
    assert len(rm._frame_anim_by_layer[1]) == 0
    assert len(rm._frame_anim_by_layer[2]) == 0

@pytest.mark.tc("TC-RPERF-U-011")
def test_apply_grass_wading_early_exit_no_grass(dummy_game):
    """TC-RPERF-U-011: Early exit if map has no grass."""
    dummy_game.map_manager._map_has_grass = False
    rm = RenderManager(dummy_game)
    
    result = rm._apply_grass_wading_to_images()
    assert result == {}
    dummy_game.visible_sprites.get_sorted_sprites.assert_not_called()

@pytest.mark.tc("TC-RPERF-U-012")
def test_apply_grass_wading_no_early_exit_with_grass(dummy_game):
    """TC-RPERF-U-012: No early exit if map has grass."""
    dummy_game.map_manager._map_has_grass = True
    rm = RenderManager(dummy_game)
    
    rm._apply_grass_wading_to_images()
    dummy_game.visible_sprites.get_sorted_sprites.assert_called_once()
