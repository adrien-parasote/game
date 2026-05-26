# src/ui/chest.py
"""Chest UI overlay implementation.
Implements the UI that appears when a chest is opened.
Refactored to delegate layout, transfer, and rendering to mixins.
"""


import pygame

from src.ui.chest_constants import (
    _INV_SLOTS_VISIBLE,
    ASSET_POINTER,
    ASSET_POINTER_SELECT,
)
from src.ui.chest_draw import ChestDrawMixin
from src.ui.chest_input import ChestInputMixin
from src.ui.chest_layout import ChestLayoutMixin
from src.ui.chest_transfer import ChestTransferMixin


class ChestUI(ChestLayoutMixin, ChestTransferMixin, ChestDrawMixin, ChestInputMixin):
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
        # Title font (lazy-init in ChestDrawMixin._draw_title — created once, never per frame)
        self._title_font: pygame.font.Font | None = None
        # Pre-rendered title surface (CHEST_TITLE_TEXT is static — rendered once)
        self._title_surf: pygame.Surface | None = None
        # Quantity badge cache: qty int → Surface
        self._qty_cache: dict[int, pygame.Surface] = {}

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
