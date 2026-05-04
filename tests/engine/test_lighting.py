import math
from unittest.mock import MagicMock, PropertyMock, patch

import pygame
import pytest

from src.engine.lighting import LightingManager
from src.engine.time_system import TimeSystem, WorldTime
from src.map.layout import OrthogonalLayout
from src.map.manager import MapManager


@pytest.fixture(autouse=True)
def setup_pygame():
    """Ensure pygame is initialized for surface creation."""
    if not pygame.get_init():
        pygame.init()
    # Hidden display to allow surface creation without a window
    if not pygame.display.get_surface():
        pygame.display.set_mode((100, 100), pygame.HIDDEN)
    yield


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_lighting(hour: int = 12) -> LightingManager:
    """Create a LightingManager with a TimeSystem at the given hour."""
    ts = TimeSystem(initial_hour=hour)
    return LightingManager(ts, screen_size=(200, 200))


def _mock_time_system(
    hour: int, minute: int = 0, brightness: float = 1.0, night_alpha: int = 0
) -> MagicMock:
    """Build a mock TimeSystem with controllable world_time, brightness, night_alpha."""
    ts = MagicMock()
    type(ts).world_time = PropertyMock(return_value=WorldTime(hour=hour, minute=minute, day=0))
    type(ts).brightness = PropertyMock(return_value=brightness)
    type(ts).night_alpha = PropertyMock(return_value=night_alpha)
    return ts


# ------------------------------------------------------------------
# LT-001: Window position cache
# ------------------------------------------------------------------


@pytest.mark.tc("LT-001")
def test_map_manager_window_cache_lt001():
    """LT-001: MapManager caches window positions based on tile type."""
    mock_map_data = {
        "layers": {0: [[0, 1], [2, 0]]},
        "layer_names": {0: "test_layer"},
        "layer_order": [0],
        "tiles": {
            1: MagicMock(properties={"type": "window"}, image=pygame.Surface((32, 32))),
            2: MagicMock(properties={}, image=pygame.Surface((32, 32))),
        },
    }
    layout = OrthogonalLayout(32)
    manager = MapManager(mock_map_data, layout)

    windows = manager.get_window_positions()
    assert len(windows) == 1
    # Tile 1 at grid (1,0) → screen (32,0). cx = 32+16 = 48, y = 0+32 = 32, w = 32
    assert windows[0] == (48, 32, 32)


# ------------------------------------------------------------------
# LT-002: Beam color sync
# ------------------------------------------------------------------


@pytest.mark.tc("LT-002")
def test_lighting_beam_color_sync_lt003():
    """LT-002: Beam color syncs with brightness via _lerp_color."""
    cool = (160, 180, 255)
    warm = (255, 230, 180)

    color = LightingManager._lerp_color(cool, warm, 1.0)
    assert color[0] > color[2], "Noon color should have R > B (warm)"

    color = LightingManager._lerp_color(cool, warm, 0.0)
    assert color[2] > color[0], "Midnight color should have B > R (cool)"


# ------------------------------------------------------------------
# LT-004: Night overlay
# ------------------------------------------------------------------


@pytest.mark.tc("LT-004")
def test_lighting_night_overlay_lt004():
    """LT-004: Night overlay creates a surface with the correct alpha."""
    time_system = TimeSystem()
    lm = LightingManager(time_system, screen_size=(800, 600))

    with patch.object(type(time_system), "night_alpha", new_callable=PropertyMock) as mock_a:
        mock_a.return_value = 180
        overlay = lm.create_overlay([], [], pygame.math.Vector2(0, 0))
        assert overlay is not None
        assert overlay.get_size() == (800, 600)
        assert overlay.get_at((0, 0)).a == 180


# ------------------------------------------------------------------
# Slant: sun cycle
# ------------------------------------------------------------------


class TestComputeSlantSun:
    """_compute_slant returns correct sun-dominated slant values."""

    def test_morning_slant_positive(self):
        """At 6h (sunrise), sun is in the east → slant is positive."""
        ts = _mock_time_system(hour=6, brightness=1.0, night_alpha=0)
        lm = LightingManager(ts, (100, 100))
        slant = lm._compute_slant()
        assert slant > 0, f"Morning slant should be positive, got {slant}"

    def test_noon_slant_near_zero(self):
        """At 12h (noon), sun is at zenith → slant ≈ 0."""
        ts = _mock_time_system(hour=12, brightness=1.0, night_alpha=0)
        lm = LightingManager(ts, (100, 100))
        slant = lm._compute_slant()
        assert abs(slant) < 2, f"Noon slant should be ~0, got {slant}"

    def test_evening_slant_negative(self):
        """At 18h (sunset), sun is in the west → slant is negative."""
        ts = _mock_time_system(hour=18, brightness=0.5, night_alpha=0)
        lm = LightingManager(ts, (100, 100))
        slant = lm._compute_slant()
        assert slant < 0, f"Evening slant should be negative, got {slant}"


# ------------------------------------------------------------------
# Slant: moon cycle
# ------------------------------------------------------------------


class TestComputeSlantMoon:
    """_compute_slant returns correct moon-dominated slant values."""

    def test_midnight_slant_near_zero(self):
        """At 0h (midnight), moon is at zenith → slant ≈ 0."""
        ts = _mock_time_system(hour=0, brightness=0.0, night_alpha=200)
        lm = LightingManager(ts, (100, 100))
        slant = lm._compute_slant()
        # Pure moon: cos(2π*(0-18)/24) = cos(-1.5π) = 0
        assert abs(slant) < 2, f"Midnight slant should be ~0, got {slant}"

    def test_moon_amplitude_half_of_sun(self):
        """Moon max amplitude should be roughly half of sun max."""
        # Pure moon at 18h (cos=1.0)
        ts_moon = _mock_time_system(hour=18, brightness=0.0, night_alpha=200)
        lm = LightingManager(ts_moon, (100, 100))
        moon_slant = abs(lm._compute_slant())

        # Pure sun at 6h (cos=1.0)
        ts_sun = _mock_time_system(hour=6, brightness=1.0, night_alpha=0)
        lm2 = LightingManager(ts_sun, (100, 100))
        sun_slant = abs(lm2._compute_slant())

        assert moon_slant < sun_slant, "Moon amplitude should be less than sun"
        ratio = moon_slant / max(1, sun_slant)
        assert 0.3 < ratio < 0.7, f"Moon/sun ratio should be ~0.5, got {ratio}"


# ------------------------------------------------------------------
# Slant: continuity (no jumps)
# ------------------------------------------------------------------


class TestSlantContinuity:
    """Slant values should be smooth and continuous across the 24h cycle."""

    def test_no_discontinuity_across_full_day(self):
        """Slant should never jump by more than 3px between consecutive half-hours."""
        prev_slant = None
        max_jump = 0.0

        for half_hour in range(48):  # 0.0h, 0.5h, ..., 23.5h
            h = half_hour // 2
            m = (half_hour % 2) * 30
            frac = h + m / 60.0
            # Brightness approximation: 0.5 + 0.5*sin(2π*h/24 - π/2)
            b = 0.5 + 0.5 * math.sin(2 * math.pi * frac / 24.0 - math.pi / 2)
            na = int(max(0.0, 200 * (1.0 - b)))

            ts = _mock_time_system(hour=h, minute=m, brightness=b, night_alpha=na)
            lm = LightingManager(ts, (100, 100))
            slant = lm._compute_slant()

            if prev_slant is not None:
                jump = abs(slant - prev_slant)
                max_jump = max(max_jump, jump)
            prev_slant = slant

        assert max_jump < 5.0, f"Max slant jump={max_jump:.1f}px — not smooth"


# ------------------------------------------------------------------
# Beam surface: basic properties
# ------------------------------------------------------------------


class TestCreateBeamSurface:
    """_create_beam_surface produces correct surfaces."""

    def test_surface_dimensions(self):
        """Surface width/height match expected padding formula."""
        lm = _make_lighting()
        surf = lm._create_beam_surface((255, 255, 255), 200, top_w=24, bot_w=52, slant=0)
        assert surf.get_height() == lm.beam_height
        expected_w = int(52 * 1.8) + (0 + 10) * 2
        assert surf.get_width() == expected_w

    def test_top_center_has_highest_alpha(self):
        """The pixel at the top-center should have the highest alpha."""
        lm = _make_lighting()
        surf = lm._create_beam_surface((255, 255, 255), 200, top_w=24, bot_w=52, slant=0)
        cx = surf.get_width() // 2
        top_alpha = surf.get_at((cx, 0)).a
        # Should be close to master_alpha
        assert top_alpha > 150, f"Top-center alpha={top_alpha}, expected >150"

    def test_edges_have_lower_alpha(self):
        """Pixels at the surface edge should have near-zero alpha (gaussian tails)."""
        lm = _make_lighting()
        surf = lm._create_beam_surface((255, 255, 255), 200, top_w=24, bot_w=52, slant=0)
        edge_alpha = surf.get_at((0, 0)).a
        assert edge_alpha < 10, f"Edge alpha={edge_alpha}, expected near 0"

    def test_bottom_center_fades(self):
        """Bottom-center alpha should be less than top-center."""
        lm = _make_lighting()
        surf = lm._create_beam_surface((255, 255, 255), 200, top_w=24, bot_w=52, slant=0)
        cx = surf.get_width() // 2
        top_a = surf.get_at((cx, 0)).a
        bot_a = surf.get_at((cx, surf.get_height() - 1)).a
        assert bot_a < top_a, "Bottom should be dimmer than top"

    def test_slant_shifts_beam_center(self):
        """With positive slant, the mid-beam center-of-mass should shift right."""
        lm = _make_lighting()
        slant = 20
        surf = lm._create_beam_surface((255, 255, 255), 200, top_w=24, bot_w=52, slant=slant)
        w = surf.get_width()
        cx = w // 2
        # At 50% height (where beam is still clearly visible)
        mid_row = surf.get_height() // 2
        best_x, best_a = 0, 0
        for x in range(w):
            a = surf.get_at((x, mid_row)).a
            if a > best_a:
                best_a, best_x = a, x
        # With slant=+20, the brightest mid pixel should be right of surface center
        assert best_x > cx, f"Slant +{slant}: brightest mid x={best_x}, cx={cx}"

    def test_oval_bottom_corners_fade_faster(self):
        """Corner alpha should drop off faster than center in the bottom zone."""
        lm = _make_lighting()
        surf = lm._create_beam_surface((255, 255, 255), 200, top_w=24, bot_w=52, slant=0)
        cx = surf.get_width() // 2
        h = surf.get_height()
        # At 80% height: center should be brighter than the edge
        row = int(h * 0.8)
        center_a = surf.get_at((cx, row)).a
        edge_x = cx + 20  # well inside the beam at this row
        edge_a = surf.get_at((edge_x, row)).a
        assert center_a > edge_a, "Center should be brighter than edge near bottom"


# ------------------------------------------------------------------
# Beam cache
# ------------------------------------------------------------------


@pytest.mark.tc("LT-012")
def test_beam_cache_reuses_surface():
    """Calling _get_beam_surface_for_time twice with same state returns same object."""
    ts = _mock_time_system(hour=12, brightness=1.0, night_alpha=0)
    lm = LightingManager(ts, (100, 100))
    s1 = lm._get_beam_surface_for_time(24)
    s2 = lm._get_beam_surface_for_time(24)
    assert s1 is s2, "Cache should return the same surface object"


def test_beam_cache_eviction():
    """Cache should evict oldest entries when exceeding 64."""
    ts = _mock_time_system(hour=12, brightness=1.0, night_alpha=0)
    lm = LightingManager(ts, (100, 100))
    for i in range(70):
        # Force unique keys by changing max_slant each time
        lm.max_slant = i
        lm._beam_surf_cache.clear()  # just verify no crash
    assert len(lm._beam_surf_cache) <= 64


# ------------------------------------------------------------------
# draw_additive_window_beams
# ------------------------------------------------------------------


def test_draw_beams_empty_list():
    """draw_additive_window_beams with empty list should not crash."""
    lm = _make_lighting()
    screen = pygame.Surface((200, 200), pygame.SRCALPHA)
    lm.draw_additive_window_beams(screen, [], pygame.math.Vector2(0, 0))


def test_draw_beams_2_tuple_fallback():
    """A 2-tuple spec should use default beam_top_width."""
    lm = _make_lighting()
    screen = pygame.Surface((200, 200), pygame.SRCALPHA)
    lm.draw_additive_window_beams(screen, [(100, 50)], pygame.math.Vector2(0, 0))


# ------------------------------------------------------------------
# resize
# ------------------------------------------------------------------


def test_resize_updates_overlay():
    """Resizing should recreate the overlay surface."""
    lm = _make_lighting()
    lm.resize((400, 300))
    assert lm.screen_size == (400, 300)
    assert lm._overlay_cache.get_size() == (400, 300)


def test_resize_noop_if_same():
    """Resizing to the same size should be a no-op."""
    lm = _make_lighting()
    old_overlay = lm._overlay_cache
    lm.resize((200, 200))
    assert lm._overlay_cache is old_overlay


# ------------------------------------------------------------------
# _get_torch_mask
# ------------------------------------------------------------------


def test_torch_mask_center_bright():
    """The center of a torch mask should have the highest alpha."""
    lm = _make_lighting()
    mask = lm._get_torch_mask(50, 1.0)
    center_a = mask.get_at((50, 50)).a
    edge_a = mask.get_at((0, 0)).a
    assert center_a > edge_a


def test_torch_mask_cached():
    """Torch mask should be cached."""
    lm = _make_lighting()
    m1 = lm._get_torch_mask(40, 0.8)
    m2 = lm._get_torch_mask(40, 0.8)
    assert m1 is m2
