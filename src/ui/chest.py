# src/ui/chest.py
"""Chest UI overlay implementation.
Implements the UI that appears when a chest is opened, showing a background
image (07-chest.png) with a title zone and a grid of slot placeholders.
"""

import os
import logging
import pygame
from src.config import Settings

# Asset paths (relative to project root)
ASSET_CHEST_BG = os.path.join("assets", "images", "HUD", "07-chest.png")
ASSET_SLOT_IMG = os.path.join("assets", "images", "ui", "03-inventory_slot.png")
ASSET_SLOT_HOVER = os.path.join("assets", "images", "ui", "04-inventory_slot_hover.png")
ASSET_POINTER = os.path.join("assets", "images", "ui", "05-pointer.png")
ASSET_POINTER_SELECT = os.path.join("assets", "images", "ui", "06-pointer_select.png")
ASSET_ARROW_DOWN_HOVER = os.path.join("assets", "images", "HUD", "08-arrow_down.png")
ASSET_ARROW_UP_HOVER = os.path.join("assets", "images", "HUD", "09-arrow_up.png")

# Layout constants (relative fractions of the background image)
_TITLE_ZONE_REL = (0.29, 0.02, 0.71, 0.23)  # left%, top%, right%, bottom%
_CONTENT_ZONE_REL = (0.11, 0.27, 0.89, 0.93)
_SLOT_COLS = 10
_SLOT_ROWS = 2
_GRID_OFFSET_Y = -23   # px shift applied to the whole grid (negative = up)
_TITLE_OFFSET_X = 10   # px shift applied to the title text (negative = left)
_TITLE_OFFSET_Y = 8  # px shift applied to the title text (negative = up)
_TARGET_WIDTH = 900   # pixels – scaled width of the background
# Arrow button zones (measured from 1200x340 source image, auto-scaled)
_ARROW_UP_ZONE_REL   = (0.7233, 0.8294, 0.7625, 0.9500)  # red zone → up arrow
_ARROW_DOWN_ZONE_REL = (0.7942, 0.8294, 0.8333, 0.9500)  # blue zone → down arrow
_ARROW_OFFSET_X = 0  # px fine-tune horizontal (escape hatch)
_ARROW_OFFSET_Y = 0  # px fine-tune vertical   (escape hatch)

class ChestUI:
    """Public interface for the chest overlay.

    The UI is *non‑blocking*: world updates are paused while the UI is open, but
    the player can still move so that the auto‑close logic can trigger when the
    player leaves the interaction zone.
    """

    def __init__(self) -> None:
        self.is_open: bool = False
        self._chest_entity = None
        self._bg: pygame.Surface | None = self._load_background()
        self._slot_img: pygame.Surface | None = self._load_slot_image()
        self._layout_computed: bool = False
        # Cached rects after scaling – filled in _compute_layout()
        self._bg_rect: pygame.Rect | None = None
        self._title_rect: pygame.Rect | None = None
        self._content_rect: pygame.Rect | None = None
        self._slot_positions: list[pygame.Rect] = []
        self._hovered_slot: int | None = None   # index into _slot_positions
        # Arrow button rects (absolute screen coordinates, filled in _compute_layout)
        self._arrow_up_rect: pygame.Rect | None = None
        self._arrow_down_rect: pygame.Rect | None = None
        # Custom pointer — same assets as InventoryUI
        self._pointer_img: pygame.Surface | None = self._load_cursor(ASSET_POINTER)
        self._pointer_select_img: pygame.Surface | None = self._load_cursor(ASSET_POINTER_SELECT)
        self._hover_img: pygame.Surface | None = None  # scaled in _compute_layout
        # Arrow hover images
        self._arrow_up_hover_img: pygame.Surface | None = None
        self._arrow_down_hover_img: pygame.Surface | None = None
        self._hovered_arrow: str | None = None  # "up" or "down"

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def open(self, entity) -> None:
        """Open the UI for *entity* (the interactive chest)."""
        self.is_open = True
        self._chest_entity = entity
        self._compute_layout()

    def close(self) -> None:
        """Close the UI and reset state."""
        self.is_open = False
        self._chest_entity = None
        self._layout_computed = False
        self._slot_positions.clear()
        self._hovered_slot = None
        self._hovered_arrow = None

    def draw(self, screen: pygame.Surface) -> None:
        """Render the UI onto *screen* if it is open."""
        if not self.is_open or self._bg is None:
            return
        # Background
        if self._bg_rect is None:
            return
        screen.blit(self._bg, self._bg_rect)
        # Update hover from current mouse position
        self.update_hover(pygame.mouse.get_pos())
        # Arrow hover overlays
        self._draw_arrow_hovers(screen)
        # Title – hard‑coded "coffre" for v1
        self._draw_title(screen)
        # Slots grid
        self._draw_slots(screen)
        # Custom cursor (always on top — drawn last)
        self._draw_cursor(screen)
    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Detect which slot or arrow index is under the mouse cursor."""
        self._hovered_slot = None
        self._hovered_arrow = None

        # Check slots
        for i, rect in enumerate(self._slot_positions):
            if rect.collidepoint(mouse_pos):
                self._hovered_slot = i
                return

        # Check arrow buttons
        if self._arrow_up_rect and self._arrow_up_rect.collidepoint(mouse_pos):
            self._hovered_arrow = "up"
        elif self._arrow_down_rect and self._arrow_down_rect.collidepoint(mouse_pos):
            self._hovered_arrow = "down"


    def _load_background(self) -> pygame.Surface | None:
        """Load and scale the chest background image.
        Returns *None* on error and logs the incident.
        """
        try:
            img = pygame.image.load(ASSET_CHEST_BG).convert_alpha()
            # Scale proportionally to target width
            w, h = img.get_size()
            scale = _TARGET_WIDTH / w
            new_size = (int(w * scale), int(h * scale))
            return pygame.transform.smoothscale(img, new_size)
        except Exception as e:
            logging.error(f"ChestUI background load failed: {e}")
            return None

    def _load_slot_image(self) -> pygame.Surface | None:
        """Load the slot placeholder image used for each chest slot.
        Returns *None* on error and logs a warning.
        """
        try:
            img = pygame.image.load(ASSET_SLOT_IMG).convert_alpha()
            return img
        except Exception as e:
            logging.warning(f"ChestUI slot image load failed: {e}")
            return None

    def _compute_layout(self) -> None:
        """Calculate all derived rectangles and slot positions.
        Called when the UI is opened. Guarded against repeated calls.
        """
        if self._bg is None:
            return
        # Position the background centred horizontally, 10 px from top
        screen_w = Settings.WINDOW_WIDTH
        bg_w, bg_h = self._bg.get_size()
        self._bg_rect = self._bg.get_rect(midtop=(screen_w // 2, 10))
        # Derive title and content zones from relative fractions
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
        # Slot size and spacing – mirror InventoryUI exactly
        # InventoryUI uses scale_factor = 1200/1344 on original px values
        _INVENTORY_SCALE = 1200 / 1344
        _SLOT_ORIGINAL_PX = 55   # original slot image width/height in px
        _SPACING_ORIGINAL_PX = 72  # original centre-to-centre spacing in inventory grid
        slot_size = int(_SLOT_ORIGINAL_PX * _INVENTORY_SCALE)   # ≈ 49 px
        step = int(_SPACING_ORIGINAL_PX * _INVENTORY_SCALE)     # ≈ 64 px

        # Scale the slot image once to the exact size
        if self._slot_img is not None:
            self._slot_img = pygame.transform.smoothscale(
                self._load_slot_image(), (slot_size, slot_size)
            )
        # Scale hover image to same size
        try:
            raw_hover = pygame.image.load(ASSET_SLOT_HOVER).convert_alpha()
            self._hover_img = pygame.transform.smoothscale(raw_hover, (slot_size, slot_size))
        except Exception as e:
            logging.warning(f"ChestUI hover image load failed: {e}")
            self._hover_img = None

        # Total grid dimensions using step (centre-to-centre)
        grid_w = step * (_SLOT_COLS - 1) + slot_size
        grid_h = step * (_SLOT_ROWS - 1) + slot_size

        # Centre the grid inside the content rect, with optional vertical offset
        origin_x = self._content_rect.left + (self._content_rect.width - grid_w) // 2
        origin_y = self._content_rect.top + (self._content_rect.height - grid_h) // 2 + _GRID_OFFSET_Y

        self._slot_positions.clear()
        for row in range(_SLOT_ROWS):
            for col in range(_SLOT_COLS):
                cx = origin_x + col * step + slot_size // 2
                cy = origin_y + row * step + slot_size // 2
                rect = pygame.Rect(0, 0, slot_size, slot_size)
                rect.center = (cx, cy)
                self._slot_positions.append(rect)

        # Compute arrow button rects (zones measured from source image)
        def _zone_rect(rel: tuple[float, float, float, float]) -> pygame.Rect:
            l, t, r, b = rel
            return pygame.Rect(
                self._bg_rect.left + int(l * bg_w) + _ARROW_OFFSET_X,
                self._bg_rect.top  + int(t * bg_h) + _ARROW_OFFSET_Y,
                int((r - l) * bg_w),
                int((b - t) * bg_h),
            )
        self._arrow_up_rect   = _zone_rect(_ARROW_UP_ZONE_REL)
        self._arrow_down_rect = _zone_rect(_ARROW_DOWN_ZONE_REL)

        # Scale arrow hover images to fit their respective rects
        def _load_and_scale_arrow(path: str, rect: pygame.Rect) -> pygame.Surface | None:
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.smoothscale(img, (rect.width, rect.height))
            except Exception as e:
                logging.warning(f"ChestUI arrow hover image load failed ({path}): {e}")
                return None

        if self._arrow_up_rect and self._arrow_down_rect:
            # Note: RED zone (up_rect) -> 08-arrow_down | BLUE zone (down_rect) -> 09-arrow_up
            self._arrow_down_hover_img = _load_and_scale_arrow(ASSET_ARROW_DOWN_HOVER, self._arrow_up_rect)
            self._arrow_up_hover_img = _load_and_scale_arrow(ASSET_ARROW_UP_HOVER, self._arrow_down_rect)

        self._layout_computed = True

    def _draw_title(self, screen: pygame.Surface) -> None:
        """Render the title "coffre" centred in the red zone."""
        if self._title_rect is None:
            return
        font = pygame.font.Font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        surf = font.render("Coffre", True, (60, 40, 30))
        cx = self._title_rect.centerx + _TITLE_OFFSET_X
        cy = self._title_rect.centery + _TITLE_OFFSET_Y
        rect = surf.get_rect(center=(cx, cy))
        screen.blit(surf, rect)

    def _draw_slots(self, screen: pygame.Surface) -> None:
        """Render each slot placeholder inside the green content zone."""
        if not self._slot_positions:
            return
        for i, rect in enumerate(self._slot_positions):
            if self._slot_img:
                screen.blit(self._slot_img, rect)
            else:
                pygame.draw.rect(screen, (200, 200, 200), rect, 2)

        # Hover overlay — drawn after all slots so it appears on top
        if self._hovered_slot is not None and self._hover_img:
            hover_rect = self._hover_img.get_rect(center=self._slot_positions[self._hovered_slot].center)
            screen.blit(self._hover_img, hover_rect)

    def _draw_arrow_hovers(self, screen: pygame.Surface) -> None:
        """Render the arrow hover images if hovering over the red/blue zones.
        RED zone (up_rect) shows arrow_down, BLUE zone (down_rect) shows arrow_up.
        """
        # RED zone (up_rect) -> 08-arrow_down
        if self._hovered_arrow == "up" and self._arrow_up_rect and self._arrow_down_hover_img:
            screen.blit(self._arrow_down_hover_img, self._arrow_up_rect)
        # BLUE zone (down_rect) -> 09-arrow_up
        elif self._hovered_arrow == "down" and self._arrow_down_rect and self._arrow_up_hover_img:
            screen.blit(self._arrow_up_hover_img, self._arrow_down_rect)

    def _load_cursor(self, path: str) -> pygame.Surface | None:
        """Load and scale a cursor image to Settings.CURSOR_SIZE."""
        try:
            img = pygame.image.load(path).convert_alpha()
            size = Settings.CURSOR_SIZE
            w, h = img.get_size()
            # Preserve aspect ratio
            ratio = min(size / w, size / h)
            scaled = pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))
            return scaled
        except Exception as e:
            logging.warning(f"ChestUI cursor load failed ({path}): {e}")
            return None

    def _draw_cursor(self, screen: pygame.Surface) -> None:
        """Draw the glove cursor at mouse position (always on top)."""
        mouse_pos = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            img = self._pointer_select_img
        else:
            img = self._pointer_img
        if img:
            screen.blit(img, mouse_pos)
