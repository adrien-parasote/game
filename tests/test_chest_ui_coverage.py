# tests/test_chest_ui_coverage.py
"""Coverage-targeted tests for src/ui/chest.py.

Focus: icon cache, drag-to-chest/inventory transfer variants, draw methods
with items, inventory arrow rendering, resolve_icon_name, and edge cases
in _transfer_inventory_to_chest stacking.
"""

import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.ui.chest import ChestUI, _INV_SLOTS_VISIBLE
from src.engine.inventory_system import Item
from src.engine.loot_table import CHEST_MAX_SLOTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(item_id="sword", qty=1, stack_max=1, icon=None):
    return Item(
        id=item_id, name="Test", description="D",
        quantity=qty, stack_max=stack_max, icon=icon,
    )


def _chest_ui():
    """Pre-configured ChestUI with mock player and entity, ready for logic tests."""
    ui = ChestUI()
    ui._player = MagicMock()
    inv = MagicMock()
    inv.capacity = 5
    inv.slots = [None] * 5
    inv.item_data = {
        "sword": {"stack_max": 1, "icon": "sword.png"},
        "potion": {"stack_max": 10, "icon": "potion.png"},
        "shield": {"stack_max": 1, "icon": "shield.png"},
    }
    inv.get_item_at = lambda idx: inv.slots[idx] if 0 <= idx < 5 else None

    def create_item(item_id, qty):
        data = inv.item_data.get(item_id, {})
        return Item(
            id=item_id, name=item_id.title(), description="D",
            quantity=qty, stack_max=data.get("stack_max", 1),
            icon=data.get("icon", f"{item_id}.png"),
        )
    inv.create_item = create_item
    ui._player.inventory = inv

    ui._chest_entity = MagicMock()
    ui._chest_entity.contents = [None] * CHEST_MAX_SLOTS
    ui.is_open = True
    return ui


# ---------------------------------------------------------------------------
# _get_item_icon (lines 362-384)
# ---------------------------------------------------------------------------

class TestChestIconCache:
    def test_icon_cached_on_second_call(self):
        """Second call with same params returns cached surface."""
        ui = ChestUI()
        dummy = pygame.Surface((40, 40))
        ui._icon_cache["test.png@40"] = dummy
        result = ui._get_item_icon("test.png", 40)
        assert result is dummy

    def test_icon_missing_file(self):
        """Missing icon returns None and caches it."""
        ui = ChestUI()
        result = ui._get_item_icon("nonexistent_icon.png", 40)
        assert result is None
        assert ui._icon_cache["nonexistent_icon.png@40"] is None

    def test_icon_adds_png_extension(self):
        """Filename without .png gets it appended."""
        ui = ChestUI()
        result = ui._get_item_icon("noext", 40)
        assert result is None


# ---------------------------------------------------------------------------
# _resolve_icon_name (lines 748-756)
# ---------------------------------------------------------------------------

class TestResolveIconName:
    def test_resolve_with_player(self):
        """Resolves icon from inventory item_data."""
        ui = _chest_ui()
        name = ui._resolve_icon_name("sword")
        assert name == "sword.png"

    def test_resolve_no_player(self):
        """Returns fallback when player is None."""
        ui = ChestUI()
        ui._player = None
        name = ui._resolve_icon_name("sword")
        assert name == "sword.png"

    def test_resolve_no_inventory(self):
        """Returns fallback when player.inventory is None."""
        ui = ChestUI()
        ui._player = MagicMock()
        ui._player.inventory = None
        name = ui._resolve_icon_name("sword")
        assert name == "sword.png"


# ---------------------------------------------------------------------------
# _transfer_dragged_to_chest (lines 632-682)
# ---------------------------------------------------------------------------

class TestTransferDraggedToChest:
    def test_chest_to_chest_same_slot_noop(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "sword", "quantity": 1}
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "chest", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_chest(0)
        # Nothing should change
        assert ui._chest_entity.contents[0]["item_id"] == "sword"

    def test_chest_to_chest_empty_target(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "sword", "quantity": 1}
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "chest", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_chest(5)
        assert ui._chest_entity.contents[5] == {"item_id": "sword", "quantity": 1}
        assert ui._chest_entity.contents[0] is None

    def test_chest_to_chest_stacking(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "potion", "quantity": 3}
        ui._chest_entity.contents[1] = {"item_id": "potion", "quantity": 4}
        ui._dragging_item = {"item_id": "potion", "quantity": 3, "source": "chest", "index": 0, "icon": "p.png"}
        ui._transfer_dragged_to_chest(1)
        assert ui._chest_entity.contents[1]["quantity"] == 7
        assert ui._chest_entity.contents[0] is None

    def test_chest_to_chest_swap(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "sword", "quantity": 1}
        ui._chest_entity.contents[1] = {"item_id": "shield", "quantity": 1}
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "chest", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_chest(1)
        assert ui._chest_entity.contents[0]["item_id"] == "shield"
        assert ui._chest_entity.contents[1]["item_id"] == "sword"

    def test_inv_to_chest_empty_target(self):
        ui = _chest_ui()
        ui._player.inventory.slots[0] = _item("sword")
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "inv", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_chest(3)
        assert ui._chest_entity.contents[3] == {"item_id": "sword", "quantity": 1}
        assert ui._player.inventory.slots[0] is None

    def test_inv_to_chest_stacking(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "potion", "quantity": 3}
        src = _item("potion", qty=5, stack_max=10)
        ui._player.inventory.slots[0] = src
        ui._dragging_item = {"item_id": "potion", "quantity": 5, "source": "inv", "index": 0, "icon": "p.png"}
        ui._transfer_dragged_to_chest(0)
        assert ui._chest_entity.contents[0]["quantity"] == 8
        assert ui._player.inventory.slots[0] is None

    def test_inv_to_chest_swap(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "shield", "quantity": 1}
        ui._player.inventory.slots[0] = _item("sword")
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "inv", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_chest(0)
        assert ui._chest_entity.contents[0] == {"item_id": "sword", "quantity": 1}
        assert ui._player.inventory.slots[0].id == "shield"

    def test_no_dragging_noop(self):
        ui = _chest_ui()
        ui._dragging_item = None
        ui._transfer_dragged_to_chest(0)  # no crash


# ---------------------------------------------------------------------------
# _transfer_dragged_to_inventory (lines 684-730)
# ---------------------------------------------------------------------------

class TestTransferDraggedToInventory:
    def test_inv_to_inv_same_slot_noop(self):
        ui = _chest_ui()
        ui._player.inventory.slots[0] = _item("sword")
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "inv", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_inventory(0)

    def test_inv_to_inv_empty_target(self):
        ui = _chest_ui()
        item = _item("sword")
        ui._player.inventory.slots[0] = item
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "inv", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_inventory(3)
        assert ui._player.inventory.slots[3] is item
        assert ui._player.inventory.slots[0] is None

    def test_inv_to_inv_stacking(self):
        ui = _chest_ui()
        src = _item("potion", qty=3, stack_max=10)
        target = _item("potion", qty=4, stack_max=10)
        ui._player.inventory.slots[0] = src
        ui._player.inventory.slots[1] = target
        ui._dragging_item = {"item_id": "potion", "quantity": 3, "source": "inv", "index": 0, "icon": "p.png"}
        ui._transfer_dragged_to_inventory(1)
        assert target.quantity == 7
        assert ui._player.inventory.slots[0] is None

    def test_inv_to_inv_swap(self):
        ui = _chest_ui()
        a = _item("sword")
        b = _item("shield")
        ui._player.inventory.slots[0] = a
        ui._player.inventory.slots[1] = b
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "inv", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_inventory(1)
        assert ui._player.inventory.slots[0] is b
        assert ui._player.inventory.slots[1] is a

    def test_chest_to_inv_empty_target(self):
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "sword", "quantity": 1}
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "chest", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_inventory(2)
        assert ui._player.inventory.slots[2].id == "sword"
        assert ui._chest_entity.contents[0] is None

    def test_chest_to_inv_stacking(self):
        ui = _chest_ui()
        target = _item("potion", qty=4, stack_max=10)
        ui._player.inventory.slots[0] = target
        ui._chest_entity.contents[0] = {"item_id": "potion", "quantity": 3}
        ui._dragging_item = {"item_id": "potion", "quantity": 3, "source": "chest", "index": 0, "icon": "p.png"}
        ui._transfer_dragged_to_inventory(0)
        assert target.quantity == 7
        assert ui._chest_entity.contents[0] is None

    def test_chest_to_inv_swap(self):
        ui = _chest_ui()
        target = _item("shield", qty=1)
        ui._player.inventory.slots[0] = target
        ui._chest_entity.contents[0] = {"item_id": "sword", "quantity": 1}
        ui._dragging_item = {"item_id": "sword", "quantity": 1, "source": "chest", "index": 0, "icon": "s.png"}
        ui._transfer_dragged_to_inventory(0)
        assert ui._player.inventory.slots[0].id == "sword"
        assert ui._chest_entity.contents[0] == {"item_id": "shield", "quantity": 1}

    def test_no_dragging_noop(self):
        ui = _chest_ui()
        ui._dragging_item = None
        ui._transfer_dragged_to_inventory(0)  # no crash


# ---------------------------------------------------------------------------
# _transfer_inventory_to_chest stacking (lines 594-630)
# ---------------------------------------------------------------------------

class TestTransferInventoryToChestStacking:
    def test_stacking_into_existing_chest_entry(self):
        """Items stack into existing chest entries before using new slots."""
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "potion", "quantity": 3}
        ui._player.inventory.slots[0] = _item("potion", qty=5, stack_max=10)
        ui._transfer_inventory_to_chest()
        assert ui._chest_entity.contents[0]["quantity"] == 8
        assert ui._player.inventory.slots[0] is None


# ---------------------------------------------------------------------------
# Drawing: _draw_slots with items (lines 788-816)
# ---------------------------------------------------------------------------

class TestDrawSlotsWithItems:
    def test_draw_chest_slots_with_items(self):
        """Drawing chest slots with items renders quantity badges."""
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "potion", "quantity": 5}
        ui._slot_positions = [pygame.Rect(50, 50, 49, 49)]
        ui._slot_img = pygame.Surface((49, 49))
        ui._hover_img = None
        ui._hovered_chest_slot = None

        screen = pygame.Surface((1280, 720))
        ui._draw_slots(screen)  # should not crash

    def test_draw_chest_slots_skips_dragged(self):
        """Drawing chest slots skips the dragged item."""
        ui = _chest_ui()
        ui._chest_entity.contents[0] = {"item_id": "sword", "quantity": 1}
        ui._slot_positions = [pygame.Rect(50, 50, 49, 49)]
        ui._slot_img = pygame.Surface((49, 49))
        ui._hover_img = None
        ui._hovered_chest_slot = None
        ui._dragging_item = {"source": "chest", "index": 0, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        screen = pygame.Surface((1280, 720))
        ui._draw_slots(screen)

    def test_draw_chest_slots_no_slot_img_fallback(self):
        """When _slot_img is None, draws rect outline instead."""
        ui = _chest_ui()
        ui._slot_positions = [pygame.Rect(50, 50, 49, 49)]
        ui._slot_img = None
        ui._hover_img = None

        screen = pygame.Surface((1280, 720))
        ui._draw_slots(screen)

    def test_draw_chest_slots_with_hover(self):
        """Drawing hover overlay on a chest slot."""
        ui = _chest_ui()
        ui._slot_positions = [pygame.Rect(50, 50, 49, 49)]
        ui._slot_img = pygame.Surface((49, 49))
        ui._hover_img = pygame.Surface((49, 49))
        ui._hovered_chest_slot = 0

        screen = pygame.Surface((1280, 720))
        ui._draw_slots(screen)


# ---------------------------------------------------------------------------
# Drawing: _draw_inv_slots (lines 835-884)
# ---------------------------------------------------------------------------

class TestDrawInvSlots:
    def test_draw_inv_slots_with_items(self):
        """Drawing inventory slots with items."""
        ui = _chest_ui()
        item = _item("potion", qty=3, stack_max=10, icon="potion.png")
        ui._player.inventory.slots[0] = item
        ui._inv_slot_positions = [pygame.Rect(100, 100, 49, 49)]
        ui._slot_img = pygame.Surface((49, 49))
        ui._hover_img = None
        ui._hovered_inv_slot = None
        ui._inv_offset = 0

        screen = pygame.Surface((1280, 720))
        ui._draw_inv_slots(screen)

    def test_draw_inv_slots_skips_dragged(self):
        """Drawing inventory slots skips dragged item."""
        ui = _chest_ui()
        item = _item("sword", icon="sword.png")
        ui._player.inventory.slots[0] = item
        ui._inv_slot_positions = [pygame.Rect(100, 100, 49, 49)]
        ui._slot_img = pygame.Surface((49, 49))
        ui._hover_img = None
        ui._hovered_inv_slot = None
        ui._inv_offset = 0
        ui._dragging_item = {"source": "inv", "index": 0, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        screen = pygame.Surface((1280, 720))
        ui._draw_inv_slots(screen)

    def test_draw_inv_slots_no_slot_img_fallback(self):
        """When _slot_img is None, draws rect outline."""
        ui = _chest_ui()
        ui._inv_slot_positions = [pygame.Rect(100, 100, 49, 49)]
        ui._slot_img = None
        ui._hover_img = None
        ui._inv_offset = 0

        screen = pygame.Surface((1280, 720))
        ui._draw_inv_slots(screen)

    def test_draw_inv_slots_hover_overlay(self):
        """Drawing hover overlay on inventory slot."""
        ui = _chest_ui()
        ui._inv_slot_positions = [pygame.Rect(100, 100, 49, 49)]
        ui._slot_img = pygame.Surface((49, 49))
        ui._hover_img = pygame.Surface((49, 49))
        ui._hovered_inv_slot = 0
        ui._inv_offset = 0

        screen = pygame.Surface((1280, 720))
        ui._draw_inv_slots(screen)


# ---------------------------------------------------------------------------
# Drawing: _draw_inv_arrows (lines 886-903)
# ---------------------------------------------------------------------------

class TestDrawInvArrows:
    def test_draw_left_arrow_when_scrollable(self):
        """Left arrow renders when can_scroll_left and hovered."""
        ui = _chest_ui()
        ui._inv_offset = 18  # can scroll left
        ui._hovered_inv_arrow = "left"
        ui._inv_arrow_left_rect = pygame.Rect(10, 10, 60, 60)
        ui._arrow_left_hover_img = pygame.Surface((30, 30))

        screen = pygame.Surface((1280, 720))
        ui._draw_inv_arrows(screen)

    def test_draw_right_arrow_when_scrollable(self):
        """Right arrow renders when can_scroll_right and hovered."""
        ui = _chest_ui()
        ui._player.inventory.capacity = 28
        ui._inv_offset = 0  # can scroll right
        ui._hovered_inv_arrow = "right"
        ui._inv_arrow_right_rect = pygame.Rect(200, 10, 60, 60)
        ui._arrow_right_hover_img = pygame.Surface((30, 30))

        screen = pygame.Surface((1280, 720))
        ui._draw_inv_arrows(screen)


# ---------------------------------------------------------------------------
# Drawing: _draw_dragged_item (lines 912-922)
# ---------------------------------------------------------------------------

class TestDrawDraggedItem:
    def test_draw_dragged_item_with_icon(self):
        """Draws icon at drag position."""
        ui = _chest_ui()
        ui._slot_img = pygame.Surface((49, 49))
        dummy_icon = pygame.Surface((41, 41))
        ui._icon_cache["sword.png@41"] = dummy_icon
        ui._dragging_item = {"source": "chest", "index": 0, "item_id": "sword", "quantity": 1, "icon": "sword.png"}
        ui._drag_pos = (200, 200)

        screen = pygame.Surface((1280, 720))
        ui._draw_dragged_item(screen)

    def test_draw_dragged_noop_when_none(self):
        """No crash when _dragging_item is None."""
        ui = ChestUI()
        ui._dragging_item = None
        screen = pygame.Surface((1280, 720))
        ui._draw_dragged_item(screen)


# ---------------------------------------------------------------------------
# _load_and_scale_arrow (lines 352-360)
# ---------------------------------------------------------------------------

class TestLoadAndScaleArrow:
    def test_load_arrow_missing_file(self, caplog):
        """Missing arrow file returns None and logs warning."""
        ui = ChestUI()
        result = ui._load_and_scale_arrow("nonexistent_arrow.png", 0.75)
        assert result is None
        assert any("failed" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# _load_inv_background (lines 321-330)
# ---------------------------------------------------------------------------

class TestLoadInvBackground:
    def test_load_inv_bg_missing_file(self, caplog):
        """Missing inv background returns None and logs error."""
        ui = ChestUI()
        with patch("src.ui.chest.ASSET_INV_BG", "nonexistent.png"):
            result = ui._load_inv_background()
        assert result is None
        assert any("failed" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# _compute_layout edge: hover img load failure (lines 434-436)
# ---------------------------------------------------------------------------

class TestComputeLayoutEdge:
    def test_compute_layout_hover_img_fail(self, monkeypatch):
        """When hover image fails to load, _hover_img is set to None."""
        ui = ChestUI()
        monkeypatch.setattr("src.ui.chest.ASSET_SLOT_HOVER", "nonexistent_hover.png")
        ui.open(object(), MagicMock(inventory=MagicMock(capacity=5)))
        assert ui._hover_img is None


# ---------------------------------------------------------------------------
# handle_event when closed (line 297)
# ---------------------------------------------------------------------------

def test_handle_event_when_closed():
    """handle_event is noop when not open."""
    ui = ChestUI()
    ui.is_open = False
    event = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
    ui.handle_event(event)  # no crash


# ---------------------------------------------------------------------------
# _current_page_slots (lines 560-566)
# ---------------------------------------------------------------------------

def test_current_page_slots_no_player():
    """Returns empty list when player is None."""
    ui = ChestUI()
    ui._player = None
    assert ui._current_page_slots() == []


# ---------------------------------------------------------------------------
# _capacity (lines 536-539)
# ---------------------------------------------------------------------------

def test_capacity_no_player():
    """Returns 0 when player is None."""
    ui = ChestUI()
    ui._player = None
    assert ui._capacity() == 0


# ---------------------------------------------------------------------------
# _get_chest_contents (lines 736-746)
# ---------------------------------------------------------------------------

def test_get_chest_contents_pads_to_max():
    """Contents are padded with None to CHEST_MAX_SLOTS."""
    ui = _chest_ui()
    ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    contents = ui._get_chest_contents()
    assert len(contents) == CHEST_MAX_SLOTS
    assert contents[0]["item_id"] == "sword"
    assert all(c is None for c in contents[1:])

def test_get_chest_contents_no_entity():
    """Returns empty list when entity is None."""
    ui = ChestUI()
    ui._chest_entity = None
    assert ui._get_chest_contents() == []
