"""Loot table loader for chest content initialization.

Loads chest contents from a JSON file, validates item IDs against
property types, splits stacks by stack_max, and trims overflow.
"""
import json
import logging
import math
import os
from typing import Optional

CHEST_MAX_SLOTS = 20  # 10 columns x 2 rows in the chest UI


class LootTable:
    """Loads and serves chest contents from a data file.

    Usage:
        loot = LootTable()
        loot.load("assets/data/loot_table.json", property_types_dict)
        contents = loot.get_contents("chest_debug_1")
    """

    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {}

    def load(self, loot_path: str, property_types: dict) -> None:
        """Load loot table from JSON, validate items, and split stacks.

        Args:
            loot_path: Absolute or relative path to loot_table.json.
            property_types: Dict of valid item_id → item metadata.
        """
        raw = self._read_json(loot_path)
        if raw is None:
            return

        for chest_key, entries in raw.items():
            if not isinstance(entries, list):
                logging.warning(
                    f"LootTable: Expected list for chest '{chest_key}', got {type(entries).__name__}. Skipped."
                )
                continue

            validated = self._validate_entries(chest_key, entries, property_types)
            split = self._split_stacks(validated, property_types)
            self._data[chest_key] = self._trim_overflow(chest_key, split)

    def get_contents(self, element_id: str) -> list[dict]:
        """Return the contents for a given chest element_id.

        Returns an empty list if the element_id has no loot entry.
        """
        return list(self._data.get(element_id, []))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_json(self, path: str) -> Optional[dict]:
        """Read and parse JSON file. Returns None on failure."""
        if not os.path.exists(path):
            logging.error(f"LootTable: File not found at '{path}'.")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logging.error(f"LootTable: Expected dict at root, got {type(data).__name__}.")
                return None
            return data
        except json.JSONDecodeError as e:
            logging.error(f"LootTable: Malformed JSON in '{path}': {e}")
            return None

    def _validate_entries(
        self, chest_key: str, entries: list, property_types: dict
    ) -> list[dict]:
        """Filter entries: skip missing item_id, unknown items, zero quantity."""
        valid = []
        for entry in entries:
            item_id = entry.get("item_id")
            if not item_id:
                logging.warning(
                    f"LootTable: Entry in chest '{chest_key}' missing 'item_id'. Skipped."
                )
                continue

            if item_id not in property_types:
                logging.warning(
                    f"LootTable: Unknown item_id '{item_id}' in chest '{chest_key}'. Skipped."
                )
                continue

            quantity = entry.get("quantity", 1)
            if quantity <= 0:
                logging.warning(
                    f"LootTable: Item '{item_id}' in chest '{chest_key}' has quantity={quantity}. Skipped."
                )
                continue

            valid.append({"item_id": item_id, "quantity": quantity})
        return valid

    def _split_stacks(
        self, entries: list[dict], property_types: dict
    ) -> list[dict]:
        """Split entries that exceed stack_max into multiple stacks."""
        result = []
        for entry in entries:
            item_id = entry["item_id"]
            quantity = entry["quantity"]
            stack_max = property_types.get(item_id, {}).get("stack_max", 1)
            stack_max = max(1, stack_max)  # guard against 0 or negative

            while quantity > 0:
                stack_qty = min(quantity, stack_max)
                result.append({"item_id": item_id, "quantity": stack_qty})
                quantity -= stack_qty
        return result

    def _trim_overflow(self, chest_key: str, entries: list[dict]) -> list[dict]:
        """Trim entries exceeding CHEST_MAX_SLOTS with a warning."""
        if len(entries) > CHEST_MAX_SLOTS:
            logging.warning(
                f"LootTable: Chest '{chest_key}' has {len(entries)} stacks, "
                f"exceeding {CHEST_MAX_SLOTS} slots. Excess trimmed."
            )
            return entries[:CHEST_MAX_SLOTS]
        return entries
