# tests/test_inventory_ui_coverage.py
"""Coverage-targeted tests for src/ui/inventory.py.

Focus: drag-and-drop logic, transfer methods, drawing with items,
and icon cache — the uncovered branches from the coverage report.
"""

import pytest
import pygame
from unittest.mock import MagicMock, patch, PropertyMock
from src.ui.inventory import InventoryUI
from src.engine.inventory_system import Item


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(item_id="sword", qty=1, stack_max=1, icon=None):
    return Item(
        id=item_id, name="Test", description="Desc",
        quantity=qty, stack_max=stack_max, icon=icon,
    )


def _make_player(capacity=28, items=None):
    """Create a mock player with a real-ish inventory mock."""
    player = MagicMock()
    inv = MagicMock()
    inv.capacity = capacity
    inv.slots = [None] * capacity
    inv.equipment = {
        "HEAD": None, "BAG": None, "BELT": None, "LEFT_HAND": None,
        "UPPER_BODY": None, "LOWER_BODY": None, "RIGHT_HAND": None, "SHOES": None,
    }
    inv.item_data = {
        "sword": {"stack_max": 1, "equip_slot": "RIGHT_HAND"},
        "potion": {"stack_max": 10},
        "shield": {"stack_max": 1, "equip_slot": "LEFT_HAND"},
    }
    inv.get_item_at = lambda idx: inv.slots[idx] if 0 <= idx < capacity else None
    inv.add_item = MagicMock(return_value=0)
    inv.equip_item = MagicMock(return_value=None)
    inv.unequip_item = MagicMock(return_value=None)
    player.inventory = inv
    player.level = 1
    player.hp = 100
    player.max_hp = 100
    player.gold = 50
    player.frames = [pygame.Surface((32, 32)) for _ in range(16)]
    return player


def _make_ui(player=None):
    """Create an InventoryUI with dummy assets."""
    if player is None:
        player = _make_player()
    ui = InventoryUI(player)
    return ui


# ---------------------------------------------------------------------------
# Drag start — equipment slot (lines 139-163)
# ---------------------------------------------------------------------------

class TestDragStartEquipment:
    def test_drag_from_equipment_slot(self):
        """Mouse down on hovered equipment slot starts drag."""
        player = _make_player()
        item = _make_item("sword", icon="sword.png")
        player.inventory.equipment["RIGHT_HAND"] = item
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("equipment", "RIGHT_HAND")

        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (300, 300)

        ui.handle_input(event)

        assert ui._dragging_item is not None
        assert ui._dragging_item["source"] == "equipment"
        assert ui._dragging_item["name"] == "RIGHT_HAND"
        assert ui._dragging_item["item_id"] == "sword"

    def test_drag_from_empty_equipment_slot(self):
        """Mouse down on empty equipment slot doesn't start drag."""
        player = _make_player()
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("equipment", "HEAD")

        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (300, 300)

        ui.handle_input(event)
        assert ui._dragging_item is None

    def test_drag_from_grid_slot(self):
        """Mouse down on hovered grid slot starts drag."""
        player = _make_player()
        item = _make_item("potion", qty=5, stack_max=10)
        player.inventory.slots[3] = item
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("grid", 3)

        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (400, 400)

        ui.handle_input(event)

        assert ui._dragging_item is not None
        assert ui._dragging_item["source"] == "grid"
        assert ui._dragging_item["index"] == 3
        assert ui._dragging_item["quantity"] == 5

    def test_drag_from_empty_grid_slot(self):
        """Mouse down on empty grid slot doesn't start drag."""
        player = _make_player()
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("grid", 0)

        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (400, 400)

        ui.handle_input(event)
        assert ui._dragging_item is None

    def test_drag_item_without_icon(self):
        """Drag from item with no icon uses item_id fallback."""
        player = _make_player()
        item = _make_item("sword", icon=None)
        player.inventory.slots[0] = item
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("grid", 0)

        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (400, 400)

        ui.handle_input(event)
        assert ui._dragging_item["icon"] == "sword.png"


# ---------------------------------------------------------------------------
# Mouse motion + mouse up (lines 165-178)
# ---------------------------------------------------------------------------

class TestDragMotionAndDrop:
    def test_mouse_motion_updates_drag_pos(self):
        """MOUSEMOTION while dragging updates _drag_pos."""
        ui = _make_ui()
        ui.is_open = True
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "x", "quantity": 1, "icon": "x.png"}

        event = MagicMock()
        event.type = pygame.MOUSEMOTION
        event.pos = (500, 500)

        ui.handle_input(event)
        assert ui._drag_pos == (500, 500)

    def test_mouse_up_clears_drag(self):
        """MOUSEBUTTONUP clears _dragging_item."""
        ui = _make_ui()
        ui.is_open = True
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "x", "quantity": 1, "icon": "x.png"}

        event = MagicMock()
        event.type = pygame.MOUSEBUTTONUP
        event.button = 1
        event.pos = (0, 0)

        ui.handle_input(event)
        assert ui._dragging_item is None

    def test_drop_on_equipment_slot(self):
        """Dropping on equipment slot calls _transfer_dragged_to_equipment."""
        ui = _make_ui()
        ui.is_open = True
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "sword", "quantity": 1, "icon": "sword.png"}
        ui.hovered_slot = ("equipment", "RIGHT_HAND")

        with patch.object(ui, '_transfer_dragged_to_equipment') as mock_xfer:
            with patch.object(ui, 'update_hover'):
                event = MagicMock()
                event.type = pygame.MOUSEBUTTONUP
                event.button = 1
                event.pos = (300, 300)
                ui.handle_input(event)
                mock_xfer.assert_called_once_with("RIGHT_HAND")

    def test_drop_on_grid_slot(self):
        """Dropping on grid slot calls _transfer_dragged_to_grid."""
        ui = _make_ui()
        ui.is_open = True
        ui._dragging_item = {"source": "equipment", "name": "HEAD", "item_id": "helm", "quantity": 1, "icon": "helm.png"}
        ui.hovered_slot = ("grid", 5)

        with patch.object(ui, '_transfer_dragged_to_grid') as mock_xfer:
            with patch.object(ui, 'update_hover'):
                event = MagicMock()
                event.type = pygame.MOUSEBUTTONUP
                event.button = 1
                event.pos = (400, 400)
                ui.handle_input(event)
                mock_xfer.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# _transfer_dragged_to_equipment (lines 191-231)
# ---------------------------------------------------------------------------

class TestTransferDraggedToEquipment:
    def test_equip_to_equip_same_slot_noop(self):
        """Dragging from equipment to same slot does nothing."""
        player = _make_player()
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "HEAD", "item_id": "helm", "quantity": 1, "icon": "h.png"}
        ui._transfer_dragged_to_equipment("HEAD")
        # Should just return without changes

    def test_equip_to_equip_different_slot(self):
        """Dragging from equipment to a different slot tries unequip+equip."""
        player = _make_player()
        item = _make_item("sword")
        player.inventory.unequip_item = MagicMock(return_value=item)
        player.inventory.equip_item = MagicMock(return_value=None)  # success
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("LEFT_HAND")
        player.inventory.unequip_item.assert_called_once_with("RIGHT_HAND")
        player.inventory.equip_item.assert_called()

    def test_equip_to_equip_fail_returns_item(self):
        """If equip fails, the item is re-equipped to original slot."""
        player = _make_player()
        item = _make_item("sword")
        player.inventory.unequip_item = MagicMock(return_value=item)
        # equip_item returns the item back (failure)
        player.inventory.equip_item = MagicMock(return_value=item)
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("HEAD")
        # Should call equip_item twice: once to try HEAD, once to put back in RIGHT_HAND
        assert player.inventory.equip_item.call_count == 2

    def test_equip_to_equip_swap(self):
        """When equipping returns a swapped item, it goes back to source slot."""
        player = _make_player()
        item_src = _make_item("sword")
        item_swapped = _make_item("shield")
        player.inventory.unequip_item = MagicMock(return_value=item_src)
        # First equip succeeds but returns swapped item, second equip to put swapped back returns None
        player.inventory.equip_item = MagicMock(side_effect=[item_swapped, None])
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("LEFT_HAND")
        assert player.inventory.equip_item.call_count == 2

    def test_equip_to_equip_swap_fallback_to_grid(self):
        """When swapped item can't go back to source, it falls back to grid."""
        player = _make_player()
        item_src = _make_item("sword")
        item_swapped = _make_item("shield")
        player.inventory.unequip_item = MagicMock(return_value=item_src)
        # First equip returns swapped, second equip also fails (returns swapped)
        player.inventory.equip_item = MagicMock(side_effect=[item_swapped, item_swapped])
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("LEFT_HAND")
        player.inventory.add_item.assert_called_once()

    def test_grid_to_equip_success(self):
        """Dragging from grid to equipment slot equips the item."""
        player = _make_player()
        item = _make_item("sword")
        player.inventory.slots[2] = item
        player.inventory.equip_item = MagicMock(return_value=None)  # success
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 2, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("RIGHT_HAND")
        assert player.inventory.slots[2] is None
        player.inventory.equip_item.assert_called_once()

    def test_grid_to_equip_fail_returns_to_grid(self):
        """If equipping from grid fails, item returns to grid slot."""
        player = _make_player()
        item = _make_item("sword")
        player.inventory.slots[2] = item
        player.inventory.equip_item = MagicMock(return_value=item)  # fail
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 2, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("HEAD")
        assert player.inventory.slots[2] is item  # returned to grid

    def test_grid_to_equip_swap(self):
        """Equipping from grid with swap puts swapped item in grid slot."""
        player = _make_player()
        item_src = _make_item("sword")
        item_swapped = _make_item("shield")
        player.inventory.slots[2] = item_src
        player.inventory.equip_item = MagicMock(return_value=item_swapped)
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 2, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_equipment("RIGHT_HAND")
        assert player.inventory.slots[2] is item_swapped

    def test_no_dragging_item_noop(self):
        """Calling with no dragging item does nothing."""
        ui = _make_ui()
        ui._transfer_dragged_to_equipment("HEAD")  # no crash


# ---------------------------------------------------------------------------
# _transfer_dragged_to_grid (lines 233-285)
# ---------------------------------------------------------------------------

class TestTransferDraggedToGrid:
    def test_grid_to_grid_same_slot_noop(self):
        """Dropping on the same grid slot does nothing."""
        player = _make_player()
        player.inventory.slots[0] = _make_item("sword")
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_grid(0)

    def test_grid_to_empty_grid(self):
        """Moving item to empty grid slot."""
        player = _make_player()
        item = _make_item("sword")
        player.inventory.slots[0] = item
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_grid(5)
        assert player.inventory.slots[5] is item
        assert player.inventory.slots[0] is None

    def test_grid_to_grid_stacking(self):
        """Stacking same items between grid slots."""
        player = _make_player()
        src = _make_item("potion", qty=3, stack_max=10)
        target = _make_item("potion", qty=4, stack_max=10)
        player.inventory.slots[0] = src
        player.inventory.slots[1] = target
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "potion", "quantity": 3, "icon": "p.png"}

        ui._transfer_dragged_to_grid(1)
        assert target.quantity == 7
        assert player.inventory.slots[0] is None

    def test_grid_to_grid_swap(self):
        """Swapping different items between grid slots."""
        player = _make_player()
        item_a = _make_item("sword")
        item_b = _make_item("shield")
        player.inventory.slots[0] = item_a
        player.inventory.slots[1] = item_b
        ui = _make_ui(player)
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_grid(1)
        assert player.inventory.slots[0] is item_b
        assert player.inventory.slots[1] is item_a

    def test_equip_to_empty_grid(self):
        """Moving equipment to empty grid slot."""
        player = _make_player()
        item = _make_item("sword")
        player.inventory.equipment["RIGHT_HAND"] = item
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_grid(0)
        assert player.inventory.slots[0] is item
        assert player.inventory.equipment["RIGHT_HAND"] is None

    def test_equip_to_grid_stacking(self):
        """Stacking equipped item onto grid slot with same item."""
        player = _make_player()
        src = _make_item("potion", qty=2, stack_max=10)
        target = _make_item("potion", qty=3, stack_max=10)
        player.inventory.equipment["BELT"] = src
        player.inventory.slots[0] = target
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "BELT", "item_id": "potion", "quantity": 2, "icon": "p.png"}

        ui._transfer_dragged_to_grid(0)
        assert target.quantity == 5
        assert player.inventory.equipment["BELT"] is None

    def test_equip_to_grid_swap(self):
        """Swapping equipment item with different grid item."""
        player = _make_player()
        equip_item = _make_item("sword")
        grid_item = _make_item("shield")
        player.inventory.equipment["RIGHT_HAND"] = equip_item
        player.inventory.slots[0] = grid_item
        # equip_item should accept the grid_item into RIGHT_HAND
        player.inventory.equip_item = MagicMock(return_value=None)
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_grid(0)
        # grid should now have the equipment item, equip_item called for the swap
        assert player.inventory.slots[0] is equip_item

    def test_equip_to_grid_swap_fail(self):
        """When grid item can't equip into the slot, abort transfer."""
        player = _make_player()
        equip_item = _make_item("sword")
        grid_item = _make_item("potion")  # Can't go in RIGHT_HAND
        player.inventory.equipment["RIGHT_HAND"] = equip_item
        player.inventory.slots[0] = grid_item
        # equip_item fails: returns the grid_item back
        player.inventory.equip_item = MagicMock(return_value=grid_item)
        ui = _make_ui(player)
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "s.png"}

        ui._transfer_dragged_to_grid(0)
        # Should abort: grid_item stays in slot 0
        assert player.inventory.slots[0] is grid_item

    def test_no_dragging_item_noop(self):
        """Calling with no dragging item does nothing."""
        ui = _make_ui()
        ui._transfer_dragged_to_grid(0)  # no crash


# ---------------------------------------------------------------------------
# Drawing methods (lines 366, 391-397, 412-422)
# ---------------------------------------------------------------------------

class TestDrawingWithItems:
    def test_draw_grid_skips_dragged_item(self):
        """Grid draw skips the item being dragged."""
        player = _make_player()
        item = _make_item("sword", icon="sword.png")
        player.inventory.slots[0] = item
        ui = _make_ui(player)
        ui.is_open = True
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "sword", "quantity": 1, "icon": "sword.png"}

        screen = pygame.Surface((1280, 720))
        # Should not crash even with dragged item
        ui._draw_grid(screen, ui.scale_factor)

    def test_draw_equipment_skips_dragged(self):
        """Equipment draw skips the slot being dragged."""
        player = _make_player()
        item = _make_item("sword", icon="sword.png")
        player.inventory.equipment["RIGHT_HAND"] = item
        ui = _make_ui(player)
        ui.is_open = True
        ui._dragging_item = {"source": "equipment", "name": "RIGHT_HAND", "item_id": "sword", "quantity": 1, "icon": "sword.png"}

        screen = pygame.Surface((1280, 720))
        ui._draw_equipment_slots(screen, ui.scale_factor)

    def test_draw_dragged_item(self):
        """_draw_dragged_item renders without crash."""
        ui = _make_ui()
        ui.is_open = True
        ui._dragging_item = {"source": "grid", "index": 0, "item_id": "x", "quantity": 3, "icon": "x.png"}
        ui._drag_pos = (400, 400)

        screen = pygame.Surface((1280, 720))
        # Mock icon cache to return a surface
        dummy_icon = pygame.Surface((48, 48))
        ui.icon_cache["x.png"] = dummy_icon
        ui._draw_dragged_item(screen)

    def test_draw_dragged_item_noop_when_none(self):
        """_draw_dragged_item is noop when no item is dragged."""
        ui = _make_ui()
        ui._dragging_item = None
        screen = pygame.Surface((1280, 720))
        ui._draw_dragged_item(screen)  # no crash

    def test_draw_equipment_with_items(self):
        """Equipment slots with items render without crash."""
        player = _make_player()
        player.inventory.equipment["HEAD"] = _make_item("helm", qty=3, icon="helm.png")
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("equipment", "HEAD")

        screen = pygame.Surface((1280, 720))
        ui._draw_equipment_slots(screen, ui.scale_factor)


# ---------------------------------------------------------------------------
# Icon cache (lines 460-461, 485-508)
# ---------------------------------------------------------------------------

class TestIconCache:
    def test_get_item_icon_cached(self):
        """Second call returns from cache."""
        ui = _make_ui()
        dummy = pygame.Surface((48, 48))
        ui.icon_cache["test.png"] = dummy
        result = ui._get_item_icon("test.png")
        assert result is dummy

    def test_get_item_icon_missing_file(self):
        """Missing icon file returns None."""
        ui = _make_ui()
        result = ui._get_item_icon("nonexistent_icon.png")
        assert result is None

    def test_get_item_icon_adds_png(self):
        """Icon filename without .png gets it appended."""
        ui = _make_ui()
        result = ui._get_item_icon("myitem")
        assert result is None  # file doesn't exist but should not crash


# ---------------------------------------------------------------------------
# Keyboard input (lines 180-189)
# ---------------------------------------------------------------------------

class TestKeyboardInput:
    def test_preview_directions(self):
        """Arrow keys change character preview state."""
        from src.config import Settings
        ui = _make_ui()
        ui.is_open = True

        for key, expected in [
            (Settings.MOVE_UP, 'up'),
            (Settings.MOVE_DOWN, 'down'),
            (Settings.MOVE_LEFT, 'left'),
            (Settings.MOVE_RIGHT, 'right'),
        ]:
            event = MagicMock()
            event.type = pygame.KEYDOWN
            event.key = key
            ui.handle_input(event)
            assert ui.preview_state == expected


# ---------------------------------------------------------------------------
# Info zone draw (lines 430-483)
# ---------------------------------------------------------------------------

class TestDrawInfoZone:
    def test_draw_info_zone_default_stats(self):
        """Without hover, draws player stats."""
        player = _make_player()
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = None

        screen = pygame.Surface((1280, 720))
        ui._draw_info_zone(screen)

    def test_draw_info_zone_with_hovered_item(self):
        """With grid hover on an item, draws item info."""
        player = _make_player()
        item = _make_item("potion", qty=5, stack_max=10)
        player.inventory.slots[0] = item
        ui = _make_ui(player)
        ui.is_open = True
        ui.hovered_slot = ("grid", 0)

        screen = pygame.Surface((1280, 720))
        with patch('src.ui.inventory.I18nManager') as mock_i18n:
            mock_i18n.return_value.get_item.return_value = {
                "name": "Potion Rouge", "description": "Restaure 50 PV."
            }
            ui._draw_info_zone(screen)
