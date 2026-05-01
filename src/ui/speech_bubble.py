# src/ui/speech_bubble.py
"""Speech bubble rendering using nine-patch PNG tiles.

The bubble is built from 32×32 tiles located in `assets/images/HUD/`:
13-21 (bottom/right/top/… corners) and 22 for pagination arrow.
The tail (queue) is tile 21-bubble_queue.png.

The `SpeechBubble` class provides a `draw` method that composes the bubble,
fills the interior with white, renders text, draws the tail above the
character, and shows a pagination arrow when needed.

Testability
-----------
`draw()` accepts an optional ``blit_func`` callable (dependency injection).
Pass a ``unittest.mock.MagicMock()`` in tests to intercept blit calls
without touching the read-only C-level ``pygame.Surface.blit`` attribute.
"""

import os
from typing import Callable, List, Optional, Tuple

import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE_SIZE: int = 32
ASSET_DIR: str = os.path.join("assets", "images", "HUD")

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
        max_width_px: int = 224,
        padding: int = 8,
        tail_gap: int = 4,
        arrow_inset: int = 4,
    ) -> None:
        self.max_width_px = max_width_px
        self.padding = padding
        self.tail_gap = tail_gap
        self.arrow_inset = arrow_inset
        self.font: Optional[pygame.font.Font] = None
        self._load_tiles()

    # ------------------------------------------------------------------
    # Asset loading
    # ------------------------------------------------------------------
    def _load_tiles(self) -> None:
        """Load all PNG tiles and cache them as pygame.Surface objects."""
        self.tiles: dict = {}
        for key, filename in TILES.items():
            path = os.path.join(ASSET_DIR, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Bubble asset not found: {path}")
            img = pygame.image.load(path).convert_alpha()
            self.tiles[key] = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))

    # ------------------------------------------------------------------
    # Font handling
    # ------------------------------------------------------------------
    def set_font(self, font: pygame.font.Font) -> None:
        """Assign the pygame font used for rendering text inside the bubble."""
        self.font = font

    # ------------------------------------------------------------------
    # Text processing
    # ------------------------------------------------------------------
    def _wrap_text(self, text: str) -> List[str]:
        """Wrap *text* to fit within the inner text area width.

        Returns a list of wrapped lines using word boundaries.
        Raises ``RuntimeError`` if no font has been assigned.
        """
        if not self.font:
            raise RuntimeError("Font not set on SpeechBubble before drawing.")

        inner_width = self.max_width_px - 2 * self.padding
        words = text.split(" ")
        lines: List[str] = []
        current: List[str] = []

        for word in words:
            candidate = " ".join(current + [word]) if current else word
            if self.font.size(candidate)[0] <= inner_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]

        if current:
            lines.append(" ".join(current))

        return lines

    # ------------------------------------------------------------------
    # Nine-patch background assembly
    # ------------------------------------------------------------------
    def _build_background(self, bubble_w: int, bubble_h: int) -> pygame.Surface:
        """Assemble the nine-patch background surface and fill its interior white."""
        bg = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)

        # Corners
        bg.blit(self.tiles["top_left"],     (0,                   0))
        bg.blit(self.tiles["top_right"],    (bubble_w - TILE_SIZE, 0))
        bg.blit(self.tiles["bottom_left"],  (0,                   bubble_h - TILE_SIZE))
        bg.blit(self.tiles["bottom_right"], (bubble_w - TILE_SIZE, bubble_h - TILE_SIZE))

        # Top / bottom edges
        h_tiles = max(1, (bubble_w - 2 * TILE_SIZE) // TILE_SIZE)
        for i in range(h_tiles):
            x = TILE_SIZE + i * TILE_SIZE
            bg.blit(self.tiles["top"],    (x, 0))
            bg.blit(self.tiles["bottom"], (x, bubble_h - TILE_SIZE))

        # Left / right edges
        v_tiles = max(1, (bubble_h - 2 * TILE_SIZE) // TILE_SIZE)
        for j in range(v_tiles):
            y = TILE_SIZE + j * TILE_SIZE
            bg.blit(self.tiles["left"],  (0,                   y))
            bg.blit(self.tiles["right"], (bubble_w - TILE_SIZE, y))

        # White interior
        inner = pygame.Rect(TILE_SIZE, TILE_SIZE, bubble_w - 2 * TILE_SIZE, bubble_h - 2 * TILE_SIZE)
        bg.fill((255, 255, 255), inner)

        return bg

    # ------------------------------------------------------------------
    # Core drawing routine
    # ------------------------------------------------------------------
    def draw(
        self,
        surface: pygame.Surface,
        char_rect: pygame.Rect,
        text: str,
        page: int = 0,
        blit_func: Optional[BlitFunc] = None,
    ) -> None:
        """Draw the speech bubble onto *surface*.

        Parameters
        ----------
        surface:
            Destination surface (the game screen).
        char_rect:
            Rectangle of the speaking character (used to position the tail).
        text:
            Full dialogue text — wrapped and paginated automatically.
        page:
            Zero-based page index for long dialogues (default 0).
        blit_func:
            Optional callable with the same signature as ``pygame.Surface.blit``.
            Defaults to ``surface.blit``.  Pass a ``MagicMock`` in unit tests
            to intercept blit calls without touching read-only C attributes.
        """
        # Use injected function or fall back to the surface's own blit
        blit: BlitFunc = blit_func if blit_func is not None else surface.blit

        # ----------------------------------------------------------
        # 1. Wrap text and paginate
        # ----------------------------------------------------------
        lines = self._wrap_text(text)
        line_height = self.font.get_linesize()
        max_lines = max(1, self.max_width_px // line_height)
        total_pages = max(1, (len(lines) + max_lines - 1) // max_lines)
        page = min(page, total_pages - 1)
        page_lines = lines[page * max_lines: (page + 1) * max_lines]

        # ----------------------------------------------------------
        # 2. Compute bubble dimensions
        # ----------------------------------------------------------
        text_width = max((self.font.size(l)[0] for l in page_lines), default=0)
        bubble_w = min(self.max_width_px, text_width + 2 * self.padding)
        bubble_h = len(page_lines) * line_height + 2 * self.padding

        # ----------------------------------------------------------
        # 3. Build nine-patch background
        # ----------------------------------------------------------
        bg = self._build_background(bubble_w, bubble_h)

        # ----------------------------------------------------------
        # 4. Render text
        # ----------------------------------------------------------
        y_offset = self.padding
        for line in page_lines:
            txt_surf = self.font.render(line, True, (0, 0, 0))
            bg.blit(txt_surf, (self.padding, y_offset))
            y_offset += line_height

        # ----------------------------------------------------------
        # 5. Pagination arrow
        # ----------------------------------------------------------
        if total_pages > 1:
            arrow = self.tiles["arrow"]
            arrow_x = bubble_w - self.arrow_inset - arrow.get_width()
            arrow_y = bubble_h - self.arrow_inset - arrow.get_height()
            bg.blit(arrow, (arrow_x, arrow_y))

        # ----------------------------------------------------------
        # 6. Position and blit tail + bubble onto destination surface
        # ----------------------------------------------------------
        tail = self.tiles["queue"]
        tail_x = char_rect.centerx - tail.get_width() // 2
        tail_y = char_rect.top - self.tail_gap - tail.get_height()

        blit(tail, (tail_x, tail_y))

        bubble_x = char_rect.centerx - bubble_w // 2
        bubble_y = tail_y - bubble_h
        blit(bg, (bubble_x, bubble_y))
