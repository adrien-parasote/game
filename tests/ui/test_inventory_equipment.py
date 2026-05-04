import unittest
from unittest.mock import MagicMock, patch

from src.engine.inventory_system import Inventory, Item


class TestInventoryEquipment(unittest.TestCase):
    def setUp(self):
        # Patch the I18nManager and item_data loading to avoid file IO and dependencies
        patcher_i18n = patch("src.engine.inventory_system.I18nManager")
        self.mock_i18n = patcher_i18n.start()
        self.mock_i18n.return_value.get_item.return_value = {
            "name": "Test Potion",
            "description": "Desc",
        }
        self.addCleanup(patcher_i18n.stop)

        patcher_load = patch.object(Inventory, "_load_item_data")
        self.mock_load = patcher_load.start()
        self.mock_load.return_value = {
            "potion_red": {"stack_max": 10, "icon": "00-potion.png", "equip_slot": "BELT"},
            "test_sword": {"stack_max": 1, "icon": "sword.png", "equip_slot": "RIGHT_HAND"},
            "test_helm": {"stack_max": 1, "icon": "helm.png", "equip_slot": "HEAD"},
            "generic_item": {"stack_max": 5, "icon": "generic.png"},  # No equip slot
        }
        self.addCleanup(patcher_load.stop)

        self.inventory = Inventory(capacity=5)

    def test_equipment_initialization(self):
        """Test that equipment slots are initialized to None."""
        expected_slots = [
            "HEAD",
            "BAG",
            "BELT",
            "LEFT_HAND",
            "UPPER_BODY",
            "LOWER_BODY",
            "RIGHT_HAND",
            "SHOES",
        ]
        for slot in expected_slots:
            self.assertIn(slot, self.inventory.equipment)
            self.assertIsNone(self.inventory.equipment[slot])

    def test_equip_item_valid(self):
        """Test equipping an item to a valid slot."""
        item = self.inventory.create_item("test_sword", 1)
        swapped = self.inventory.equip_item("RIGHT_HAND", item)
        self.assertIsNone(swapped)
        assert self.inventory.equipment["RIGHT_HAND"] is not None
        self.assertEqual(self.inventory.equipment["RIGHT_HAND"].id, "test_sword")

    def test_equip_item_invalid_slot(self):
        """Test equipping an item to a slot it doesn't belong to."""
        item = self.inventory.create_item("test_sword", 1)
        swapped = self.inventory.equip_item("HEAD", item)
        # Should return the item back because it can't be equipped there
        self.assertEqual(swapped, item)
        self.assertIsNone(self.inventory.equipment["HEAD"])

    def test_equip_item_no_equip_slot(self):
        """Test equipping an item that has no equip_slot property."""
        item = self.inventory.create_item("generic_item", 1)
        swapped = self.inventory.equip_item("BAG", item)
        self.assertEqual(swapped, item)
        self.assertIsNone(self.inventory.equipment["BAG"])

    def test_equip_item_swap(self):
        """Test equipping an item to a slot that already has an item."""
        sword1 = self.inventory.create_item("test_sword", 1)
        sword2 = self.inventory.create_item("test_sword", 1)

        self.inventory.equip_item("RIGHT_HAND", sword1)
        swapped = self.inventory.equip_item("RIGHT_HAND", sword2)

        self.assertEqual(swapped, sword1)
        self.assertEqual(self.inventory.equipment["RIGHT_HAND"], sword2)

    def test_unequip_item(self):
        """Test unequipping an item."""
        item = self.inventory.create_item("test_helm", 1)
        self.inventory.equip_item("HEAD", item)

        unequipped = self.inventory.unequip_item("HEAD")
        self.assertEqual(unequipped, item)
        self.assertIsNone(self.inventory.equipment["HEAD"])

    def test_unequip_empty_slot(self):
        """Test unequipping an empty slot returns None."""
        unequipped = self.inventory.unequip_item("BAG")
        self.assertIsNone(unequipped)


if __name__ == "__main__":
    unittest.main()
