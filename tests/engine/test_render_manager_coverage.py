import pygame
import pytest
from unittest.mock import MagicMock, patch
from src.engine.render_manager import RenderManager

@pytest.fixture
def mock_game():
    game = MagicMock()
    game.tile_size = 32
    game.screen = MagicMock(spec=pygame.Surface)
    game.screen.get_width.return_value = 1280
    game.screen.get_height.return_value = 720
    game.visible_sprites.offset = pygame.Vector2(0, 0)
    game.player.depth = 10
    game.player.rect = pygame.Rect(100, 100, 32, 32)
    game.player.image.get_rect.return_value = pygame.Rect(100, 100, 32, 32)
    
    game.map_manager.layer_order = [1]
    game.map_manager.layer_depths = {1: 5}
    game.map_manager.tiles = {1: MagicMock(image=MagicMock())}
    
    return game

def test_render_manager_draw_background_animated(mock_game):
    """Test background rendering with animated tiles (L39-42)."""
    rm = RenderManager(mock_game)
    
    # Setup animated chunks
    mock_game.anim_map_manager.get_current_frame_image.return_value = MagicMock(spec=pygame.Surface)
    mock_game.map_manager.get_visible_animated_chunks.return_value = [(0, 0, 1, 5)] # x, y, tile_id, depth (depth 5 <= player 10)
    
    rm.draw_background()
    assert mock_game.screen.fblits.called

def test_render_manager_draw_foreground_animated(mock_game):
    """Test foreground rendering with animated tiles (L93-96)."""
    rm = RenderManager(mock_game)
    
    mock_game.anim_map_manager.get_current_frame_image.return_value = MagicMock(spec=pygame.Surface)
    mock_game.map_manager.get_visible_animated_chunks.return_value = [(0, 0, 1, 15)] # depth 15 > player 10
    mock_game.map_manager.get_visible_chunks.return_value = [] # no normal tiles
    
    rm.draw_foreground()
    assert mock_game.screen.fblits.called

def test_render_manager_draw_scene_with_emotes_and_chest(mock_game):
    """Test draw_scene covers emotes (L146-147) and open chest (L169)."""
    rm = RenderManager(mock_game)
    
    # Setup emote
    mock_emote = MagicMock()
    mock_emote.rect = pygame.Rect(50, 50, 32, 32)
    mock_emote.image = MagicMock(spec=pygame.Surface)
    mock_game.emote_group = [mock_emote]
    
    # Setup chest open
    mock_game.inventory_ui.is_open = False
    mock_game.chest_ui.is_open = True
    
    # Mock lighting/time to avoid heavy logic
    mock_game.time_system.night_alpha = 0
    mock_game.interactives = []
    mock_game.dialogue_manager.is_active = False
    mock_game.map_manager.get_window_positions.return_value = []
    
    with patch("src.config.Settings.COLOR_BG", (0, 0, 0)):
        rm.draw_scene()
        
    # Verify blit for emote
    assert mock_game.screen.blit.called
    # Verify chest_ui.draw called
    mock_game.chest_ui.draw.assert_called_once()
