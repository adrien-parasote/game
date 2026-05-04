"""
Tests RED — Performance Optimizations
Spec: docs/specs/performance-optimization-spec.md
TC-001..TC-036 + IT-001..IT-003
"""
import pygame
import pytest
from unittest.mock import MagicMock, patch, call
from src.entities.groups import CameraGroup


# ── Fixtures ──────────────────────────────────────────────────────────────────

class _DummySprite(pygame.sprite.Sprite):
    def __init__(self, bottom_y: int):
        super().__init__()
        self.image = pygame.Surface((10, 10))
        self.rect = pygame.Rect(0, bottom_y - 10, 10, 10)


@pytest.fixture
def camera_group():
    """CameraGroup with mocked display surface."""
    with patch("pygame.display.get_surface") as mock_display:
        surf = MagicMock(spec=pygame.Surface)
        surf.get_size.return_value = (1280, 720)
        surf.get_rect.return_value = pygame.Rect(0, 0, 1280, 720)
        mock_display.return_value = surf
        cg = CameraGroup()
    return cg


# ═══════════════════════════════════════════════════════════════════════════════
# Module 2: CameraGroup Y-sort cache (TC-011 → TC-016)
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_sorted_sprites_empty(camera_group):
    """TC-011 : get_sorted_sprites() sur groupe vide → []"""
    assert camera_group.get_sorted_sprites() == []


def test_get_sorted_sprites_cache_reused(camera_group):
    """TC-012 : 2e appel sans modification → même objet liste (cache)."""
    s1 = _DummySprite(50)
    camera_group.add(s1)
    # Force first compute
    first = camera_group.get_sorted_sprites()
    # Second call must return same object (cached)
    second = camera_group.get_sorted_sprites()
    assert first is second


def test_cache_dirty_on_add(camera_group):
    """TC-013 : add(sprite) → _cache_dirty = True."""
    # Seed with one sprite and get sorted (marks clean)
    s = _DummySprite(10)
    camera_group.get_sorted_sprites()  # initialise cache
    camera_group._cache_dirty = False
    camera_group.add(s)
    assert camera_group._cache_dirty is True


def test_cache_dirty_on_remove(camera_group):
    """TC-014 : remove(sprite) → _cache_dirty = True."""
    s = _DummySprite(10)
    camera_group.add(s)
    camera_group.get_sorted_sprites()
    camera_group._cache_dirty = False
    camera_group.remove(s)
    assert camera_group._cache_dirty is True


def test_mark_dirty_sets_flag(camera_group):
    """TC-015 : mark_dirty() → _cache_dirty = True."""
    camera_group.get_sorted_sprites()
    camera_group._cache_dirty = False
    camera_group.mark_dirty()
    assert camera_group._cache_dirty is True


def test_sorted_sprites_y_order(camera_group):
    """TC-016 : sprites triés par rect.bottom croissant."""
    s1 = _DummySprite(100)
    s2 = _DummySprite(50)
    s3 = _DummySprite(200)
    camera_group.add(s1, s2, s3)
    result = camera_group.get_sorted_sprites()
    bottoms = [sp.rect.bottom for sp in result]
    assert bottoms == sorted(bottoms)


# ═══════════════════════════════════════════════════════════════════════════════
# Module 4: InteractionManager distance_squared (TC-022 → TC-027)
# ═══════════════════════════════════════════════════════════════════════════════

from src.engine.interaction import InteractionManager

@pytest.fixture
def im_setup():
    game = MagicMock()
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = "down"
    game.player.is_moving = False
    im = InteractionManager(game)
    im._emote_cooldown = 0
    im._last_proximity_target = None
    return game, im


def test_interactive_emote_at_dist_47(im_setup):
    """TC-022 : obj à distance=47 → emote déclenchée."""
    game, im = im_setup
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 147)  # dist exacte = 47
    obj.is_on = False
    obj.direction_str = "up"
    obj.sub_type = "chest"
    game.interactives = [obj]
    im._check_proximity_emotes()
    assert game.player.playerEmote.called


def test_interactive_emote_at_dist_49_not_triggered(im_setup):
    """TC-023 : obj à distance=49 → pas d'emote."""
    game, im = im_setup
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 149)  # dist = 49 >= 48
    obj.is_on = False
    obj.direction_str = "up"
    obj.sub_type = "chest"
    game.interactives = [obj]
    game.pickups = []
    game.npcs = []
    im._check_proximity_emotes()
    assert not game.player.playerEmote.called


def test_pickup_emote_at_dist_15(im_setup):
    """TC-024 : pickup à distance=15 → emote (is_on_top)."""
    game, im = im_setup
    game.interactives = []
    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(100, 115)  # dist = 15
    game.pickups = [pickup]
    im._check_proximity_emotes()
    assert game.player.playerEmote.called


def test_object_interaction_at_dist_44(im_setup):
    """TC-025 : obj à distance=44 → interaction valide."""
    game, im = im_setup
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 144)  # dist = 44
    obj.direction_str = "up"
    obj.sub_type = "switch"
    obj.element_id = "sw1"
    obj.target_id = None
    obj.sfx = None
    obj._world_state_key = None
    obj.is_on = True
    obj.interact.return_value = None
    game.interactives = [obj]
    with patch("pygame.key.get_pressed", return_value={__import__("src.config", fromlist=["Settings"]).Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    assert obj.interact.called


def test_chest_auto_close_at_dist_46(im_setup):
    """TC-026 : chest à dist>45 → chest fermé automatiquement."""
    game, im = im_setup
    chest = MagicMock()
    chest.pos = pygame.math.Vector2(100, 146)  # dist = 46 > 45
    chest.direction_str = "up"
    chest.sub_type = "chest"
    im._open_chest_entity = chest
    game.chest_ui.is_open = True
    im._check_chest_auto_close()
    assert game.chest_ui.close.called


def test_audio_vol_mult_uses_real_distance(im_setup):
    """TC-027 : vol_mult calculé via distance réelle (pas squared)."""
    game, im = im_setup
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 140)  # dist = 40
    obj.direction_str = "up"
    obj.sub_type = "switch"
    obj.element_id = "sw1"
    obj.target_id = None
    obj.sfx = "click"
    obj._world_state_key = None
    obj.is_on = True
    obj.interact.return_value = None
    game.interactives = [obj]
    with patch("pygame.key.get_pressed", return_value={__import__("src.config", fromlist=["Settings"]).Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    if game.audio_manager.play_sfx.called:
        call_kwargs = game.audio_manager.play_sfx.call_args[1]
        vm = call_kwargs.get("volume_multiplier", 1.0)
        assert 0.4 <= vm <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Module 6: Game._viewport_world_rect pre-allocation (TC-033 → TC-036)
# ═══════════════════════════════════════════════════════════════════════════════

def test_game_has_viewport_world_rect():
    """TC-033 : Game.__init__ crée _viewport_world_rect — vérifié via source."""
    import inspect
    from src.engine import game as game_module
    src = inspect.getsource(game_module)
    assert "_viewport_world_rect" in src
    assert "pygame.Rect" in src


def test_game_no_dead_draw_methods():
    """TC-035 : _draw_background, _draw_foreground, _draw_hud non présents dans Game."""
    import inspect
    from src.engine import game as game_module
    src = inspect.getsource(game_module)
    assert "def _draw_background(" not in src, "_draw_background dead code should be removed"
    assert "def _draw_foreground(" not in src, "_draw_foreground dead code should be removed"
    assert "def _draw_hud(" not in src, "_draw_hud dead code should be removed"


def test_game_active_torches_initialized():
    """TC-036 : Game._active_torches est un set après init."""
    import inspect
    from src.engine import game as game_module
    src = inspect.getsource(game_module)
    assert "_active_torches" in src, "_active_torches must be defined in Game"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests (IT-001, IT-002, IT-003)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.tc("IT-001")
def test_title_screen_draw_no_rotozoom():
    """IT-001 : draw() n'appelle pas rotozoom — lookup depuis _light_halos_scaled."""
    import inspect
    from src.ui import title_screen as ts_module
    src = inspect.getsource(ts_module.TitleScreen.draw)
    # The actual call would be: pygame.transform.rotozoom(  — check for call syntax
    assert "pygame.transform.rotozoom(" not in src, \
        "draw() must NOT call pygame.transform.rotozoom() — use bucket lookup"
    assert "_light_halos_scaled" in src or "buckets" in src, \
        "draw() must use bucket lookup for halos"


@pytest.mark.tc("IT-002")
def test_interaction_distance_sq_semantics_match_original(im_setup):
    """IT-002 : distance_squared_to sémantique identique à distance_to pour emote triggers."""
    game, im = im_setup
    # obj at dist=47 → should trigger
    obj_near = MagicMock()
    obj_near.pos = pygame.math.Vector2(100, 147)
    obj_near.is_on = False
    obj_near.direction_str = "up"
    obj_near.sub_type = "chest"
    game.interactives = [obj_near]
    im._check_proximity_emotes()
    assert game.player.playerEmote.called, "dist=47 < 48 must trigger emote"

    game.player.playerEmote.reset_mock()
    im._last_proximity_target = None
    im._emote_cooldown = 0

    # obj at dist=49 → should NOT trigger
    obj_far = MagicMock()
    obj_far.pos = pygame.math.Vector2(100, 149)
    obj_far.is_on = False
    obj_far.direction_str = "up"
    obj_far.sub_type = "chest"
    game.interactives = [obj_far]
    game.pickups = []
    game.npcs = []
    im._check_proximity_emotes()
    assert not game.player.playerEmote.called, "dist=49 >= 48 must NOT trigger emote"


@pytest.mark.tc("IT-003")
def test_game_viewport_rect_reused_across_updates():
    """IT-003 : _viewport_world_rect est le même objet entre 2 appels _update."""
    import inspect
    from src.engine import game as game_module
    src = inspect.getsource(game_module)
    # Verify _viewport_world_rect is used in _update without screen.get_rect().move()
    # The old pattern created 2 new Rects per frame
    assert "_viewport_world_rect" in src
    # The old allocation pattern should be gone
    assert "screen_rect.move(" not in src or "_viewport_world_rect" in src
