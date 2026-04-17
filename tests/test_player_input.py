import os
import pygame
import pytest
from src.entities.player import Player
from src.config import Settings

# Ensure pygame uses dummy video driver for headless testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

@pytest.fixture
def player():
    # Position at (0,0), dummy group
    return Player(pos=(0, 0), groups=pygame.sprite.Group(), speed=Settings.PLAYER_SPEED)

def mock_key_state(keys_pressed):
    """Return a function that mimics pygame.key.get_pressed returning the given dict."""
    def get_pressed():
        # pygame.key.get_pressed returns a sequence; we simulate with a dict lookup
        class KeySeq:
            def __getitem__(self, key):
                return keys_pressed.get(key, False)
        return KeySeq()
    return get_pressed

def test_player_moves_up(monkeypatch, player):
    # Simulate pressing MOVE_UP key
    monkeypatch.setattr(pygame.key, "get_pressed", mock_key_state({Settings.MOVE_UP: True}))
    player.input()
    assert player.direction.y == -1
    assert player.direction.x == 0
    assert player.current_state == "up"

def test_player_moves_down(monkeypatch, player):
    monkeypatch.setattr(pygame.key, "get_pressed", mock_key_state({Settings.MOVE_DOWN: True}))
    player.input()
    assert player.direction.y == 1
    assert player.direction.x == 0
    assert player.current_state == "down"

def test_player_moves_left(monkeypatch, player):
    # No vertical key, left key pressed
    monkeypatch.setattr(pygame.key, "get_pressed", mock_key_state({Settings.MOVE_LEFT: True}))
    player.input()
    assert player.direction.x == -1
    assert player.direction.y == 0
    assert player.current_state == "left"

def test_player_moves_right(monkeypatch, player):
    monkeypatch.setattr(pygame.key, "get_pressed", mock_key_state({Settings.MOVE_RIGHT: True}))
    player.input()
    assert player.direction.x == 1
    assert player.direction.y == 0
    assert player.current_state == "right"

def test_player_no_input(monkeypatch, player):
    monkeypatch.setattr(pygame.key, "get_pressed", mock_key_state({}))
    player.input()
    assert player.direction.x == 0
    assert player.direction.y == 0
    # State should remain default (down)
    assert player.current_state == "down"
