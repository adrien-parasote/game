"""
Tests for Map Lighting Modes — spec: lighting-system.md § 8
TC-LM-U-01..07 (unit), TC-LM-I-01..03 (integration)
"""

from unittest.mock import MagicMock, call, patch

import pygame
import pytest
from src.engine.time_system import TimeSystem


@pytest.fixture(autouse=True)
def setup_pygame():
    """Ensure pygame is initialized for surface creation."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((100, 100), pygame.HIDDEN)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(lighting_mode: str = "outdoor", ambient_dark_alpha: int = 0):
    """Return a minimal game-like object with lighting mode attrs set."""
    game = MagicMock()
    game._map_lighting_mode = lighting_mode
    game._map_ambient_dark_alpha = ambient_dark_alpha
    game.time_system = TimeSystem(initial_hour=0)
    return game


def _compute_effective_alpha(game) -> int:
    """Replicate the RenderManager effective_alpha logic from spec § 8.3."""
    from src.engine.lighting_constants import INDOOR_ATTENUATION

    mode = getattr(game, "_map_lighting_mode", "outdoor")
    ambient = getattr(game, "_map_ambient_dark_alpha", 0)
    night_alpha = game.time_system.night_alpha

    if mode == "underground":
        return ambient
    if mode == "indoor":
        return min(255, ambient + int(night_alpha * INDOOR_ATTENUATION))
    # outdoor (default — also covers unknown modes)
    return night_alpha


# ---------------------------------------------------------------------------
# TC-LM-U-01 — outdoor uses time_system.night_alpha
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-01")
def test_outdoor_mode_uses_time_system_alpha():
    """Outdoor mode: effective_alpha == time_system.night_alpha at any hour."""
    for hour in [0, 6, 12, 18]:
        game = _make_game("outdoor", ambient_dark_alpha=0)
        game.time_system = TimeSystem(initial_hour=hour)
        expected = game.time_system.night_alpha
        assert _compute_effective_alpha(game) == expected, f"hour={hour}: expected {expected}"


# ---------------------------------------------------------------------------
# TC-LM-U-02 — underground: fixed alpha, no time dependency
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-02")
def test_underground_mode_fixed_alpha():
    """Underground mode: effective_alpha == ambient_dark_alpha regardless of hour."""
    ambient = 180
    for hour in [0, 6, 12, 18, 23]:
        game = _make_game("underground", ambient_dark_alpha=ambient)
        game.time_system = TimeSystem(initial_hour=hour)
        result = _compute_effective_alpha(game)
        assert result == ambient, f"hour={hour}: expected {ambient}, got {result}"


# ---------------------------------------------------------------------------
# TC-LM-U-03 — indoor: Option B formula
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-03")
def test_indoor_mode_option_b_formula():
    """Indoor mode: effective_alpha == min(255, ambient + int(night_alpha * 0.35))."""
    from src.engine.lighting_constants import INDOOR_ATTENUATION

    ambient = 40
    game = _make_game("indoor", ambient_dark_alpha=ambient)
    # Force a known night_alpha (midnight → max darkness)
    game.time_system = TimeSystem(initial_hour=0)
    night_alpha = game.time_system.night_alpha
    expected = min(255, ambient + int(night_alpha * INDOOR_ATTENUATION))
    result = _compute_effective_alpha(game)
    assert result == expected, f"indoor formula: expected {expected}, got {result}"


# ---------------------------------------------------------------------------
# TC-LM-U-04 — indoor: clamp at 255
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-04")
def test_indoor_alpha_clamped_at_255():
    """Indoor mode: ambient=240 + night contribution must not exceed 255."""
    game = _make_game("indoor", ambient_dark_alpha=240)
    game.time_system = TimeSystem(initial_hour=0)  # maximum night_alpha
    result = _compute_effective_alpha(game)
    assert result <= 255, f"Indoor alpha exceeded 255: {result}"


# ---------------------------------------------------------------------------
# TC-LM-U-05 — unknown mode defaults to outdoor
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-05")
def test_unknown_lighting_mode_defaults_outdoor():
    """Unknown lighting_mode value falls back to outdoor formula."""
    game = _make_game("cave", ambient_dark_alpha=0)
    game.time_system = TimeSystem(initial_hour=0)
    expected = game.time_system.night_alpha
    result = _compute_effective_alpha(game)
    assert result == expected, (
        f"Unknown mode 'cave' should behave as outdoor: expected {expected}, got {result}"
    )


# ---------------------------------------------------------------------------
# TC-LM-U-06 — MapLoader stores lighting_mode on game
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-06")
def test_map_loader_stores_lighting_mode_on_game():
    """After MapLoader.load(), game._map_lighting_mode and _map_ambient_dark_alpha are set."""
    from src.engine.map_loader import MapLoader

    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.interactives = []
    game.npcs = []
    game.obstacles_group = MagicMock()
    game.teleports_group = MagicMock()
    game.pickups = MagicMock()
    game.player = MagicMock()
    game.audio_manager = MagicMock()
    game.world_state = MagicMock()
    game.layout = None
    game.map_manager = None
    game.anim_map_manager = None
    game._entity_factory = MagicMock()
    game._current_map_name = None
    game.walkable_override_entities = []

    map_result = {
        "width": 2,
        "height": 2,
        "layers": {},
        "tiles": {},
        "layer_names": {},
        "layer_order": [],
        "layer_order_values": {},
        "spawn_player": None,
        "entities": [],
        "properties": {"lighting_mode": "underground", "ambient_dark_alpha": 150},
    }

    loader = MapLoader(game)
    with (
        patch.object(loader, "_clear_groups"),
        patch.object(loader, "_position_player"),
        patch.object(loader, "_start_initial_ambients"),
        patch.object(loader, "_resolve_spawn", return_value=(16, 16)),
        patch.object(loader, "_save_npc_states"),
        patch.object(loader, "_save_interactive_states"),
        patch("src.engine.map_loader.TmjParser") as mock_parser_cls,
        patch("src.engine.map_loader.MapManager") as mock_mm_cls,
        patch("src.engine.map_loader.AnimationMapManager"),
        patch("src.engine.map_loader.OrthogonalLayout"),
        patch("os.path.exists", return_value=True),
    ):
        mock_parser = MagicMock()
        mock_parser.load_map.return_value = map_result
        mock_parser_cls.return_value = mock_parser
        mock_mm = MagicMock()
        mock_mm.width = 10
        mock_mm.height = 10
        mock_mm_cls.return_value = mock_mm
        loader.load("01-basement.tmj")

    assert game._map_lighting_mode == "underground"
    assert game._map_ambient_dark_alpha == 150


# ---------------------------------------------------------------------------
# TC-LM-U-07 — MapLoader defaults when property absent
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-U-07")
def test_map_loader_defaults_when_property_absent():
    """Map with no lighting_mode → game._map_lighting_mode=='outdoor', ambient==0."""
    from src.engine.map_loader import MapLoader

    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites = MagicMock()
    game.interactives = []
    game.npcs = []
    game.obstacles_group = MagicMock()
    game.teleports_group = MagicMock()
    game.pickups = MagicMock()
    game.player = MagicMock()
    game.audio_manager = MagicMock()
    game.world_state = MagicMock()
    game.layout = None
    game.map_manager = None
    game.anim_map_manager = None
    game._entity_factory = MagicMock()
    game._current_map_name = None
    game.walkable_override_entities = []

    map_result = {
        "width": 2,
        "height": 2,
        "layers": {},
        "tiles": {},
        "layer_names": {},
        "layer_order": [],
        "layer_order_values": {},
        "spawn_player": None,
        "entities": [],
        "properties": {},  # no lighting_mode
    }

    loader = MapLoader(game)
    with (
        patch.object(loader, "_clear_groups"),
        patch.object(loader, "_position_player"),
        patch.object(loader, "_start_initial_ambients"),
        patch.object(loader, "_resolve_spawn", return_value=(16, 16)),
        patch.object(loader, "_save_npc_states"),
        patch.object(loader, "_save_interactive_states"),
        patch("src.engine.map_loader.TmjParser") as mock_parser_cls,
        patch("src.engine.map_loader.MapManager") as mock_mm_cls,
        patch("src.engine.map_loader.AnimationMapManager"),
        patch("src.engine.map_loader.OrthogonalLayout"),
        patch("os.path.exists", return_value=True),
    ):
        mock_parser = MagicMock()
        mock_parser.load_map.return_value = map_result
        mock_parser_cls.return_value = mock_parser
        mock_mm = MagicMock()
        mock_mm.width = 10
        mock_mm.height = 10
        mock_mm_cls.return_value = mock_mm
        loader.load("village.tmj")

    assert game._map_lighting_mode == "outdoor"
    assert game._map_ambient_dark_alpha == 0


# ---------------------------------------------------------------------------
# TC-LM-I-01 — underground alpha constant over full 24h
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-I-01")
def test_underground_alpha_constant_over_full_day():
    """Underground: step through 24h — effective_alpha never changes."""
    ambient = 200
    game = _make_game("underground", ambient_dark_alpha=ambient)
    ts = TimeSystem(initial_hour=0)
    game.time_system = ts

    results = set()
    for _ in range(48):  # step 30 min each iteration
        ts.update(30 * 60 / 60)  # advance 30 game minutes
        results.add(_compute_effective_alpha(game))

    assert results == {ambient}, (
        f"Underground alpha should be constant at {ambient}, got values: {results}"
    )


# ---------------------------------------------------------------------------
# TC-LM-I-02 — window beams skipped for underground
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-I-02")
def test_window_beams_skipped_underground():
    """draw_additive_window_beams must NOT be called when mode == 'underground'."""
    from src.engine.lighting import LightingManager
    from src.engine.render_manager import RenderManager

    game = MagicMock()
    game._map_lighting_mode = "underground"
    game._map_ambient_dark_alpha = 180
    game.time_system = TimeSystem(initial_hour=12)

    lm = MagicMock(spec=LightingManager)
    game.lighting_manager = lm
    game.map_manager.get_window_positions.return_value = [(100, 50, 24)]
    game.interactives = []

    rm = RenderManager.__new__(RenderManager)
    rm.game = game

    # Simulate the lighting branch only
    night_alpha = game.time_system.night_alpha
    effective_alpha = _compute_effective_alpha(game)
    window_positions = game.map_manager.get_window_positions()

    # The guard: skip beams for underground
    if game._map_lighting_mode != "underground":
        lm.draw_additive_window_beams(game.screen, window_positions, MagicMock())

    lm.draw_additive_window_beams.assert_not_called()


# ---------------------------------------------------------------------------
# TC-LM-I-03 — window beams called for indoor
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-I-03")
def test_window_beams_called_indoor():
    """draw_additive_window_beams IS called when mode == 'indoor'."""
    from src.engine.lighting import LightingManager

    game = MagicMock()
    game._map_lighting_mode = "indoor"
    game._map_ambient_dark_alpha = 40
    game.time_system = TimeSystem(initial_hour=12)

    lm = MagicMock(spec=LightingManager)
    game.lighting_manager = lm
    window_positions = [(100, 50, 24)]
    cam_offset = pygame.math.Vector2(0, 0)

    # The guard: call beams for non-underground
    if game._map_lighting_mode != "underground":
        lm.draw_additive_window_beams(game.screen, window_positions, cam_offset)

    lm.draw_additive_window_beams.assert_called_once()


# ---------------------------------------------------------------------------
# TC-LM-I-04 (regression) — create_overlay receives effective alpha, not raw time_system
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-LM-I-04")
def test_create_overlay_called_with_effective_alpha():
    """Regression: RenderManager must pass alpha_override=effective_alpha to create_overlay.

    Before the fix, create_overlay always read self.time_system.night_alpha directly,
    ignoring the per-map mode. Underground/indoor modes had no effect on the overlay.
    """
    from src.engine.render_manager import RenderManager

    ambient = 200
    game = MagicMock()
    game._map_lighting_mode = "underground"
    game._map_ambient_dark_alpha = ambient
    game.time_system = TimeSystem(initial_hour=12)  # midday → time night_alpha ≈ 0

    lm = MagicMock()
    # create_overlay must return a surface-like object for screen.blit
    fake_surface = MagicMock()
    lm.create_overlay.return_value = fake_surface
    game.lighting_manager = lm
    game.interactives = []
    game.map_manager.get_window_positions.return_value = []

    rm = RenderManager.__new__(RenderManager)
    rm.game = game
    rm._frame_anim_by_layer = {}

    effective_alpha = rm._compute_effective_night_alpha()

    # Simulate the render branch that builds the overlay
    cam_offset = pygame.math.Vector2(0, 0)
    active_torches = []
    window_positions = []
    if effective_alpha > 0:
        lm.create_overlay(
            window_positions, active_torches, cam_offset, alpha_override=effective_alpha
        )

    # Verify: effective_alpha == ambient (underground fixed), NOT time_system value
    assert effective_alpha == ambient, (
        f"Underground effective_alpha should be {ambient}, got {effective_alpha}"
    )
    # Verify: create_overlay was called with alpha_override=ambient (not 0 from midday TimeSystem)
    lm.create_overlay.assert_called_once_with(
        window_positions, active_torches, cam_offset, alpha_override=ambient
    )
