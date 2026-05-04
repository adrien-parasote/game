from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.graphics.spritesheet import SpriteSheet


def test_spritesheet_load_grid():
    surface = pygame.Surface((128, 128))
    with (
        patch("pygame.image.load", return_value=surface),
        patch("os.path.exists", return_value=True),
    ):
        ss = SpriteSheet("dummy.png")
        frames = ss.load_grid(4, 4)
        assert len(frames) == 16
        assert frames[0].get_size() == (32, 32)


def test_spritesheet_load_grid_by_size():
    surface = pygame.Surface((64, 64))
    with (
        patch("pygame.image.load", return_value=surface),
        patch("os.path.exists", return_value=True),
    ):
        ss = SpriteSheet("dummy.png")
        frames = ss.load_grid_by_size(32, 32)
        assert len(frames) == 4
        assert frames[0].get_size() == (32, 32)


# --- Invalid / missing file ---


def test_spritesheet_empty_filename():
    """Empty filename marks sheet as invalid without crashing."""
    ss = SpriteSheet("")
    assert ss.valid is False
    assert ss.sheet is None


def test_spritesheet_directory_path():
    """Path ending with / is treated as no-sprite."""
    ss = SpriteSheet("some/path/")
    assert ss.valid is False


def test_spritesheet_file_not_found():
    """Non-existent file marks sheet as invalid."""
    with patch("os.path.exists", return_value=False):
        ss = SpriteSheet("missing.png")
    assert ss.valid is False
    assert ss.sheet is None


def test_spritesheet_pygame_load_error():
    """pygame.error during load marks sheet as invalid."""
    with (
        patch("os.path.exists", return_value=True),
        patch("pygame.image.load", side_effect=pygame.error("bad image")),
    ):
        ss = SpriteSheet("corrupt.png")
    assert ss.valid is False
    assert ss.sheet is None


# --- Fallback surfaces when invalid ---


def test_load_grid_invalid_returns_dummies():
    """load_grid returns dummy surfaces when sheet is invalid."""
    ss = SpriteSheet("")
    frames = ss.load_grid(4, 4)
    assert len(frames) == 16
    assert frames[0].get_size() == (32, 32)


def test_load_grid_by_size_invalid_returns_dummies():
    """load_grid_by_size returns dummy surfaces when sheet is invalid."""
    ss = SpriteSheet("")
    frames = ss.load_grid_by_size(16, 16)
    assert len(frames) == 16
    assert frames[0].get_size() == (16, 16)


# --- _create_dummy_surface ---


def test_create_dummy_surface_opaque():
    """Opaque dummy surface is solid blue."""
    ss = SpriteSheet("")
    surf = ss._create_dummy_surface((32, 32), transparent=False)
    assert surf.get_size() == (32, 32)
    assert surf.get_at((0, 0))[:3] == (0, 0, 255)  # Blue


def test_create_dummy_surface_transparent():
    """Transparent dummy surface has SRCALPHA flag."""
    ss = SpriteSheet("")
    surf = ss._create_dummy_surface((24, 24), transparent=True)
    assert surf.get_size() == (24, 24)
    assert surf.get_flags() & pygame.SRCALPHA
