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
    assert inv.active_tab == 0 # Should fallback or clamp
