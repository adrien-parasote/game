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
    
    print("was_moving:", was_moving, "is_moving:", game.player.is_moving)
    if was_moving == game.player.is_moving:
        print("returned early")
    else:
        for t in game.teleports_group:
            print("collides:", game.player.rect.colliderect(t.rect))
            req = getattr(t, 'required_direction', 'any')
            print("req:", req, "state:", game.player.current_state)
            if req != 'any' and game.player.current_state != req:
                print("continue")
            else:
                print("Transition WOULD trigger")
