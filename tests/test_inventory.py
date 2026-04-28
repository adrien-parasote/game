import pytest
import pygame
from unittest.mock import MagicMock
from src.entities.player import Player
from src.config import Settings

# InventoryUI might not exist yet, so we'll try to import it inside tests
# or mock it if needed to show they are RED.

@pytest.fixture(scope="module", autouse=True)
def pygame_env():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

# INV-002: Player stats initialization
def test_player_stats_initialization():
    """Verify that player has level, hp, and gold attributes."""
    player = Player((0, 0))
    assert hasattr(player, 'level'), "Player should have a level attribute"
    assert player.level == 1
    assert hasattr(player, 'hp'), "Player should have an hp attribute"
    assert player.hp == 100
    assert hasattr(player, 'max_hp'), "Player should have a max_hp attribute"
    assert player.max_hp == 100
    assert hasattr(player, 'gold'), "Player should have a gold attribute"
    assert player.gold == 0

# INV-001: InventoryUI toggle logic
def test_inventory_ui_toggle():
    """Verify that InventoryUI toggles its open state."""
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    
    assert inv.is_open is False
    inv.toggle()
    assert inv.is_open is True
    inv.toggle()
    assert inv.is_open is False

# INV-003: InventoryUI tab switching
def test_inventory_ui_tab_switching():
    """Verify that clicking/switching tabs works."""
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    
    assert inv.active_tab == 0
    inv.set_tab(1)
    assert inv.active_tab == 1
    
    # Boundary check
    inv.set_tab(99)
    assert inv.active_tab == 0 # Falls back to 0 as per implementation

# NEW: Keyboard direction rotation
def test_inventory_preview_rotation():
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    # Test all directions
    directions = {
        Settings.MOVE_UP: 'up',
        Settings.MOVE_DOWN: 'down',
        Settings.MOVE_LEFT: 'left',
        Settings.MOVE_RIGHT: 'right'
    }
    
    for key, state in directions.items():
        event = pygame.event.Event(pygame.KEYDOWN, {'key': key})
        inv.handle_input(event)
        assert inv.preview_state == state

# NEW: Mouse interaction (Tabs)
def test_inventory_mouse_tabs():
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    # Click on the second tab
    tab2_center = inv.tab_rects[1].center
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': tab2_center})
    inv.handle_input(event)
    assert inv.active_tab == 1

# NEW: Mouse interaction (Equipment)
def test_inventory_mouse_equipment():
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    # Click on HEAD slot
    head_pos = inv.equipment_slots["HEAD"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': head_pos})
    
    # We just verify it doesn't crash and maybe check if it logs (hard to check log in simple test)
    inv.handle_input(event)

# NEW: Mouse interaction (Grid)
def test_inventory_mouse_grid():
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    # Click on first grid slot
    grid_pos = inv.grid_start
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': grid_pos})
    inv.handle_input(event)

# NEW: Animation update
def test_inventory_animation():
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    initial_frame = inv.anim_frame
    # Update with enough dt to trigger frame change (150ms = 0.15s)
    inv.update(0.2)
    assert inv.anim_frame != initial_frame

# NEW: Render sanity
def test_inventory_draw():
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    screen = pygame.Surface((1280, 720))
    # Should not crash
    inv.draw(screen)

# NEW: Hover detection
def test_inventory_hover_detection():
    """Verify that hovered_slot updates correctly based on mouse position."""
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    inv.is_open = True
    
    # Initially none
    assert hasattr(inv, 'hovered_slot')
    assert inv.hovered_slot is None
    
    # 1. Test Equipment Hover (HEAD) - RE-ENABLED
    head_pos = inv.equipment_slots["HEAD"]
    inv.update_hover(head_pos)
    assert inv.hovered_slot == ("equipment", "HEAD")
    
    # 2. Test Grid Hover (Slot 0)
    grid_pos = inv.grid_start
    inv.update_hover(grid_pos)
    assert inv.hovered_slot == ("grid", 0)
    
    # 3. Test No Hover
    inv.update_hover((0, 0))
    assert inv.hovered_slot is None

# NEW: Equipment Hit Area
def test_inventory_equipment_hit_area():
    """Verify that equipment hit area matches the larger side size."""
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    assert hasattr(inv, 'equip_rect_side')
    assert inv.equip_rect_side > inv.slot_img.get_width()

# NEW: Cursor assets
def test_inventory_cursor_assets():
    """Verify cursor images are loaded."""
    from src.ui.inventory import InventoryUI
    player = Player((0, 0))
    inv = InventoryUI(player)
    assert hasattr(inv, 'pointer_img')
    assert hasattr(inv, 'pointer_select_img')
