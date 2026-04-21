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
    tp = Teleport(pygame.Rect(0, 0, 32, 32), [], "map.tmj", "spawn", "instant", "down")
    game.teleports_group.add(tp)
    
    # 1. Player arrives at teleport but facing up
    game.player.rect.center = (16, 16)
    game.player.pos = pygame.math.Vector2(16, 16)
    game.player.current_state = 'up'
    
    # 3. Turns and starts moving down
    was_moving = False
    game.player.current_state = 'down'
    game.player.direction = pygame.math.Vector2(0, 1)
    
    game.player.collision_func = lambda x,y: False
    
    print(f"before update: pos={game.player.pos}, target={game.player.target_pos}, is_moving={game.player.is_moving}")
    game.player.update(1/60.0)
    print(f"after update: pos={game.player.pos}, target={game.player.target_pos}, is_moving={game.player.is_moving}")
