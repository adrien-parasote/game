"""
RED test for UT-006: LightingManager uses BEAM_COLOR_MOON/SUN constants.

Spec: docs/specs/perf-constants-spec.md#feature-p-const-01a--lighting-beam-colors
"""
from unittest.mock import MagicMock, patch

import pytest


def test_lighting_uses_beam_color_constants():
    """UT-006: _get_beam_surface_for_time must use BEAM_COLOR_MOON and BEAM_COLOR_SUN."""
    from src.engine.lighting_constants import BEAM_COLOR_MOON, BEAM_COLOR_SUN

    captured_colors = []

    def capture_lerp(c1, c2, t):
        captured_colors.append((c1, c2, t))
        return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

    from src.engine.lighting import LightingManager

    # Build a minimal LightingManager-like object bypassing full __init__
    lm = object.__new__(LightingManager)
    lm._beam_surf_cache = {}
    lm._lerp_color = capture_lerp

    # time_system mock: brightness=1.0 (full sun)
    mock_ts = MagicMock()
    mock_ts.brightness = 1.0
    lm.time_system = mock_ts
    lm.beam_top_width = 24
    lm.beam_bottom_width = 52

    # Patch downstream helpers so we don't need a full init
    lm._compute_slant = lambda: 0
    lm._create_beam_surface = lambda *a, **kw: MagicMock()

    lm._get_beam_surface_for_time()

    assert captured_colors, "_lerp_color was never called"
    found = any(c1 == BEAM_COLOR_MOON and c2 == BEAM_COLOR_SUN for c1, c2, _ in captured_colors)
    assert found, (
        f"Expected _lerp_color called with BEAM_COLOR_MOON={BEAM_COLOR_MOON} "
        f"and BEAM_COLOR_SUN={BEAM_COLOR_SUN}. Got: {captured_colors}"
    )
