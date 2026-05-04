# src/ui/chest_layout.py
"""Layout computation logic for the Chest UI."""

import logging
from typing import TYPE_CHECKING

import pygame

from src.config import Settings
from src.ui.chest_constants import (
    _ARROW_DOWN_ZONE_REL,
    _ARROW_OFFSET_X,
    _ARROW_OFFSET_Y,
    _ARROW_UP_ZONE_REL,
    _CONTENT_ZONE_REL,
    _GRID_OFFSET_Y,
    _INV_ARROW_EDGE_OFFSET,
    _INV_ARROW_ZONE_W,
    _INV_CONTENT_ZONE_REL,
    _INV_GRID_OFFSET_X,
    _INV_GRID_OFFSET_Y,
    _INV_SLOT_COLS,
    _INV_SLOT_ROWS,
    _SLOT_COLS,
    _SLOT_ROWS,
    _TARGET_WIDTH,
    _TITLE_ZONE_REL,
    ASSET_ARROW_DOWN_HOVER,
    ASSET_ARROW_LEFT_HOVER,
    ASSET_ARROW_RIGHT_HOVER,
    ASSET_ARROW_UP_HOVER,
    ASSET_SLOT_HOVER,
)

if TYPE_CHECKING:
    from src.ui.chest_protocol import ChestUIProtocol


class ChestLayoutMixin:
    """Mixin handling the calculation of rectangles and coordinates for the chest UI."""

    def _compute_layout(self: "ChestUIProtocol") -> None:
        """Calculate all derived rectangles and slot positions.
        Called once per open(). Guarded against repeated calls.
        """
        if self._bg is None:
            return

        _surf = pygame.display.get_surface()
        screen_w = _surf.get_width() if _surf else Settings.WINDOW_WIDTH
        screen_h = _surf.get_height() if _surf else Settings.WINDOW_HEIGHT

        # --- Chest panel ---
        bg_w, bg_h = self._bg.get_size()
        self._bg_rect = self._bg.get_rect(midtop=(screen_w // 2, 10))

        left, top, right, bottom = _TITLE_ZONE_REL
        self._title_rect = pygame.Rect(
            self._bg_rect.left + int(left * bg_w),
            self._bg_rect.top + int(top * bg_h),
            int((right - left) * bg_w),
            int((bottom - top) * bg_h),
        )

        left, top, right, bottom = _CONTENT_ZONE_REL
        self._content_rect = pygame.Rect(
            self._bg_rect.left + int(left * bg_w),
            self._bg_rect.top + int(top * bg_h),
            int((right - left) * bg_w),
            int((bottom - top) * bg_h),
        )

        # Slot dimensions (mirror InventoryUI scale)
        _INV_SCALE = 1200 / 1344
        _SLOT_ORIG_PX = 55
        _STEP_ORIG_PX = 72
        slot_size = int(_SLOT_ORIG_PX * _INV_SCALE)
        step = int(_STEP_ORIG_PX * _INV_SCALE)

        # Scale slot & hover images (use already-loaded attribute — no disk I/O)
        if self._slot_img is not None:
            self._slot_img = pygame.transform.smoothscale(self._slot_img, (slot_size, slot_size))
        try:
            raw = pygame.image.load(ASSET_SLOT_HOVER).convert_alpha()
            self._hover_img = pygame.transform.smoothscale(raw, (slot_size, slot_size))
        except Exception as e:
            logging.warning(f"ChestUI hover image load failed: {e}")
            self._hover_img = None

        # Chest grid
        grid_w = step * (_SLOT_COLS - 1) + slot_size
        grid_h = step * (_SLOT_ROWS - 1) + slot_size
        origin_x = self._content_rect.left + (self._content_rect.width - grid_w) // 2
        origin_y = (
            self._content_rect.top + (self._content_rect.height - grid_h) // 2 + _GRID_OFFSET_Y
        )

        self._slot_positions.clear()
        for row in range(_SLOT_ROWS):
            for col in range(_SLOT_COLS):
                cx = origin_x + col * step + slot_size // 2
                cy = origin_y + row * step + slot_size // 2
                rect = pygame.Rect(0, 0, slot_size, slot_size)
                rect.center = (cx, cy)
                self._slot_positions.append(rect)

        # Chest arrow zones
        chest_scale = _TARGET_WIDTH / 1200

        def _chest_zone(rel):
            left, t, r, b = rel
            assert self._bg_rect is not None
            return pygame.Rect(
                self._bg_rect.left + int(left * bg_w) + _ARROW_OFFSET_X,
                self._bg_rect.top + int(t * bg_h) + _ARROW_OFFSET_Y,
                int((r - left) * bg_w),
                int((b - t) * bg_h),
            )

        self._arrow_up_rect = _chest_zone(_ARROW_UP_ZONE_REL)
        self._arrow_down_rect = _chest_zone(_ARROW_DOWN_ZONE_REL)

        # Scale chest arrow hover images
        self._arrow_down_hover_img = self._load_and_scale_arrow(ASSET_ARROW_DOWN_HOVER, chest_scale)
        self._arrow_up_hover_img = self._load_and_scale_arrow(ASSET_ARROW_UP_HOVER, chest_scale)

        # --- Player inventory panel ---
        self._compute_inv_layout(slot_size, step, screen_w, screen_h, chest_scale)

        self._layout_computed = True

    def _compute_inv_layout(
        self: "ChestUIProtocol",
        slot_size: int,
        step: int,
        screen_w: int,
        screen_h: int,
        arrow_scale: float,
    ) -> None:
        """Compute the player inventory panel rects and slot positions."""
        if self._inv_bg is None:
            return

        inv_w, inv_h = self._inv_bg.get_size()
        self._inv_bg_rect = self._inv_bg.get_rect(midbottom=(screen_w // 2, screen_h))

        left, top, right, bottom = _INV_CONTENT_ZONE_REL
        content_rect = pygame.Rect(
            self._inv_bg_rect.left + int(left * inv_w) + _INV_ARROW_ZONE_W,
            self._inv_bg_rect.top + int(top * inv_h),
            int((right - left) * inv_w) - 2 * _INV_ARROW_ZONE_W,
            int((bottom - top) * inv_h),
        )

        grid_w = step * (_INV_SLOT_COLS - 1) + slot_size
        grid_h = step * (_INV_SLOT_ROWS - 1) + slot_size
        origin_x = content_rect.left + (content_rect.width - grid_w) // 2 + _INV_GRID_OFFSET_X
        origin_y = content_rect.top + (content_rect.height - grid_h) // 2 + _INV_GRID_OFFSET_Y

        self._inv_slot_positions.clear()
        for row in range(_INV_SLOT_ROWS):
            for col in range(_INV_SLOT_COLS):
                cx = origin_x + col * step + slot_size // 2
                cy = origin_y + row * step + slot_size // 2
                rect = pygame.Rect(0, 0, slot_size, slot_size)
                rect.center = (cx, cy)
                self._inv_slot_positions.append(rect)

        # Arrow zones — aligned to the vertical centre of the slot row
        # Use actual slot grid centre so arrows follow _INV_GRID_OFFSET_Y
        slot_center_y = origin_y + slot_size // 2
        self._inv_arrow_left_rect = pygame.Rect(
            self._inv_bg_rect.left + _INV_ARROW_EDGE_OFFSET,
            slot_center_y - _INV_ARROW_ZONE_W // 2,
            _INV_ARROW_ZONE_W,
            _INV_ARROW_ZONE_W,
        )
        self._inv_arrow_right_rect = pygame.Rect(
            self._inv_bg_rect.right - _INV_ARROW_EDGE_OFFSET - _INV_ARROW_ZONE_W,
            slot_center_y - _INV_ARROW_ZONE_W // 2,
            _INV_ARROW_ZONE_W,
            _INV_ARROW_ZONE_W,
        )

        # Scale inventory arrow hover images
        self._arrow_left_hover_img = self._load_and_scale_arrow(ASSET_ARROW_LEFT_HOVER, arrow_scale)
        self._arrow_right_hover_img = self._load_and_scale_arrow(
            ASSET_ARROW_RIGHT_HOVER, arrow_scale
        )
