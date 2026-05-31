"""
RED tests for constants and performance specs.

Covers:
  UT-004 — SaveMenuOverlay.refresh() populates _cached_title_surfs
  UT-007 — DialogueManager uses DIALOGUE_SHADOW_COLOR / DIALOGUE_TEXT_COLOR
  UT-008 — ChestDrawMixin._draw_title() renders CHEST_TITLE_TEXT
  UT-009 — ChestDrawMixin._title_font lazy-init: same object on 2nd call
  UT-010 — SaveSlotUI uses SAVE_SLOT_BG_W/H for background scaling
  IT-001 — No French comment "# Sauvegarder" in source files
  IT-003 — save_menu_constants imports without error

Spec: game/docs/specs/perf-constants-spec.md
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pygame
import pytest

# ── UT-004 ─────────────────────────────────────────────────────────────────


def test_save_menu_refresh_populates_cached_title_surfs():
    """UT-004: SaveMenuOverlay.refresh() must set _cached_title_surfs (list of 3)."""
    from src.engine.save_manager import SlotInfo
    from src.ui.save_menu import SaveMenuOverlay

    pygame.font.init()
    mock_screen = MagicMock()
    mock_screen.get_size.return_value = (1280, 720)
    mock_sm = MagicMock()
    mock_sm.list_slots.return_value = [
        SlotInfo(
            slot_id=1,
            saved_at="2025-01-01 12:00",
            playtime_seconds=3600.0,
            map_name="Map",
            map_display_name="Map",
            player_name="Hero",
            level=5,
        ),
        None,
        None,
    ]
    mock_sm.load_thumbnail.return_value = pygame.Surface((82, 82))

    with patch("src.ui.save_menu.SaveSlotUI") as mock_slot_cls:
        mock_slot_cls.return_value.get_size.return_value = (800, 200)
        menu = SaveMenuOverlay(mock_screen, mock_sm, "Title")
        menu.refresh()

    assert hasattr(menu, "_cached_title_surfs"), (
        "SaveMenuOverlay must have _cached_title_surfs after refresh()"
    )
    assert len(menu._cached_title_surfs) == 3, (
        f"Expected 3 cached title surfs (one per slot), got {len(menu._cached_title_surfs)}"
    )


# ── UT-007 ─────────────────────────────────────────────────────────────────


def test_dialogue_manager_uses_constant_colors():
    """UT-007: DialogueManager._shadow_color and _text_color must match constants."""
    from src.ui.dialogue import DialogueManager
    from src.ui.dialogue_constants import DIALOGUE_SHADOW_COLOR, DIALOGUE_TEXT_COLOR

    with (
        patch("src.engine.asset_manager.AssetManager.get_font", return_value=MagicMock()),
        patch("pygame.image.load", return_value=pygame.Surface((10, 10))),
        patch("os.path.exists", return_value=False),
    ):
        dm = DialogueManager()

    assert dm._shadow_color == DIALOGUE_SHADOW_COLOR, (
        f"_shadow_color {dm._shadow_color!r} != DIALOGUE_SHADOW_COLOR {DIALOGUE_SHADOW_COLOR!r}"
    )
    assert dm._text_color == DIALOGUE_TEXT_COLOR, (
        f"_text_color {dm._text_color!r} != DIALOGUE_TEXT_COLOR {DIALOGUE_TEXT_COLOR!r}"
    )


# ── UT-008 ─────────────────────────────────────────────────────────────────


def test_chest_draw_title_uses_constant_text():
    """UT-008: _draw_title() must render CHEST_TITLE_TEXT, not a hardcoded string."""
    from src.ui.chest_constants import CHEST_TITLE_TEXT
    from src.ui.chest_draw import ChestDrawMixin

    pygame.font.init()

    class FakeChest(ChestDrawMixin):
        def __init__(self):
            self._title_rect = pygame.Rect(100, 100, 200, 40)
            self._title_font = None

    chest = FakeChest()
    screen = MagicMock()

    rendered_texts = []

    def capture_render(text, aa, color):
        rendered_texts.append(text)
        return pygame.Surface((80, 20))

    with patch("pygame.font.Font") as mock_font_cls:
        mock_font = MagicMock()
        mock_font.render.side_effect = capture_render
        mock_font_cls.return_value = mock_font

        chest._draw_title(screen)

    assert CHEST_TITLE_TEXT in rendered_texts, (
        f"Expected '{CHEST_TITLE_TEXT}' to be rendered, got {rendered_texts}"
    )


# ── UT-009 ─────────────────────────────────────────────────────────────────


def test_chest_draw_title_font_lazy_init_only_once():
    """UT-009: _title_font must be created once and reused on subsequent calls."""
    from src.ui.chest_draw import ChestDrawMixin

    pygame.font.init()

    class FakeChest(ChestDrawMixin):
        def __init__(self):
            self._title_rect = pygame.Rect(0, 0, 200, 40)
            self._title_font = None

    chest = FakeChest()
    screen = MagicMock()

    with patch("pygame.font.Font") as mock_font_cls:
        mock_font_cls.return_value = MagicMock()
        mock_font_cls.return_value.render.return_value = pygame.Surface((80, 20))

        chest._draw_title(screen)
        font_after_first_call = chest._title_font

        chest._draw_title(screen)
        font_after_second_call = chest._title_font

    assert mock_font_cls.call_count == 1, (
        f"pygame.font.Font() called {mock_font_cls.call_count} times; "
        "must only be called once (lazy-init guard)."
    )
    assert font_after_first_call is font_after_second_call, (
        "_title_font must be the same object on both calls"
    )


# ── UT-010 ─────────────────────────────────────────────────────────────────


def test_save_slot_ui_uses_constant_bg_size():
    """UT-010: SaveSlotUI must pass (SAVE_SLOT_BG_W, SAVE_SLOT_BG_H) to smoothscale."""
    from src.ui.save_menu import SaveSlotUI
    from src.ui.save_menu_constants import SAVE_SLOT_BG_H, SAVE_SLOT_BG_W

    pygame.font.init()
    mock_am = MagicMock()
    mock_am.get_font.return_value = pygame.font.SysFont(None, 24)

    scaled_sizes = []

    def capture_scale(surf, size):
        scaled_sizes.append(size)
        return pygame.Surface(size)

    with patch("pygame.transform.smoothscale", side_effect=capture_scale):  # noqa: SIM117
        with patch("pygame.image.load", return_value=pygame.Surface((427, 200))):
            slot = SaveSlotUI(mock_am)

    expected = (SAVE_SLOT_BG_W, SAVE_SLOT_BG_H)
    assert expected in scaled_sizes, (
        f"Expected smoothscale called with {expected}, got {scaled_sizes}"
    )


# ── IT-001 ─────────────────────────────────────────────────────────────────


def test_no_french_comment_in_source():
    """IT-001: No '# Sauvegarder' comment must exist in any .py source file."""
    src_root = Path(__file__).parent.parent.parent / "src"
    matches = list(src_root.rglob("*.py"))
    violations = []
    for py_file in matches:
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            # Only check actual comments (strip leading whitespace first)
            stripped = line.strip()
            if stripped.startswith("#") and "Sauvegarder" in stripped:
                violations.append(f"{py_file}:{i}: {line.rstrip()}")
    assert not violations, "French comment '# Sauvegarder' found in source:\n" + "\n".join(
        violations
    )


# ── IT-003 ─────────────────────────────────────────────────────────────────


def test_save_menu_constants_importable():
    """IT-003: save_menu_constants must import without error."""
    try:
        import src.ui.save_menu_constants as smc
    except ImportError as e:
        pytest.fail(f"save_menu_constants failed to import: {e}")
