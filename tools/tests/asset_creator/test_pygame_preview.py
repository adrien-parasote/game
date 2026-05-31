"""Tests for pygame preview module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Create a mock pygame
mock_pygame = MagicMock()
mock_pygame.QUIT = 12  # Dummy value for QUIT event
mock_pygame.KEYDOWN = 2
mock_pygame.K_ESCAPE = 27
mock_pygame.K_r = 114
mock_pygame.K_s = 115
mock_pygame.K_d = 100
mock_pygame.K_a = 97
mock_pygame.K_SPACE = 32
mock_pygame.K_UP = 273
mock_pygame.K_DOWN = 274

@pytest.fixture
def preview_module():
    """Fixture to safely patch pygame and import pygame_preview."""
    with patch.dict("sys.modules", {"pygame": mock_pygame}):
        from asset_creator.preview import pygame_preview
        yield pygame_preview

def test_pygame_preview_import(preview_module) -> None:
    """Importing the pygame preview module succeeds with mocked pygame."""
    assert preview_module is not None

def test_run_preview_quit(preview_module) -> None:
    """Test run_preview loop exits on QUIT event."""
    image = Image.new("RGBA", (256, 256), "white")

    # Mock pygame.event.get to return a QUIT event
    quit_event = MagicMock()
    quit_event.type = mock_pygame.QUIT

    with patch.object(mock_pygame.event, "get", return_value=[quit_event]):
        preview_module.run_preview(image)

    mock_pygame.display.set_mode.assert_called()
    mock_pygame.quit.assert_called()

def test_run_preview_escape(preview_module) -> None:
    """Test run_preview loop exits on Escape key."""
    image = Image.new("RGBA", (256, 256), "white")

    esc_event = MagicMock()
    esc_event.type = mock_pygame.KEYDOWN
    esc_event.key = mock_pygame.K_ESCAPE

    with patch.object(mock_pygame.event, "get", return_value=[esc_event]):
        preview_module.run_preview(image)

    mock_pygame.quit.assert_called()

def test_run_preview_with_subtiles(preview_module) -> None:
    """Test run_preview handling subtiles."""
    image = Image.new("RGBA", (256, 256), "white")
    from asset_creator.core.subtile import SubTileSet
    subtiles = SubTileSet(tiles={})

    quit_event = MagicMock()
    quit_event.type = mock_pygame.QUIT

    with patch.object(mock_pygame.event, "get", return_value=[quit_event]):
        preview_module.run_preview(image, subtile_set=subtiles)

    mock_pygame.quit.assert_called()
