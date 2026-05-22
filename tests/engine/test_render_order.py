"""
TC-RENDER-001: Ordre de rendu background — les tiles animées d'une layer L
doivent être dessinées APRÈS les tiles statiques de L et AVANT les tiles
statiques et animées de L+1.

Symptôme: un pont statique (depth=0) sur 01-layer (order=1) est invisible
car le water animé (01-water, sur 00-layer order=0) est dessiné en masse
APRÈS toutes les surfaces statiques, écrasant le pont.

Spec du rendu background:
  Pour chaque layer dans l'ordre croissant (order 0, 1, 2...):
    1. Dessiner les tiles statiques de cette layer (get_layer_surface)
    2. Dessiner les tiles animées de cette layer (get_visible_animated_chunks filtrée)
  Résultat: layer(order=1) toujours au-dessus de layer(order=0), animé ou non.
"""

from collections import defaultdict
from unittest.mock import MagicMock, call, patch

import pygame
import pytest

from src.config import Settings
from src.engine.render_manager import RenderManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_render_manager():
    """Create a minimal RenderManager with mocked game object."""
    game = MagicMock()
    game.tile_size = 32
    screen = MagicMock(spec=pygame.Surface)
    screen.get_width.return_value = 1280
    screen.get_height.return_value = 720
    game.screen = screen

    rm = RenderManager.__new__(RenderManager)
    rm.game = game
    rm._tile_rect = pygame.Rect(0, 0, 32, 32)
    rm._screen_rect = pygame.Rect(0, 0, 1280, 720)
    rm._viewport_world = pygame.Rect(0, 0, 0, 0)
    return rm


# ---------------------------------------------------------------------------
# TC-RENDER-001: ordre de rendu par layer (statique + animé entrelacés)
# ---------------------------------------------------------------------------

class TestBackgroundLayerRenderOrder:
    """
    TC-RENDER-001: les tiles animées doivent être dessinées par layer,
    pas toutes après toutes les surfaces statiques.
    """

    def test_animated_tiles_drawn_per_layer_not_after_all_static(self):
        """
        TC-RENDER-001 RED:
        Setup : 2 layers.
          - 00-layer (order=0) : water animé (depth=0)
          - 01-layer (order=1) : pont statique (depth=0)

        Comportement attendu : ordre des blit sur l'écran :
          1. surface statique 00-layer
          2. tile animée 00-layer (water)
          3. surface statique 01-layer (bridge)  ← DOIT être après l'animé 00-layer

        Comportement actuel (bug) :
          1. surface statique 00-layer
          2. surface statique 01-layer (bridge)
          3. tile animée ALL layers (water)   ← ÉCRASE le pont
        """
        rm = _make_render_manager()

        rm.game.player = MagicMock(depth=1)
        rm.game.visible_sprites.offset = MagicMock(x=0, y=0)

        # Map manager setup
        map_mgr = MagicMock()
        map_mgr.layer_order = [7, 8]  # 00-layer=7, 01-layer=8
        map_mgr.layer_depths = {7: 0, 8: 1}  # orders

        # Static surfaces
        surf_00 = MagicMock(name="surf_00-layer")
        surf_01 = MagicMock(name="surf_01-layer")
        map_mgr.get_layer_surface.side_effect = lambda lid, pg, max_bg_depth=1: (
            surf_00 if lid == 7 else surf_01
        )

        # Animated chunks: only 00-layer has animated water tiles
        water_anim_img = MagicMock(name="water_anim_img")
        # get_visible_animated_chunks called with layer_id=7 → yields water
        # called with layer_id=8 → yields nothing
        def animated_chunks(viewport, layer_id=None):
            if layer_id is None or layer_id == 7:
                yield (0, 0, 1001, 0)  # water tile on 00-layer, depth=0
        map_mgr.get_visible_animated_chunks.side_effect = animated_chunks

        rm.game.map_manager = map_mgr

        anim_mgr = MagicMock()
        anim_mgr.get_current_frame_image.return_value = water_anim_img
        rm.game.anim_map_manager = anim_mgr

        # Track blit call order
        blit_order = []
        def track_blit(img, pos):
            blit_order.append(img)
        def track_fblits(lst):
            for img, _pos in lst:
                blit_order.append(img)

        rm.game.screen.blit.side_effect = track_blit
        rm.game.screen.fblits.side_effect = track_fblits

        # Act
        rm.draw_background()

        # Assert: surf_01 (bridge on 01-layer) must appear AFTER water_anim_img
        assert surf_00 in blit_order, "00-layer static surface must be drawn"
        assert surf_01 in blit_order, "01-layer static surface (bridge) must be drawn"
        assert water_anim_img in blit_order, "water animated tile must be drawn"

        idx_water = blit_order.index(water_anim_img)
        idx_bridge = blit_order.index(surf_01)

        assert idx_bridge > idx_water, (
            f"Bridge (01-layer static) must be drawn AFTER water anim (00-layer animated). "
            f"Got: bridge at index {idx_bridge}, water at index {idx_water}. "
            f"Full order: {[getattr(x, '_mock_name', str(x)) for x in blit_order]}"
        )


# ---------------------------------------------------------------------------
# TC-RENDER-002: draw_foreground skips occlusion during scripted walk
# ---------------------------------------------------------------------------

class TestOcclusionSkippedDuringWalk:
    """TC-RENDER-002: During intra-map scripted walk, draw_foreground must
    treat all foreground tiles as normal (no occluded_image blit) and
    return a list[tuple] (rects are still collected regardless — the caller
    guards with walk_active before calling _apply_partial_occlusion).
    """

    def _make_rm_with_occluding_tile(self):
        """Return a RenderManager where a foreground tile overlaps the player rect."""
        rm = _make_render_manager()

        rm.game.player = MagicMock(depth=1)
        rm.game.player.rect = pygame.Rect(0, 0, 32, 32)
        rm.game.visible_sprites.offset = MagicMock(x=0, y=0)

        # One foreground tile (depth=2 > player.depth=1) at (0,0) — overlaps player
        map_mgr = MagicMock()
        fg_tile_data = MagicMock()
        fg_tile_data.occluded_image = MagicMock(name="occluded_tile")
        fg_tile_data.image = MagicMock(name="normal_tile")
        map_mgr.tiles = {42: fg_tile_data}
        map_mgr.get_visible_chunks.return_value = [(0, 0, 42, 2)]  # depth=2 > player.depth=1
        map_mgr.get_visible_animated_chunks.return_value = []
        rm.game.map_manager = map_mgr
        rm.game.anim_map_manager = None

        normal_blits = []
        occluded_blits = []

        def track_blit(img, pos):
            if img is fg_tile_data.occluded_image:
                occluded_blits.append(img)
            else:
                normal_blits.append(img)

        def track_fblits(lst):
            for img, _pos in lst:
                if img is fg_tile_data.occluded_image:
                    occluded_blits.append(img)
                else:
                    normal_blits.append(img)

        rm.game.screen.blit.side_effect = track_blit
        rm.game.screen.fblits.side_effect = track_fblits
        return rm, fg_tile_data, normal_blits, occluded_blits

    def test_occlusion_active_when_not_walking(self):
        """TC-RENDER-002a (non-regression): Without walk, occluded_image IS used,
        and draw_foreground() returns a non-empty list[tuple[Rect, int]]."""
        rm, fg_tile_data, normal_blits, occluded_blits = self._make_rm_with_occluding_tile()
        rm.game._intra_walk_target = None  # no walk

        result = rm.draw_foreground()

        # New contract: returns list[tuple], not bool
        assert isinstance(result, list) and len(result) > 0, (
            f"draw_foreground() must return non-empty list when player is occluded, got: {result!r}"
        )
        assert isinstance(result[0], tuple) and len(result[0]) == 2
        assert isinstance(result[0][0], pygame.Rect)
        assert isinstance(result[0][1], int)
        assert len(occluded_blits) == 1, "occluded_image must be blit once"
        assert len(normal_blits) == 0, "normal tile image must NOT be used"

    def test_occlusion_skipped_during_walk(self):
        """TC-RENDER-002b (non-regression): During scripted walk, occluded_image must NOT be used.
        draw_foreground() still returns the collected rects (the caller guards with walk_active).
        """
        rm, fg_tile_data, normal_blits, occluded_blits = self._make_rm_with_occluding_tile()
        rm.game._intra_walk_target = pygame.math.Vector2(100, 100)  # walk active

        result = rm.draw_foreground()

        # New contract: returns list[tuple] even during walk — caller is responsible for the guard.
        assert isinstance(result, list), (
            f"draw_foreground() must return list even during walk, got: {type(result)!r}"
        )
        assert len(occluded_blits) == 0, (
            "occluded_image must NOT be blit during walk — tiles should not go alpha"
        )
        assert len(normal_blits) == 1, "normal tile image must be used instead"


# ---------------------------------------------------------------------------
# TC-RENDER-003: draw_scene does not apply occlusion alpha to player during walk
# ---------------------------------------------------------------------------

class TestDrawSceneOcclusionDuringWalk:
    """TC-RENDER-003: When scripted walk is active, draw_scene must not call
    player.image.set_alpha() with the occlusion alpha value — player is already
    invisible and we must not risk altering the transparent surface.
    """

    def test_no_occlusion_alpha_applied_to_player_during_walk(self):
        """TC-RENDER-003: player.image.set_alpha must NOT be called during walk."""
        rm = _make_render_manager()

        rm.game.player = MagicMock(depth=1)
        rm.game._intra_walk_target = pygame.math.Vector2(50, 50)  # walk active

        # Stub out subsystem calls so draw_scene runs end-to-end
        rm.draw_background = MagicMock()
        rm.draw_foreground = MagicMock(return_value=[(pygame.Rect(0, 0, 32, 32), 2)])  # reports occluded (new list contract)
        rm.draw_hud = MagicMock()

        player_image = MagicMock(name="player_image")
        rm.game.player.image = player_image

        rm.game.visible_sprites.custom_draw = MagicMock()
        rm.game.visible_sprites.calculate_offset = MagicMock()
        rm.game.time_system.night_alpha = 0
        rm.game.map_manager.get_window_positions.return_value = []
        rm.game.lighting_manager.draw_additive_window_beams = MagicMock()
        rm.game.interactives = []
        rm.game.inventory_ui.is_open = False
        rm.game.emote_group = []
        rm.game.dialogue_manager.is_active = False
        rm.game._npc_bubble = None
        rm.game.chest_ui.is_open = False
        rm.game.screen.fill = MagicMock()

        rm.draw_scene()

        # player.image.set_alpha must NOT be called with OCCLUSION_ALPHA during walk
        for call_args in player_image.set_alpha.call_args_list:
            alpha_val = call_args.args[0] if call_args.args else None
            assert alpha_val != Settings.OCCLUSION_ALPHA, (
                f"set_alpha({Settings.OCCLUSION_ALPHA}) must not be called on player "
                f"during scripted walk — player is already invisible"
            )
