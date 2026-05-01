import json
import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from src.engine.i18n import I18nManager

@dataclass
class Item:
    id: str
    name: str
    description: str
    icon: Optional[str] = None
    quantity: int = 1
    stack_max: int = 1

class Inventory:
    """
    Manages player items, stacking, and capacity.
    """
    def __init__(self, capacity: int = 28):
        self.capacity = capacity
        self.slots: List[Optional[Item]] = [None] * capacity
        self.item_data = self._load_item_data()
        self.i18n = I18nManager()

    def _load_item_data(self) -> Dict[str, dict]:
        """Load item properties from JSON."""
        path = os.path.join("assets", "data", "propertytypes.json")
        if not os.path.exists(path):
            logging.error(f"Inventory: Properties file not found at {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Inventory: Failed to load properties: {e}")
            return {}

    def add_item(self, item_id: str, quantity: int = 1) -> int:
        """
        Add items to inventory. Returns the remaining quantity that couldn't be added.
        """
        remaining = quantity
        
        # Merge technical data (stack_max, icon) with localized strings (name, description)
        tech_data = self.item_data.get(item_id, {})
        lang_data = self.i18n.get_item(item_id)
        
        data = {
            "name": lang_data["name"],
            "description": lang_data["description"],
            "stack_max": tech_data.get("stack_max", 1),
            "icon": tech_data.get("icon", f"{item_id}.png")
        }
        
        stack_max = data.get("stack_max", 1)

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
                self.slots[i] = Item(
                    id=item_id,
                    name=data["name"],
                    description=data["description"],
                    icon=data.get("icon", f"{item_id}.png"),
                    quantity=can_add,
                    stack_max=stack_max
                )
                remaining -= can_add
                if remaining <= 0:
                    return 0
                    
        return remaining

    def is_full(self) -> bool:
        """Check if there are no empty slots."""
        return all(slot is not None for slot in self.slots)

    def get_item_at(self, index: int) -> Optional[Item]:
        if 0 <= index < self.capacity:
            return self.slots[index]
        return None

    def remove_item(self, index: int) -> Optional[Item]:
        """Remove and return the item at *index*. Return None if empty or out of bounds."""
        if 0 <= index < self.capacity:
            item = self.slots[index]
            self.slots[index] = None
            return item
        return None
