# src/ui/inventory_input.py
"""Input mixin for InventoryUI — handles all user interaction and drag-and-drop logic."""

import logging
from typing import TYPE_CHECKING

import pygame
from src.config import Settings

if TYPE_CHECKING:
    from src.ui.inventory_protocol import InventoryUIProtocol


class InventoryInputMixin:
    """Mixin handling input events and drag-and-drop logic for InventoryUI."""

    def handle_input(self: "InventoryUIProtocol", event: pygame.event.Event) -> None:
        """Process keyboard and mouse events."""
        if not self.is_open:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_down(event.pos)
        elif event.type == pygame.MOUSEMOTION and self._dragging_item:
            self._drag_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._dragging_item:
            self._handle_mouse_up(event.pos)
        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)

    def _handle_mouse_down(self: "InventoryUIProtocol", mouse_pos: tuple[int, int]) -> None:
        """Handle initial click for tabs and starting drag."""
        logging.debug(f"Inventory click at {mouse_pos}")
        for i, rect in enumerate(self.tab_rects):
            if rect.collidepoint(mouse_pos):
                logging.info(f"Tab {i} selected")
                self.set_tab(i)
                return

        if self.hovered_slot:
            slot_type, value = self.hovered_slot
            if slot_type == "equipment":
                item = self.player.inventory.equipment.get(value)
                if item:
                    self._start_drag("equipment", value, item, mouse_pos)
            elif slot_type == "grid":
                item = self.player.inventory.get_item_at(value)
                if item:
                    self._start_drag("grid", value, item, mouse_pos)

    def _start_drag(
        self: "InventoryUIProtocol",
        source: str,
        identifier: str | int,
        item: object,
        mouse_pos: tuple[int, int],
    ) -> None:
        """Initialize drag state."""
        self._dragging_item = {
            "source": source,
            "name": identifier if source == "equipment" else None,
            "index": identifier if source == "grid" else None,
            "item_id": item.id,
            "quantity": item.quantity,
            "icon": item.icon if item.icon else f"{item.id}.png",
        }
        self._drag_pos = mouse_pos

    def _handle_mouse_up(self: "InventoryUIProtocol", mouse_pos: tuple[int, int]) -> None:
        """Handle drop logic when mouse is released."""
        self.update_hover(mouse_pos)
        if self.hovered_slot:
            slot_type, value = self.hovered_slot
            if slot_type == "equipment" and isinstance(value, str):
                self._transfer_dragged_to_equipment(value)
            elif slot_type == "grid" and isinstance(value, int):
                self._transfer_dragged_to_grid(value)
        self._dragging_item = None

    def _handle_keydown(self: "InventoryUIProtocol", key: int) -> None:
        """Handle keyboard input for character preview direction."""
        if key == Settings.MOVE_UP:
            self.preview_state = "up"
        elif key == Settings.MOVE_DOWN:
            self.preview_state = "down"
        elif key == Settings.MOVE_LEFT:
            self.preview_state = "left"
        elif key == Settings.MOVE_RIGHT:
            self.preview_state = "right"

    def _transfer_dragged_to_equipment(self: "InventoryUIProtocol", target_name: str) -> None:  # noqa: C901
        """Transfer dragged item to the equipment slot."""
        if not self._dragging_item or not self.player:
            return

        source = self._dragging_item["source"]
        inv = self.player.inventory

        if source == "equipment":
            src_name = self._dragging_item["name"]
            if src_name == target_name:
                return

            src_item = inv.unequip_item(src_name)
            if not src_item:
                return

            swapped = inv.equip_item(target_name, src_item)
            if swapped == src_item:
                # Failed to equip, put back
                inv.equip_item(src_name, src_item)
            elif swapped is not None:
                # Put swapped item back in source slot if possible
                swapped_back = inv.equip_item(src_name, swapped)
                if swapped_back == swapped:
                    # Couldn't swap back, add to grid as fallback
                    inv.add_item(swapped.id, swapped.quantity)
        else:
            # Source is grid
            src_idx = self._dragging_item["index"]
            src_item = inv.slots[src_idx]
            if not src_item:
                return

            inv.slots[src_idx] = None

            swapped = inv.equip_item(target_name, src_item)
            if swapped == src_item:
                # Failed to equip, return to grid
                inv.slots[src_idx] = src_item
            elif swapped is not None:
                # Equip successful, we got a swapped item. Put it in grid
                inv.slots[src_idx] = swapped

    def _transfer_dragged_to_grid(self: "InventoryUIProtocol", target_idx: int) -> None:  # noqa: C901
        """Transfer dragged item to a grid slot."""
        if not self._dragging_item or not self.player:
            return

        item_id = self._dragging_item["item_id"]
        qty = self._dragging_item["quantity"]
        source = self._dragging_item["source"]

        inv = self.player.inventory
        target_slot = inv.slots[target_idx]

        if source == "grid":
            src_idx = self._dragging_item["index"]
            if src_idx == target_idx:
                return

            if target_slot is None:
                inv.slots[target_idx] = inv.slots[src_idx]
                inv.slots[src_idx] = None
            elif target_slot.id == item_id:
                can_add = min(qty, target_slot.stack_max - target_slot.quantity)
                target_slot.quantity += can_add
                inv.slots[src_idx].quantity -= can_add
                if inv.slots[src_idx].quantity <= 0:
                    inv.slots[src_idx] = None
            else:
                inv.slots[target_idx], inv.slots[src_idx] = (
                    inv.slots[src_idx],
                    inv.slots[target_idx],
                )
        else:
            # Source is equipment
            src_name = self._dragging_item["name"]
            src_item = inv.equipment.get(src_name)
            if not src_item:
                return

            if target_slot is None:
                inv.slots[target_idx] = src_item
                inv.equipment[src_name] = None
            elif target_slot.id == item_id:
                can_add = min(qty, target_slot.stack_max - target_slot.quantity)
                target_slot.quantity += can_add
                src_item.quantity -= can_add
                if src_item.quantity <= 0:
                    inv.equipment[src_name] = None
            else:
                # Swap target into equipment
                inv.slots[target_idx] = None
                swapped = inv.equip_item(src_name, target_slot)
                if swapped == target_slot:
                    # Failed to equip target item to this slot, abort transfer
                    inv.slots[target_idx] = target_slot
                else:
                    # Put the previously equipped item into the grid
                    inv.slots[target_idx] = src_item
