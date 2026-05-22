"""Tests for inventory_system.py missing branches (lines 122, 142)."""

from unittest.mock import MagicMock, patch

import pytest

from src.engine.inventory_system import Inventory, Item


class TestInventoryEquip:
    def _make_inventory(self):
        with patch("src.engine.inventory_system.os.path.exists", return_value=False):
            return Inventory()

    def test_equip_item_invalid_slot_name_returns_item(self):
        """Ligne 122 : slot_name not in equipment → retourne item inchangé."""
        inv = self._make_inventory()
        item = Item(id="sword", name="Sword", description="A sword", quantity=1, stack_max=1)
        result = inv.equip_item("INVALID_SLOT", item)
        assert result is item

    def test_equip_item_wrong_equip_slot_returns_item(self):
        """Ligne 128 : valid_slot != slot_name → retourne item inchangé."""
        inv = self._make_inventory()
        # item_data maps "sword" to equip_slot="RIGHT_HAND"
        inv.item_data = {"sword": {"equip_slot": "RIGHT_HAND", "stack_max": 1}}
        item = Item(id="sword", name="Sword", description="", quantity=1, stack_max=1)
        result = inv.equip_item("HEAD", item)  # "RIGHT_HAND" != "HEAD"
        assert result is item

    def test_equip_item_valid_slot_swaps(self):
        """equip_item retourne l'item précédent quand le slot correspond."""
        inv = self._make_inventory()
        inv.item_data = {"helm": {"equip_slot": "HEAD", "stack_max": 1}}
        helm = Item(id="helm", name="Helm", description="", quantity=1, stack_max=1)
        swapped = inv.equip_item("HEAD", helm)
        assert swapped is None  # slot était vide
        assert inv.equipment["HEAD"] is helm


class TestInventoryUnequip:
    def _make_inventory(self):
        with patch("src.engine.inventory_system.os.path.exists", return_value=False):
            return Inventory()

    def test_unequip_item_invalid_slot_returns_none(self):
        """Ligne 142 : slot_name not in equipment → retourne None."""
        inv = self._make_inventory()
        result = inv.unequip_item("INVALID_SLOT")
        assert result is None

    def test_unequip_item_valid_slot_returns_item(self):
        """unequip_item retourne l'item équipé depuis un slot valide."""
        inv = self._make_inventory()
        helm = Item(id="helm", name="Helm", description="", quantity=1, stack_max=1)
        inv.equipment["HEAD"] = helm
        result = inv.unequip_item("HEAD")
        assert result is helm
        assert inv.equipment["HEAD"] is None
