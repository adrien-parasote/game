import os
import pygame
import pytest
import random
from src.entities.npc import NPC
from src.config import Settings

# Setup dummy video driver for pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1, 1))

@pytest.fixture
def npc():
    # Position at (64, 64), dummy group
    return NPC(pos=(64, 64), groups=pygame.sprite.Group(), wander_radius=0)

def test_npc_interact_faces_player(monkeypatch, npc):
    class DummyPlayer:
        def __init__(self):
            self.pos = pygame.math.Vector2(96, 64)  # to the right of NPC
    player = DummyPlayer()
    npc.interact(player)
    assert npc.state == "interact"
    # Should face right because player is to the right
    assert npc.current_facing == "right"

def test_npc_start_move_respects_radius(monkeypatch, npc):
    # Set radius to 0 so any movement exceeds it
    npc.wander_radius = 0
    # Force direction to move left
    npc.direction = pygame.math.Vector2(-1, 0)
    npc.start_move()
    # Should cancel since dist (1 tile) > radius (0)
    assert npc.is_moving is False
    
    # Set radius to 2, move 1 tile
    npc.wander_radius = 2
    npc.direction = pygame.math.Vector2(1, 0)
    npc.start_move()
    # Should be allowed
    assert npc.is_moving is True

def test_npc_process_ai_wander(monkeypatch, npc):
    # Mock random.choice to deterministic direction (1 tile movement)
    monkeypatch.setattr(random, "choice", lambda seq: pygame.math.Vector2(0, 1))
    # Ensure NPC is idle and not moving, with radius 2
    npc.wander_radius = 2
    npc.state = "idle"
    npc.is_moving = False
    # Simulate enough time to trigger AI decision
    npc._action_timer = npc._action_cooldown + 0.1
    npc.process_ai(dt=0.1)
    # Should have set direction to down and state to wander
    assert npc.direction.y == 1
    assert npc.state == "wander"
    assert npc.current_facing == "down"

def test_npc_update_calls_move_and_animation(monkeypatch, npc):
    # Spy on move and _update_animation
    called = {"move": False, "anim": False}
    def fake_move(dt):
        called["move"] = True
    def fake_anim(dt):
        called["anim"] = True
    monkeypatch.setattr(npc, "move", fake_move)
    monkeypatch.setattr(npc, "_update_animation", fake_anim)
    npc.update(dt=0.016)
    assert called["move"] and called["anim"]
