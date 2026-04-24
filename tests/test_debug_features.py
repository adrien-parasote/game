import pytest
from src.config import Settings
from src.engine.game import Game
from unittest.mock import patch, MagicMock
import os

def test_settings_has_debug_attribute():
    """Verify that Settings has a DEBUG attribute."""
    assert hasattr(Settings, "DEBUG")

def test_game_init_selects_debug_map_when_enabled():
    """Verify that Game selects 99-debug_room.tmj when DEBUG is True."""
    with patch("src.config.Settings.DEBUG", True):
        with patch("os.path.exists", return_value=True):
            # Mock groups to avoid display errors
            with patch("src.engine.game.CameraGroup"):
                with patch.object(Game, "_load_map") as mock_load:
                    with patch.object(Game, "_setup_logging"):
                        with patch("pygame.display.set_mode"):
                            with patch("pygame.display.set_caption"):
                                with patch("src.engine.game.Player"):
                                    game = Game()
                                    mock_load.assert_called_with("99-debug_room.tmj")
