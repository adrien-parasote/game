import pygame
import pytest
import os
from unittest.mock import MagicMock, patch
from src.ui.dialogue import DialogueManager
from src.entities.groups import CameraGroup
from src.engine.inventory_system import Inventory, Item
from src.ui.hud import GameHUD, HUD_MARGIN_X, HUD_MARGIN_Y
from src.ui.inventory import InventoryUI
from src.config import Settings
from src.entities.pickup import PickupItem
from src.engine.game import Game
from src.engine.time_system import TimeSystem

"""
Consolidated UI/UX Test Suite
Includes: HUD, Dialogue, Inventory UI, and Camera tests.
"""

@pytest.fixture
def time_system():
    return TimeSystem(initial_hour=14)

# --- HUD Tests ---

def test_hud_initialization(time_system):
    """GameHUD initializes and loads assets."""
    hud = GameHUD(time_system)
    assert hud is not None
    assert hud._clock_surf is not None
    assert len(hud._season_surfs) == 4

def test_hud_draw_no_fail(time_system):
    """GameHUD.draw renders without crashing."""
    hud = GameHUD(time_system)
    screen = pygame.Surface((1280, 720))
    hud.draw(screen)

def test_hud_lang_labels(time_system):
    """Language file is loaded correctly by HUD."""
    hud = GameHUD(time_system, lang='fr')
    seasons = hud._lang.get('seasons', {})
    assert seasons.get('SPRING') == 'Printemps'

# --- Dialogue Manager Tests ---

def test_dialogue_state():
    dm = DialogueManager()
    assert dm.is_active is False

def test_dialogue_start():
    dm = DialogueManager()
    dm.start_dialogue('Test Message', title='Hero')
    assert dm.is_active is True
    assert dm.title == 'Hero'
    assert len(dm._pages) > 0

def test_dialogue_typewriter():
    dm = DialogueManager()
    dm.typewriter_speed = 100.0
    dm.start_dialogue('Fast type')
    dm.update(0.05)
    assert len(dm.displayed_text) == 5

def test_dialogue_pagination_logic(mock_font):
    dm = DialogueManager()
    long_text = 'word ' * 200
    dm.start_dialogue(long_text, title='Title')
    max_lines_title = len(dm._pages[0])
    dm.start_dialogue(long_text, title='')
    max_lines_no_title = len(dm._pages[0])
    assert max_lines_no_title > max_lines_title

def test_dialogue_advance_skip():
    dm = DialogueManager()
    dm.start_dialogue('Page 1 text. More words.', title='A')
    dm.typewriter_speed = 1.0
    dm.update(0.1)
    dm.advance() # Should skip typewriter
    assert dm._is_page_complete is True

# --- Inventory UI Tests ---

def test_inventory_ui_basic():
    player_mock = MagicMock()
    player_mock.inventory.items = []
    player_mock.frames = [pygame.Surface((32, 32))] * 16
    with patch('src.ui.inventory.InventoryUI._load_asset', return_value=pygame.Surface((32, 32))):
        inv_ui = InventoryUI(player_mock)
        assert not inv_ui.is_open
        inv_ui.toggle()
        assert inv_ui.is_open

def test_inventory_ui_localization():
    """InventoryUI should use lang file for item names."""
    player_mock = MagicMock()
    player_mock.frames = [pygame.Surface((32, 32))] * 16
    with patch('src.ui.inventory.InventoryUI._load_asset', return_value=pygame.Surface((32, 32))):
        inv_ui = InventoryUI(player_mock, lang='fr')
        # Simulate item
        item = MagicMock()
        item.id = 'potion_red'
        item.name = 'Default Name'
        item.description = 'Default Desc'
        
        # In InventoryUI._draw_stats, it should resolve 'Potion Rouge'
        name = inv_ui._lang.get('items', {}).get(item.id, {}).get('name', item.name)
        assert name == 'Potion Rouge'

def test_inventory_ui_drawing(mock_font):
    player = MagicMock()
    player.inventory = Inventory(capacity=28)
    player.frames = [pygame.Surface((32, 32))] * 16
    with patch('src.ui.inventory.InventoryUI._load_asset', return_value=pygame.Surface((32, 32))):
        ui = InventoryUI(player)
        ui.is_open = True
        ui.slot_img = pygame.Surface((32, 32))
        ui.hover_img = pygame.Surface((32, 32))
        ui.bg = pygame.Surface((100, 100))
        ui.bg_rect = ui.bg.get_rect()
        ui.active_tab_img = pygame.Surface((10, 10))
        ui.tab_rects = {0: pygame.Rect(0, 0, 10, 10)}
        screen = pygame.Surface((1280, 720))
        ui.draw(screen)
        assert mock_font.render.called

# --- Camera & Graphics Tests ---

def test_camera_clamping():
    camera = CameraGroup()
    camera.set_world_size(2000, 2000)
    class MockSprite:
        rect = pygame.Rect(2000, 2000, 32, 32)
        rect.center = (2000, 2000)
    offset = camera.calculate_offset(MockSprite())
    # 2000 - 1280/2 = 1360. But clamped to world_size - screen_size = 2000 - 1280 = 720.
    assert offset.x == -720
    assert offset.y == -1280

def test_camera_centering():
    camera = CameraGroup()
    camera.set_world_size(800, 600)
    class MockSprite:
        rect = pygame.Rect(400, 300, 32, 32)
        rect.center = (400, 300)
    offset = camera.calculate_offset(MockSprite())
    # Small map centered on 1280x720 screen: (1280-800)/2 = 240
    assert offset.x == 240
    assert offset.y == 60