# src/ui/chest.py
"""Chest UI overlay implementation.
Implements the UI that appears when a chest is opened, showing:
- Top panel: chest contents (07-chest.png, 900px centered)
- Bottom panel: player inventory (12-inventory.png, full-screen width)
"""

import os
import math
import logging
import pygame
from src.config import Settings

# ---------------------------------------------------------------------------
# Asset paths (relative to project root)
# ---------------------------------------------------------------------------
ASSET_CHEST_BG       = os.path.join("assets", "images", "HUD", "07-chest.png")
ASSET_INV_BG         = os.path.join("assets", "images", "HUD", "12-inventory.png")
ASSET_SLOT_IMG       = os.path.join("assets", "images", "ui", "03-inventory_slot.png")
ASSET_SLOT_HOVER     = os.path.join("assets", "images", "ui", "04-inventory_slot_hover.png")
ASSET_POINTER        = os.path.join("assets", "images", "ui", "05-pointer.png")
ASSET_POINTER_SELECT = os.path.join("assets", "images", "ui", "06-pointer_select.png")
ASSET_ARROW_DOWN_HOVER  = os.path.join("assets", "images", "HUD", "08-arrow_down.png")
ASSET_ARROW_UP_HOVER    = os.path.join("assets", "images", "HUD", "09-arrow_up.png")
ASSET_ARROW_LEFT_HOVER  = os.path.join("assets", "images", "HUD", "10-arrow_left.png")
ASSET_ARROW_RIGHT_HOVER = os.path.join("assets", "images", "HUD", "11-arrow_right.png")

# ---------------------------------------------------------------------------
# Chest panel layout constants
# ---------------------------------------------------------------------------
_TITLE_ZONE_REL   = (0.29, 0.02, 0.71, 0.23)
_CONTENT_ZONE_REL = (0.11, 0.27, 0.89, 0.93)
_SLOT_COLS        = 10
_SLOT_ROWS        = 2
_GRID_OFFSET_Y    = -23
_TITLE_OFFSET_X   = 10
_TITLE_OFFSET_Y   = 8
_TARGET_WIDTH     = 900

# Arrow button zones (measured from 1200px source)
_ARROW_UP_ZONE_REL   = (0.7233, 0.8294, 0.7625, 0.9500)
_ARROW_DOWN_ZONE_REL = (0.7942, 0.8294, 0.8333, 0.9500)
_ARROW_OFFSET_X = 1
_ARROW_OFFSET_Y = 1

# ---------------------------------------------------------------------------
# Player inventory panel layout constants
# ---------------------------------------------------------------------------
_INV_TARGET_WIDTH     = 1280          # Full screen width
_INV_SLOT_COLS        = 18            # Slots visible at once
_INV_SLOT_ROWS        = 1
_INV_SLOTS_VISIBLE    = _INV_SLOT_COLS * _INV_SLOT_ROWS   # 18
_INV_CONTENT_ZONE_REL = (0.05, 0.05, 0.95, 0.95)
_INV_GRID_OFFSET_X    = 0             # Fine-tune escape hatch
_INV_GRID_OFFSET_Y    = 15            # Fine-tune escape hatch
_INV_ARROW_ZONE_W     = 60            # px — hit zone size for left/right arrows
_INV_ARROW_EDGE_OFFSET = 20           # px — inset from the panel edge


class ChestUI:
    """Public interface for the chest overlay.

    Displays two panels simultaneously:
    - Top: chest contents with up/down navigation.
    - Bottom: player inventory (full-width) with left/right pagination.

    The UI is non-blocking: the world update continues so the auto-close
    logic can fire when the player leaves the interaction zone.
    """

    def __init__(self) -> None:
        self.is_open: bool = False
        self._chest_entity = None
        self._player = None

        # Chest panel assets
        self._bg: pygame.Surface | None = self._load_background()
        self._slot_img: pygame.Surface | None = self._load_slot_image()
        self._hover_img: pygame.Surface | None = None   # scaled in _compute_layout

        # Inventory panel assets
        self._inv_bg: pygame.Surface | None = self._load_inv_background()

        # Arrow hover images (loaded in _compute_layout after scale is known)
        self._arrow_down_hover_img: pygame.Surface | None = None
        self._arrow_up_hover_img: pygame.Surface | None = None
        self._arrow_left_hover_img: pygame.Surface | None = None
        self._arrow_right_hover_img: pygame.Surface | None = None

        # Custom cursor
        self._pointer_img: pygame.Surface | None = self._load_cursor(ASSET_POINTER)
        self._pointer_select_img: pygame.Surface | None = self._load_cursor(ASSET_POINTER_SELECT)

        # Item icon cache (shared across frames)
        self._icon_cache: dict[str, pygame.Surface | None] = {}
        # Quantity badge font (tech font, lazy-init to match InventoryUI)
        self._qty_font: pygame.font.Font | None = None

        # --- Computed layout (filled in _compute_layout) ---
        self._bg_rect: pygame.Rect | None = None
        self._title_rect: pygame.Rect | None = None
        self._content_rect: pygame.Rect | None = None
        self._slot_positions: list[pygame.Rect] = []       # chest slots
        self._arrow_up_rect: pygame.Rect | None = None
        self._arrow_down_rect: pygame.Rect | None = None

        self._inv_bg_rect: pygame.Rect | None = None
        self._inv_slot_positions: list[pygame.Rect] = []   # player inv slots (current page)
        self._inv_arrow_left_rect: pygame.Rect | None = None
        self._inv_arrow_right_rect: pygame.Rect | None = None

        # --- Hover state ---
        self._hovered_chest_slot: int | None = None
        self._hovered_chest_arrow: str | None = None   # "up" | "down"
        self._hovered_inv_slot: int | None = None
        self._hovered_inv_arrow: str | None = None     # "left" | "right"

        # --- Scroll offset (index of first visible inv slot) ---
        self._inv_offset: int = 0

        self._layout_computed: bool = False

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def open(self, entity, player) -> None:
        """Open the UI for *entity* (chest) and *player*."""
        self.is_open = True
        self._chest_entity = entity
        self._player = player
        self._inv_offset = 0
        self._compute_layout()

    def close(self) -> None:
        """Close the UI and reset all state."""
        self.is_open = False
        self._chest_entity = None
        self._player = None
        self._layout_computed = False
        self._slot_positions.clear()
        self._inv_slot_positions.clear()
        self._hovered_chest_slot = None
        self._hovered_chest_arrow = None
        self._hovered_inv_slot = None
        self._hovered_inv_arrow = None
        self._inv_offset = 0

    def draw(self, screen: pygame.Surface) -> None:
        """Render both panels onto *screen* if the UI is open."""
        if not self.is_open:
            return
        if self._bg is None or self._bg_rect is None:
            return

        # --- Chest panel ---
        screen.blit(self._bg, self._bg_rect)
        self._draw_title(screen)
        self._draw_slots(screen)
        self._draw_arrow_hovers(screen)

        # --- Inventory panel ---
        if self._inv_bg is not None and self._inv_bg_rect is not None:
            screen.blit(self._inv_bg, self._inv_bg_rect)
            self._draw_inv_slots(screen)
            self._draw_inv_arrows(screen)

        # Update hover (after drawing so cursor is on top)
        self.update_hover(pygame.mouse.get_pos())

        # Custom cursor always on top
        self._draw_cursor(screen)

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Detect which element is under the mouse cursor."""
        self._hovered_chest_slot = None
        self._hovered_chest_arrow = None
        self._hovered_inv_slot = None
        self._hovered_inv_arrow = None

        # 1. Chest slots
        for i, rect in enumerate(self._slot_positions):
            if rect.collidepoint(mouse_pos):
                self._hovered_chest_slot = i
                return

        # 2. Chest arrow buttons
        if self._arrow_up_rect and self._arrow_up_rect.collidepoint(mouse_pos):
            self._hovered_chest_arrow = "up"
            return
        if self._arrow_down_rect and self._arrow_down_rect.collidepoint(mouse_pos):
            self._hovered_chest_arrow = "down"
            return

        # 3. Player inventory slots (only hit-test slots that are currently rendered)
        visible_count = min(_INV_SLOTS_VISIBLE, max(0, self._capacity() - self._inv_offset))
        for i, rect in enumerate(self._inv_slot_positions[:visible_count]):
            if rect.collidepoint(mouse_pos):
                self._hovered_inv_slot = i
                return

        # 4. Inventory arrow buttons (only if visible)
        # Left arrow: rewinds window — visible when there are items behind (offset > 0)
        if self._can_scroll_left() and self._inv_arrow_left_rect and self._inv_arrow_left_rect.collidepoint(mouse_pos):
            self._hovered_inv_arrow = "left"
            return
        # Right arrow: advances window — visible when more items exist ahead
        if self._can_scroll_right() and self._inv_arrow_right_rect and self._inv_arrow_right_rect.collidepoint(mouse_pos):
            self._hovered_inv_arrow = "right"

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a single pygame event for the chest UI."""
        if not self.is_open:
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos

        # Inventory scroll (page-based jumps)
        if self._can_scroll_right() and self._inv_arrow_right_rect and self._inv_arrow_right_rect.collidepoint(pos):
            self._scroll_right()
        elif self._can_scroll_left() and self._inv_arrow_left_rect and self._inv_arrow_left_rect.collidepoint(pos):
            self._scroll_left()

    # -----------------------------------------------------------------------
    # Private: asset loading
    # -----------------------------------------------------------------------

    def _load_background(self) -> pygame.Surface | None:
        """Load and scale the chest background image to _TARGET_WIDTH."""
        try:
            img = pygame.image.load(ASSET_CHEST_BG).convert_alpha()
            w, h = img.get_size()
            scale = _TARGET_WIDTH / w
            return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        except Exception as e:
            logging.error(f"ChestUI background load failed: {e}")
            return None

    def _load_inv_background(self) -> pygame.Surface | None:
        """Load and scale the inventory background image to _INV_TARGET_WIDTH."""
        try:
            img = pygame.image.load(ASSET_INV_BG).convert_alpha()
            w, h = img.get_size()
            scale = _INV_TARGET_WIDTH / w
            return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        except Exception as e:
            logging.error(f"ChestUI inventory background load failed: {e}")
            return None

    def _load_slot_image(self) -> pygame.Surface | None:
        """Load the slot placeholder image."""
        try:
            return pygame.image.load(ASSET_SLOT_IMG).convert_alpha()
        except Exception as e:
            logging.warning(f"ChestUI slot image load failed: {e}")
            return None

    def _load_cursor(self, path: str) -> pygame.Surface | None:
        """Load and scale a cursor image."""
        try:
            img = pygame.image.load(path).convert_alpha()
            size = Settings.CURSOR_SIZE
            w, h = img.get_size()
            ratio = min(size / w, size / h)
            return pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))
        except Exception as e:
            logging.warning(f"ChestUI cursor load failed ({path}): {e}")
            return None

    def _load_and_scale_arrow(self, path: str, scale: float) -> pygame.Surface | None:
        """Load an arrow icon and scale it by the given factor."""
        try:
            img = pygame.image.load(path).convert_alpha()
            w, h = img.get_size()
            return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        except Exception as e:
            logging.warning(f"ChestUI arrow hover load failed ({path}): {e}")
            return None

    def _get_item_icon(
        self, icon_filename: str, slot_size: int
    ) -> pygame.Surface | None:
        """Load, scale, and cache an item icon to *slot_size* px."""
        cache_key = f"{icon_filename}@{slot_size}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        path = os.path.join("assets", "images", "icons", icon_filename)
        if not path.endswith(".png"):
            path += ".png"

        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (slot_size, slot_size))
                self._icon_cache[cache_key] = img
                return img
        except Exception as e:
            logging.warning(f"ChestUI: Could not load icon {icon_filename}: {e}")

        self._icon_cache[cache_key] = None
        return None

    # -----------------------------------------------------------------------
    # Private: layout computation
    # -----------------------------------------------------------------------

    def _compute_layout(self) -> None:
        """Calculate all derived rectangles and slot positions.
        Called once per open(). Guarded against repeated calls.
        """
        if self._bg is None:
            return

        _surf = pygame.display.get_surface()
        screen_w = _surf.get_width()  if _surf else Settings.WINDOW_WIDTH
        screen_h = _surf.get_height() if _surf else Settings.WINDOW_HEIGHT

        # --- Chest panel ---
        bg_w, bg_h = self._bg.get_size()
        self._bg_rect = self._bg.get_rect(midtop=(screen_w // 2, 10))

        left, top, right, bottom = _TITLE_ZONE_REL
        self._title_rect = pygame.Rect(
            self._bg_rect.left + int(left * bg_w),
            self._bg_rect.top  + int(top  * bg_h),
            int((right - left) * bg_w),
            int((bottom - top) * bg_h),
        )

        left, top, right, bottom = _CONTENT_ZONE_REL
        self._content_rect = pygame.Rect(
            self._bg_rect.left + int(left * bg_w),
            self._bg_rect.top  + int(top  * bg_h),
            int((right - left) * bg_w),
            int((bottom - top) * bg_h),
        )

        # Slot dimensions (mirror InventoryUI scale)
        _INV_SCALE      = 1200 / 1344
        _SLOT_ORIG_PX   = 55
        _STEP_ORIG_PX   = 72
        slot_size = int(_SLOT_ORIG_PX * _INV_SCALE)
        step      = int(_STEP_ORIG_PX * _INV_SCALE)

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
        origin_x = self._content_rect.left + (self._content_rect.width  - grid_w) // 2
        origin_y = self._content_rect.top  + (self._content_rect.height - grid_h) // 2 + _GRID_OFFSET_Y

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
            l, t, r, b = rel
            return pygame.Rect(
                self._bg_rect.left + int(l * bg_w) + _ARROW_OFFSET_X,
                self._bg_rect.top  + int(t * bg_h) + _ARROW_OFFSET_Y,
                int((r - l) * bg_w),
                int((b - t) * bg_h),
            )
        self._arrow_up_rect   = _chest_zone(_ARROW_UP_ZONE_REL)
        self._arrow_down_rect = _chest_zone(_ARROW_DOWN_ZONE_REL)

        # Scale chest arrow hover images
        self._arrow_down_hover_img = self._load_and_scale_arrow(ASSET_ARROW_DOWN_HOVER, chest_scale)
        self._arrow_up_hover_img   = self._load_and_scale_arrow(ASSET_ARROW_UP_HOVER,   chest_scale)

        # --- Player inventory panel ---
        self._compute_inv_layout(slot_size, step, screen_w, screen_h, chest_scale)

        self._layout_computed = True

    def _compute_inv_layout(
        self,
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
            self._inv_bg_rect.top  + int(top  * inv_h),
            int((right - left) * inv_w) - 2 * _INV_ARROW_ZONE_W,
            int((bottom - top) * inv_h),
        )

        grid_w = step * (_INV_SLOT_COLS - 1) + slot_size
        grid_h = step * (_INV_SLOT_ROWS - 1) + slot_size
        origin_x = content_rect.left + (content_rect.width  - grid_w) // 2 + _INV_GRID_OFFSET_X
        origin_y = content_rect.top  + (content_rect.height - grid_h) // 2 + _INV_GRID_OFFSET_Y

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
        self._arrow_left_hover_img  = self._load_and_scale_arrow(ASSET_ARROW_LEFT_HOVER,  arrow_scale)
        self._arrow_right_hover_img = self._load_and_scale_arrow(ASSET_ARROW_RIGHT_HOVER, arrow_scale)

    # -----------------------------------------------------------------------
    # Private: scroll logic
    # -----------------------------------------------------------------------

    def _capacity(self) -> int:
        if self._player is None:
            return 0
        return self._player.inventory.capacity

    def _can_scroll_left(self) -> bool:
        return self._inv_offset > 0

    def _can_scroll_right(self) -> bool:
        return self._inv_offset + _INV_SLOTS_VISIBLE < self._capacity()

    def _scroll_right(self) -> None:
        if self._can_scroll_right():
            # Advance by a full page; clamp so we show at least 1 real slot
            self._inv_offset = min(
                self._inv_offset + _INV_SLOTS_VISIBLE,
                self._capacity() - 1,
            )


    def _scroll_left(self) -> None:
        if self._can_scroll_left():
            self._inv_offset = max(0, self._inv_offset - _INV_SLOTS_VISIBLE)

    def _current_page_slots(self) -> list:
        """Return the 18 visible player inventory slots starting at _inv_offset."""
        if self._player is None:
            return []
        start = self._inv_offset
        end   = start + _INV_SLOTS_VISIBLE
        return self._player.inventory.slots[start:end]

    # -----------------------------------------------------------------------
    # Private: chest content helpers
    # -----------------------------------------------------------------------

    def _get_chest_contents(self) -> list[dict]:
        """Return the contents list from the chest entity, or empty list."""
        if self._chest_entity is None:
            return []
        return getattr(self._chest_entity, "contents", [])

    def _resolve_icon_name(self, item_id: str) -> str:
        """Resolve the icon filename for an item_id via propertytypes."""
        if self._player is None:
            return f"{item_id}.png"
        item_data = getattr(self._player, "inventory", None)
        if item_data is None:
            return f"{item_id}.png"
        tech_data = item_data.item_data.get(item_id, {})
        return tech_data.get("icon", f"{item_id}.png")

    # -----------------------------------------------------------------------
    # Private: drawing
    # -----------------------------------------------------------------------

    def _draw_title(self, screen: pygame.Surface) -> None:
        """Render the chest name centred in the title zone."""
        if self._title_rect is None:
            return
        font = pygame.font.Font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        surf = font.render("Coffre", True, (60, 40, 30))
        cx = self._title_rect.centerx + _TITLE_OFFSET_X
        cy = self._title_rect.centery + _TITLE_OFFSET_Y
        screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _draw_slots(self, screen: pygame.Surface) -> None:
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
            item_id = entry.get("item_id", "")
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

    def _draw_arrow_hovers(self, screen: pygame.Surface) -> None:
        """Render chest arrow hover overlays (RED→down, BLUE→up)."""
        if self._hovered_chest_arrow == "up" and self._arrow_up_rect and self._arrow_down_hover_img:
            rect = self._arrow_down_hover_img.get_rect(center=self._arrow_up_rect.center)
            screen.blit(self._arrow_down_hover_img, rect)
        elif self._hovered_chest_arrow == "down" and self._arrow_down_rect and self._arrow_up_hover_img:
            rect = self._arrow_up_hover_img.get_rect(center=self._arrow_down_rect.center)
            screen.blit(self._arrow_up_hover_img, rect)

    def _draw_inv_slots(self, screen: pygame.Surface) -> None:
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

            item = page_items[i]
            icon_name = item.icon if hasattr(item, "icon") and item.icon else f"{item.id}.png"
            icon = self._get_item_icon(icon_name, icon_size)
            if icon:
                icon_rect = icon.get_rect(center=rect.center)
                screen.blit(icon, icon_rect)

            qty = getattr(item, "quantity", 1)
            if qty > 1:
                qty_surf = self._qty_font.render(f"x{qty}", True, (60, 40, 30))
                qty_rect = qty_surf.get_rect(bottomright=(rect.right - margin, rect.bottom - margin))
                screen.blit(qty_surf, qty_rect)

        # Hover overlay (guard against hovering a now-hidden slot)
        hov = self._hovered_inv_slot
        if hov is not None and hov < visible_count and self._hover_img:
            hover_rect = self._hover_img.get_rect(
                center=self._inv_slot_positions[hov].center
            )
            screen.blit(self._hover_img, hover_rect)

    def _draw_inv_arrows(self, screen: pygame.Surface) -> None:
        """Render left/right arrow hover overlays.
        Left arrow: rewinds window — visible when there are items behind (offset > 0).
        Right arrow: advances window — visible when more items exist ahead.
        """
        if (self._can_scroll_left()
                and self._hovered_inv_arrow == "left"
                and self._inv_arrow_left_rect
                and self._arrow_left_hover_img):
            rect = self._arrow_left_hover_img.get_rect(center=self._inv_arrow_left_rect.center)
            screen.blit(self._arrow_left_hover_img, rect)

        if (self._can_scroll_right()
                and self._hovered_inv_arrow == "right"
                and self._inv_arrow_right_rect
                and self._arrow_right_hover_img):
            rect = self._arrow_right_hover_img.get_rect(center=self._inv_arrow_right_rect.center)
            screen.blit(self._arrow_right_hover_img, rect)

    def _draw_cursor(self, screen: pygame.Surface) -> None:
        """Draw the glove cursor at mouse position (always on top)."""
        mouse_pos = pygame.mouse.get_pos()
        img = self._pointer_select_img if pygame.mouse.get_pressed()[0] else self._pointer_img
        if img:
            screen.blit(img, mouse_pos)
