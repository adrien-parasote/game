import pygame
import sys
from unittest.mock import Mock, patch
from src.engine.game import Game
from src.entities.teleport import Teleport

pygame.init()
pygame.display.set_mode((1, 1))

with patch('src.engine.game.os.path.exists', return_value=True), \
     patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}):
    game = Game()
    tp = Teleport(pygame.Rect(0, 0, 32, 32), [], "map.tmj", "spawn", "instant", "any")
    game.teleports_group.add(tp)
    
    # 1. Player spawned on teleport
    game.player.rect.center = (16, 16)
    game.player.pos = pygame.math.Vector2(16, 16)
    
    # 2. Wants to walk away (to the right)
    was_moving = False
    game.player.current_state = 'right'
    game.player.direction = pygame.math.Vector2(1, 0)
    
    game.player.collision_func = lambda x,y: False
    game.player.update(1/60.0)
    
    with patch.object(game, 'transition_map') as mock_trans:
        game._check_teleporters(was_moving)
        print(f"Walking away... Transition called: {mock_trans.called}")

