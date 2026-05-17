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

        # Player depth = 1
        player = MagicMock()
        player.depth = 1
        rm.game.player = player

        # Camera offset
        offset = MagicMock()
        offset.x = 0
        offset.y = 0
        rm.game.visible_sprites.offset = offset

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

        # AnimMapManager returns image for water
        anim_mgr = MagicMock()
        anim_mgr.get_current_frame_image.return_value = water_anim_img
        rm.game.anim_map_manager = anim_mgr

        # Track blit call order
        blit_order = []
        def track_blit(img, pos):
            blit_order.append(img)
        def track_fblits(lst):
            for img, pos in lst:
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
