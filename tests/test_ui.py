import pytest
import pygame
from unittest.mock import MagicMock
from src.ui.dialogue import DialogueManager
from src.ui.inventory import InventoryUI
from src.engine.inventory_system import Inventory
from src.engine.i18n import I18nManager

def test_dialogue_pagination():
    """Verify that long text is paginated."""
    dm = DialogueManager()
    long_text = "Word " * 100
    dm.start_dialogue(long_text)
    assert len(dm._pages) > 1

def test_inventory_localization():
    """Verify item names are localized in inventory UI context."""
    I18nManager().load("fr")
    inv = Inventory()
    inv.add_item("potion_red")
    item = inv.get_item_at(0)
    assert item.name == "Potion Rouge"

def test_ui_visibility_toggle():
    player = MagicMock()
    ui = InventoryUI(player)
    assert ui.is_open is False
    ui.toggle()
    assert ui.is_open is True