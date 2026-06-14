"""Tests for SpriteSheet (src/graphics/spritesheet.py).

Covers: invalid/empty path → valid=False, non-existent file → valid=False,
        pygame load error → valid=False, load_grid fallback, load_grid_by_size fallback,
        successful grid slicing on a real surface.
"""
# TC traceability: engine-core.md §SpriteSheet (graphics/spritesheet.py)
# TC IDs to be assigned when spec test case table is added.

import logging
from unittest.mock import patch

import pygame
import pytest

# ── Constructor — invalid paths ────────────────────────────────────────────────


def test_empty_filename_is_invalid():
    """SpriteSheet('') → valid=False, sheet=None (no-sprite case)."""
    from src.graphics.spritesheet import SpriteSheet

    ss = SpriteSheet("")
    assert ss.valid is False
    assert ss.sheet is None


def test_directory_path_is_invalid():
    """SpriteSheet('/some/dir/') → valid=False (directory, not a file)."""
    from src.graphics.spritesheet import SpriteSheet

    ss = SpriteSheet("/some/dir/")
    assert ss.valid is False


def test_missing_file_is_invalid(tmp_path):
    """SpriteSheet pointing to a non-existent file → valid=False."""
    from src.graphics.spritesheet import SpriteSheet

    ss = SpriteSheet(str(tmp_path / "nonexistent.png"))
    assert ss.valid is False
    assert ss.sheet is None


def test_pygame_error_on_load_is_invalid(tmp_path):
    """SpriteSheet that triggers pygame.error during load → valid=False."""
    from src.graphics.spritesheet import SpriteSheet

    fake_file = tmp_path / "bad.png"
    fake_file.write_bytes(b"not a real png")

    with patch("pygame.image.load", side_effect=pygame.error("bad image")):
        ss = SpriteSheet(str(fake_file))

    assert ss.valid is False
    assert ss.sheet is None


# ── load_grid — fallback (invalid sheet) ───────────────────────────────────────


def test_load_grid_fallback_when_invalid():
    """load_grid on invalid sheet returns list of (cols*rows) dummy surfaces."""
    from src.graphics.spritesheet import SpriteSheet

    ss = SpriteSheet("")
    frames = ss.load_grid(4, 4)
    assert len(frames) == 16
    assert all(isinstance(f, pygame.Surface) for f in frames)


def test_load_grid_by_size_fallback_when_invalid():
    """load_grid_by_size on invalid sheet returns 16 dummy surfaces of the given size."""
    from src.graphics.spritesheet import SpriteSheet

    ss = SpriteSheet("")
    frames = ss.load_grid_by_size(32, 32)
    assert len(frames) == 16
    for f in frames:
        assert isinstance(f, pygame.Surface)


# ── Successful slicing ─────────────────────────────────────────────────────────


def test_load_grid_slices_correctly():
    """load_grid on a valid 64x64 surface with 2 cols x 2 rows -> 4 surfaces of 32x32."""
    from src.graphics.spritesheet import SpriteSheet

    # Build a fake 64x64 sheet
    sheet_surf = pygame.Surface((64, 64), pygame.SRCALPHA)

    ss = SpriteSheet.__new__(SpriteSheet)
    ss.filename = "fake"
    ss.sheet = sheet_surf
    ss.valid = True

    frames = ss.load_grid(2, 2)
    assert len(frames) == 4
    for f in frames:
        assert f.get_size() == (32, 32)


def test_load_grid_by_size_stores_last_cols():
    """load_grid_by_size stores last_cols for callers that need column count."""
    from src.graphics.spritesheet import SpriteSheet

    sheet_surf = pygame.Surface((128, 64), pygame.SRCALPHA)

    ss = SpriteSheet.__new__(SpriteSheet)
    ss.filename = "fake"
    ss.sheet = sheet_surf
    ss.valid = True

    ss.load_grid_by_size(32, 32)
    # 128 // 32 = 4 cols
    assert ss.last_cols == 4


def test_load_grid_transparent_fallback_surface():
    """load_grid with transparent=True returns SRCALPHA surfaces in fallback path."""
    from src.graphics.spritesheet import SpriteSheet

    ss = SpriteSheet("")  # invalid → fallback path
    frames = ss.load_grid(2, 2, transparent=True)
    assert len(frames) == 4
    for f in frames:
        # SRCALPHA flag means per-pixel alpha — can be detected via get_flags()
        assert f.get_flags() & pygame.SRCALPHA
