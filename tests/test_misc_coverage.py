import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.asset_manager import AssetManager
from src.engine.inventory_system import Inventory
from src.ui.hud import GameHUD

def test_asset_manager_load():
    am = AssetManager()
    mock_surf = MagicMock(spec=pygame.Surface)
    mock_surf.convert_alpha.return_value = mock_surf
    with patch('pygame.image.load', return_value=mock_surf):
        with patch('os.path.exists', return_value=True):
            img = am.get_image("test.png")
            assert img is not None

def test_inventory_system_logic():
    inv = Inventory(capacity=10)
    inv.item_data = {"potion": {"stack_max": 99, "name": "Potion", "description": "Desc"}}
    assert inv.add_item("potion", 5) == 0
    assert inv.slots[0].quantity == 5
    
    assert inv.add_item("potion", 10) == 0
    assert inv.slots[0].quantity == 15

def test_game_hud_draw():
    game = MagicMock()
    game.player.hp = 10
    game.player.max_hp = 100
    game.time_system.current_season = "printemps"
    game.time_system.time_label = "12:00"
    game.time_system.day_label = "Jour 1"
    
    pygame.font.init()
    hud = GameHUD(game)
    hud._font = MagicMock()
    hud._font.render.return_value = pygame.Surface((10, 10))
    hud._clock_surf = pygame.Surface((100, 100))
    hud._season_surfs = {"printemps": pygame.Surface((10, 10))}
    hud.hp_bar_bg = pygame.Surface((100, 10))
    hud.hp_bar_fill = pygame.Surface((100, 10))
    hud.time_system = game.time_system
    
    screen = pygame.Surface((800, 600))
    hud.draw(screen)
    assert hud._font.render.called
