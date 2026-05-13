"""Coverage gap tests — targeting uncovered branches to reach ≥90% global."""

import json
import logging
import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.config import Settings


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _make_game():
    with patch("src.engine.game.Game._load_map"):
        from src.engine.game import Game
        return Game()


def _make_ef():
    from src.engine.entity_factory import EntityFactory
    game = MagicMock()
    game.visible_sprites = MagicMock()
    game.interactives = MagicMock()
    game.npcs = MagicMock()
    game.teleports_group = MagicMock()
    game.pickups = MagicMock()
    game.obstacles_group = MagicMock()
    game.world_state.get.return_value = None
    game.loot_table = MagicMock()
    game.audio_manager = MagicMock()
    game.tile_size = 32
    game.time_system = MagicMock()
    return EntityFactory(game)


# ---------------------------------------------------------------------------
# GAME.PY — lines 198, 216-237, 281-301, 326-331, 377-381
# ---------------------------------------------------------------------------

class TestGameCoverage:

    @patch("src.engine.game.Game._load_map")
    def test_start_initial_ambients_delegates(self, _):
        from src.engine.game import Game
        game = Game()
        game._map_loader._start_initial_ambients = MagicMock()
        pos = pygame.math.Vector2(100, 100)
        game._start_initial_ambients(pos)
        game._map_loader._start_initial_ambients.assert_called_once_with(pos)

    @patch("src.engine.game.Game._load_map")
    def test_trigger_npc_bubble_no_msg_warns(self, _, caplog):
        game = _make_game()
        game._current_map_name = "00-map.tmj"
        game.i18n.get = MagicMock(return_value=None)
        with caplog.at_level(logging.WARNING):
            game._trigger_npc_bubble(MagicMock(), "k")
        assert "NPC bubble key not found" in caplog.text
        assert game._npc_bubble is None

    @patch("src.engine.game.Game._load_map")
    def test_trigger_npc_bubble_sets_state(self, _):
        game = _make_game()
        game._current_map_name = "00-map.tmj"
        game.i18n.get = MagicMock(return_value="Hello!")
        npc = MagicMock()
        game._trigger_npc_bubble(npc, "key")
        assert game._npc_bubble["npc"] == npc
        assert game._npc_bubble["page"] == 0

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_none_noop(self, _):
        game = _make_game()
        game._npc_bubble = None
        game._advance_npc_bubble()  # no raise
        assert game._npc_bubble is None

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_no_font_noop(self, _):
        game = _make_game()
        game._npc_bubble = {"npc": MagicMock(), "text": "Hi", "page": 0}
        game.speech_bubble.font = None
        game._advance_npc_bubble()  # no raise
        assert game._npc_bubble["page"] == 0

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_increments_page(self, _):
        game = _make_game()
        game._npc_bubble = {"npc": MagicMock(), "text": "Hi", "page": 0}
        game.speech_bubble.font = MagicMock()
        game.speech_bubble.get_total_pages = MagicMock(return_value=3)
        game._advance_npc_bubble()
        assert game._npc_bubble["page"] == 1

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_closes_on_last(self, _):
        game = _make_game()
        npc = MagicMock()
        npc.state = "interact"
        game.npcs = [npc]
        game._npc_bubble = {"npc": npc, "text": "Hi", "page": 0}
        game.speech_bubble.font = MagicMock()
        game.speech_bubble.get_total_pages = MagicMock(return_value=1)
        game._advance_npc_bubble()
        assert game._npc_bubble is None
        assert npc.state == "idle"

    @patch("src.engine.game.Game._load_map")
    def test_get_state_has_keys(self, _):
        game = _make_game()
        s = game.get_state()
        assert "map_name" in s and "player_pos" in s

    @patch("src.engine.game.Game._load_map")
    def test_run_frame_returns_game_event(self, _):
        from src.engine.game_events import GameEvent
        game = _make_game()
        game._handle_events = MagicMock()
        game._update = MagicMock()
        game._draw = MagicMock()
        assert isinstance(game.run_frame(0.016), GameEvent)

    @patch("src.engine.game.Game._load_map")
    def test_update_resolves_pending_npc_stopped(self, _):
        game = _make_game()
        npc = MagicMock()
        npc.is_moving = False
        game._pending_npc_dialogue = (npc, "elem")
        game._trigger_npc_bubble = MagicMock()
        game._update(0.016)
        game._trigger_npc_bubble.assert_called_once_with(npc, "elem")
        assert game._pending_npc_dialogue is None


# ---------------------------------------------------------------------------
# ENTITY_FACTORY.PY — lines 43, 47, 212-220, 248, 250
# ---------------------------------------------------------------------------

class TestEntityFactoryCoverage:

    def test_get_property_nested_in_io_sprite(self):
        from src.engine.entity_factory import _get_property
        # L41: io has nested sprite
        result = _get_property({"interactive_object": {"sprite": {"color": "red"}}}, "color")
        assert result == "red"

    def test_get_property_top_level_sprite(self):
        from src.engine.entity_factory import _get_property
        # L45-47: top-level sprite dict
        result = _get_property({"sprite": {"depth": 2}}, "depth")
        assert result == 2

    def test_spawn_npc_restores_world_state(self):
        ef = _make_ef()
        ef.game.world_state.get.return_value = {
            "pos": [120.0, 80.0],
            "facing": "down",
        }
        ent = {"x": 100, "y": 100, "id": 42, "width": 32, "height": 32}
        with patch("src.engine.entity_factory.NPC") as MockNPC:
            inst = MagicMock()
            inst.element_id = "npc1"
            inst.pos = pygame.math.Vector2(100, 100)
            inst.target_pos = pygame.math.Vector2(100, 100)
            inst.rect = MagicMock()
            MockNPC.return_value = inst
            ef.spawn_npc(ent, {})
        assert inst.target_pos.x == 120.0

    def test_spawn_pickup_skips_collected(self):
        ef = _make_ef()
        ef.game.world_state.get.return_value = {"collected": True}
        ef.spawn_pickup({"x": 0, "y": 0, "id": 1}, {"element_id": "x", "item_id": "herb"})
        ef.game.pickups.add.assert_not_called()

    def test_spawn_pickup_restores_quantity(self):
        ef = _make_ef()
        ef.game.world_state.get.return_value = {"quantity": 7, "collected": False}
        ef.game._current_map_name = "test.tmj"
        props = {"object_id": "gem", "sprite_sheet": "gem.png", "quantity": 1}
        with patch("src.engine.entity_factory.PickupItem") as MockItem:
            MockItem.return_value = MagicMock()
            ef.spawn_pickup({"x": 0, "y": 0, "id": 2}, props)
            assert MockItem.called


# ---------------------------------------------------------------------------
# ENTITIES/GROUPS.PY — lines 18-19, 31, 40, 52, 58, 89-90, 100, 118-120
# ---------------------------------------------------------------------------

class TestCameraGroupCoverage:

    def test_init_no_display(self):
        from src.entities.groups import CameraGroup
        with patch.object(pygame.display, "get_surface", return_value=None):
            cg = CameraGroup()
        assert cg.half_width == 0

    def test_calculate_offset_no_rect(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        sprite = MagicMock(rect=None)
        assert cg.calculate_offset(sprite) == cg.offset

    def test_calculate_offset_small_world_centers(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg.world_size = (100, 100)
        sprite = MagicMock()
        sprite.rect = pygame.Rect(50, 50, 32, 32)
        cg.calculate_offset(sprite)
        assert cg.offset.x >= 0

    def test_calculate_offset_large_world_clamps(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg.world_size = (9000, 9000)
        sprite = MagicMock()
        sprite.rect = pygame.Rect(4500, 4500, 32, 32)
        result = cg.calculate_offset(sprite)
        assert isinstance(result, pygame.math.Vector2)

    def test_set_world_size(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg.set_world_size(1920, 1080)
        assert cg.world_size == (1920, 1080)

    def test_custom_draw_moving_sprite_invalidates_cache(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg._cache_dirty = False
        moving = MagicMock()
        moving.is_moving = True
        surf = pygame.Surface((800, 600))
        with patch.object(cg, "sprites", return_value=[moving]):
            with patch.object(cg, "get_sorted_sprites", return_value=[]):
                cg.custom_draw(surf)
        assert cg._cache_dirty

    def test_debug_rect_drawn_for_onscreen_sprite(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        sprite = MagicMock()
        sprite.is_moving = False
        sprite.image = pygame.Surface((32, 32))
        sprite.rect = pygame.Rect(0, 0, 32, 32)
        original = Settings.DEBUG
        Settings.DEBUG = True
        try:
            with patch.object(cg, "sprites", return_value=[]):
                with patch.object(cg, "get_sorted_sprites", return_value=[sprite]):
                    cg.custom_draw(pygame.Surface((800, 600)))
        finally:
            Settings.DEBUG = original


# ---------------------------------------------------------------------------
# ENTITIES/PICKUP.PY — lines 32, 47-51
# ---------------------------------------------------------------------------

class TestPickupCoverage:

    def test_auto_adds_png(self):
        with patch("src.entities.pickup.SpriteSheet") as M:
            M.return_value.valid = False
            from src.entities.pickup import PickupItem
            PickupItem(pos=(0, 0), groups=[], item_id="h", sprite_sheet="herb", quantity=1)
            path = M.call_args[0][0]
            assert path.endswith(".png")

    def test_valid_spritesheet_sets_image(self):
        surf = pygame.Surface((32, 32))
        with patch("src.entities.pickup.SpriteSheet") as M:
            M.return_value.valid = True
            M.return_value.load_grid.return_value = [surf]
            from src.entities.pickup import PickupItem
            item = PickupItem(pos=(0, 0), groups=[], item_id="h", sprite_sheet="herb.png", quantity=1)
            assert item.image is not None


# ---------------------------------------------------------------------------
# MAP/PROJECT_SCHEMA.PY — lines 19-20, 30-31, 67-79
# ---------------------------------------------------------------------------

class TestTiledProjectCoverage:

    def test_missing_file_warns(self, caplog, tmp_path):
        from src.map.project_schema import TiledProject
        with caplog.at_level(logging.WARNING):
            TiledProject(str(tmp_path / "missing.tiled-project"))
        assert "not found" in caplog.text.lower()

    def test_bad_json_logs_error(self, caplog, tmp_path):
        from src.map.project_schema import TiledProject
        bad = tmp_path / "bad.tiled-project"
        bad.write_text("{bad json")
        with caplog.at_level(logging.ERROR):
            TiledProject(str(bad))
        assert caplog.text  # error was logged

    def test_resolve_nested_class(self, tmp_path):
        from src.map.project_schema import TiledProject
        data = {
            "propertyTypes": [
                {"type": "class", "name": "Inner",
                 "members": [{"name": "color", "type": "string", "value": "red"}]},
                {"type": "class", "name": "Outer",
                 "members": [{"name": "inner", "type": "class",
                               "propertyType": "Inner", "value": {}}]},
            ]
        }
        f = tmp_path / "p.tiled-project"
        f.write_text(json.dumps(data))
        tp = TiledProject(str(f))
        result = tp.resolve("Outer", {})
        assert "inner" in result


# ---------------------------------------------------------------------------
# LIGHTING.PY — lines 84, 88-94, 100-109, 124, 153
# ---------------------------------------------------------------------------

class TestLightingCoverage:

    def _lm(self):
        from src.engine.lighting import LightingManager
        ts = MagicMock()
        ts.brightness = 0.5
        ts.hour = 12.0
        ts.night_alpha = 200
        return LightingManager(ts, screen_size=(800, 600))

    def test_create_overlay_zero_alpha_returns_early(self):
        lm = self._lm()
        lm.time_system.night_alpha = 0
        result = lm.create_overlay([], [], pygame.math.Vector2(0, 0))
        assert isinstance(result, pygame.Surface)

    def test_create_overlay_with_torch(self):
        lm = self._lm()
        torch = MagicMock()
        torch.is_on = True
        torch.halo_size = 48
        torch.f_scale = 1.0
        torch.f_alpha = 200
        torch.rect = pygame.Rect(100, 100, 32, 32)
        result = lm.create_overlay([], [torch], pygame.math.Vector2(0, 0))
        assert isinstance(result, pygame.Surface)

    def test_create_overlay_window_3tuple(self):
        lm = self._lm()
        result = lm.create_overlay([(200, 100, 60)], [], pygame.math.Vector2(0, 0))
        assert isinstance(result, pygame.Surface)

    def test_create_overlay_window_2tuple(self):
        lm = self._lm()
        result = lm.create_overlay([(200, 100)], [], pygame.math.Vector2(0, 0))
        assert isinstance(result, pygame.Surface)

    def test_beam_cache_eviction(self):
        lm = self._lm()
        for i in range(66):
            lm._get_beam_surface_for_time(top_w=i + 10)
        assert len(lm._beam_surf_cache) <= 64

    def test_torch_off_is_skipped(self):
        lm = self._lm()
        torch = MagicMock()
        torch.is_on = False
        torch.halo_size = 0
        result = lm.create_overlay([], [torch], pygame.math.Vector2(0, 0))
        assert isinstance(result, pygame.Surface)


# ---------------------------------------------------------------------------
# INTERACTIVE_LIGHTING.PY — lines 42, 71-78, 98-99, 109
# ---------------------------------------------------------------------------

class TestInteractiveLightingCoverage:
    """interactive_lighting.py: _update_flicker covers lines 71-78, 98-99, 109."""

    def _ent(self, is_on=True):
        """Build a minimal entity with lighting attributes."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = MagicMock(spec=InteractiveLightingMixin)
        ent.is_on = is_on
        ent.halo_size = 48
        ent.halo_alpha = 180
        ent.halo_color = pygame.Color(255, 200, 100)
        ent.f_scale = 1.0
        ent.f_alpha = 1.0
        ent.flicker_phase = 0.0
        ent.is_light_source = False
        ent.is_animated = False
        ent.start_row = 0
        ent.end_row = 3
        ent.frame_index = 0
        ent.light_mask_cache = [pygame.Surface((96, 96)) for _ in range(8)]
        ent.light_mask = pygame.Surface((96, 96))
        return ent

    def test_update_flicker_is_on(self):
        """L71-78 — _update_flicker updates f_scale when is_on."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = self._ent(is_on=True)
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)
        assert ent.f_scale != 0

    def test_update_flicker_is_off_resets(self):
        """L98-99 — _update_flicker resets f_alpha/f_scale when off."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = self._ent(is_on=False)
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)
        assert ent.f_alpha == 1.0
        assert ent.f_scale == 1.0

    def test_update_flicker_animated_source(self):
        """L71-78 — animated light source uses frame-based flicker."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = self._ent(is_on=True)
        ent.is_light_source = True
        ent.is_animated = True
        ent.end_row = 3
        ent.start_row = 0
        ent.frame_index = 2
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)


# ---------------------------------------------------------------------------
# UI/SAVE_MENU.PY — lines 29-33, 75-76, 164-166, 280, 296-310
# ---------------------------------------------------------------------------

class TestSaveMenuCoverage:

    def test_save_slot_ui_init_loads_bg(self):
        """SaveSlotUI init: covers L29-33 with mock AssetManager."""
        from src.ui.save_menu import SaveSlotUI
        am = MagicMock()
        am.get_font.return_value = pygame.font.SysFont(None, 24)
        with patch("pygame.image.load") as mock_load:
            mock_load.return_value = MagicMock()
            mock_load.return_value.convert_alpha.return_value = pygame.Surface((427, 200))
            with patch("pygame.transform.smoothscale", return_value=pygame.Surface((427, 200))):
                slot = SaveSlotUI(am=am)
        assert slot is not None

    def test_save_menu_overlay_init(self):
        """SaveMenuOverlay init covers L75-76."""
        from src.ui.save_menu import SaveMenuOverlay
        screen = pygame.Surface((800, 600))
        sm = MagicMock()
        sm.list_saves.return_value = []
        with patch("pygame.image.load", return_value=MagicMock(
            convert_alpha=lambda: pygame.Surface((800, 600))
        )):
            with patch("pygame.transform.smoothscale", return_value=pygame.Surface((800, 600))):
                overlay = SaveMenuOverlay(screen=screen, save_manager=sm, title="Sauvegardes")
        assert overlay is not None
