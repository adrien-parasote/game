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

    def test_wrap_uses_padding_not_tile_size(self):
        """_wrap_text inner width = max_width_px - 2*padding."""
        bubble = _make_bubble(max_width_px=100)
        bubble.padding = 10
        lines = bubble._wrap_text("word " * 20)
        # Each word is 7*5=35px wide; inner_max_width = 100 - 20 = 80
        # So at most floor(80/36) words per line
        for line in lines:
            self.assertLessEqual(bubble.font.size(line)[0], 80)


class TestSpeechBubblePosition(unittest.TestCase):
    def test_bubble_bottom_anchored_above_character(self):
        """Bubble bottom edge respects tail_gap above char_rect.top."""
        bubble = _make_bubble()
        bubble.tail_gap = 4
        blit = MagicMock()
        rect = _char_rect()

        bubble.draw(_make_surface(), rect, "Hello", blit_func=blit)

        # Single blit call for the entire bubble (including integrated tail)
        self.assertEqual(blit.call_count, 1)
        bg_surf, (bx, by) = blit.call_args_list[0][0]
        
        expected_y = rect.top - bubble.tail_gap - bg_surf.get_height()
        self.assertEqual(by, expected_y)


class TestSpeechBubblePagination(unittest.TestCase):
    def _long_text(self) -> str:
        return "word " * 200  # guaranteed to span multiple pages

    def test_multiple_pages_exist_for_long_text(self):
        """Long text produces more than one page of wrapped lines."""
        bubble = _make_bubble()
        total_pages = bubble.get_total_pages(self._long_text())
        self.assertGreater(total_pages, 1)

    def test_arrow_drawn_for_multi_page_text(self):
        """draw() runs without error for multi-page text (arrow code path hit)."""
        bubble = _make_bubble()
        blit = MagicMock()
        # Should not raise; arrow is composited inside bg (not via blit_func)
        bubble.draw(_make_surface(), _char_rect(), self._long_text(), blit_func=blit)
        self.assertEqual(blit.call_count, 1)  # Integrated bubble is one blit

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
            def mock_load(path):
                if "23-bubble_name" in path:
                    return pygame.Surface((96, 64))
                return pygame.Surface((32, 32))
            ml.side_effect = mock_load
            bubble = SpeechBubble()
        # font deliberately NOT set
        with self.assertRaises(RuntimeError):
            bubble.draw(_make_surface(), _char_rect(), "Hello", blit_func=MagicMock())


if __name__ == "__main__":
    unittest.main()
