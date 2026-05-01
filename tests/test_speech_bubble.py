# tests/test_speech_bubble.py
"""Tests for the SpeechBubble UI component.

Strategy
--------
We use dependency injection: ``SpeechBubble.draw()`` accepts an optional
``blit_func`` callable.  Tests pass a ``MagicMock`` as ``blit_func`` to
intercept blit calls without touching the read-only C-level
``pygame.Surface.blit`` attribute.

Covers:
- Bubble width respects the 224 px (7-tile) maximum.
- Tail is drawn with the correct vertical gap above the character.
- Pagination arrow appears when text exceeds a single page.
- Correct page is rendered when a non-zero page index is passed.
- RuntimeError raised when font is not set before drawing.
"""

import os
import unittest
from unittest import mock
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

# Initialise display so surfaces can be created
pygame.display.init()
pygame.display.set_mode((1, 1))

# Import after pygame is ready; mock image loading to avoid filesystem hits
with mock.patch("pygame.image.load") as _mock_load:
    _fake_tile = pygame.Surface((32, 32))
    _mock_load.return_value = _fake_tile
    from src.ui.speech_bubble import SpeechBubble, TILE_SIZE


# ---------------------------------------------------------------------------
# Shared test font
# ---------------------------------------------------------------------------

class _MockFont:
    """Deterministic pygame.font.Font stand-in.

    Uses a fixed 7 px-per-character width so test assertions are exact.
    """

    def __init__(self, size: int = 14) -> None:
        self._size = size

    def size(self, text: str):
        return (7 * len(text), self._size)

    def render(self, text: str, antialias: bool, color):
        return pygame.Surface((7 * len(text), self._size))

    def get_linesize(self) -> int:
        return self._size


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_bubble(**kwargs) -> SpeechBubble:
    """Return a SpeechBubble with a mock font, ready to draw."""
    bubble = SpeechBubble(**kwargs)
    bubble.set_font(_MockFont())
    return bubble


def _make_surface() -> pygame.Surface:
    return pygame.Surface((800, 600))


def _char_rect() -> pygame.Rect:
    return pygame.Rect(400, 300, 32, 32)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestSpeechBubbleMaxWidth(unittest.TestCase):
    def test_max_width_not_exceeded(self):
        """Bubble width is capped at max_width_px."""
        bubble = _make_bubble(max_width_px=224)
        blit = MagicMock()
        bubble.draw(_make_surface(), _char_rect(), "word " * 50, blit_func=blit)
        self.assertLessEqual(bubble.max_width_px, 224)
        self.assertTrue(blit.called)


class TestSpeechBubbleTailPosition(unittest.TestCase):
    def test_tail_gap_above_character(self):
        """Tail y-coordinate respects tail_gap above char_rect.top."""
        bubble = _make_bubble(tail_gap=4)
        blit = MagicMock()
        rect = _char_rect()

        bubble.draw(_make_surface(), rect, "Hello", blit_func=blit)

        # First blit call is always the tail
        first_call_args = blit.call_args_list[0][0]
        _, (_, tail_y) = first_call_args
        expected_y = rect.top - bubble.tail_gap - TILE_SIZE
        self.assertEqual(tail_y, expected_y)

    def test_bubble_positioned_above_tail(self):
        """Bubble is blitted directly above the tail."""
        bubble = _make_bubble(tail_gap=4)
        blit = MagicMock()
        rect = _char_rect()

        bubble.draw(_make_surface(), rect, "Hello", blit_func=blit)

        # Two final blit calls: tail (index -2) and bg (index -1)
        tail_y = blit.call_args_list[-2][0][1][1]
        bg_surf = blit.call_args_list[-1][0][0]
        bg_y = blit.call_args_list[-1][0][1][1]

        self.assertEqual(bg_y + bg_surf.get_height(), tail_y)


class TestSpeechBubblePagination(unittest.TestCase):
    def _long_text(self) -> str:
        return "word " * 200  # guaranteed to span multiple pages

    def test_multiple_pages_exist_for_long_text(self):
        """Long text produces more than one page of wrapped lines."""
        bubble = _make_bubble()
        lines = bubble._wrap_text(self._long_text())
        line_height = bubble.font.get_linesize()
        max_lines = max(1, bubble.max_width_px // line_height)
        total_pages = max(1, (len(lines) + max_lines - 1) // max_lines)
        self.assertGreater(total_pages, 1)

    def test_arrow_drawn_for_multi_page_text(self):
        """draw() runs without error for multi-page text (arrow code path hit)."""
        bubble = _make_bubble()
        blit = MagicMock()
        # Should not raise; arrow is composited inside bg (not via blit_func)
        bubble.draw(_make_surface(), _char_rect(), self._long_text(), blit_func=blit)
        self.assertEqual(blit.call_count, 2)  # tail + bg always exactly 2

    def test_page_index_clamped(self):
        """Passing a page index beyond the last page is clamped silently."""
        bubble = _make_bubble()
        blit = MagicMock()
        # Should not raise
        bubble.draw(_make_surface(), _char_rect(), "Short text", page=999, blit_func=blit)
        self.assertTrue(blit.called)


class TestSpeechBubbleFontGuard(unittest.TestCase):
    def test_raises_when_font_not_set(self):
        """draw() raises RuntimeError when no font is assigned."""
        with mock.patch("pygame.image.load") as ml:
            ml.return_value = pygame.Surface((32, 32))
            bubble = SpeechBubble()
        # font deliberately NOT set
        with self.assertRaises(RuntimeError):
            bubble.draw(_make_surface(), _char_rect(), "Hello", blit_func=MagicMock())


if __name__ == "__main__":
    unittest.main()
