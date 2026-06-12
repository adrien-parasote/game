"""Tests for AnimationMapManager (src/map/animation.py).

Covers: no-data fallback, static tile (no frames), animated tile frame cycling,
        zero-duration guard, missing frame_gid fallback.
"""

from unittest.mock import MagicMock, patch

import pygame
import pytest


def _make_manager(tiles: dict):
    """Build an AnimationMapManager with a mocked MapManager."""
    from src.map.animation import AnimationMapManager

    mm = MagicMock()
    mm.tiles = tiles
    return AnimationMapManager(mm)


# ── No tile data ────────────────────────────────────────────────────────────────


def test_get_current_frame_image_unknown_tile_returns_none():
    """Tile ID not in tiles dict → returns None."""
    manager = _make_manager({})
    result = manager.get_current_frame_image(99)
    assert result is None


def test_get_current_frame_image_no_frames_returns_base_image():
    """Tile with no frames list → returns tile_data.image directly (static tile)."""
    fake_surf = pygame.Surface((32, 32))
    tile_data = MagicMock()
    tile_data.frames = None
    tile_data.image = fake_surf

    manager = _make_manager({1: tile_data})
    result = manager.get_current_frame_image(1)
    assert result is fake_surf


def test_get_current_frame_image_empty_frames_returns_base_image():
    """Tile with empty frames list → returns base image (not animated)."""
    fake_surf = pygame.Surface((32, 32))
    tile_data = MagicMock()
    tile_data.frames = []
    tile_data.image = fake_surf

    manager = _make_manager({1: tile_data})
    result = manager.get_current_frame_image(1)
    assert result is fake_surf


# ── Zero-duration guard ─────────────────────────────────────────────────────────


def test_get_current_frame_image_zero_duration_returns_first_frame():
    """When total_duration == 0, the first frame_gid is used."""
    base_surf = pygame.Surface((32, 32))
    frame_surf = pygame.Surface((32, 32))

    tile_data = MagicMock()
    tile_data.frames = [(10, 0), (11, 0)]  # zero durations
    tile_data.image = base_surf

    frame_tile = MagicMock()
    frame_tile.image = frame_surf

    manager = _make_manager({1: tile_data, 10: frame_tile})
    result = manager.get_current_frame_image(1)
    # First frame_gid = 10 → frame_surf
    assert result is frame_surf


# ── Normal animated cycling ─────────────────────────────────────────────────────


def test_get_current_frame_image_selects_correct_frame_by_time():
    """Frame selection follows absolute time modulo total duration."""
    frame_surf_a = pygame.Surface((32, 32))
    frame_surf_b = pygame.Surface((32, 32))
    base_surf = pygame.Surface((32, 32))

    tile_data = MagicMock()
    tile_data.frames = [(10, 500), (11, 500)]  # two 500ms frames, total=1000ms
    tile_data.image = base_surf

    frame_a = MagicMock()
    frame_a.image = frame_surf_a
    frame_b = MagicMock()
    frame_b.image = frame_surf_b

    tiles = {1: tile_data, 10: frame_a, 11: frame_b}
    manager = _make_manager(tiles)

    # At t=250ms → time_in_cycle=250 < 500 → frame 10
    with patch("pygame.time.get_ticks", return_value=250):
        result = manager.get_current_frame_image(1)
    assert result is frame_surf_a

    # At t=750ms → time_in_cycle=750 ≥ 500 → frame 11
    with patch("pygame.time.get_ticks", return_value=750):
        result = manager.get_current_frame_image(1)
    assert result is frame_surf_b


def test_get_current_frame_image_missing_frame_gid_returns_base():
    """If the resolved frame_gid is absent from tiles, fall back to base image."""
    base_surf = pygame.Surface((32, 32))
    tile_data = MagicMock()
    tile_data.frames = [(999, 100)]  # 999 does not exist in tiles
    tile_data.image = base_surf

    manager = _make_manager({1: tile_data})

    with patch("pygame.time.get_ticks", return_value=0):
        result = manager.get_current_frame_image(1)
    assert result is base_surf
