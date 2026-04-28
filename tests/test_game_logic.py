import pytest
import pygame
import os
from unittest.mock import MagicMock, patch
from src.engine.game import Game
from src.config import Settings

@pytest.fixture
def mock_pygame_init():
    pygame.font.init()
    with patch('pygame.init'):
        with patch('pygame.display.set_mode', return_value=pygame.Surface((1280, 720))):
            with patch('pygame.display.set_caption'):
                with patch('src.engine.game.CameraGroup'):
                    with patch('src.engine.game.GameHUD'):
                        yield
    pygame.font.quit()

def test_game_load_map_logic(mock_pygame_init):
    with patch('src.engine.game.Game._setup_logging'):
        # Mocking the map data returned by parser
        mock_map_data = {
            "width": 10, "height": 10,
            "layers": {"ground": MagicMock()},
            "entities": [
                {"type": "14-spawn_point", "x": 32, "y": 32, "properties": {"spawn_player": True, "is_initial_spawn": True}}
            ],
            "properties": {"bgm": "spawn_bgm"}
        }
        
        with patch('src.map.tmj_parser.TmjParser.load_map', return_value=mock_map_data):
            with patch('src.engine.game.Game._spawn_entities'):
                game = Game()
                # Should have loaded the map
                assert game._current_map_name is not None

def test_game_is_collidable(mock_pygame_init):
    with patch('src.engine.game.Game._setup_logging'):
        with patch('src.engine.game.Game._load_map'):
            game = Game()
            game.map_manager = MagicMock()
            game.map_manager.is_collidable.return_value = True
            game.layout = MagicMock()
            game.layout.to_world.return_value = (100, 100)
            
            assert game._is_collidable(100, 100) is True
            game.map_manager.is_collidable.assert_called_with(100, 100)

def test_game_transition_map(mock_pygame_init):
    with patch('src.engine.game.Game._setup_logging'):
        with patch('src.engine.game.Game._load_map'):
            game = Game()
            with patch.object(game, '_load_map') as mock_load:
                with patch('os.path.exists', return_value=True):
                    game.transition_map("new_map", "spawn_1", "instant")
                    mock_load.assert_called_with("new_map", "spawn_1", "instant")

def test_game_draw_scene(mock_pygame_init):
    with patch('src.engine.game.Game._setup_logging'):
        with patch('src.engine.game.Game._load_map'):
            game = Game()
            game.map_manager = MagicMock()
            game.map_manager.layers = {}
            game.visible_sprites = MagicMock()
            game.time_system = MagicMock()
            game.time_system.night_alpha = 0
            game.inventory_ui = MagicMock()
            game.inventory_ui.is_open = False
            game.dialogue_manager = MagicMock()
            game.dialogue_manager.is_active = False
            game.interactives = []
            game.emote_group = []
            
            screen = pygame.Surface((1280, 720))
            game._draw_scene()
            assert game.visible_sprites.custom_draw.called

def test_game_toggle_entity_by_id(mock_pygame_init):
    with patch('src.engine.game.Game._setup_logging'):
        with patch('src.engine.game.Game._load_map'):
            game = Game()
            target = MagicMock()
            target.element_id = "target_1"
            game.interactives = [target]
            game.audio_manager = MagicMock()
            
            game.toggle_entity_by_id("target_1")
            assert target.interact.called
