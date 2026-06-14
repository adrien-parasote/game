"""Tests for DialogueManager optimization."""

from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.ui.dialogue import DialogueManager


@pytest.mark.tc("UT-DLG-01")
def test_dialogue_manager_pre_renders_pages():
    game = MagicMock()
    game.i18n.current_locale = "en"

    # Mock font so sizes can be calculated
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))

    with (
        patch("src.engine.asset_manager.AssetManager.get_font", return_value=mock_font),
        patch("pygame.image.load"),
        patch("os.path.exists", return_value=True),
    ):
        dm = DialogueManager()

        # Override the font manually since it loads via asset manager
        dm.font_message = mock_font
        dm.font_title = mock_font
        dm.dialogue_box = pygame.Surface((400, 200))  # mock the box

        dm.start_dialogue(
            "This is a test that spans multiple lines because it is very long and needs to wrap."
        )

        # After start_dialogue, _paginate should have pre-rendered the pages
        assert hasattr(dm, "_page_surfaces")
        assert len(dm._page_surfaces) > 0

        # Each item in _page_surfaces should be a pygame Surface
        for surf in dm._page_surfaces:
            assert isinstance(surf, pygame.Surface)


@pytest.mark.tc("UT-DLG-02")
def test_dialogue_manager_advance_and_update():
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))

    with (
        patch("src.engine.asset_manager.AssetManager.get_font", return_value=mock_font),
        patch("pygame.image.load", return_value=pygame.Surface((100, 100))),
        patch("os.path.exists", return_value=True),
    ):
        dm = DialogueManager()
        dm.font_message = mock_font
        dm.dialogue_box = pygame.Surface((400, 200))  # Restore valid dimensions

        # Long text that generates multiple pages
        dm.start_dialogue("Long text to span multiple pages. " * 50)

        # We can check how many pages were generated
        assert len(dm._pages) >= 2
        assert dm._is_page_complete is False
        assert dm.displayed_text == ""

        dm.update(0.1)  # 100ms
        assert len(dm.displayed_text) > 0
        assert not dm._is_page_complete

        # Test skip to end of page
        dm.advance()
        assert dm._is_page_complete is True

        # Test next page
        dm.advance()
        assert dm._current_page_index == 1
        assert dm._is_page_complete is False

        # Advance through all remaining pages
        max_attempts = len(dm._pages) * 2
        attempts = 0
        while dm.is_active and attempts < max_attempts:
            dm.advance()
            attempts += 1

        assert dm.is_active is False
        assert dm.message == ""


@pytest.mark.tc("UT-DLG-03")
def test_dialogue_manager_draw():
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))

    with (
        patch("src.engine.asset_manager.AssetManager.get_font", return_value=mock_font),
        patch("pygame.image.load", return_value=pygame.Surface((100, 100))),
        patch("os.path.exists", return_value=True),
    ):
        dm = DialogueManager()
        dm.font_message = mock_font
        dm.font_title = mock_font
        dm.dialogue_box = pygame.Surface((400, 200))
        dm.next_arrow = pygame.Surface((10, 10))

        dm.start_dialogue("Test drawing logic.", title="NPC")

        # Test drawing before page complete (dynamic text)
        dm.update(0.1)
        screen = MagicMock()
        dm.draw(screen)
        assert screen.blit.call_count > 0

        # Test drawing after page complete (pre-rendered page)
        screen.reset_mock()
        dm.advance()
        dm.draw(screen)
        assert screen.blit.call_count > 0


# ── Coverage gap tests ────────────────────────────────────────────────────────


def _make_dm():
    """Helper: build a DialogueManager with mocked assets."""
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))

    with (
        patch("src.engine.asset_manager.AssetManager.get_font", return_value=mock_font),
        patch("pygame.image.load", return_value=pygame.Surface((100, 100))),
        patch("os.path.exists", return_value=True),
    ):
        dm = DialogueManager()
    dm.font_message = mock_font
    dm.font_title = mock_font
    dm.dialogue_box = pygame.Surface((400, 200))
    return dm


def test_paginate_without_font_fallback():
    """_paginate falls back to [[text]] when font_message or dialogue_box is None (lines 98-99)."""
    dm = _make_dm()
    dm.font_message = None  # Force fallback path
    dm._paginate("Hello world")
    assert dm._pages == [["Hello world"]]


def test_paginate_without_dialogue_box_fallback():
    """_paginate falls back to [[text]] when dialogue_box is None."""
    dm = _make_dm()
    dm.dialogue_box = None  # Force fallback path
    dm._paginate("Hello")
    assert dm._pages == [["Hello"]]


def test_start_dialogue_empty_text_deactivates(caplog):
    """start_dialogue('') immediately sets is_active=False (lines 156-157)."""
    dm = _make_dm()
    dm.is_active = True
    dm.start_dialogue("")
    assert dm.is_active is False


def test_start_dialogue_empty_pages_deactivates():
    """start_dialogue with text that produces no pages deactivates (lines 170-171)."""
    dm = _make_dm()
    dm.font_message = None
    dm.dialogue_box = None
    dm.start_dialogue("")  # Empty text → _paginate → empty pages
    assert dm.is_active is False


def test_update_marks_page_complete_when_index_reaches_end():
    """update() sets _is_page_complete=True when char index hits end of text (lines 213-214)."""
    dm = _make_dm()
    dm.start_dialogue("Hi")  # Short text
    dm._page_char_index = 1.9  # Just before end
    dm.typewriter_speed = 1000  # Force completion in one step
    dm.update(1.0)
    assert dm._is_page_complete is True


def test_update_sets_page_complete_when_already_past_end():
    """update() takes else branch (line 217) when char index >= text length at call time."""
    dm = _make_dm()
    dm.start_dialogue("Hi")
    current_text = " ".join(dm._pages[0])
    dm._page_char_index = float(len(current_text))  # Already at end
    dm._is_page_complete = False  # Force update path
    dm.update(0.01)
    assert dm._is_page_complete is True


def test_draw_typewriter_full_line_blit():
    """_draw_typewriter_text blits full pre-rendered lines for complete lines (lines 236-238)."""
    dm = _make_dm()
    # Two-line text — first line complete, second partial
    dm.start_dialogue("First line second line third line")
    dm._page_char_index = 20.0
    dm.displayed_text = " ".join(dm._pages[0])[:20]
    screen = MagicMock()
    page_surf = dm._page_surfaces[0]
    dm._draw_typewriter_text(screen, 0, 0, page_surf)
    assert screen.blit.call_count >= 1


def test_advance_does_nothing_when_not_active():
    """advance() is a no-op when is_active is False."""
    dm = _make_dm()
    dm.is_active = False
    dm.advance()  # Must not raise
    assert dm.is_active is False
