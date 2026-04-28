import pytest
from src.engine.inventory_system import Inventory, Item

@pytest.fixture
def inventory():
    inv = Inventory(capacity=5)
    # Mock item data for testing
    inv.item_data = {
        "potion": {"name": "Potion", "description": "Heals", "stack_max": 10},
        "sword": {"name": "Sword", "description": "Sharp", "stack_max": 1}
    }
    return inv

def test_add_item_stacking(inventory):
    # Add 5 potions
    rem = inventory.add_item("potion", 5)
    assert rem == 0
    assert inventory.slots[0].quantity == 5
    
    # Add 8 more (total 13, max 10)
    rem = inventory.add_item("potion", 8)
    assert rem == 0
    assert inventory.slots[0].quantity == 10
    assert inventory.slots[1].id == "potion"
    assert inventory.slots[1].quantity == 3

def test_add_item_non_stackable(inventory):
    rem = inventory.add_item("sword", 1)
    assert rem == 0
    assert inventory.slots[0].id == "sword"
    
    rem = inventory.add_item("sword", 1)
    assert rem == 0
    assert inventory.slots[1].id == "sword"

def test_inventory_full(inventory):
    # Fill 5 slots
    for i in range(5):
        inventory.add_item("sword", 1)
    
    assert inventory.is_full()
    rem = inventory.add_item("sword", 1)
    assert rem == 1
