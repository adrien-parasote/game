"""Consolidated Chest UI tests: state, draw, drag-and-drop, transfer logic."""

# tests/test_chest_ui.py
"""Unit tests for the Chest UI component."""

import pytest
import pygame
import os
import logging
from unittest.mock import MagicMock

# Headless mode for tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.ui.chest import ChestUI
from src.config import Settings


def make_screen():
    return pygame.Surface((Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT))


def make_player(capacity=28):
    """Create a mock player with an inventory of given capacity."""
    player = MagicMock()
    player.inventory = MagicMock()
    player.inventory.capacity = capacity
    player.inventory.slots = [None] * capacity
    return player


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------

def test_initial_state():
    ui = ChestUI()
    assert not ui.is_open
    assert ui._chest_entity is None


def test_open_sets_state():
    ui = ChestUI()
    dummy_entity = object()
    player = make_player()
    ui.open(dummy_entity, player)
    assert ui.is_open
    assert ui._chest_entity is dummy_entity


def test_close_resets_state():
    ui = ChestUI()
    ui.open(object(), make_player())
    ui.close()
    assert not ui.is_open
    assert ui._chest_entity is None


def test_close_when_already_closed_is_idempotent():
    ui = ChestUI()
    ui.close()
    assert not ui.is_open


def test_draw_noop_when_closed(monkeypatch):
    ui = ChestUI()
    screen = make_screen()
    before = screen.copy()
    ui.draw(screen)
    assert pygame.image.tobytes(screen, "RGB") == pygame.image.tobytes(before, "RGB")


def test_draw_when_open_and_assets_present(monkeypatch):
    ui = ChestUI()
    dummy_bg = pygame.Surface((900, 300))
    dummy_bg.fill((255, 0, 0))
    dummy_slot = pygame.Surface((55, 58))
    dummy_slot.fill((0, 255, 0))
    monkeypatch.setattr(ui, "_bg", dummy_bg)
    monkeypatch.setattr(ui, "_slot_img", dummy_slot)
    ui.open(object(), make_player())
    screen = make_screen()
    ui.draw(screen)
    midx = Settings.WINDOW_WIDTH // 2
    midy = 10 + 15
    assert screen.get_at((midx, midy))[:3] == (255, 0, 0)


def test_load_background_missing_file(monkeypatch, caplog):
    ui = ChestUI()
    monkeypatch.setattr("src.ui.chest.ASSET_CHEST_BG", "nonexistent.png")
    result = ui._load_background()
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_load_slot_image_missing_file(monkeypatch, caplog):
    ui = ChestUI()
    monkeypatch.setattr("src.ui.chest.ASSET_SLOT_IMG", "nonexistent.png")
    result = ui._load_slot_image()
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_update_hover_hit():
    """update_hover sets _hovered_chest_slot when mouse is over a chest slot."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._slot_positions, "No slot positions computed"
    first_rect = ui._slot_positions[0]
    ui.update_hover(first_rect.center)
    assert ui._hovered_chest_slot == 0


def test_update_hover_miss():
    """update_hover clears _hovered_chest_slot when mouse is outside all slots."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui.update_hover((0, 0))
    assert ui._hovered_chest_slot is None


def test_hovered_slot_reset_on_close():
    """close() resets _hovered_chest_slot to None."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._hovered_chest_slot = 3
    ui.close()
    assert ui._hovered_chest_slot is None


def test_load_cursor_missing_file(monkeypatch, caplog):
    ui = ChestUI()
    result = ui._load_cursor("nonexistent_cursor.png")
    assert result is None
    assert any("failed" in rec.message.lower() for rec in caplog.records)


def test_draw_hover_overlay_rendered(monkeypatch):
    """When _hovered_chest_slot is set and hover image exists, hover is drawn."""
    ui = ChestUI()
    dummy_bg = pygame.Surface((900, 300))
    dummy_bg.fill((20, 20, 20))
    dummy_slot = pygame.Surface((49, 49))
    dummy_slot.fill((0, 200, 0))
    dummy_hover = pygame.Surface((49, 49))
    dummy_hover.fill((255, 255, 0))
    monkeypatch.setattr(ui, "_bg", dummy_bg)
    monkeypatch.setattr(ui, "_slot_img", dummy_slot)
    ui.open(object(), make_player())
    ui._hover_img = dummy_hover
    ui._hovered_chest_slot = 0
    screen = make_screen()
    monkeypatch.setattr(ui, "_draw_cursor", lambda s: None)
    ui._draw_slots(screen)
    center = ui._slot_positions[0].center
    pixel = screen.get_at(center)[:3]
    assert pixel == (255, 255, 0), f"Expected yellow hover pixel, got {pixel}"


# --- Chest arrow button tests ---

def test_arrow_rects_computed_after_open():
    ui = ChestUI()
    assert ui._arrow_up_rect is None
    assert ui._arrow_down_rect is None
    ui.open(object(), make_player())
    assert ui._arrow_up_rect is not None
    assert ui._arrow_down_rect is not None


def test_arrow_up_rect_is_left_of_down():
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._arrow_up_rect.left < ui._arrow_down_rect.left


def test_update_hover_chest_arrows():
    """update_hover sets _hovered_chest_arrow when mouse is over chest arrow buttons."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui.update_hover(ui._arrow_up_rect.center)
    assert ui._hovered_chest_arrow == "up"
    assert ui._hovered_chest_slot is None
    ui.update_hover(ui._arrow_down_rect.center)
    assert ui._hovered_chest_arrow == "down"
    ui.update_hover((0, 0))
    assert ui._hovered_chest_arrow is None


def test_hovered_arrow_reset_on_close():
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._hovered_chest_arrow = "up"
    ui.close()
    assert ui._hovered_chest_arrow is None


def test_draw_arrow_hover_overlay_rendered(monkeypatch):
    ui = ChestUI()
    ui.open(object(), make_player())
    up_hover = pygame.Surface((30, 30))
    up_hover.fill((255, 0, 0))
    down_hover = pygame.Surface((30, 30))
    down_hover.fill((0, 0, 255))
    ui._arrow_down_hover_img = down_hover
    ui._arrow_up_hover_img = up_hover
    screen = make_screen()
    ui._hovered_chest_arrow = "up"
    ui._draw_arrow_hovers(screen)
    pixel = screen.get_at(ui._arrow_up_rect.center)[:3]
    assert pixel == (0, 0, 255), f"Expected blue hover overlay in RED zone, got {pixel}"
    screen.fill((0, 0, 0))
    ui._hovered_chest_arrow = "down"
    ui._draw_arrow_hovers(screen)
    pixel = screen.get_at(ui._arrow_down_rect.center)[:3]
    assert pixel == (255, 0, 0), f"Expected red hover overlay in BLUE zone, got {pixel}"


# ---------------------------------------------------------------------------
# NEW: Dual-panel tests (Player Inventory panel)
# ---------------------------------------------------------------------------

def test_open_with_player_stores_player():
    """open(entity, player) stores the player reference."""
    ui = ChestUI()
    player = make_player()
    ui.open(object(), player)
    assert ui._player is player


def test_open_resets_inv_offset():
    """open() always resets the inventory offset to 0."""
    ui = ChestUI()
    ui._inv_offset = 5
    ui.open(object(), make_player())
    assert ui._inv_offset == 0


def test_close_resets_inv_state():
    """close() resets all inventory panel state."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._inv_offset = 3
    ui._hovered_inv_slot = 5
    ui._hovered_inv_arrow = "right"
    ui.close()
    assert ui._inv_offset == 0
    assert ui._hovered_inv_slot is None
    assert ui._hovered_inv_arrow is None
    assert ui._player is None


def test_inv_bg_rect_computed_after_open():
    """open() must compute _inv_bg_rect at bottom of screen."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._inv_bg_rect is not None
    # Should be flush to bottom of screen
    assert ui._inv_bg_rect.bottom == Settings.WINDOW_HEIGHT


def test_inv_slot_positions_computed_after_open():
    """open() must populate _inv_slot_positions with exactly _INV_SLOTS_VISIBLE entries."""
    from src.ui.chest import _INV_SLOTS_VISIBLE
    ui = ChestUI()
    ui.open(object(), make_player())
    assert len(ui._inv_slot_positions) == _INV_SLOTS_VISIBLE


def test_update_hover_inv_slot():
    """update_hover sets _hovered_inv_slot when mouse is over a player inventory slot."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._inv_slot_positions, "No inv slot positions computed"
    first = ui._inv_slot_positions[0]
    ui.update_hover(first.center)
    assert ui._hovered_inv_slot == 0
    assert ui._hovered_chest_slot is None


def test_update_hover_chest_slot_when_mouse_in_chest():
    """update_hover sets _hovered_chest_slot and clears inv state when in chest grid."""
    ui = ChestUI()
    ui.open(object(), make_player())
    chest_first = ui._slot_positions[0]
    ui.update_hover(chest_first.center)
    assert ui._hovered_chest_slot == 0
    assert ui._hovered_inv_slot is None


def test_inv_offset_advance_on_right_click():
    """handle_event jumps _inv_offset by a full page when right arrow is clicked."""
    from src.ui.chest import _INV_SLOTS_VISIBLE
    ui = ChestUI()
    player = make_player(capacity=28)
    ui.open(object(), player)
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui._inv_arrow_right_rect.center
    ui.handle_event(event)
    # Full page jump: offset = 0 + 18 = 18, clamped to capacity-1 = 27 → 18
    assert ui._inv_offset == _INV_SLOTS_VISIBLE


def test_inv_offset_no_overflow():
    """handle_event does not advance _inv_offset beyond max_offset (right arrow at max)."""
    from src.ui.chest import _INV_SLOTS_VISIBLE
    ui = ChestUI()
    player = make_player(capacity=28)
    ui.open(object(), player)
    max_offset = 28 - _INV_SLOTS_VISIBLE
    ui._inv_offset = max_offset
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui._inv_arrow_right_rect.center
    ui.handle_event(event)
    assert ui._inv_offset == max_offset  # already at limit — no change


def test_inv_offset_no_underflow():
    """handle_event does not go below 0 when clicking left arrow."""
    ui = ChestUI()
    ui.open(object(), make_player())
    ui._inv_offset = 0
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = ui._inv_arrow_left_rect.center
    ui.handle_event(event)
    assert ui._inv_offset == 0


def test_inv_bg_full_screen_width():
    """Inventory background should span the full screen width."""
    ui = ChestUI()
    ui.open(object(), make_player())
    assert ui._inv_bg_rect.width == Settings.WINDOW_WIDTH


# tests/test_chest_ui_coverage.py
"""Coverage-targeted tests for src/ui/chest.py.

Focus: icon cache, drag-to-chest/inventory transfer variants, draw methods
with items, inventory arrow rendering, resolve_icon_name, and edge cases
in _transfer_inventory_to_chest stacking.
"""

import pytest
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

import pytest
from unittest.mock import MagicMock
from src.ui.chest import ChestUI
from src.engine.inventory_system import Inventory, Item

@pytest.fixture
def chest_ui():
    ui = ChestUI()
    ui._player = MagicMock()
    ui._player.inventory = Inventory(capacity=5)
    ui._player.inventory.item_data = {"potion": {"stack_max": 10}, "coin": {"stack_max": 100}}
    ui._chest_entity = MagicMock()
    ui._chest_entity.contents = []
    ui.is_open = True
    return ui

def test_transfer_chest_to_inventory_success(chest_ui):
    # Setup chest contents
    chest_ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    
    # Execute transfer
    chest_ui._transfer_chest_to_inventory()
    
    # Verify
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 0
    assert chest_ui._player.inventory.slots[0].id == "sword"

def test_transfer_chest_to_inventory_stacking(chest_ui):
    # Setup inventory with some items
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="potion", name="Potion", description="Desc", quantity=2, stack_max=10, icon="potion.png")
    
    # Setup chest contents
    chest_ui._chest_entity.contents = [{"item_id": "potion", "quantity": 5}]
    
    # Execute transfer
    chest_ui._transfer_chest_to_inventory()
    
    # Verify
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 0
    assert inv.slots[0].quantity == 7

def test_transfer_chest_to_inventory_full(chest_ui):
    # Fill inventory
    inv = chest_ui._player.inventory
    for i in range(inv.capacity):
        inv.slots[i] = Item(id="dirt", name="Dirt", description="Desc", quantity=1)
    
    # Setup chest contents
    chest_ui._chest_entity.contents = [{"item_id": "gold", "quantity": 10}]
    
    # Execute transfer
    chest_ui._transfer_chest_to_inventory()
    
    # Verify nothing moved
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 1
    assert chest_ui._chest_entity.contents[0]["quantity"] == 10

def test_transfer_inventory_to_chest_success(chest_ui):
    # Setup inventory
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="coin", name="Coin", description="Desc", quantity=10, stack_max=100)
    
    # Execute transfer
    chest_ui._transfer_inventory_to_chest()
    
    # Verify
    assert inv.slots[0] is None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 1
    assert chest_ui._chest_entity.contents[0]["item_id"] == "coin"
    assert chest_ui._chest_entity.contents[0]["quantity"] == 10

def test_transfer_inventory_to_chest_full(chest_ui):
    # Fill chest
    from src.engine.loot_table import CHEST_MAX_SLOTS
    chest_ui._chest_entity.contents = [{"item_id": "junk", "quantity": 1} for _ in range(CHEST_MAX_SLOTS)]
    
    # Setup inventory
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="diamond", name="Diamond", description="Desc", quantity=1)
    
    # Execute transfer
    chest_ui._transfer_inventory_to_chest()
    
    # Verify nothing moved
    assert inv.slots[0] is not None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == CHEST_MAX_SLOTS

# -----------------------------------------------------------------------
# Manual Drag & Drop tests
# -----------------------------------------------------------------------

def test_manual_drag_chest_to_inventory(chest_ui):
    # Setup
    chest_ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    chest_ui._layout_computed = True
    # Mock slot position
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._inv_slot_positions = [pygame.Rect(100, 100, 50, 50)]
    chest_ui._inv_bg_rect = pygame.Rect(100, 100, 200, 200)
    
    # 1. Mouse down on slot 0
    event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    chest_ui.handle_event(event_down)
    assert chest_ui._dragging_item is not None
    assert chest_ui._dragging_item["item_id"] == "sword"
    
    # 2. Mouse motion
    event_move = MagicMock(type=pygame.MOUSEMOTION, pos=(125, 125))
    chest_ui.handle_event(event_move)
    assert chest_ui._drag_pos == (125, 125)
    
    # 3. Mouse up on inventory panel
    event_up = MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(125, 125))
    chest_ui.handle_event(event_up)
    
    # Verify
    assert chest_ui._dragging_item is None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 0
    assert chest_ui._player.inventory.slots[0].id == "sword"

def test_manual_drag_inventory_to_chest_stacking(chest_ui):
    # Setup
    inv = chest_ui._player.inventory
    inv.slots[0] = Item(id="potion", name="P", description="D", quantity=5, stack_max=10)
    chest_ui._chest_entity.contents = [{"item_id": "potion", "quantity": 2}]
    
    chest_ui._layout_computed = True
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._inv_slot_positions = [pygame.Rect(100, 100, 50, 50)]
    chest_ui._bg_rect = pygame.Rect(10, 10, 80, 80)
    
    # 1. Drag from inv
    event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(110, 110))
    chest_ui.handle_event(event_down)
    assert chest_ui._dragging_item["item_id"] == "potion"
    
    # 2. Drop in chest panel
    event_up = MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(20, 20))
    chest_ui.handle_event(event_up)
    
    # Verify
    assert chest_ui._chest_entity.contents[0]["quantity"] == 7
    assert inv.slots[0] is None

def test_manual_drag_from_empty_slot(chest_ui):
    # Setup
    chest_ui._chest_entity.contents = []
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    
    # Mouse down on empty slot
    event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    chest_ui.handle_event(event_down)
    
    assert chest_ui._dragging_item is None

def test_manual_drag_cancel_drop(chest_ui):
    # Setup
    chest_ui._chest_entity.contents = [{"item_id": "sword", "quantity": 1}]
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._bg_rect = pygame.Rect(10, 10, 80, 80)
    chest_ui._inv_bg_rect = pygame.Rect(100, 100, 200, 200)
    
    # Drag
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)))
    
    # Drop in nowhere (e.g. at 0, 0 outside panels)
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    
    # Verify item remains in chest
    assert chest_ui._dragging_item is None
    assert sum(1 for e in chest_ui._chest_entity.contents if e is not None) == 1
    assert chest_ui._chest_entity.contents[0]["item_id"] == "sword"

def test_auto_transfer_buttons(chest_ui):
    # Mock button rects
    chest_ui._arrow_up_rect = pygame.Rect(10, 10, 20, 20)
    chest_ui._arrow_down_rect = pygame.Rect(40, 10, 20, 20)
    
    # Mock transfer methods
    chest_ui._transfer_chest_to_inventory = MagicMock()
    chest_ui._transfer_inventory_to_chest = MagicMock()
    
    # Click UP (Left)
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)))
    chest_ui._transfer_chest_to_inventory.assert_called_once()
    
    # Click DOWN (Right)
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 20)))
    chest_ui._transfer_inventory_to_chest.assert_called_once()

def test_inventory_scroll_buttons(chest_ui):
    # Mock scroll rects
    chest_ui._inv_arrow_left_rect = pygame.Rect(10, 10, 20, 20)
    chest_ui._inv_arrow_right_rect = pygame.Rect(40, 10, 20, 20)
    
    # Mock scroll methods and capacity
    chest_ui._scroll_left = MagicMock()
    chest_ui._scroll_right = MagicMock()
    chest_ui._can_scroll_left = MagicMock(return_value=True)
    chest_ui._can_scroll_right = MagicMock(return_value=True)
    
    # Click Left
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)))
    chest_ui._scroll_left.assert_called_once()
    
    # Click Right
    chest_ui.handle_event(MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 20)))
    chest_ui._scroll_right.assert_called_once()

def test_hover_updates(chest_ui):
    # Mock elements
    chest_ui._slot_positions = [pygame.Rect(10, 10, 50, 50)]
    chest_ui._inv_slot_positions = [pygame.Rect(100, 100, 50, 50)]
    chest_ui._inv_offset = 0
    chest_ui._player.inventory.capacity = 28
    
    chest_ui._arrow_up_rect = pygame.Rect(200, 10, 20, 20)
    chest_ui._arrow_down_rect = pygame.Rect(230, 10, 20, 20)
    chest_ui._inv_arrow_left_rect = pygame.Rect(260, 10, 20, 20)
    chest_ui._inv_arrow_right_rect = pygame.Rect(290, 10, 20, 20)
    
    chest_ui._can_scroll_left = MagicMock(return_value=True)
    chest_ui._can_scroll_right = MagicMock(return_value=True)
    
    # Hover Chest Slot
    chest_ui.update_hover((20, 20))
    assert chest_ui._hovered_chest_slot == 0
    
    # Hover Inventory Slot
    chest_ui.update_hover((110, 110))
    assert chest_ui._hovered_inv_slot == 0
    
    # Hover Chest Arrows
    chest_ui.update_hover((210, 20))
    assert chest_ui._hovered_chest_arrow == "up"
    chest_ui.update_hover((240, 20))
    assert chest_ui._hovered_chest_arrow == "down"
    
    # Hover Inv Arrows
    chest_ui.update_hover((270, 20))
    assert chest_ui._hovered_inv_arrow == "left"
    chest_ui.update_hover((300, 20))
    assert chest_ui._hovered_inv_arrow == "right"
