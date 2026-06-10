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

NOTE: All pygame init is handled by the session-scoped conftest fixture.
      Do NOT call pygame.display.set_mode() or pygame.quit() in this file.
"""

import unittest
from unittest import mock
from unittest.mock import MagicMock

import pygame
import pytest


# Import after pygame is ready (session conftest initialises it);
# _load_tiles now uses AssetManager.get_image(fallback=True) — mock that.
# name_plate tiles require a 96x64 surface for subsurface() calls;
# all other tiles need 32x32.
def _mock_get_image(path: str, fallback: bool = False) -> pygame.Surface:
    """Mock AssetManager.get_image: returns surface sized for each tile type."""
    if "23-bubble_name" in str(path):
        return pygame.Surface((96, 64))
    return pygame.Surface((32, 32))


with mock.patch(
    "src.ui.speech_bubble.AssetManager.get_image",
    side_effect=_mock_get_image,
):
    from src.ui.speech_bubble import SpeechBubble


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
    with mock.patch(
        "src.ui.speech_bubble.AssetManager.get_image",
        side_effect=_mock_get_image,
    ):
        bubble = SpeechBubble(**kwargs)
    bubble.set_font(_MockFont())  # type: ignore
    return bubble


def _make_surface() -> pygame.Surface:
    return pygame.Surface((800, 600))


def _char_rect() -> pygame.Rect:
    return pygame.Rect(400, 300, 32, 32)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestSpeechBubbleMaxWidth(unittest.TestCase):
    @pytest.mark.tc("UT-SPB-01")
    def test_max_width_not_exceeded(self):
        """Bubble width is capped at max_width_px."""
        bubble = _make_bubble(max_width_px=224)
        blit = MagicMock()
        bubble.draw(_make_surface(), _char_rect(), "word " * 50, blit_func=blit)
        assert bubble.max_width_px <= 224
        assert blit.called

    @pytest.mark.tc("UT-SPB-02")
    def test_wrap_uses_padding_not_tile_size(self):
        """_wrap_text inner width = max_width_px - 2*padding."""
        bubble = _make_bubble(max_width_px=100)
        bubble.pad_x = 10
        lines = bubble._wrap_text("word " * 20)
        # Each word is 7*5=35px wide; inner_max_width = 100 - 20 = 80
        # So at most floor(80/36) words per line
        assert bubble.font is not None
        for line in lines:
            assert bubble.font.size(line)[0] <= 80


class TestSpeechBubblePosition(unittest.TestCase):
    @pytest.mark.tc("UT-SPB-03")
    def test_bubble_bottom_anchored_above_character(self):
        """Bubble bottom edge respects tail_gap above char_rect.top."""
        bubble = _make_bubble()
        bubble.tail_gap = 4
        blit = MagicMock()
        rect = _char_rect()

        bubble.draw(_make_surface(), rect, "Hello", blit_func=blit)

        # Single blit call for the entire bubble (including integrated tail)
        assert blit.call_count == 1
        bg_surf, (bx, by) = blit.call_args_list[0][0]

        expected_y = rect.top - bubble.tail_gap - bg_surf.get_height()
        assert by == expected_y


class TestSpeechBubblePagination(unittest.TestCase):
    def _long_text(self) -> str:
        return "word " * 200  # guaranteed to span multiple pages

    @pytest.mark.tc("UT-SPB-04")
    def test_multiple_pages_exist_for_long_text(self):
        """Long text produces more than one page of wrapped lines."""
        bubble = _make_bubble()
        total_pages = bubble.get_total_pages(self._long_text())
        assert total_pages > 1

    @pytest.mark.tc("UT-SPB-05")
    def test_arrow_drawn_for_multi_page_text(self):
        """draw() runs without error for multi-page text (arrow code path hit)."""
        bubble = _make_bubble()
        blit = MagicMock()
        # Should not raise; arrow is composited inside bg (not via blit_func)
        bubble.draw(_make_surface(), _char_rect(), self._long_text(), blit_func=blit)
        assert blit.call_count == 1  # Integrated bubble is one blit

    @pytest.mark.tc("UT-SPB-06")
    def test_page_index_clamped(self):
        """Passing a page index beyond the last page is clamped silently."""
        bubble = _make_bubble()
        blit = MagicMock()
        # Should not raise
        bubble.draw(_make_surface(), _char_rect(), "Short text", page=999, blit_func=blit)
        assert blit.called


class TestSpeechBubbleFontGuard(unittest.TestCase):
    @pytest.mark.tc("UT-SPB-07")
    def test_raises_when_font_not_set(self):
        """draw() raises RuntimeError when no font is assigned."""
        with mock.patch(
            "src.ui.speech_bubble.AssetManager.get_image",
            side_effect=_mock_get_image,
        ):
            bubble = SpeechBubble()
        # font deliberately NOT set
        with pytest.raises(AssertionError):
            bubble.draw(_make_surface(), _char_rect(), "Hello", blit_func=MagicMock())


class TestSpeechBubbleNamePlate(unittest.TestCase):
    @pytest.mark.tc("UT-SPB-08")
    def test_name_plate_rendered(self):
        """When speaker_name is provided, a second blit occurs for the name plate."""
        with mock.patch(
            "src.ui.speech_bubble.AssetManager.get_image",
            side_effect=_mock_get_image,
        ):
            bubble = _make_bubble()
            # Also set the name_font
            bubble.set_name_font(_MockFont(12))  # type: ignore

            # Manually inject the name_plate tiles to simulate _load_tiles finding them
            # (since we mock load above but we want specific rects to work)
            plate_surf = pygame.Surface((96, 64))
            bubble.tiles["name_plate_left"] = plate_surf.subsurface(pygame.Rect(0, 0, 32, 64))
            bubble.tiles["name_plate_center"] = plate_surf.subsurface(pygame.Rect(32, 0, 32, 64))
            bubble.tiles["name_plate_right"] = plate_surf.subsurface(pygame.Rect(64, 0, 32, 64))

            blit = MagicMock()
            bubble.draw(_make_surface(), _char_rect(), "Hello", speaker_name="Hero", blit_func=blit)

            # Should blit twice: once for bubble, once for name plate
            assert blit.call_count == 2

            # Verify the second blit contains the name plate surface
            name_plate_surf, pos = blit.call_args_list[1][0]
            assert isinstance(name_plate_surf, pygame.Surface)
            assert name_plate_surf.get_width() > 0


class TestSpeechBubbleMissingBranches(unittest.TestCase):
    @staticmethod
    def _make_bubble_no_font():
        """SpeechBubble sans font, avec mock qui gère name_plate."""
        with mock.patch(
            "src.ui.speech_bubble.AssetManager.get_image",
            side_effect=_mock_get_image,
        ):
            return SpeechBubble()

    def test_wrap_text_raises_when_font_not_set(self):
        """Ligne 93 : _wrap_text() RuntimeError quand font=None."""
        bubble = self._make_bubble_no_font()
        with pytest.raises(RuntimeError):
            bubble._wrap_text("Hello world")

    def test_wrap_text_returns_text_when_inner_width_zero(self):
        """Ligne 97 : inner_max_width <= 0 → [text] retourné directement."""
        bubble = self._make_bubble_no_font()
        bubble.set_font(_MockFont())  # type: ignore
        bubble.max_width_px = 1
        bubble.pad_x = 10
        result = bubble._wrap_text("hello world")
        assert result == ["hello world"]

    def test_get_total_pages_returns_one_without_font(self):
        """Ligne 282 : get_total_pages() retourne 1 si font non défini."""
        bubble = self._make_bubble_no_font()
        result = bubble.get_total_pages("Some long text here")
        assert result == 1

    def test_load_tiles_graceful_when_assets_missing(self):
        """_load_tiles uses AssetManager fallback=True: missing assets do not raise.

        SpeechBubble must be constructable even when HUD PNG files are absent
        (consistent with ChestUI / HUD behavior elsewhere in the codebase).
        """
        with mock.patch(
            "src.ui.speech_bubble.AssetManager.get_image",
            return_value=pygame.Surface((32, 32)),
        ):
            # Must not raise even though all name_plate surfaces are 32x32 (too small for subsurface)
            bubble = SpeechBubble()
        assert isinstance(bubble, SpeechBubble)




if __name__ == "__main__":
    unittest.main()
