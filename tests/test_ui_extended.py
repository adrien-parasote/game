import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.ui.inventory import InventoryUI
from src.ui.dialogue import DialogueManager
from src.engine.inventory_system import Inventory
from src.config import Settings

@pytest.fixture
def mock_pygame_init():
    pygame.font.init()
    with patch('pygame.mouse.get_pos', return_value=(0,0)):
        with patch('pygame.mouse.get_pressed', return_value=(False, False, False)):
            yield
    pygame.font.quit()

def test_inventory_ui_drawing(mock_pygame_init):
    game = MagicMock()
    game.inventory = Inventory(capacity=28)
    
    ui = InventoryUI(game)
    ui.is_open = True
    ui.slot_img = pygame.Surface((32, 32))
    ui.hover_img = pygame.Surface((32, 32))
    ui.active_tab = 0 # Grid
    ui._get_item_icon = MagicMock(return_value=pygame.Surface((16, 16)))
    
    item = MagicMock()
    item.quantity = 2
    item.icon = "apple.png"
    game.inventory.slots = [item] + [None]*27
    ui.player.inventory = game.inventory
    
    ui.font = MagicMock()
    ui.font.render.return_value = pygame.Surface((10, 10))
    ui.font_title = MagicMock()
    ui.font_title.render.return_value = pygame.Surface((10, 10))
    ui.item_font = MagicMock()
    ui.item_font.render.return_value = pygame.Surface((10, 10))
    ui.info_font = MagicMock()
    ui.info_font.render.return_value = pygame.Surface((10, 10))
    ui.info_title_font = MagicMock()
    ui.info_title_font.render.return_value = pygame.Surface((10, 10))
    ui.player = MagicMock()
    ui.player.frames = [pygame.Surface((32, 32))] * 16
    ui.bg = pygame.Surface((100, 100))
    ui.bg_rect = ui.bg.get_rect()
    ui.active_tab_img = pygame.Surface((10, 10))
    ui.tab_rects = {"items": pygame.Rect(0, 0, 10, 10)}
    ui.active_tab = "items"
    
    screen = pygame.Surface((1280, 720))
    ui.draw(screen)
    assert ui.font.render.called
    
    # Test Hovering
    ui.hovered_slot = ("grid", 0)
    ui.draw(screen)
    
    # Test Info Zone with item
    ui._draw_info_zone(screen)

def test_inventory_ui_input(mock_pygame_init):
    game = MagicMock()
    ui = InventoryUI(game)
    ui.is_open = True
    
    # Test tab switching via mouse
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui.tab_rects[1].center
    ui.handle_input(event)
    assert ui.active_tab == 1
    
    # Test equipment slot click
    slot_name = list(ui.equipment_slots.keys())[0]
    event.type = pygame.MOUSEBUTTONDOWN
    event.pos = ui.equipment_slots[slot_name]
    ui.handle_input(event)
    
    # Test grid slot click
    ui.active_tab = 0
    event.pos = (ui.grid_start[0] + 5, ui.grid_start[1] + 5)
    ui.handle_input(event)
    
    # Test preview direction switching
    event.type = pygame.KEYDOWN
    event.key = Settings.MOVE_UP
    ui.handle_input(event)
    assert ui.preview_state == 'up'
    
    # Test mouse hover equipment
    slot_name = list(ui.equipment_slots.keys())[0]
    ui.update_hover(ui.equipment_slots[slot_name])
    assert ui.hovered_slot is not None
    assert ui.hovered_slot[0] == "equipment"
    
    # Test mouse hover grid
    ui.active_tab = 0
    mouse_x = ui.grid_start[0] + 5
    mouse_y = ui.grid_start[1] + 5
    ui.update_hover((mouse_x, mouse_y))
    assert ui.hovered_slot is not None
    assert ui.hovered_slot[0] == "grid"

def test_dialogue_manager_full_cycle(mock_pygame_init):
    dm = DialogueManager()
    dm.font_message = MagicMock()
    dm.font_message.size.return_value = (10, 10)
    dm.font_message.get_linesize.return_value = 15
    dm.font_title = MagicMock()
    dm.dialogue_box = pygame.Surface((800, 200))
    
    # Start dialogue
    dm.start_dialogue("Test Message", "Title")
    assert dm.is_active is True
    
    # Update (typewriter)
    dm.update(100.0) # Finish typing
    assert dm._is_page_complete is True
    
    # Advance (finish typewriter)
    dm.advance()
    assert dm._is_page_complete is True # If only one page
    
    # Advance (close)
    dm.advance()
    assert dm.is_active is False
