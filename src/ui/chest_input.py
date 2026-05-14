# src/ui/chest_input.py
"""Input mixin for ChestUI — handles all user interaction and drag-and-drop logic."""

import pygame

from src.ui.chest_constants import _INV_SLOTS_VISIBLE


class ChestInputMixin:
    """Mixin handling input events and drag-and-drop logic for ChestUI."""

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        pos = event.pos

        # Inventory scroll (page-based jumps)
        if (
            self._can_scroll_right()
            and self._inv_arrow_right_rect
            and self._inv_arrow_right_rect.collidepoint(pos)
        ):
            self._scroll_right()
        elif (
            self._can_scroll_left()
            and self._inv_arrow_left_rect
            and self._inv_arrow_left_rect.collidepoint(pos)
        ):
            self._scroll_left()

        # Auto-transfer arrows
        elif self._arrow_up_rect and self._arrow_up_rect.collidepoint(pos):
            self._transfer_chest_to_inventory()
        elif self._arrow_down_rect and self._arrow_down_rect.collidepoint(pos):
            self._transfer_inventory_to_chest()

        # Manual Drag: start
        else:
            # Check Chest slots
            for i, rect in enumerate(self._slot_positions):
                if rect.collidepoint(pos):
                    contents = self._get_chest_contents()
                    if i < len(contents):
                        entry = contents[i]
                        if entry is None:
                            continue
                        self._dragging_item = {
                            "item_id": entry["item_id"],
                            "quantity": entry["quantity"],
                            "source": "chest",
                            "index": i,
                            "icon": self._resolve_icon_name(entry["item_id"]),
                        }
                        self._drag_pos = pos
                        return

            # Check Inventory slots
            visible_count = min(_INV_SLOTS_VISIBLE, max(0, self._capacity() - self._inv_offset))
            if self._player:
                for i, rect in enumerate(self._inv_slot_positions[:visible_count]):
                    if rect.collidepoint(pos):
                        actual_index = self._inv_offset + i
                        item = self._player.inventory.get_item_at(actual_index)
                        if item:
                            self._dragging_item = {
                                "item_id": item.id,
                                "quantity": item.quantity,
                                "source": "inv",
                                "index": actual_index,
                                "icon": item.icon if item.icon else f"{item.id}.png",
                            }
                            self._drag_pos = pos
                            return

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        """Update drag position."""
        if self._dragging_item:
            self._drag_pos = event.pos

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        """Handle item drop."""
        if not self._dragging_item:
            return

        pos = event.pos
        self.update_hover(pos)  # Ensure accurate drop location

        # Determine destination
        if self._hovered_chest_slot is not None:
            self._transfer_dragged_to_chest(self._hovered_chest_slot)
        elif self._hovered_inv_slot is not None:
            actual_inv_idx = self._inv_offset + self._hovered_inv_slot
            self._transfer_dragged_to_inventory(actual_inv_idx)
        else:
            # Dropped outside any valid slot, item stays at its source
            pass

        self._dragging_item = None

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a single pygame event for the chest UI."""
        if not self.is_open:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_down(event)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._handle_mouse_up(event)
