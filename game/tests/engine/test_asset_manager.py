"""Tests for AssetManager (src/engine/asset_manager.py).

Covers: singleton pattern, cache hits/misses, font loading (path/fallback),
        occlusion mask caching, cache clearing, get_image fallback and error paths.
"""

from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.engine.asset_manager import AssetManager


# ── Singleton ──────────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance():
    """AssetManager() must return the same instance on each call."""
    # conftest.py resets _instance before each test
    a = AssetManager()
    b = AssetManager()
    assert a is b


def test_singleton_reset_creates_fresh():
    """After resetting _instance, a new AssetManager is constructed."""
    first = AssetManager()
    AssetManager._instance = None
    second = AssetManager()
    assert first is not second
    assert second._images == {}


# ── get_image — cache hit ─────────────────────────────────────────────────────


def test_get_image_cache_hit():
    """Second call with same path returns the cached Surface without disk I/O."""
    am = AssetManager()
    fake_surf = pygame.Surface((32, 32))
    am._images["some/path.png"] = fake_surf

    with patch("os.path.exists", return_value=True):
        result = am.get_image("some/path.png")

    assert result is fake_surf


# ── get_image — fallback placeholder ─────────────────────────────────────────


def test_get_image_missing_file_with_fallback_returns_placeholder():
    """Missing file + fallback=True → returns a 32x32 placeholder Surface."""
    am = AssetManager()
    with patch("os.path.exists", return_value=False):
        result = am.get_image("missing.png", fallback=True)

    assert isinstance(result, pygame.Surface)
    assert result.get_size() == (32, 32)


def test_get_image_missing_file_no_fallback_raises():
    """Missing file + fallback=False → raises FileNotFoundError."""
    am = AssetManager()
    with patch("os.path.exists", return_value=False), pytest.raises(FileNotFoundError):
        am.get_image("missing.png", fallback=False)


def test_get_image_pygame_error_with_fallback_returns_placeholder():
    """pygame.error during load + fallback=True → returns placeholder."""
    am = AssetManager()
    with (
        patch("os.path.exists", return_value=True),
        patch("pygame.image.load", side_effect=pygame.error("bad file")),
    ):
        result = am.get_image("bad.png", fallback=True)

    assert isinstance(result, pygame.Surface)


def test_get_image_pygame_error_no_fallback_raises():
    """pygame.error during load + fallback=False → re-raises pygame.error."""
    am = AssetManager()
    with (
        patch("os.path.exists", return_value=True),
        patch("pygame.image.load", side_effect=pygame.error("bad file")),
        pytest.raises(pygame.error),
    ):
        am.get_image("bad.png", fallback=False)


# ── get_font ───────────────────────────────────────────────────────────────────


def test_get_font_cache_hit():
    """Second call with same (path, size) returns cached font."""
    am = AssetManager()
    fake_font = MagicMock(spec=pygame.font.Font)
    am._fonts[("my.ttf", 16)] = fake_font

    result = am.get_font("my.ttf", 16)
    assert result is fake_font


def test_get_font_missing_path_uses_sysfont():
    """get_font with missing file falls back to SysFont without raising."""
    am = AssetManager()
    with patch("os.path.exists", return_value=False):
        font = am.get_font("nonexistent.ttf", 14)
    assert font is not None


def test_get_font_empty_path_uses_sysfont():
    """get_font with empty string path uses SysFont fallback."""
    am = AssetManager()
    font = am.get_font("", 12)
    assert font is not None


# ── get_occlusion_mask ─────────────────────────────────────────────────────────


def test_get_occlusion_mask_cache_hit():
    """Second call with same surface id returns cached mask without recomputing."""
    am = AssetManager()
    surf = pygame.Surface((8, 8), pygame.SRCALPHA)
    key = id(surf)
    fake_mask = pygame.Surface((8, 8), pygame.SRCALPHA)
    am._occlusion_masks[key] = fake_mask

    result = am.get_occlusion_mask(surf)
    assert result is fake_mask


def test_get_occlusion_mask_fully_opaque_returns_none():
    """Fully opaque tile (no transparent pixels) → get_occlusion_mask returns None."""
    am = AssetManager()
    # 8×8 opaque surface (no alpha)
    surf = pygame.Surface((8, 8))
    surf.fill((255, 0, 0))
    # Convert to per-pixel alpha so get_at().a works
    surf = surf.convert_alpha()
    # Fill fully opaque
    for x in range(8):
        for y in range(8):
            surf.set_at((x, y), (255, 0, 0, 255))

    result = am.get_occlusion_mask(surf)
    assert result is None


def test_get_occlusion_mask_transparent_pixel_returns_surface():
    """Tile with at least one transparent pixel → returns a pygame.Surface mask."""
    am = AssetManager()
    surf = pygame.Surface((4, 4), pygame.SRCALPHA)
    surf.fill((255, 0, 0, 0))  # fully transparent

    result = am.get_occlusion_mask(surf)
    assert isinstance(result, pygame.Surface)


# ── clear_cache ────────────────────────────────────────────────────────────────


def test_clear_cache_empties_all_dicts():
    """clear_cache() resets images, tilesets, sounds, fonts, and occlusion_masks."""
    am = AssetManager()
    am._images["a"] = pygame.Surface((1, 1))
    am._fonts[("f", 10)] = MagicMock()
    am._occlusion_masks[99] = None

    am.clear_cache()

    assert am._images == {}
    assert am._fonts == {}
    assert am._occlusion_masks == {}
