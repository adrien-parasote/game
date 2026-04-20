import os
import sys
import pygame
import pytest
from src.entities.base import BaseEntity
from src.entities.player import Player
from src.entities.npc import NPC
from src.config import Settings

# Ensure pygame dummy driver for headless testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1, 1))

@pytest.fixture
def base_entity():
    # Position at (64, 64), dummy group
    return BaseEntity(pos=(64, 64), groups=pygame.sprite.Group())

def test_base_start_move_clamps_to_world_bounds(monkeypatch, base_entity):
    # Set direction to move right beyond world bounds
    base_entity.direction = pygame.math.Vector2(1, 0)
    # Mock Settings for map size 2 tiles (64px each) -> world width 128
    monkeypatch.setattr(Settings, "MAP_SIZE", 2)
    monkeypatch.setattr(Settings, "TILE_SIZE", 64)
    base_entity.start_move()
    # Target should be clamped to max world width - half width
    half_w = base_entity.rect.width / 2
    expected_x = max(half_w, min(base_entity.target_pos.x, Settings.MAP_SIZE * Settings.TILE_SIZE - half_w))
    assert base_entity.target_pos.x == expected_x
    assert base_entity.is_moving is True

def test_base_move_reaches_target(monkeypatch, base_entity):
    # Set direction down
    base_entity.direction = pygame.math.Vector2(0, 1)
    base_entity.speed = 64  # tiles per second
    # Start move
    base_entity.start_move()
    # Simulate dt that should reach target in one step
    dt = 1.0  # 1 second, distance = 64, speed 64
    base_entity.move(dt)
    # Position should equal target_pos
    assert base_entity.pos == base_entity.target_pos
    assert base_entity.is_moving is False

# Tests for Game helper methods
from src.engine.game import Game

class DummyMapManager:
    def __init__(self, map_result, layout):
        self.width = 2
        self.height = 2
    def is_collidable(self, x, y):
        return x == 1 and y == 1
    def get_visible_chunks(self, viewport):
        return []

class DummyLayout:
    def to_world(self, x, y):
        return (x, y)

@pytest.fixture
def game_instance(monkeypatch):
    # Patch TmjParser.load_map to return minimal map data
    class DummyParser:
        def load_map(self, path):
            return {"spawn_player": {"x": 0, "y": 0}, "entities": []}
    
    # Patch the TmjParser in its own module to ensure local imports find it
    monkeypatch.setattr('src.map.tmj_parser.TmjParser', DummyParser)
    # Also patch MapManager in its module
    monkeypatch.setattr('src.map.manager.MapManager', DummyMapManager)
    # And specifically for game.py scope if needed
    monkeypatch.setattr('src.engine.game.MapManager', DummyMapManager, raising=False)
    
    # Mock settings to avoid MapManager trying to read them during some parts of init if any
    monkeypatch.setattr(Settings, "FULLSCREEN", False)
    
    game = Game()
    # Replace layout with dummy
    game.layout = DummyLayout()
    # Ensure obstacles_group empty
    game.obstacles_group = pygame.sprite.Group()
    return game

def test_game_is_collidable_map(monkeypatch, game_instance):
    # Position that maps to collidable tile (1,1)
    result = game_instance._is_collidable(1, 1)
    assert result is True

def test_game_is_collidable_obstacle(monkeypatch, game_instance):
    # Add obstacle sprite at (5,5) with size 10x10
    obstacle = pygame.sprite.Sprite()
    obstacle.rect = pygame.Rect(5, 5, 10, 10)
    game_instance.obstacles_group.add(obstacle)
    # Point inside obstacle
    result = game_instance._is_collidable(6, 6)
    assert result is True

def test_game_is_collidable_none(monkeypatch, game_instance):
    # Point not collidable and no obstacle
    result = game_instance._is_collidable(0, 0)
    assert result is False

def test_game_toggle_fullscreen(game_instance):
    initial_state = game_instance.is_fullscreen
    game_instance.toggle_fullscreen()
    assert game_instance.is_fullscreen != initial_state
    game_instance.toggle_fullscreen()
    assert game_instance.is_fullscreen == initial_state

def test_spawn_entities_complex(game_instance):
    # Clear any entities that might have been spawned during init
    game_instance.interactives.empty()
    game_instance.npcs.empty()
    
    entities_data = [
        {
            "type": "interactive_object",
            "x": 100, "y": 100, "width": 32, "height": 32,
            "properties": {
                "entity_type": "interactive",
                "sub_type": "door",
                "is_passable": True,
                "direction": "up"
            }
        },
        {
            "type": "npc",
            "x": 200, "y": 200, "width": 32, "height": 32,
            "properties": {
                "type": "npc_villager",
                "wander_radius": 5
            }
        }
    ]
    game_instance._spawn_entities(entities_data)
    # Check if objects were added to groups
    assert len(game_instance.interactives) == 1
    assert len(game_instance.npcs) == 1

def test_handle_interactions_npc(monkeypatch, game_instance):
    # Setup player and NPC for interaction
    game_instance.player.pos = pygame.math.Vector2(100, 100)
    game_instance.player.current_state = 'down'
    
    # NPC below player
    npc = NPC(pos=(100, 132), groups=game_instance.npcs)
    
    # Mock keys to simulate SPACE pressed
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: {pygame.K_SPACE: True, Settings.INTERACT_KEY: False})
    
    # Spy on NPC interact
    interacted = False
    def mock_interact(initiator):
        nonlocal interacted
        interacted = True
    monkeypatch.setattr(npc, "interact", mock_interact)
    
    # Interaction cooldown check
    game_instance._interaction_cooldown = 0
    
    game_instance._handle_interactions()
    assert interacted is True

def test_handle_interactions_object(monkeypatch, game_instance):
    # Setup player facing a door
    game_instance.player.pos = pygame.math.Vector2(100, 100)
    game_instance.player.current_state = 'up'
    
    # Door above player (y < player_y)
    from src.entities.interactive import InteractiveEntity
    door = InteractiveEntity(
        pos=(84, 68), # result in base_pos slightly above (100, 100)
        groups=[game_instance.visible_sprites, game_instance.interactives],
        sub_type='door',
        sprite_sheet='dummy.png',
        position=0,
        is_passable=True
    )
    
    # Mock keys to simulate E pressed
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: {Settings.INTERACT_KEY: True, pygame.K_SPACE: False})
    
    # Spy on door interact
    interacted = False
    def mock_interact(initiator):
        nonlocal interacted
        interacted = True
    monkeypatch.setattr(door, "interact", mock_interact)
    
    game_instance._interaction_cooldown = 0
    game_instance._handle_interactions()
    assert interacted is True

def test_handle_interactions_cooldown(monkeypatch, game_instance):
    # Setup player facing a door
    game_instance.player.pos = pygame.math.Vector2(100, 100)
    game_instance.player.current_state = 'up'
    # Interaction cooldown > 0
    game_instance._interaction_cooldown = 1000
    # Mock keys
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: {Settings.INTERACT_KEY: True, pygame.K_SPACE: False})
    # Should not interact
    game_instance._handle_interactions()

    # Draw call
    game_instance._draw_hud()

def test_game_run_loop_quit(monkeypatch, game_instance):
    # Mock events to return QUIT then nothing
    events = [pygame.event.Event(pygame.QUIT)]
    monkeypatch.setattr(pygame.event, "get", lambda: [events.pop(0)] if events else [])
    
    # Mock sys.exit to avoid killing the test runner
    exit_called = False
    def mock_exit(code=0):
        nonlocal exit_called
        exit_called = True
        raise StopIteration() # Generic exception to break the loop
        
    monkeypatch.setattr(sys, "exit", mock_exit)
    # Monkeypatch sys.exit in game.py scope too if it was imported differently
    import sys as sys_module
    monkeypatch.setattr("src.engine.game.sys.exit", mock_exit, raising=False)
    
    # Run loop
    with pytest.raises(StopIteration):
        game_instance.run()
    
    assert exit_called is True

def test_game_toggle_fullscreen_fallback(monkeypatch, game_instance):
    # Mock toggle_fullscreen to fail
    def mock_fail():
        raise pygame.error("Mock Failure")
    monkeypatch.setattr(pygame.display, "toggle_fullscreen", mock_fail)
    
    # Spy on set_mode
    set_mode_called = False
    def mock_set_mode(size, flags=0):
        nonlocal set_mode_called
        set_mode_called = True
        return pygame.Surface(size)
    monkeypatch.setattr(pygame.display, "set_mode", mock_set_mode)
    
    game_instance.toggle_fullscreen()
    assert set_mode_called is True
    assert game_instance.is_fullscreen is True # Since it started False and we toggled


