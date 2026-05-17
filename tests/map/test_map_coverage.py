from unittest.mock import MagicMock

import pygame
import pytest

from src.map.animation import AnimationMapManager
from src.map.layout import OrthogonalLayout


def test_animation_manager_edge_cases():
    """Test AnimationMapManager edge cases (L17, 30, 46)."""
    mock_map = MagicMock()
    amm = AnimationMapManager(mock_map)

    # L17: update is pass
    amm.update(16)

    # L30: total_duration <= 0
    tile_data = MagicMock()
    tile_data.frames = [(100, 0)] # gid 100, duration 0
    tile_data.image = MagicMock(spec=pygame.Surface)
    mock_map.tiles.get.side_effect = lambda tid: tile_data if tid == 1 else None

    # L46: fallback to base image when frame_gid missing in manager
    assert amm.get_current_frame_image(1) == tile_data.image

def test_map_layout_orthogonal():
    """Test OrthogonalLayout (coverage for L27, 30)."""
    layout = OrthogonalLayout(tile_size=32)
    assert layout.to_screen(1, 1) == (32, 32)
    assert layout.to_world(32, 32) == (1.0, 1.0)
