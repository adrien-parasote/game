"""RED tests for Phase 1.5 — verify asset methods exist on ChestDrawMixin.

TC-CA-01..TC-CA-08 from docs/game/specs/phase-1.5-chest-refactoring.md
IT-CA-01..IT-CA-05 regression/integration tests.
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()

from src.ui.chest import ChestUI
from src.ui.chest_draw import ChestDrawMixin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_chest_ui() -> ChestUI:
    return ChestUI()


# ---------------------------------------------------------------------------
# TC-CA-01 — _load_background: absent asset → None + log error
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-01")
def test_load_background_missing_asset_returns_none(caplog):
    """_load_background with AssetManager fallback returns a Surface (not None).

    After migration to AssetManager, missing assets return a placeholder
    surface instead of None. The method always returns a Surface.
    """
    ui = make_chest_ui()
    with patch("src.ui.chest_draw.ASSET_CHEST_BG", "nonexistent_bg.png"):
        result = ui._load_background()
    # AssetManager fallback: returns a Surface, not None
    assert isinstance(result, pygame.Surface)
    assert any("asset not found" in rec.message.lower() for rec in caplog.records)


# ---------------------------------------------------------------------------
# TC-CA-02 — _load_inv_background: absent asset → None + log error
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-02")
def test_load_inv_background_missing_asset_returns_none(caplog):
    """_load_inv_background with AssetManager fallback returns a Surface."""
    ui = make_chest_ui()
    with patch("src.ui.chest_draw.ASSET_INV_BG", "nonexistent_inv.png"):
        result = ui._load_inv_background()
    assert isinstance(result, pygame.Surface)
    assert any("asset not found" in rec.message.lower() for rec in caplog.records)


# ---------------------------------------------------------------------------
# TC-CA-03 — _load_slot_image: absent asset → None + log warning
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-03")
def test_load_slot_image_missing_asset_returns_none(caplog):
    """_load_slot_image returns None when asset is absent (32x32 fallback detection)."""
    ui = make_chest_ui()
    with patch("src.ui.chest_draw.ASSET_SLOT_IMG", "nonexistent_slot.png"):
        result = ui._load_slot_image()
    # Implementation checks for 32x32 size to detect placeholder
    assert result is None
    assert any("asset not found" in rec.message.lower() for rec in caplog.records)


# ---------------------------------------------------------------------------
# TC-CA-04 — _load_cursor: invalid path → None + log warning
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-04")
def test_load_cursor_invalid_path_returns_none(caplog):
    """_load_cursor with missing file returns a scaled placeholder Surface (not None)."""
    ui = make_chest_ui()
    result = ui._load_cursor("nonexistent.png")
    # AssetManager returns a placeholder — _load_cursor scales it
    assert isinstance(result, pygame.Surface)


# ---------------------------------------------------------------------------
# TC-CA-05 — _load_and_scale_arrow: invalid path → None + log warning
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-05")
def test_load_and_scale_arrow_invalid_path_returns_none(caplog):
    """_load_and_scale_arrow with missing file returns a scaled placeholder Surface."""
    ui = make_chest_ui()
    result = ui._load_and_scale_arrow("nonexistent.png", 1.0)
    # AssetManager returns a placeholder — method scales it
    assert isinstance(result, pygame.Surface)


# ---------------------------------------------------------------------------
# TC-CA-06 — _get_item_icon cache hit: second call does not re-load
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-06")
def test_get_item_icon_cache_hit_no_second_io():
    """_get_item_icon must return cached surface on second call."""
    ui = make_chest_ui()
    # Pre-populate cache with a mock surface
    mock_surface = MagicMock(spec=pygame.Surface)
    cache_key = "sword@32"
    ui._icon_cache[cache_key] = mock_surface

    with patch("pygame.image.load") as mock_load:
        result = ui._get_item_icon("sword", 32)
        mock_load.assert_not_called()

    assert result is mock_surface


# ---------------------------------------------------------------------------
# TC-CA-07 — _get_item_icon: absent file → None cached
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-07")
def test_get_item_icon_absent_file_caches_none(tmp_path):
    """_get_item_icon must cache None and return None when file is absent."""
    ui = make_chest_ui()
    result = ui._get_item_icon("nonexistent_icon_xyz_abc", 32)
    assert result is None
    assert ui._icon_cache.get("nonexistent_icon_xyz_abc@32") is None


# ---------------------------------------------------------------------------
# TC-CA-08 — _get_item_icon: auto-appends .png extension
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CA-08")
def test_get_item_icon_appends_png_extension(tmp_path):
    """_get_item_icon must append .png if missing."""
    ui = make_chest_ui()
    # File does not exist → returns None, but we verify path used
    with patch("os.path.exists", return_value=False) as mock_exists:
        result = ui._get_item_icon("sword", 32)
    # Verify the path checked ends in .png
    called_path = mock_exists.call_args[0][0]
    assert called_path.endswith(".png")
    assert result is None


# ---------------------------------------------------------------------------
# IT-CA-01 — regression: _load_background accessible via ChestUI (mixin)
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-CA-01")
def test_load_background_accessible_via_chest_ui():
    """ChestUI must expose _load_background via ChestDrawMixin inheritance."""
    ui = ChestUI()
    assert hasattr(ui, "_load_background")
    assert callable(ui._load_background)


# ---------------------------------------------------------------------------
# IT-CA-02 — regression: ChestUI instanciable (no AttributeError)
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-CA-02")
def test_chest_ui_instantiation_no_error():
    """ChestUI() must not raise AttributeError or ImportError."""
    ui = ChestUI()
    assert ui is not None
    assert not ui.is_open


# ---------------------------------------------------------------------------
# IT-CA-03 — regression: _get_item_icon accessible via self in ChestDrawMixin
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-CA-03")
def test_get_item_icon_accessible_via_mixin():
    """ChestDrawMixin must provide _get_item_icon (accessed via ChestUI)."""
    ui = ChestUI()
    assert hasattr(ui, "_get_item_icon")
    assert callable(ui._get_item_icon)


# ---------------------------------------------------------------------------
# IT-CA-04 — no double definition: methods absent from ChestUI class body
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-CA-04")
def test_asset_methods_not_defined_in_chest_ui_class():
    """After refactoring, _load_background must NOT be in ChestUI.__dict__
    (it must come from ChestDrawMixin via MRO, not be redefined on ChestUI)."""
    # They should NOT be directly on ChestUI but on ChestDrawMixin
    assert "_load_background" not in ChestUI.__dict__, (
        "_load_background should be on ChestDrawMixin, not ChestUI"
    )
    assert "_get_item_icon" not in ChestUI.__dict__, (
        "_get_item_icon should be on ChestDrawMixin, not ChestUI"
    )


# ---------------------------------------------------------------------------
# IT-CA-05 — methods present on ChestDrawMixin after move
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-CA-05")
def test_asset_methods_present_on_chest_draw_mixin():
    """After refactoring, _load_background and _get_item_icon must be on ChestDrawMixin."""
    assert hasattr(ChestDrawMixin, "_load_background"), (
        "_load_background must exist on ChestDrawMixin after move"
    )
    assert hasattr(ChestDrawMixin, "_get_item_icon"), (
        "_get_item_icon must exist on ChestDrawMixin after move"
    )
    assert hasattr(ChestDrawMixin, "_load_cursor"), (
        "_load_cursor must exist on ChestDrawMixin after move"
    )
    assert hasattr(ChestDrawMixin, "_load_and_scale_arrow"), (
        "_load_and_scale_arrow must exist on ChestDrawMixin after move"
    )
