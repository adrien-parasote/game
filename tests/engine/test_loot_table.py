"""Tests for the LootTable module.

Covers: loading, item_id validation, stack splitting, overflow trimming,
and edge cases (missing files, malformed JSON, zero quantity).
"""

import json
import logging
import os
from unittest.mock import mock_open, patch

import pytest

from src.engine.loot_table import CHEST_MAX_SLOTS, LootTable

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def property_types():
    """Minimal property_types dict for validation."""
    return {
        "potion_red": {"name": "Potion Rouge", "stack_max": 10, "icon": "00-potions.png"},
        "potion_big_red": {"name": "Grande Potion", "stack_max": 10, "icon": "01-potions.png"},
        "ether_potion": {"name": "Ether", "stack_max": 10, "icon": "05-potion.png"},
        "potion_purple": {"name": "Violette", "stack_max": 10, "icon": "02-potions.png"},
        "potion_yellow": {"name": "Jaune", "stack_max": 10, "icon": "03-potions.png"},
        "potion_green": {"name": "Verte", "stack_max": 10, "icon": "04-potions.png"},
    }


@pytest.fixture
def valid_loot_data():
    """Simple loot table with valid items."""
    return {
        "chest_1": [
            {"item_id": "potion_red", "quantity": 5},
            {"item_id": "ether_potion", "quantity": 2},
        ]
    }


@pytest.fixture
def loot_table():
    """Fresh LootTable instance."""
    return LootTable()


# ---------------------------------------------------------------------------
# TC-LT-01: Valid load
# ---------------------------------------------------------------------------


class TestLootTableLoad:
    """Tests for LootTable.load()."""

    @pytest.mark.tc("TC-LT-01")
    def test_load_valid_json(self, loot_table, property_types, valid_loot_data, tmp_path):
        """TC-LT-01: Valid JSON + valid property_types → all entries loaded."""
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(valid_loot_data))

        loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        assert len(contents) == 2
        assert contents[0]["item_id"] == "potion_red"
        assert contents[0]["quantity"] == 5
        assert contents[1]["item_id"] == "ether_potion"
        assert contents[1]["quantity"] == 2

    @pytest.mark.tc("TC-LT-02")
    def test_load_unknown_item_id_skipped_and_warned(
        self, loot_table, property_types, tmp_path, caplog
    ):
        """TC-LT-02: Unknown item_id → warning logged, entry skipped."""
        data = {
            "chest_1": [
                {"item_id": "potion_red", "quantity": 3},
                {"item_id": "unknown_sword", "quantity": 1},
            ]
        }
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))

        with caplog.at_level(logging.WARNING):
            loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        assert len(contents) == 1
        assert contents[0]["item_id"] == "potion_red"
        assert "unknown_sword" in caplog.text

    @pytest.mark.tc("TC-LT-03")
    def test_load_missing_file(self, loot_table, property_types, caplog):
        """TC-LT-03: Missing file → error logged, empty data."""
        with caplog.at_level(logging.ERROR):
            loot_table.load("/nonexistent/path.json", property_types)

        assert loot_table.get_contents("anything") == []
        assert "not found" in caplog.text.lower() or "error" in caplog.text.lower()

    @pytest.mark.tc("TC-LT-04")
    def test_load_malformed_json(self, loot_table, property_types, tmp_path, caplog):
        """TC-LT-04: Malformed JSON → error logged, empty data."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json content}")

        with caplog.at_level(logging.ERROR):
            loot_table.load(str(bad_file), property_types)

        assert loot_table.get_contents("anything") == []

    def test_load_all_items_invalid(self, loot_table, property_types, tmp_path, caplog):
        """TC-LT-07: All items unknown → warnings for each, chest empty."""
        data = {
            "chest_1": [
                {"item_id": "fake_item_a", "quantity": 1},
                {"item_id": "fake_item_b", "quantity": 2},
            ]
        }
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))

        with caplog.at_level(logging.WARNING):
            loot_table.load(str(loot_file), property_types)

        assert loot_table.get_contents("chest_1") == []
        assert "fake_item_a" in caplog.text
        assert "fake_item_b" in caplog.text

    def test_load_entry_missing_item_id(self, loot_table, property_types, tmp_path, caplog):
        """TC-LT-08: Entry without item_id key → warning, skipped."""
        data = {
            "chest_1": [
                {"quantity": 5},  # no item_id
                {"item_id": "potion_red", "quantity": 1},
            ]
        }
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))

        with caplog.at_level(logging.WARNING):
            loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        assert len(contents) == 1
        assert contents[0]["item_id"] == "potion_red"

    def test_load_entry_zero_quantity(self, loot_table, property_types, tmp_path, caplog):
        """TC-LT-09: Entry with quantity=0 → skipped with warning."""
        data = {
            "chest_1": [
                {"item_id": "potion_red", "quantity": 0},
            ]
        }
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))

        with caplog.at_level(logging.WARNING):
            loot_table.load(str(loot_file), property_types)

        assert loot_table.get_contents("chest_1") == []


# ---------------------------------------------------------------------------
# TC-LT-05/06: get_contents
# ---------------------------------------------------------------------------


class TestGetContents:
    """Tests for LootTable.get_contents()."""

    @pytest.mark.tc("TC-LT-08")
    def test_known_element_id(self, loot_table, property_types, valid_loot_data, tmp_path):
        """TC-LT-05: Known element_id → returns item list."""
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(valid_loot_data))
        loot_table.load(str(loot_file), property_types)

        result = loot_table.get_contents("chest_1")
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.tc("TC-LT-09")
    def test_unknown_element_id(self, loot_table, property_types, valid_loot_data, tmp_path):
        """TC-LT-06: Unknown element_id → returns empty list."""
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(valid_loot_data))
        loot_table.load(str(loot_file), property_types)

        assert loot_table.get_contents("nonexistent_chest") == []

    @pytest.mark.tc("TC-LT-10")
    def test_get_contents_before_load(self, loot_table):
        """get_contents before load() → empty list."""
        assert loot_table.get_contents("anything") == []


# ---------------------------------------------------------------------------
# Stack splitting tests
# ---------------------------------------------------------------------------


class TestStackSplitting:
    """Tests for stack_max splitting logic."""

    @pytest.mark.tc("TC-LT-05")
    def test_quantity_within_stack_max(self, loot_table, property_types, tmp_path):
        """Quantity <= stack_max → single entry unchanged."""
        data = {"chest_1": [{"item_id": "potion_red", "quantity": 5}]}
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))
        loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        assert len(contents) == 1
        assert contents[0]["quantity"] == 5

    @pytest.mark.tc("TC-LT-06")
    def test_quantity_exceeds_stack_max(self, loot_table, property_types, tmp_path):
        """Quantity > stack_max → split into multiple stacks."""
        data = {"chest_1": [{"item_id": "potion_red", "quantity": 25}]}
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))
        loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        # 25 / stack_max=10 → 3 stacks: 10 + 10 + 5
        assert len(contents) == 3
        assert contents[0]["quantity"] == 10
        assert contents[1]["quantity"] == 10
        assert contents[2]["quantity"] == 5

    def test_exact_stack_max_multiple(self, loot_table, property_types, tmp_path):
        """Quantity is exact multiple of stack_max → no remainder."""
        data = {"chest_1": [{"item_id": "potion_red", "quantity": 20}]}
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))
        loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        # 20 / 10 = 2 stacks of 10
        assert len(contents) == 2
        assert all(c["quantity"] == 10 for c in contents)

    @pytest.mark.tc("TC-LT-07")
    def test_overflow_trimmed_with_warning(self, loot_table, property_types, tmp_path, caplog):
        """More stacks than CHEST_MAX_SLOTS → excess trimmed."""
        # 21 items with stack_max=1 would need 21 slots > 20
        props = {"single_stack_item": {"name": "X", "stack_max": 1, "icon": "x.png"}}
        entries = [{"item_id": "single_stack_item", "quantity": 1} for _ in range(25)]
        data = {"chest_1": entries}

        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))

        with caplog.at_level(logging.WARNING):
            loot_table.load(str(loot_file), props)

        contents = loot_table.get_contents("chest_1")
        assert len(contents) == CHEST_MAX_SLOTS
        assert "trimmed" in caplog.text.lower() or "excess" in caplog.text.lower()

    def test_multiple_items_split_and_combined(self, loot_table, property_types, tmp_path):
        """Multiple items with different quantities → correct total slots."""
        data = {
            "chest_1": [
                {"item_id": "potion_red", "quantity": 15},  # 10+5 = 2 slots
                {"item_id": "ether_potion", "quantity": 3},  # 1 slot
            ]
        }
        loot_file = tmp_path / "loot_table.json"
        loot_file.write_text(json.dumps(data))
        loot_table.load(str(loot_file), property_types)

        contents = loot_table.get_contents("chest_1")
        assert len(contents) == 3
        # potion_red stacks
        red_stacks = [c for c in contents if c["item_id"] == "potion_red"]
        assert len(red_stacks) == 2
        assert red_stacks[0]["quantity"] == 10
        assert red_stacks[1]["quantity"] == 5
        # ether stack
        ether_stacks = [c for c in contents if c["item_id"] == "ether_potion"]
        assert len(ether_stacks) == 1
        assert ether_stacks[0]["quantity"] == 3
