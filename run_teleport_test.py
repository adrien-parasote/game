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
    
    # Simulation: arrived this frame
    was_moving = True
    game.player.is_moving = False
    
    print("Arrival Test:")
    with patch.object(game, 'transition_map') as mock_trans:
        game._check_teleporters(was_moving)
        print(f"Transition called: {mock_trans.called}")
        if not mock_trans.called:
            print(" -> Teleport skipped (expected)")

    # 2. standing there, next frame
    was_moving = False
    game.player.is_moving = False
    print("\nIdle Test:")
    with patch.object(game, 'transition_map') as mock_trans:
        game._check_teleporters(was_moving)
        print(f"Transition called: {mock_trans.called}")

    # 3. Turns and starts moving down
    was_moving = False
    game.player.current_state = 'down'
    game.player.direction = pygame.math.Vector2(0, 1)
    
    # Run a mock update to simulate starting move
    game.player.collision_func = lambda x,y: False
    game.player.update(1/60.0)
    
    print("\nIntent Test (Starts moving down):")
    print(f"was_moving: {was_moving}, is_moving: {game.player.is_moving}")
    print(f"player rect: {game.player.rect}, collides with tp? {game.player.rect.colliderect(tp.rect)}")
    with patch.object(game, 'transition_map') as mock_trans:
        game._check_teleporters(was_moving)
        print(f"Transition called: {mock_trans.called}")

