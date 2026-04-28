import pytest
import pygame
from src.graphics.spritesheet import SpriteSheet
from unittest.mock import patch, MagicMock

def test_spritesheet_load_grid():
    surface = pygame.Surface((128, 128))
    with patch('pygame.image.load', return_value=surface), \
         patch('os.path.exists', return_value=True):
        ss = SpriteSheet("dummy.png")
        frames = ss.load_grid(4, 4)
        assert len(frames) == 16
        assert frames[0].get_size() == (32, 32)

def test_spritesheet_load_grid_by_size():
    surface = pygame.Surface((64, 64))
    with patch('pygame.image.load', return_value=surface), \
         patch('os.path.exists', return_value=True):
        ss = SpriteSheet("dummy.png")
        frames = ss.load_grid_by_size(32, 32)
        assert len(frames) == 4
        assert frames[0].get_size() == (32, 32)
