# src/ui/chest.py
"""Chest UI overlay implementation.
Implements the UI that appears when a chest is opened.
Refactored to delegate layout, transfer, and rendering to mixins.
"""

import logging
import os

import pygame

from src.config import Settings
from src.ui.chest_constants import (
    _INV_SLOTS_VISIBLE,
    _INV_TARGET_WIDTH,
    _TARGET_WIDTH,
    ASSET_CHEST_BG,
    ASSET_INV_BG,
    ASSET_POINTER,
    ASSET_POINTER_SELECT,
    ASSET_SLOT_IMG,
)
from src.ui.chest_draw import ChestDrawMixin
from src.ui.chest_layout import ChestLayoutMixin
from src.ui.chest_transfer import ChestTransferMixin


class ChestUI(ChestLayoutMixin, ChestTransferMixin, ChestDrawMixin):
    """Public interface for the chest overlay."""

    def __init__(self) -> None:
        self.is_open: bool = False
        self._chest_entity = None
        self._player = None

        # Chest panel assets
        self._bg: pygame.Surface | None = self._load_background()
        self._slot_img: pygame.Surface | None = self._load_slot_image()
        self._hover_img: pygame.Surface | None = None  # scaled in _compute_layout

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
        self._slot_positions: list[pygame.Rect] = []  # chest slots
        self._arrow_up_rect: pygame.Rect | None = None
        self._arrow_down_rect: pygame.Rect | None = None

        self._inv_bg_rect: pygame.Rect | None = None
        self._inv_slot_positions: list[pygame.Rect] = []  # player inv slots (current page)
        self._inv_arrow_left_rect: pygame.Rect | None = None
        self._inv_arrow_right_rect: pygame.Rect | None = None

        # --- Hover state ---
        self._hovered_chest_slot: int | None = None
        self._hovered_chest_arrow: str | None = None  # "up" | "down"
        self._hovered_inv_slot: int | None = None
        self._hovered_inv_arrow: str | None = None  # "left" | "right"

        # --- Scroll offset (index of first visible inv slot) ---
        self._inv_offset: int = 0
        self._layout_computed: bool = False

        # --- Drag & Drop state ---
        self._dragging_item: dict | None = (
            None  # {"item_id": str, "quantity": int, "source": str, "index": int, "icon": str}
        )
        self._drag_pos: tuple[int, int] = (0, 0)

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

        # Draw dragged item icon
        self._draw_dragged_item(screen)

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
        if (
            self._can_scroll_left()
            and self._inv_arrow_left_rect
            and self._inv_arrow_left_rect.collidepoint(mouse_pos)
        ):
            self._hovered_inv_arrow = "left"
            return
        if (
            self._can_scroll_right()
            and self._inv_arrow_right_rect
            and self._inv_arrow_right_rect.collidepoint(mouse_pos)
        ):
            self._hovered_inv_arrow = "right"

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

    def _get_item_icon(self, icon_filename: str, slot_size: int) -> pygame.Surface | None:
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
            self._inv_offset = min(
                self._inv_offset + _INV_SLOTS_VISIBLE,
                self._capacity() - 1,
            )

    def _scroll_left(self) -> None:
        if self._can_scroll_left():
            self._inv_offset = max(0, self._inv_offset - _INV_SLOTS_VISIBLE)

    def _current_page_slots(self) -> list:
        """Return the visible player inventory slots starting at _inv_offset."""
        if self._player is None:
            return []
        start = self._inv_offset
        end = start + _INV_SLOTS_VISIBLE
        return self._player.inventory.slots[start:end]

    # -----------------------------------------------------------------------
    # Private: chest content helpers
    # -----------------------------------------------------------------------

    def _get_chest_contents(self) -> list[dict]:
        """Return the contents list from the chest entity, padded to CHEST_MAX_SLOTS."""
        if self._chest_entity is None:
            return []
        contents = getattr(self._chest_entity, "contents", [])

        from src.engine.loot_table import CHEST_MAX_SLOTS

        while len(contents) < CHEST_MAX_SLOTS:
            contents.append(None)

        return contents

    def _resolve_icon_name(self, item_id: str) -> str:
        """Resolve the icon filename for an item_id via propertytypes."""
        if self._player is None:
            return f"{item_id}.png"
        item_data = getattr(self._player, "inventory", None)
        if item_data is None:
            return f"{item_id}.png"
        tech_data = item_data.item_data.get(item_id, {})
        return tech_data.get("icon", f"{item_id}.png")
