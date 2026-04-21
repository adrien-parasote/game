import pytest
import pygame
import os
import json
from unittest.mock import Mock, patch, mock_open

from src.engine.game import Game
from src.config import Settings

@pytest.fixture
def mock_pygame_display():
    """Provides a controlled mock of pygame display to avoid real windowing issues."""
    with patch('pygame.display.set_mode') as mock_set_mode, \
         patch('pygame.display.set_caption'), \
         patch('pygame.display.get_surface') as mock_get_surf:
        
        mock_surf = pygame.Surface((800, 600))
        mock_set_mode.return_value = mock_surf
        mock_get_surf.return_value = mock_surf
        yield mock_set_mode

class TestWorldTeleport:
    def test_teleport_init_defaults(self):
        """TC-001: Teleport missing transition type should default to instant."""
        from src.entities.teleport import Teleport
        groups = [pygame.sprite.Group()]
        
        teleport = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=groups,
            target_map="01-castel.tmj",
            target_spawn_id="corridor"
        )
        
        assert teleport.target_map == "01-castel.tmj"
        assert teleport.target_spawn_id == "corridor"
        assert teleport.transition_type == "instant"

    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
        "maps": [{"fileName": "custom_default.tmj"}]
    }))
    def test_game_world_parsing(self, mock_file, mock_pygame_display):
        """TC-002: game.py should parse world.world to find default map."""
        # Mock load_map to skip actual parsing
        with patch.object(Game, '_load_map') as mock_load:
            # We mock the constructor dependencies and targeted os.path.exists
            with patch('src.map.tmj_parser.TmjParser.load_map'), \
                 patch('src.engine.game.os.path.exists', side_effect=lambda p: "world.world" in p):
                game = Game()
                mock_load.assert_any_call("custom_default.tmj")
                
    def test_logic_is_moving_edge_case(self, mock_pygame_display):
        """TC-003: Player inside teleport rect but not finishing a move -> no trigger."""
        
        class DummySprite(pygame.sprite.Sprite):
            def __init__(self, rect):
                super().__init__()
                self.rect = rect
                self.target_map = "next.tmj"
                self.target_spawn_id = "target_x"
                self.transition_type = "instant"

        # Mocking TmjParser and others to instantiate Game without assets
        fake_map_data = {"layers": {"l1": [[0]*10]*10}, "spawn_player": None, "entities": []}
        with patch('src.map.tmj_parser.TmjParser.load_map', return_value=fake_map_data), \
             patch('src.engine.game.os.path.exists', return_value=True):
    
            game = Game()
            with patch.object(game, '_load_map') as mock_load:
                # Create a mock teleporter
                teleport_rect = pygame.Rect(100, 100, 32, 32)
                mock_teleport = DummySprite(teleport_rect)
        
                game.teleports_group = pygame.sprite.Group()
                game.teleports_group.add(mock_teleport)
        
                # Player stands directly inside the teleport rect!
                game.player.pos = pygame.math.Vector2(116, 116)
                game.player.rect.center = (116, 116)
                game.player.is_moving = False
        
                # was_moving=False -> no trigger
                game._check_teleporters(was_moving=False)
                mock_load.assert_not_called()
        
                # was_moving=True -> trigger
                game._check_teleporters(was_moving=True)
                mock_load.assert_called_with("next.tmj", "target_x", "instant")

    def test_group_cleanup_on_load(self, mock_pygame_display):
        """TC-005: _load_map clears existing groups fully before placing new ones."""
        fake_map_data = {"layers": {"l1": [[0]*10]*10}, "entities": [], "spawn_player": None}
        
        class DummySprite(pygame.sprite.Sprite):
            def __init__(self):
                super().__init__()

        with patch('src.map.tmj_parser.TmjParser.load_map', return_value=fake_map_data), \
             patch('src.engine.game.os.path.exists', return_value=True):
             
            with patch('builtins.open', mock_open(read_data='{"maps": [{"fileName": "00-spawn.tmj"}]}')):
                game = Game()
                # Populate garbage
                sprite1, sprite2, obs1, obs2 = DummySprite(), DummySprite(), DummySprite(), DummySprite()
                game.interactives.add(sprite1)
                game.npcs.add(sprite2)
                game.obstacles_group.add(obs1)
                
                if not hasattr(game, 'teleports_group'):
                    game.teleports_group = pygame.sprite.Group()
                game.teleports_group.add(obs2)
                
                with patch.object(game, '_spawn_entities'):
                    game._load_map("01-castel.tmj", transition_type="instant")
                    
                    assert len(game.interactives) == 0
                    assert len(game.npcs) == 0
                    assert len(game.obstacles_group) == 0
                    assert len(game.teleports_group) == 0
