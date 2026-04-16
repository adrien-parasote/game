import pygame
import pytest
from unittest.mock import patch, MagicMock
from src.entities.player import Player
from src.entities.npc import NPC
from src.engine.game import Game

@pytest.fixture
def test_game():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 48)) for _ in range(16)]):
        with patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None):
            game = Game()
            yield game
            
    pygame.quit()

def test_player_npc_interaction(test_game):
    """IT-N-01: Player interacts with facing NPC."""
    # Place Player at (16, 16)
    test_game.player.pos = pygame.math.Vector2(16, 16)
    test_game.player.rect.center = (16, 16)
    
    # Place NPC directly right of the player (48, 16)
    npc = NPC((48, 16))
    npc.interact = MagicMock()
    test_game.npcs.add(npc)
    test_game.visible_sprites.add(npc)
    
    # Player faces RIGHT
    test_game.player.direction = pygame.math.Vector2(1, 0)
    test_game.player.current_state = 'right'
    
    # Simulate ACTION key press (Space)
    class MockKeys(dict):
        def __getitem__(self, key):
            return self.get(key, False)
            
    keys = MockKeys({pygame.K_SPACE: True})
    
    # We call standard engine logic for handling input
    with patch('pygame.key.get_pressed', return_value=keys):
        # We need a custom event or check in self.player.input() or game loop
        # The game engine handles the interaction trigger
        test_game._handle_interactions()
        
    # NPC should receive the interaction event
    npc.interact.assert_called_once_with(test_game.player)
