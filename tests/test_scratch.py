import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from src.engine.game import Game
from unittest.mock import patch, mock_open, Mock

fake_map_data = {"layers": {"l1": [[0]*10]*10}, "entities": [], "spawn_player": None}

with patch('src.map.tmj_parser.TmjParser.load_map', return_value=fake_map_data), \
     patch('os.path.exists', return_value=True), \
     patch('builtins.open', mock_open(read_data='{"maps": [{"fileName": "00-spawn.tmj"}]}')):
    game = Game()
    class DummySprite(pygame.sprite.Sprite): pass
    sprite1 = DummySprite()
    game.interactives.add(sprite1)
    
    with patch.object(game, '_spawn_entities'):
        game._load_map("01-castel.tmj", "instant")
    
    print(f"Interactives count: {len(game.interactives)}")
