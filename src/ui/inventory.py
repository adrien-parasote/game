import logging
import os

import pygame

from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.ui.inventory_draw import InventoryDrawMixin
from src.ui.inventory_constants import (
    INV_ASSET_BG,
    INV_ASSET_HOVER,
    INV_ASSET_POINTER,
    INV_ASSET_POINTER_SELECT,
    INV_ASSET_SLOT,
    INV_ASSET_TAB,
    INV_CHAR_NAME_POS,
    INV_CHAR_PREVIEW_POS,
    INV_EQUIP_RECT_SIDE,
    INV_EQUIPMENT_SLOTS,
    INV_GRID_COLS,
    INV_GRID_ROWS,
    INV_GRID_SPACING_X,
    INV_GRID_SPACING_Y,
    INV_GRID_START,
    INV_ORIGINAL_CURSOR_HEIGHT,
    INV_ORIGINAL_CURSOR_WIDTH,
    INV_PLACEHOLDER_SIZE,
    INV_TAB_X_POSITIONS,
    INV_TAB_Y,
    INV_TARGET_WIDTH,
)
from src.ui.ui_colors import COLOR_DEBUG_MISSING


class InventoryUI(InventoryDrawMixin):
    """
    RPG Inventory UI management.
    Handles rendering of the inventory background, slots, tabs, and character preview.
    Drawing methods are provided by InventoryDrawMixin.
    """

    def __init__(self, player):
        self.player = player
        self.is_open = False
        self.active_tab = 0  # 0: Inventory, 1-3: Other

        am = AssetManager()
        self.noble_font = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        self.narrative_font = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        self.tech_font = am.get_font(Settings.FONT_TECH, Settings.FONT_SIZE_TECH)

        self.icon_cache = {}

        # Load and Scale Assets
        self.bg = self._load_asset(INV_ASSET_BG)
        self.slot_img = self._load_asset(INV_ASSET_SLOT)
        self.active_tab_img = self._load_asset(INV_ASSET_TAB)
        self.hover_img = self._load_asset(INV_ASSET_HOVER)
        self.pointer_img = self._load_asset(INV_ASSET_POINTER)
        self.pointer_select_img = self._load_asset(INV_ASSET_POINTER_SELECT)

        # Urbanization: Scale down to fit 1280px screen (1344 -> 1200)
        original_width = self.bg.get_width()
        self.scale_factor = INV_TARGET_WIDTH / original_width

        # Rescale all visual assets
        new_bg_size = (
            int(self.bg.get_width() * self.scale_factor),
            int(self.bg.get_height() * self.scale_factor),
        )
        self.bg = pygame.transform.smoothscale(self.bg, new_bg_size)
        self.bg_rect = self.bg.get_rect(
            center=(Settings.WINDOW_WIDTH // 2, Settings.WINDOW_HEIGHT // 2)
        )

        self.slot_img = pygame.transform.smoothscale(
            self.slot_img,
            (
                int(self.slot_img.get_width() * self.scale_factor),
                int(self.slot_img.get_height() * self.scale_factor),
            ),
        )
        self.active_tab_img = pygame.transform.smoothscale(
            self.active_tab_img,
            (
                int(self.active_tab_img.get_width() * self.scale_factor),
                int(self.active_tab_img.get_height() * self.scale_factor),
            ),
        )
        self.hover_img = pygame.transform.smoothscale(
            self.hover_img,
            (
                int(self.hover_img.get_width() * self.scale_factor),
                int(self.hover_img.get_height() * self.scale_factor),
            ),
        )
        # Scale cursors while preserving aspect ratio
        target_h = Settings.CURSOR_SIZE
        ratio = target_h / INV_ORIGINAL_CURSOR_HEIGHT
        target_w = int(INV_ORIGINAL_CURSOR_WIDTH * ratio)

        self.pointer_img = pygame.transform.smoothscale(self.pointer_img, (target_w, target_h))
        self.pointer_select_img = pygame.transform.smoothscale(
            self.pointer_select_img, (target_w, target_h)
        )

        # UI Layout Constants
        s = self.scale_factor

        # Tabs positions (RED zone)
        self.tab_rects = [
            self.active_tab_img.get_rect(
                center=(self.bg_rect.x + int(x * s), self.bg_rect.y + int(INV_TAB_Y * s))
            )
            for x in INV_TAB_X_POSITIONS
        ]

        # Equipment Slots (MAGENTA zone - Left)
        self.equip_rect_side = int(INV_EQUIP_RECT_SIDE * s)
        self.equipment_slots = {
            k: (self.bg_rect.x + int(v[0] * s), self.bg_rect.y + int(v[1] * s))
            for k, v in INV_EQUIPMENT_SLOTS.items()
        }

        # Inventory Grid (BLUE zone - Right)
        self.grid_start = (
            self.bg_rect.x + int(INV_GRID_START[0] * s),
            self.bg_rect.y + int(INV_GRID_START[1] * s),
        )
        self.grid_cols = INV_GRID_COLS
        self.grid_rows = INV_GRID_ROWS
        self.grid_spacing_x = int(INV_GRID_SPACING_X * s)
        self.grid_spacing_y = int(INV_GRID_SPACING_Y * s)

        # Character Preview (ORANGE zone - Center Left)
        self.char_preview_pos = (
            self.bg_rect.x + int(INV_CHAR_PREVIEW_POS[0] * s),
            self.bg_rect.y + int(INV_CHAR_PREVIEW_POS[1] * s),
        )
        self.char_name_pos = (
            self.bg_rect.x + int(INV_CHAR_NAME_POS[0] * s),
            self.bg_rect.y + int(INV_CHAR_NAME_POS[1] * s),
        )

        self.anim_timer = 0
        self.anim_frame = 0
        self.preview_state = "down"
        self.hovered_slot = None  # None, ('equipment', name), or ('grid', index)

        # Drag & Drop State
        self._dragging_item = None
        self._drag_pos = (0, 0)

    def _load_asset(self, filename):
        path = os.path.join("assets", "images", "ui", filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"InventoryUI: Could not load {filename}: {e}")
            surf = pygame.Surface((INV_PLACEHOLDER_SIZE, INV_PLACEHOLDER_SIZE))
            surf.fill(COLOR_DEBUG_MISSING)
            return surf

    def toggle(self):
        self.is_open = not self.is_open
        logging.info(f"Inventory {'opened' if self.is_open else 'closed'}")

    def set_tab(self, index):
        if 0 <= index < 4:
            self.active_tab = index
        else:
            self.active_tab = 0

    def handle_input(self, event):
        if not self.is_open:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_pos = event.pos
                logging.debug(f"Inventory click at {mouse_pos}")

                # Check Tabs
                for i, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(mouse_pos):
                        logging.info(f"Tab {i} selected")
                        self.set_tab(i)
                        return

                # Drag Start
                if self.hovered_slot:
                    slot_type, value = self.hovered_slot
                    if slot_type == "equipment":
                        item = self.player.inventory.equipment.get(value)
                        if item:
                            self._dragging_item = {
                                "source": "equipment",
                                "name": value,
                                "item_id": item.id,
                                "quantity": item.quantity,
                                "icon": item.icon if item.icon else f"{item.id}.png",
                            }
                            self._drag_pos = mouse_pos
                            return
                    elif slot_type == "grid":
                        item = self.player.inventory.get_item_at(value)
                        if item:
                            self._dragging_item = {
                                "source": "grid",
                                "index": value,
                                "item_id": item.id,
                                "quantity": item.quantity,
                                "icon": item.icon if item.icon else f"{item.id}.png",
                            }
                            self._drag_pos = mouse_pos
                            return

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging_item:
                self._drag_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._dragging_item:
                self.update_hover(event.pos)  # ensure accurate drop target
                if self.hovered_slot:
                    slot_type, value = self.hovered_slot
                    if slot_type == "equipment" and isinstance(value, str):
                        self._transfer_dragged_to_equipment(value)
                    elif slot_type == "grid" and isinstance(value, int):
                        self._transfer_dragged_to_grid(value)
                self._dragging_item = None

        elif event.type == pygame.KEYDOWN:
            # Change character preview direction
            if event.key == Settings.MOVE_UP:
                self.preview_state = "up"
            elif event.key == Settings.MOVE_DOWN:
                self.preview_state = "down"
            elif event.key == Settings.MOVE_LEFT:
                self.preview_state = "left"
            elif event.key == Settings.MOVE_RIGHT:
                self.preview_state = "right"

    def _transfer_dragged_to_equipment(self, target_name: str) -> None:
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

    def _transfer_dragged_to_grid(self, target_idx: int) -> None:
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

    def update_hover(self, mouse_pos):
        """Detect which slot is under the mouse."""
        self.hovered_slot = None

        # Check Equipment Slots
        for name, pos in self.equipment_slots.items():
            rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
            rect.center = pos
            if rect.collidepoint(mouse_pos):
                self.hovered_slot = ("equipment", name)
                return

        # Check Grid Slots (only if Tab 0)
        if self.active_tab == 0:
            for row in range(self.grid_rows):
                for col in range(self.grid_cols):
                    x = self.grid_start[0] + (col * self.grid_spacing_x)
                    y = self.grid_start[1] + (row * self.grid_spacing_y)
                    rect = self.slot_img.get_rect(center=(x, y))
                    if rect.collidepoint(mouse_pos):
                        self.hovered_slot = ("grid", row * self.grid_cols + col)
                        return

    def update(self, dt):
        if not self.is_open:
            return

        # Update character preview animation (Idle)
        self.anim_timer += dt
        if self.anim_timer >= 0.15:  # 150ms per frame
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4

        # Update hover state
        self.update_hover(pygame.mouse.get_pos())

    def _get_item_icon(self, icon_filename):
        """Load and cache item icon."""
        if icon_filename in self.icon_cache:
            return self.icon_cache[icon_filename]

        path = os.path.join("assets", "images", "icons", icon_filename)
        # Ensure .png extension if missing
        if not path.endswith(".png"):
            path += ".png"
            icon_filename += ".png"

        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                # Scale icon to fit slot (approx 48x48 base, scaled by s)
                target_size = int(48 * self.scale_factor)
                img = pygame.transform.smoothscale(img, (target_size, target_size))
                self.icon_cache[icon_filename] = img
                return img
        except Exception as e:
            logging.error(f"InventoryUI: Could not load icon {icon_filename}: {e}")

        return None
