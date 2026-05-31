# src/ui/inventory_draw.py
"""Drawing mixin for InventoryUI — handles all rendering logic."""

import logging
from typing import TYPE_CHECKING

import pygame
from src.engine.i18n import I18nManager
from src.ui.inventory_constants import (
    INV_DRAG_BORDER_RADIUS_BASE,
    INV_DRAG_HIGHLIGHT_BORDER,
    INV_GOLD_X,
    INV_HP_X,
    INV_INFO_MAX_W_OFFSET,
    INV_STAT_NAME_OFFSET_Y,
    INV_STATS_X,
    INV_STATS_Y,
)
from src.ui.ui_colors import COLOR_HIGHLIGHT_GOLD, COLOR_TEXT_STONE

if TYPE_CHECKING:
    from src.ui.inventory_protocol import InventoryUIProtocol


class InventoryDrawMixin:
    """Mixin handling all draw-related methods for InventoryUI."""

    def _render_text(
        self: "InventoryUIProtocol",
        font: pygame.font.Font,
        text: str,
        color: tuple,
    ) -> pygame.Surface:
        """Cache-aware font.render. Zero alloc on repeat (text, color) pairs."""
        key = (id(font), text, color)
        if key not in self._text_cache:
            self._text_cache[key] = font.render(text, True, color)
        return self._text_cache[key]

    def draw(self: "InventoryUIProtocol", screen: pygame.Surface) -> None:
        """Render the complete inventory overlay."""
        if not self.is_open:
            return

        s = self.scale_factor
        screen.blit(self.bg, self.bg_rect)
        screen.blit(self.active_tab_img, self.tab_rects[self.active_tab])

        # Character preview
        self._draw_character_preview(screen)

        if self.active_tab == 0:
            self._draw_grid(screen, s)

        self._draw_equipment_slots(screen, s)
        self._draw_info_zone(screen)
        self._draw_dragged_item(screen)
        self._draw_cursor(screen)

    def _draw_character_preview(self: "InventoryUIProtocol", screen: pygame.Surface) -> None:
        """Draw the animated character preview and name."""
        row_offsets = {"down": 0, "left": 4, "right": 8, "up": 12}
        offset = row_offsets.get(self.preview_state, 0)
        try:
            char_image = self.player.frames[offset + self.anim_frame]
            screen.blit(char_image, char_image.get_rect(center=self.char_preview_pos))
        except Exception as e:
            logging.error(f"InventoryUI: Character preview failed: {e}")

        name_text = self._render_text(self.noble_font, "Player", COLOR_TEXT_STONE)
        screen.blit(name_text, name_text.get_rect(midbottom=self.char_name_pos))

    def _draw_grid(self: "InventoryUIProtocol", screen: pygame.Surface, s: float) -> None:
        """Draw inventory grid slots and item icons for the active tab."""
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = self.grid_start[0] + (col * self.grid_spacing_x)
                y = self.grid_start[1] + (row * self.grid_spacing_y)
                slot_rect = self.slot_img.get_rect(center=(x, y))
                screen.blit(self.slot_img, slot_rect)

                index = row * self.grid_cols + col
                item = self.player.inventory.get_item_at(index)
                if not item:
                    continue
                # Skip if dragged
                if (
                    self._dragging_item
                    and self._dragging_item["source"] == "grid"
                    and self._dragging_item["index"] == index
                ):
                    continue
                icon = self._get_item_icon(item.icon if item.icon else f"{item.id}.png")
                if icon:
                    screen.blit(icon, icon.get_rect(center=(x, y)))
                if item.quantity > 1:
                    qty_text = self._render_text(self.tech_font, f"x{item.quantity}", COLOR_TEXT_STONE)
                    margin = int(8 * s)
                    screen.blit(
                        qty_text,
                        qty_text.get_rect(
                            bottomright=(slot_rect.right - margin, slot_rect.bottom - margin)
                        ),
                    )

        if self.hovered_slot and self.hovered_slot[0] == "grid":
            _, value = self.hovered_slot
            col, row = value % self.grid_cols, value // self.grid_cols
            pos = (
                self.grid_start[0] + col * self.grid_spacing_x,
                self.grid_start[1] + row * self.grid_spacing_y,
            )
            screen.blit(self.hover_img, self.hover_img.get_rect(center=pos))

    def _draw_equipment_slots(
        self: "InventoryUIProtocol", screen: pygame.Surface, s: float
    ) -> None:
        """Draw equipped items and gold border on hovered equipment slot."""
        for name, pos in self.equipment_slots.items():
            item = self.player.inventory.equipment.get(name)
            rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
            rect.center = pos

            # Draw item if equipped
            if item and not (
                self._dragging_item
                and self._dragging_item["source"] == "equipment"
                and self._dragging_item["name"] == name
            ):
                icon = self._get_item_icon(item.icon if item.icon else f"{item.id}.png")
                if icon:
                    screen.blit(icon, icon.get_rect(center=pos))
                if item.quantity > 1:
                    qty_text = self._render_text(self.tech_font, f"x{item.quantity}", COLOR_TEXT_STONE)
                    margin = int(8 * s)
                    screen.blit(
                        qty_text,
                        qty_text.get_rect(bottomright=(rect.right - margin, rect.bottom - margin)),
                    )

        if not self.hovered_slot or self.hovered_slot[0] != "equipment":
            return
        _, name = self.hovered_slot
        pos = self.equipment_slots[name]
        rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
        rect.center = pos
        pygame.draw.rect(
            screen,
            COLOR_HIGHLIGHT_GOLD,
            rect,
            INV_DRAG_HIGHLIGHT_BORDER,
            border_radius=int(INV_DRAG_BORDER_RADIUS_BASE * s),
        )

    def _draw_dragged_item(self: "InventoryUIProtocol", screen: pygame.Surface) -> None:
        """Draw the item currently being dragged."""
        if not self._dragging_item:
            return

        icon = self._get_item_icon(self._dragging_item["icon"])
        if icon:
            rect = icon.get_rect(center=self._drag_pos)
            screen.blit(icon, rect)

            qty = self._dragging_item["quantity"]
            if qty > 1:
                qty_text = self._render_text(self.tech_font, f"x{qty}", COLOR_TEXT_STONE)
                # align to bottom right of the icon rect
                margin = int(8 * self.scale_factor)
                screen.blit(
                    qty_text,
                    qty_text.get_rect(bottomright=(rect.right - margin, rect.bottom - margin)),
                )

    def _draw_cursor(self: "InventoryUIProtocol", screen: pygame.Surface) -> None:
        """Draw custom cursor on top of all UI elements."""
        mouse_pos = pygame.mouse.get_pos()
        cursor_img = self.pointer_select_img if pygame.mouse.get_pressed()[0] else self.pointer_img
        screen.blit(cursor_img, mouse_pos)

    def _draw_info_zone(self: "InventoryUIProtocol", screen: pygame.Surface) -> None:
        """Draw either character stats or hovered item info in the green bar."""
        s = self.scale_factor
        stats_x = self.bg_rect.x + int(INV_STATS_X * s)
        stats_y = self.bg_rect.y + int(INV_STATS_Y * s)

        # Check if we should show item info instead of stats
        if self.hovered_slot:
            slot_type, value = self.hovered_slot
            if slot_type == "grid":
                item = self.player.inventory.get_item_at(value)
                if item:
                    self._draw_item_info(screen, item, stats_x, stats_y, s)
                    return

        # Default: Draw Stats
        self._draw_stats(screen, stats_x, stats_y, s)

    def _draw_item_info(
        self: "InventoryUIProtocol",
        screen: pygame.Surface,
        item: object,
        stats_x: int,
        stats_y: int,
        s: float,
    ) -> None:
        """Draw localized item name and wrapped description."""
        item_data = I18nManager().get_item(item.id)
        name = item_data["name"]
        description = item_data["description"]

        name_text = self.noble_font.render(name, True, COLOR_TEXT_STONE)
        screen.blit(name_text, (stats_x, stats_y - int(INV_STAT_NAME_OFFSET_Y * s)))

        # Draw Wrapped Description (More compact)
        max_w = self.bg_rect.width - int(INV_INFO_MAX_W_OFFSET * s)
        words = description.split(" ")
        lines: list[str] = []
        current_line: list[str] = []
        for word in words:
            test_line = " ".join(current_line + [word])
            if self.narrative_font.size(test_line)[0] < max_w:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        lines.append(" ".join(current_line))

        for i, line in enumerate(lines[:3]):  # Max 3 lines
            desc_surf = self.narrative_font.render(line, True, COLOR_TEXT_STONE)
            screen.blit(desc_surf, (stats_x, stats_y + int(5 * s) + i * int(18 * s)))

    def _draw_stats(
        self: "InventoryUIProtocol",
        screen: pygame.Surface,
        stats_x: int,
        stats_y: int,
        s: float,
    ) -> None:
        """Draw LVL, HP, and GOLD in the stats bar."""
        # LVL (Left part of green bar)
        lvl_text = self._render_text(
            self.noble_font, f"LVL {self.player.level}", COLOR_TEXT_STONE
        )
        lvl_rect = lvl_text.get_rect(midleft=(stats_x, stats_y))
        screen.blit(lvl_text, lvl_rect)

        # HP (Center)
        hp_text = self._render_text(
            self.noble_font,
            f"HP {self.player.hp}/{self.player.max_hp}",
            COLOR_TEXT_STONE,
        )
        hp_rect = hp_text.get_rect(center=(self.bg_rect.x + int(INV_HP_X * s), stats_y))
        screen.blit(hp_text, hp_rect)

        # GOLD (Right)
        gold_text = self._render_text(
            self.noble_font, f"GOLD {self.player.gold}", COLOR_TEXT_STONE
        )
        gold_rect = gold_text.get_rect(
            midright=(self.bg_rect.x + int(INV_GOLD_X * s), stats_y)
        )
        screen.blit(gold_text, gold_rect)
