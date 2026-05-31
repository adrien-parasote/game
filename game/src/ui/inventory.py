import logging
import os
from pathlib import Path

import pygame
from src.config import Settings
from src.engine.asset_manager import AssetManager
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
    INV_TAB_X_POSITIONS,
    INV_TAB_Y,
    INV_TARGET_WIDTH,
)
from src.ui.inventory_draw import InventoryDrawMixin
from src.ui.inventory_input import InventoryInputMixin


class InventoryUI(InventoryDrawMixin, InventoryInputMixin):
    """
    RPG Inventory UI management.
    Handles rendering of the inventory background, slots, tabs, and character preview.
    Drawing methods are provided by InventoryDrawMixin.
    """

    def __init__(self, player):
        self.player = player
        self.icon_cache = {}
        self._text_cache: dict[tuple, pygame.Surface] = {}  # (text, color_tuple) → Surface
        self._init_state()

        am = AssetManager()
        self.noble_font = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        self.narrative_font = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        self.tech_font = am.get_font(Settings.FONT_TECH, Settings.FONT_SIZE_TECH)

        self._load_and_scale_assets()
        self._init_layout_constants()

    def _init_state(self):
        self.is_open = False
        self.active_tab = 0  # 0: Inventory, 1-3: Other
        self.anim_timer = 0
        self.anim_frame = 0
        self.preview_state = "down"
        self.hovered_slot = None  # None, ('equipment', name), or ('grid', index)
        # Drag & Drop State
        self._dragging_item = None
        self._drag_pos = (0, 0)

    def _load_and_scale_assets(self):
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

        def _scale(img, ratio=self.scale_factor):
            return pygame.transform.smoothscale(
                img, (int(img.get_width() * ratio), int(img.get_height() * ratio))
            )

        # Rescale all visual assets
        self.bg = _scale(self.bg)
        self.bg_rect = self.bg.get_rect(
            center=(Settings.WINDOW_WIDTH // 2, Settings.WINDOW_HEIGHT // 2)
        )

        self.slot_img = _scale(self.slot_img)
        self.active_tab_img = _scale(self.active_tab_img)
        self.hover_img = _scale(self.hover_img)

        # Scale cursors while preserving aspect ratio
        target_h = Settings.CURSOR_SIZE
        ratio = target_h / INV_ORIGINAL_CURSOR_HEIGHT
        target_w = int(INV_ORIGINAL_CURSOR_WIDTH * ratio)

        self.pointer_img = pygame.transform.smoothscale(self.pointer_img, (target_w, target_h))
        self.pointer_select_img = pygame.transform.smoothscale(
            self.pointer_select_img, (target_w, target_h)
        )

    def _init_layout_constants(self):
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

    def _load_asset(self, filename):
        path = str(Path("assets") / "images" / "ui" / filename)
        return AssetManager().get_image(path, fallback=True)

    def toggle(self):
        self.is_open = not self.is_open
        logging.info(f"Inventory {'opened' if self.is_open else 'closed'}")

    def set_tab(self, index):
        if 0 <= index < 4:
            self.active_tab = index
        else:
            self.active_tab = 0

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

        path = str(Path("assets") / "images" / "icons" / icon_filename)
        # Ensure .png extension if missing
        if not path.endswith(".png"):
            path += ".png"
            icon_filename += ".png"

        if os.path.exists(path):
            try:
                img = AssetManager().get_image(path, fallback=True)
            except Exception as e:
                logging.error(f"InventoryUI: Could not load icon {icon_filename}: {e}")
                self.icon_cache[icon_filename] = None
                return None
            # Scale icon to fit slot (approx 48x48 base, scaled by s)
            target_size = int(48 * self.scale_factor)
            img = pygame.transform.smoothscale(img, (target_size, target_size))
            self.icon_cache[icon_filename] = img
            return img

        return None
