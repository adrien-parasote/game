import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.game import Game
from src.engine.asset_manager import AssetManager

@patch('src.engine.game.Game._load_map')
def test_game_initialization(mock_load):
    game = Game()
    assert game.player is not None
    assert game.i18n.current_locale == "fr"

def test_asset_manager_cache():
    am = AssetManager()
    am.clear_cache()
    # Mock font loading
    with patch('pygame.font.SysFont') as mock_sys:
        f1 = am.get_font(None, 20)
        f2 = am.get_font(None, 20)
        assert f1 == f2
        assert mock_sys.call_count == 1