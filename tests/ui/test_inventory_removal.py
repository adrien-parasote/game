import pytest

from src.engine.inventory_system import Inventory, Item


def test_inventory_remove_item():
    inv = Inventory(capacity=5)
    inv.slots[0] = Item(id="test_item", name="Test", description="Desc", quantity=5)

    removed = inv.remove_item(0)
    assert removed is not None
    assert removed.id == "test_item"
    assert inv.slots[0] is None


def test_inventory_remove_item_invalid_index():
    inv = Inventory(capacity=5)
    assert inv.remove_item(10) is None
    assert inv.remove_item(-1) is None


def test_inventory_remove_item_empty_slot():
    inv = Inventory(capacity=5)
    assert inv.remove_item(0) is None


# Note: Integration tests for UI transfers will be harder to unit test without mocking
# but I can test the logic helper if I extract it.
