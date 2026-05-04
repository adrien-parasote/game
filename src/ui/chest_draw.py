from typing import TYPE_CHECKING

import pygame

from src.config import Settings
from src.ui.chest_constants import _INV_SLOTS_VISIBLE, _TITLE_OFFSET_X, _TITLE_OFFSET_Y

if TYPE_CHECKING:
    from src.ui.chest_protocol import ChestUIProtocol


class ChestDrawMixin:
    """Mixin handling drawing of chest and player inventory panels."""

    def _draw_title(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Render the chest name centred in the title zone."""
        if self._title_rect is None:
            return
        font = pygame.font.Font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        surf = font.render("Chest", True, (60, 40, 30))
        cx = self._title_rect.centerx + _TITLE_OFFSET_X
        cy = self._title_rect.centery + _TITLE_OFFSET_Y
        screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _draw_slots(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Render chest slot frames, item icons, quantities, and hover overlay."""
        if self._qty_font is None:
            self._qty_font = pygame.font.Font(Settings.FONT_TECH, Settings.FONT_SIZE_TECH)

        contents = self._get_chest_contents()
        slot_size = self._slot_img.get_width() if self._slot_img else 49
        icon_size = max(1, slot_size - 8)
        scale_factor = slot_size / 55
        margin = int(8 * scale_factor)

        for i, rect in enumerate(self._slot_positions):
            # Slot background
            if self._slot_img:
                screen.blit(self._slot_img, rect)
            else:
                pygame.draw.rect(screen, (200, 200, 200), rect, 2)

            # Item icon + quantity
            if i >= len(contents):
                continue

            entry = contents[i]
            if entry is None:
                continue

            item_id = entry.get("item_id", "")

            # Skip drawing if this item is being dragged
            if (
                self._dragging_item
                and self._dragging_item["source"] == "chest"
                and self._dragging_item["index"] == i
            ):
                continue

            icon_name = self._resolve_icon_name(item_id)
            icon = self._get_item_icon(icon_name, icon_size)
            if icon:
                icon_rect = icon.get_rect(center=rect.center)
                screen.blit(icon, icon_rect)

            qty = entry.get("quantity", 1)
            if qty > 1:
                qty_surf = self._qty_font.render(f"x{qty}", True, (60, 40, 30))
                qty_rect = qty_surf.get_rect(
                    bottomright=(rect.right - margin, rect.bottom - margin)
                )
                screen.blit(qty_surf, qty_rect)

        if self._hovered_chest_slot is not None and self._hover_img:
            hover_rect = self._hover_img.get_rect(
                center=self._slot_positions[self._hovered_chest_slot].center
            )
            screen.blit(self._hover_img, hover_rect)

    def _draw_arrow_hovers(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Render chest arrow hover overlays."""
        # Left button (up_rect) should show DOWN arrow (to inventory)
        if self._hovered_chest_arrow == "up" and self._arrow_up_rect and self._arrow_down_hover_img:
            rect = self._arrow_down_hover_img.get_rect(center=self._arrow_up_rect.center)
            screen.blit(self._arrow_down_hover_img, rect)
        # Right button (down_rect) should show UP arrow (to chest)
        elif (
            self._hovered_chest_arrow == "down"
            and self._arrow_down_rect
            and self._arrow_up_hover_img
        ):
            rect = self._arrow_up_hover_img.get_rect(center=self._arrow_down_rect.center)
            screen.blit(self._arrow_up_hover_img, rect)

    def _draw_inv_slots(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Render player inventory slot frames, item icons, quantities and hover overlay."""
        if self._qty_font is None:
            self._qty_font = pygame.font.Font(Settings.FONT_TECH, Settings.FONT_SIZE_TECH)

        page_items = self._current_page_slots()
        slot_size = self._slot_img.get_width() if self._slot_img else 49
        icon_size = max(1, slot_size - 8)
        scale_factor = slot_size / 55
        margin = int(8 * scale_factor)

        # Only draw as many frames as there are real slots at this offset
        visible_count = min(_INV_SLOTS_VISIBLE, max(0, self._capacity() - self._inv_offset))

        for i, rect in enumerate(self._inv_slot_positions[:visible_count]):
            # Slot background
            if self._slot_img:
                screen.blit(self._slot_img, rect)
            else:
                pygame.draw.rect(screen, (180, 180, 180), rect, 2)

            # Item icon + quantity
            if i >= len(page_items) or page_items[i] is None:
                continue

            # Skip drawing if this item is being dragged
            actual_index = self._inv_offset + i
            if (
                self._dragging_item
                and self._dragging_item["source"] == "inv"
                and self._dragging_item["index"] == actual_index
            ):
                continue

            item = page_items[i]
            icon_name = item.icon if hasattr(item, "icon") and item.icon else f"{item.id}.png"
            icon = self._get_item_icon(icon_name, icon_size)
            if icon:
                icon_rect = icon.get_rect(center=rect.center)
                screen.blit(icon, icon_rect)

            qty = getattr(item, "quantity", 1)
            if qty > 1:
                qty_surf = self._qty_font.render(f"x{qty}", True, (60, 40, 30))
                qty_rect = qty_surf.get_rect(
                    bottomright=(rect.right - margin, rect.bottom - margin)
                )
                screen.blit(qty_surf, qty_rect)

        # Hover overlay (guard against hovering a now-hidden slot)
        hov = self._hovered_inv_slot
        if hov is not None and hov < visible_count and self._hover_img:
            hover_rect = self._hover_img.get_rect(center=self._inv_slot_positions[hov].center)
            screen.blit(self._hover_img, hover_rect)

    def _draw_inv_arrows(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Render left/right arrow hover overlays.
        Left arrow: rewinds window — visible when there are items behind (offset > 0).
        Right arrow: advances window — visible when more items exist ahead.
        """
        if (
            self._can_scroll_left()
            and self._hovered_inv_arrow == "left"
            and self._inv_arrow_left_rect
            and self._arrow_left_hover_img
        ):
            rect = self._arrow_left_hover_img.get_rect(center=self._inv_arrow_left_rect.center)
            screen.blit(self._arrow_left_hover_img, rect)

        if (
            self._can_scroll_right()
            and self._hovered_inv_arrow == "right"
            and self._inv_arrow_right_rect
            and self._arrow_right_hover_img
        ):
            rect = self._arrow_right_hover_img.get_rect(center=self._inv_arrow_right_rect.center)
            screen.blit(self._arrow_right_hover_img, rect)

    def _draw_cursor(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Draw the glove cursor at mouse position (always on top)."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        if img:
            screen.blit(img, mouse_pos)

    def _draw_dragged_item(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
        """Render the icon of the item currently being dragged."""
        if not self._dragging_item:
            return

        slot_size = self._slot_img.get_width() if self._slot_img else 49
        icon_size = max(1, slot_size - 8)
        icon = self._get_item_icon(self._dragging_item["icon"], icon_size)
        if icon:
            icon_rect = icon.get_rect(center=self._drag_pos)
            screen.blit(icon, icon_rect)
