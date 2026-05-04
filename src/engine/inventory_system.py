import json
import logging
import os
from dataclasses import dataclass

from src.engine.i18n import I18nManager


@dataclass
class Item:
    id: str
    name: str
    description: str
    icon: str | None = None
    quantity: int = 1
    stack_max: int = 1


class Inventory:
    """
    Manages player items, stacking, and capacity.
    """

    def __init__(self, capacity: int = 28):
        self.capacity = capacity
        self.slots: list[Item | None] = [None] * capacity
        self.equipment: dict[str, Item | None] = {
            "HEAD": None,
            "BAG": None,
            "BELT": None,
            "LEFT_HAND": None,
            "UPPER_BODY": None,
            "LOWER_BODY": None,
            "RIGHT_HAND": None,
            "SHOES": None,
        }
        self.item_data = self._load_item_data()
        self.i18n = I18nManager()

    def _load_item_data(self) -> dict[str, dict]:
        """Load item properties from JSON."""
        path = os.path.join("assets", "data", "propertytypes.json")
        if not os.path.exists(path):
            logging.error(f"Inventory: Properties file not found at {path}")
            return dict()
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Inventory: Failed to load properties: {e}")
            return dict()

    def create_item(self, item_id: str, quantity: int) -> Item:
        """Create a new Item object populated with tech and lang data."""
        tech_data = self.item_data.get(item_id, {})
        lang_data = self.i18n.get_item(item_id)

        return Item(
            id=item_id,
            name=lang_data["name"],
            description=lang_data["description"],
            icon=tech_data.get("icon", f"{item_id}.png"),
            quantity=quantity,
            stack_max=tech_data.get("stack_max", 1),
        )

    def add_item(self, item_id: str, quantity: int = 1) -> int:
        """
        Add items to inventory. Returns the remaining quantity that couldn't be added.
        """
        remaining = quantity

        temp_item = self.create_item(item_id, 1)
        stack_max = temp_item.stack_max

        # 1. Try to stack in existing slots
        for i in range(self.capacity):
            slot = self.slots[i]
            if slot and slot.id == item_id and slot.quantity < stack_max:
                can_add = min(remaining, stack_max - slot.quantity)
                slot.quantity += can_add
                remaining -= can_add
                if remaining <= 0:
                    return 0

        # 2. Fill empty slots
        for i in range(self.capacity):
            if self.slots[i] is None:
                can_add = min(remaining, stack_max)
                self.slots[i] = self.create_item(item_id, can_add)
                remaining -= can_add
                if remaining <= 0:
                    return 0

        return remaining

    def is_full(self) -> bool:
        """Check if there are no empty slots."""
        return all(slot is not None for slot in self.slots)

    def get_item_at(self, index: int) -> Item | None:
        if 0 <= index < self.capacity:
            return self.slots[index]
        return None

    def remove_item(self, index: int) -> Item | None:
        """Remove and return the item at *index*. Return None if empty or out of bounds."""
        if 0 <= index < self.capacity:
            item = self.slots[index]
            self.slots[index] = None
            return item
        return None

    def equip_item(self, slot_name: str, item: Item) -> Item | None:
        """
        Equips the given item into the specified slot.
        Returns the previously equipped item if one was swapped out.
        If the item is not valid for this slot based on propertytypes.json,
        returns the passed item untouched and does not equip it.
        """
        if slot_name not in self.equipment:
            return item

        tech_data = self.item_data.get(item.id, {})
        valid_slot = tech_data.get("equip_slot")

        if valid_slot != slot_name:
            return item

        swapped = self.equipment[slot_name]
        self.equipment[slot_name] = item
        return swapped

    def unequip_item(self, slot_name: str) -> Item | None:
        """
        Removes and returns the equipped item from the specified slot.
        """
        if slot_name in self.equipment:
            item = self.equipment[slot_name]
            self.equipment[slot_name] = None
            return item
        return None
