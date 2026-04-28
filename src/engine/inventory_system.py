import json
import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Item:
    id: str
    name: str
    description: str
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
        data = self.item_data.get(item_id, {
            "name": item_id.replace("_", " ").title(),
            "description": "Un objet mystérieux.",
            "stack_max": 1
        })
        
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
