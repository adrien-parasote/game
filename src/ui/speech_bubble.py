# src/ui/speech_bubble.py
"""Speech bubble rendering using nine-patch PNG tiles.

The bubble is built from 32×32 tiles located in `assets/images/HUD/`:
13-21 (bottom/right/top/… corners) and 22 for pagination arrow.
The tail (queue) is tile 21-bubble_queue.png.
"""

import os
from collections.abc import Callable

import pygame

from src.ui.speech_bubble_constants import (
    _ARROW_OFFSET_X,
    _ARROW_OFFSET_Y,
    _NAME_PLATE_OFFSET_X,
    _NAME_PLATE_OFFSET_Y,
    _PADDING_BOTTOM,
    _PADDING_TOP,
    _PADDING_X,
    _TAIL_GAP,
    ASSET_DIR,
    MIN_BUBBLE_SIZE,
    TILE_SIZE,
    TILES,
)

# Type alias for the blit callable signature used by pygame.Surface.blit
BlitFunc = Callable[[pygame.Surface, tuple[int, int]], None]


class SpeechBubble:
    """Render a dialogue bubble above a character.

    Parameters
    ----------
    max_width_px:
        Maximum bubble width in pixels (default 224 px = 7 tiles).
    padding:
        Inner padding around the text in pixels (default 8).
    tail_gap:
        Vertical gap between the character head and the tail (default 4 px).
    arrow_inset:
        Inset for the pagination arrow from the bubble border (default 4 px).
    """

    def __init__(
        self,
        max_width_px: int = 352,
        arrow_inset: int = 4,
    ) -> None:
        self.max_width_px = max(max_width_px, MIN_BUBBLE_SIZE)
        self.pad_top = _PADDING_TOP
        self.pad_bottom = _PADDING_BOTTOM
        self.pad_x = _PADDING_X
        self.tail_gap = _TAIL_GAP
        self.arrow_inset = arrow_inset
        self.font: pygame.font.Font | None = None
        self.name_font: pygame.font.Font | None = None
        self._load_tiles()

    def _load_tiles(self) -> None:
        """Load all PNG tiles and cache them as pygame.Surface objects."""
        self.tiles: dict = {}
        for key, filename in TILES.items():
            path = os.path.join(ASSET_DIR, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Bubble asset not found: {path}")
            img = pygame.image.load(path).convert_alpha()

            # Use default size for arrow as requested; scale others to TILE_SIZE
            if key == "arrow":
                self.tiles[key] = img
            elif key == "name_plate":
                self.tiles["name_plate_left"] = img.subsurface(pygame.Rect(0, 0, 32, 64))
                self.tiles["name_plate_center"] = img.subsurface(pygame.Rect(32, 0, 32, 64))
                self.tiles["name_plate_right"] = img.subsurface(pygame.Rect(64, 0, 32, 64))
            else:
                self.tiles[key] = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))

    def set_font(self, font: pygame.font.Font) -> None:
        """Assign the pygame font used for rendering text."""
        self.font = font

    def set_name_font(self, font: pygame.font.Font) -> None:
        """Assign the pygame font used for rendering the speaker name."""
        self.name_font = font

    def _wrap_text(self, text: str) -> list[str]:
        """Wrap *text* to fit within bubble width minus padding on each side."""
        if not self.font:
            raise RuntimeError("Font not set on SpeechBubble before drawing.")

        inner_max_width = self.max_width_px - (2 * self.pad_x)
        if inner_max_width <= 0:
            return [text]

        words = text.split(" ")
        lines: list[str] = []
        current: list[str] = []

        for word in words:
            candidate = " ".join(current + [word]) if current else word
            if self.font.size(candidate)[0] <= inner_max_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]

        if current:
            lines.append(" ".join(current))

        return lines

    def _build_background(self, bubble_w: int, bubble_h: int) -> pygame.Surface:
        """Assemble the nine-patch background. Fills carefully to avoid covering transparent corners."""
        bg = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)

        edge_w = bubble_w - 2 * TILE_SIZE
        edge_h = bubble_h - 2 * TILE_SIZE

        # Center fill
        if edge_w > 0 and edge_h > 0:
            bg.fill((255, 255, 255), pygame.Rect(TILE_SIZE, TILE_SIZE, edge_w, edge_h))

        # Top edge
        if edge_w > 0:
            top_edge = pygame.transform.scale(self.tiles["top"], (edge_w, TILE_SIZE))
            bg.blit(top_edge, (TILE_SIZE, 0))

        # Left edge
        if edge_h > 0:
            left_edge = pygame.transform.scale(self.tiles["left"], (TILE_SIZE, edge_h))
            bg.blit(left_edge, (0, TILE_SIZE))

        # Right edge
        if edge_h > 0:
            right_edge = pygame.transform.scale(self.tiles["right"], (TILE_SIZE, edge_h))
            bg.blit(right_edge, (bubble_w - TILE_SIZE, TILE_SIZE))

        # Bottom row (queue and gaps)
        queue = self.tiles["queue"]
        queue_x = (bubble_w - TILE_SIZE) // 2
        queue_y = bubble_h - TILE_SIZE

        left_gap_w = queue_x - TILE_SIZE
        if left_gap_w > 0:
            left_bot = pygame.transform.scale(self.tiles["bottom"], (left_gap_w, TILE_SIZE))
            bg.blit(left_bot, (TILE_SIZE, queue_y))

        right_gap_x = queue_x + TILE_SIZE
        right_gap_w = (bubble_w - TILE_SIZE) - right_gap_x
        if right_gap_w > 0:
            right_bot = pygame.transform.scale(self.tiles["bottom"], (right_gap_w, TILE_SIZE))
            bg.blit(right_bot, (right_gap_x, queue_y))

        # Queue doesn't get a white background fill because it's transparent around the tail
        bg.blit(queue, (queue_x, queue_y))

        # Corners (drawn last)
        bg.blit(self.tiles["top_left"], (0, 0))
        bg.blit(self.tiles["top_right"], (bubble_w - TILE_SIZE, 0))
        bg.blit(self.tiles["bottom_left"], (0, queue_y))
        bg.blit(self.tiles["bottom_right"], (bubble_w - TILE_SIZE, queue_y))

        return bg

    def draw(
        self,
        surface: pygame.Surface,
        char_rect: pygame.Rect,
        text: str,
        page: int = 0,
        speaker_name: str | None = None,
        blit_func: BlitFunc | None = None,
    ) -> None:
        """Draw the speech bubble anchored to char_rect."""
        assert self.font is not None
        blit: BlitFunc = blit_func if blit_func is not None else surface.blit  # type: ignore

        # 1. Wrap and paginate
        all_lines = self._wrap_text(text)
        line_height = self.font.get_linesize()

        # Limit to 4 lines per page for typical speech bubble size
        lines_per_page = 4
        total_pages = max(1, (len(all_lines) + lines_per_page - 1) // lines_per_page)
        page = max(0, min(page, total_pages - 1))
        page_lines = all_lines[page * lines_per_page : (page + 1) * lines_per_page]

        # 2. Dimensions: text_w + 2*pad_x for width; +TILE_SIZE for bottom border row
        text_w = max((self.font.size(line)[0] for line in page_lines), default=0)
        text_h = len(page_lines) * line_height

        bubble_w = max(MIN_BUBBLE_SIZE, text_w + 2 * self.pad_x)
        bubble_w = min(self.max_width_px, bubble_w)
        bubble_h = max(
            MIN_BUBBLE_SIZE + TILE_SIZE, text_h + self.pad_top + self.pad_bottom + TILE_SIZE
        )

        # 3. Background
        bg = self._build_background(bubble_w, bubble_h)

        # 4. Text rendered at (pad_x, pad_top) — full bubble width minus padding
        inner_y = self.pad_top
        for line in page_lines:
            txt_surf = self.font.render(line, True, (60, 40, 30))
            bg.blit(txt_surf, (self.pad_x, inner_y))
            inner_y += line_height

        # 5. Pagination arrow: INSIDE the top-left corner of the bottom-right tile, with manual offset
        if total_pages > 1:
            arrow = self.tiles["arrow"]
            arrow_x = bubble_w - TILE_SIZE + _ARROW_OFFSET_X
            arrow_y = bubble_h - TILE_SIZE + _ARROW_OFFSET_Y
            bg.blit(arrow, (arrow_x, arrow_y))

        # 6. Build the name plate if speaker_name is provided
        name_plate_bg = None
        name_plate_offset = (_NAME_PLATE_OFFSET_X, _NAME_PLATE_OFFSET_Y)

        if speaker_name and "name_plate_left" in self.tiles:
            # Use name_font if available, else fallback to standard font
            font_to_use = self.name_font if self.name_font else self.font
            name_surf = font_to_use.render(speaker_name, True, (255, 255, 255))

            name_w = name_surf.get_width()
            plate_padding_x = 16
            target_w = name_w + plate_padding_x * 2

            # Scale down the plate to be less massive (32px high instead of 64px)
            plate_h = 32
            edge_w = 16

            left_tile = pygame.transform.smoothscale(
                self.tiles["name_plate_left"], (edge_w, plate_h)
            )
            center_tile = pygame.transform.smoothscale(
                self.tiles["name_plate_center"], (edge_w, plate_h)
            )
            right_tile = pygame.transform.smoothscale(
                self.tiles["name_plate_right"], (edge_w, plate_h)
            )

            # Minimum width is left + right
            target_w = max(edge_w * 2, target_w)

            name_plate_bg = pygame.Surface((target_w, plate_h), pygame.SRCALPHA)
            name_plate_bg.blit(left_tile, (0, 0))

            center_w = target_w - (edge_w * 2)
            if center_w > 0:
                scaled_center = pygame.transform.scale(center_tile, (center_w, plate_h))
                name_plate_bg.blit(scaled_center, (edge_w, 0))

            name_plate_bg.blit(right_tile, (target_w - edge_w, 0))

            # Center the text inside the plate (adjusted slightly upwards if the bottom has a drop shadow)
            text_rect = name_surf.get_rect(center=(target_w // 2, plate_h // 2))
            name_plate_bg.blit(name_surf, text_rect)

        # 7. Final blit: single draw of the fully composed bubble
        # Position bubble so its bottom edge (with tail) is above the character head
        bubble_x = char_rect.centerx - bubble_w // 2
        bubble_y = char_rect.top - self.tail_gap - bubble_h

        blit(bg, (bubble_x, bubble_y))

        if name_plate_bg:
            blit(name_plate_bg, (bubble_x + name_plate_offset[0], bubble_y + name_plate_offset[1]))

    def get_total_pages(self, text: str) -> int:
        """Calculate the total number of pages for the given text."""
        if not self.font:
            return 1
        all_lines = self._wrap_text(text)
        lines_per_page = 4
        return max(1, (len(all_lines) + lines_per_page - 1) // lines_per_page)
