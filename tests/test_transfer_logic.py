import pytest
import pygame
from unittest.mock import MagicMock
from src.ui.chest import ChestUI
from src.engine.inventory_system import Inventory, Item

@pytest.fixture
def chest_ui():
    ui = ChestUI()
    ui._player = MagicMock()
    ui._player.inventory = Inventory(capacity=5)
    ui._player.inventory.item_data = {"potion": {"stack_max": 10}, "coin": {"stack_max": 100}}
    ui._chest_entity = MagicMock()
    ui._chest_entity.contents = []
    ui.is_open = True
    return ui

def test_transfer_chest_to_inventory_success(chest_ui):
    # Setup chest contents
    chest_ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    
    # Execute transfer
    chest_ui._transfer_chest_to_inventory()
    
    # Verify
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 0
    assert chest_ui._player.inventory.slots[0].id == "sword"

def test_transfer_chest_to_inventory_stacking(chest_ui):
    # Setup inventory with some items
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="potion", name="Potion", description="Desc", quantity=2, stack_max=10, icon="potion.png")
    
    # Setup chest contents
    chest_ui._chest_entity.contents = [{"item_id": "potion", "quantity": 5}]
    
    # Execute transfer
    chest_ui._transfer_chest_to_inventory()
    
    # Verify
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 0
    assert inv.slots[0].quantity == 7

def test_transfer_chest_to_inventory_full(chest_ui):
    # Fill inventory
    inv = chest_ui._player.inventory
    for i in range(inv.capacity):
        inv.slots[i] = Item(id="dirt", name="Dirt", description="Desc", quantity=1)
    
    # Setup chest contents
    chest_ui._chest_entity.contents = [{"item_id": "gold", "quantity": 10}]
    
    # Execute transfer
    chest_ui._transfer_chest_to_inventory()
    
    # Verify nothing moved
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 1
    assert chest_ui._chest_entity.contents[0]["quantity"] == 10

def test_transfer_inventory_to_chest_success(chest_ui):
    # Setup inventory
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="coin", name="Coin", description="Desc", quantity=10, stack_max=100)
    
    # Execute transfer
    chest_ui._transfer_inventory_to_chest()
    
    # Verify
    assert inv.slots[0] is None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 1
    assert chest_ui._chest_entity.contents[0]["item_id"] == "coin"
    assert chest_ui._chest_entity.contents[0]["quantity"] == 10

def test_transfer_inventory_to_chest_full(chest_ui):
    # Fill chest
    from src.engine.loot_table import CHEST_MAX_SLOTS
    chest_ui._chest_entity.contents = [{"item_id": "junk", "quantity": 1} for _ in range(CHEST_MAX_SLOTS)]
    
    # Setup inventory
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="diamond", name="Diamond", description="Desc", quantity=1)
    
    # Execute transfer
    chest_ui._transfer_inventory_to_chest()
    
    # Verify nothing moved
    assert inv.slots[0] is not None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == CHEST_MAX_SLOTS

# -----------------------------------------------------------------------
# Manual Drag & Drop tests
# -----------------------------------------------------------------------

def test_manual_drag_chest_to_inventory(chest_ui):
    # Setup
    chest_ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    chest_ui._layout_computed = True
    # Mock slot position
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._inv_slot_positions = [pygame.Rect(100, 100, 50, 50)]
    chest_ui._inv_bg_rect = pygame.Rect(100, 100, 200, 200)
    
    # 1. Mouse down on slot 0
    event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    chest_ui.handle_event(event_down)
    assert chest_ui._dragging_item is not None
    assert chest_ui._dragging_item["item_id"] == "sword"
    
    # 2. Mouse motion
    event_move = MagicMock(type=pygame.MOUSEMOTION, pos=(125, 125))
    chest_ui.handle_event(event_move)
    assert chest_ui._drag_pos == (125, 125)
    
    # 3. Mouse up on inventory panel
    event_up = MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(125, 125))
    chest_ui.handle_event(event_up)
    
    # Verify
    assert chest_ui._dragging_item is None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 0
    assert chest_ui._player.inventory.slots[0].id == "sword"

def test_manual_drag_inventory_to_chest_stacking(chest_ui):
    # Setup
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="potion", name="P", description="D", quantity=5, stack_max=10)
    chest_ui._chest_entity.contents = [{"item_id": "potion", "quantity": 2}]
    
    chest_ui._layout_computed = True
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._inv_slot_positions = [pygame.Rect(100, 100, 50, 50)]
    chest_ui._bg_rect = pygame.Rect(10, 10, 80, 80)
    
    # 1. Drag from inv
    event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(110, 110))
    chest_ui.handle_event(event_down)
    assert chest_ui._dragging_item["item_id"] == "potion"
    
    # 2. Drop in chest panel
    event_up = MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(20, 20))
    chest_ui.handle_event(event_up)
    
    # Verify
    assert chest_ui._chest_entity.contents[0]["quantity"] == 7
    assert inv.slots[0] is None

def test_manual_drag_from_empty_slot(chest_ui):
    # Setup
    chest_ui._chest_entity.contents = []
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    
    # Mouse down on empty slot
    event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    chest_ui.handle_event(event_down)
    
    assert chest_ui._dragging_item is None

def test_manual_drag_cancel_drop(chest_ui):
    # Setup
    chest_ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._bg_rect = pygame.Rect(10, 10, 80, 80)
    chest_ui._inv_bg_rect = pygame.Rect(100, 100, 200, 200)
    
    # Drag
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)))
    
    # Drop in nowhere (e.g. at 0, 0 outside panels)
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    
    # Verify item remains in chest
    assert chest_ui._dragging_item is None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 1
    assert chest_ui._chest_entity.contents[0]["item_id"] == "sword"

def test_auto_transfer_buttons(chest_ui):
    # Mock button rects
    chest_ui._arrow_up_rect = pygame.Rect(10, 10, 20, 20)
    chest_ui._arrow_down_rect = pygame.Rect(40, 10, 20, 20)
    
    # Mock transfer methods
    chest_ui._transfer_chest_to_inventory = MagicMock()
    chest_ui._transfer_inventory_to_chest = MagicMock()
    
    # Click UP (Left)
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)))
    chest_ui._transfer_chest_to_inventory.assert_called_once()
    
    # Click DOWN (Right)
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 20)))
    chest_ui._transfer_inventory_to_chest.assert_called_once()

def test_inventory_scroll_buttons(chest_ui):
    # Mock scroll rects
    chest_ui._inv_arrow_left_rect = pygame.Rect(10, 10, 20, 20)
    chest_ui._inv_arrow_right_rect = pygame.Rect(40, 10, 20, 20)
    
    # Mock scroll methods and capacity
    chest_ui._scroll_left = MagicMock()
    chest_ui._scroll_right = MagicMock()
    chest_ui._can_scroll_left = MagicMock(return_value=True)
    chest_ui._can_scroll_right = MagicMock(return_value=True)
    
    # Click Left
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)))
    chest_ui._scroll_left.assert_called_once()
    
    # Click Right
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 20)))
    chest_ui._scroll_right.assert_called_once()

def test_hover_updates(chest_ui):
    # Mock elements
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._inv_slot_positions = [pygame.Rect(100, 100, 50, 50)]
    chest_ui._inv_offset = 0
    chest_ui._player.inventory.capacity = 28
    
    chest_ui._arrow_up_rect = pygame.Rect(200, 10, 20, 20)
    chest_ui._arrow_down_rect = pygame.Rect(230, 10, 20, 20)
    chest_ui._inv_arrow_left_rect = pygame.Rect(260, 10, 20, 20)
    chest_ui._inv_arrow_right_rect = pygame.Rect(290, 10, 20, 20)
    
    chest_ui._can_scroll_left = MagicMock(return_value=True)
    chest_ui._can_scroll_right = MagicMock(return_value=True)
    
    # Hover Chest Slot
    chest_ui.update_hover((20, 20))
    assert chest_ui._hovered_chest_slot == 0
    
    # Hover Inventory Slot
    chest_ui.update_hover((110, 110))
    assert chest_ui._hovered_inv_slot == 0
    
    # Hover Chest Arrows
    chest_ui.update_hover((210, 20))
    assert chest_ui._hovered_chest_arrow == "up"
    chest_ui.update_hover((240, 20))
    assert chest_ui._hovered_chest_arrow == "down"
    
    # Hover Inv Arrows
    chest_ui.update_hover((270, 20))
    assert chest_ui._hovered_inv_arrow == "left"
    chest_ui.update_hover((300, 20))
    assert chest_ui._hovered_inv_arrow == "right"
