# src/ui/speech_bubble.py
"""Speech bubble rendering using nine-patch PNG tiles.

The bubble is built from 32×32 tiles located in `assets/images/HUD/`:
13-21 (bottom/right/top/… corners) and 22 for pagination arrow.
The tail (queue) is tile 21-bubble_queue.png.
"""

import os
from typing import Callable, List, Optional, Tuple

import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE_SIZE: int = 32
MIN_BUBBLE_SIZE: int = 2 * TILE_SIZE  # Minimum size to fit corners (64x64)
ASSET_DIR: str = os.path.join("assets", "images", "HUD")

_ARROW_OFFSET_X = 8
_ARROW_OFFSET_Y = -13
_BUBBLE_PADDING = 18
_TAIL_GAP = 20

TILES: dict = {
    "bottom_right": "13-bubble_bottom_right.png",
    "bottom":       "14-bubble_bottom.png",
    "bottom_left":  "15-bubble_bottom_left.png",
    "left":         "17-bubble_left.png",
    "right":        "16-bubble_right.png",
    "top_right":    "18-bubble_top_right.png",
    "top":          "19-bubble_top.png",
    "top_left":     "20-bubble_top_left.png",
    "queue":        "21-bubble_queue.png",
    "arrow":        "22-bubble_arrow.png",
}

# Type alias for the blit callable signature used by pygame.Surface.blit
BlitFunc = Callable[[pygame.Surface, Tuple[int, int]], None]


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
        self.padding = _BUBBLE_PADDING
        self.tail_gap = _TAIL_GAP
        self.arrow_inset = arrow_inset
        self.font: Optional[pygame.font.Font] = None
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
            else:
                self.tiles[key] = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))

    def set_font(self, font: pygame.font.Font) -> None:
        """Assign the pygame font used for rendering text."""
        self.font = font

    def _wrap_text(self, text: str) -> List[str]:
        """Wrap *text* to fit within bubble width minus padding on each side."""
        if not self.font:
            raise RuntimeError("Font not set on SpeechBubble before drawing.")

        inner_max_width = self.max_width_px - (2 * self.padding)
        if inner_max_width <= 0:
            return [text]

        words = text.split(" ")
        lines: List[str] = []
        current: List[str] = []

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
        bg.blit(self.tiles["top_left"],     (0, 0))
        bg.blit(self.tiles["top_right"],    (bubble_w - TILE_SIZE, 0))
        bg.blit(self.tiles["bottom_left"],  (0, queue_y))
        bg.blit(self.tiles["bottom_right"], (bubble_w - TILE_SIZE, queue_y))

        return bg

    def draw(
        self,
        surface: pygame.Surface,
        char_rect: pygame.Rect,
        text: str,
        page: int = 0,
        blit_func: Optional[BlitFunc] = None,
    ) -> None:
        """Draw the speech bubble anchored to char_rect."""
        blit: BlitFunc = blit_func if blit_func is not None else surface.blit

        # 1. Wrap and paginate
        all_lines = self._wrap_text(text)
        line_height = self.font.get_linesize()
        
        # Limit to 4 lines per page for typical speech bubble size
        lines_per_page = 4
        total_pages = max(1, (len(all_lines) + lines_per_page - 1) // lines_per_page)
        page = max(0, min(page, total_pages - 1))
        page_lines = all_lines[page * lines_per_page : (page + 1) * lines_per_page]

        # 2. Dimensions: text_w + 2*padding for width; +TILE_SIZE for bottom border row
        text_w = max((self.font.size(line)[0] for line in page_lines), default=0)
        text_h = len(page_lines) * line_height

        bubble_w = max(MIN_BUBBLE_SIZE, text_w + 2 * self.padding)
        bubble_w = min(self.max_width_px, bubble_w)
        bubble_h = max(MIN_BUBBLE_SIZE + TILE_SIZE, text_h + 2 * self.padding + TILE_SIZE)

        # 3. Background
        bg = self._build_background(bubble_w, bubble_h)

        # 4. Text rendered at (padding, padding) — full bubble width minus padding
        inner_y = self.padding
        for line in page_lines:
            txt_surf = self.font.render(line, True, (0, 0, 0))
            bg.blit(txt_surf, (self.padding, inner_y))
            inner_y += line_height

        # 5. Pagination arrow: INSIDE the top-left corner of the bottom-right tile, with manual offset
        if total_pages > 1:
            arrow = self.tiles["arrow"]
            arrow_x = bubble_w - TILE_SIZE + _ARROW_OFFSET_X
            arrow_y = bubble_h - TILE_SIZE + _ARROW_OFFSET_Y
            bg.blit(arrow, (arrow_x, arrow_y))

        # 6. Final blit: single draw of the fully composed bubble
        # Position bubble so its bottom edge (with tail) is above the character head
        bubble_x = char_rect.centerx - bubble_w // 2
        bubble_y = char_rect.top - self.tail_gap - bubble_h
        
        blit(bg, (bubble_x, bubble_y))

    def get_total_pages(self, text: str) -> int:
        """Calculate the total number of pages for the given text."""
        if not self.font:
            return 1
        all_lines = self._wrap_text(text)
        lines_per_page = 4
        return max(1, (len(all_lines) + lines_per_page - 1) // lines_per_page)
