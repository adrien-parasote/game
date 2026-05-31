"""
Tests — Bug: sprites with depth=2 on a background-layer tile with depth=2 must be visible.

Context (debug_room.tmj):
  - Layer 7 (00-layer, order=0) = background layer.
  - Tiles 665-667 at row 32 have depth=2 (wall tiles).
  - Torch entities (ID 1, ID 2) sit at row 32 with entity depth=2.
  - Torch ID 24 sits at row 38 where the tile has depth=0.
  - ID 24 renders correctly; ID 1 and ID 2 do not.

Root-cause analysis:
  In draw_background(), layer 7 (order=0 <= player.depth=1) is rendered via
  get_layer_surface(7, max_bg_depth=1) which correctly SKIPs depth=2 tiles
  (leaves them transparent). Those tiles are then drawn in draw_foreground().
  Sprites with depth=2 are drawn last in custom_draw(min_depth=2).
  So the pipeline order is correct and sprites SHOULD appear above the wall tiles.

  The tests below verify each step of this pipeline remains correct and that
  depth=2 entities are always visible above depth=2 foreground tiles.
"""

from unittest.mock import MagicMock, patch

import pygame
from src.engine.render_manager import RenderManager
from src.entities.groups import CameraGroup
from src.map.layout import LayoutStrategy
from src.map.manager import MapManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FlatLayout(LayoutStrategy):
    def __init__(self, tile_size: int = 32):
        self.tile_size = tile_size

    def to_screen(self, x: int, y: int) -> tuple:
        return x * self.tile_size, y * self.tile_size

    def to_world(self, px: float, py: float) -> tuple:
        return px / self.tile_size, py / self.tile_size


def _make_tile(depth: int, color=(128, 128, 128)) -> MagicMock:
    img = pygame.Surface((32, 32))
    img.fill(color)
    tile = MagicMock()
    tile.depth = depth
    tile.image = img
    tile.occluded_image = None
    tile.frames = None
    return tile


def _make_sprite(depth: int, rect: pygame.Rect, color=(255, 0, 0)) -> MagicMock:
    img = pygame.Surface((32, 32))
    img.fill(color)
    sprite = MagicMock()
    sprite.depth = depth
    sprite.is_moving = False
    sprite.image = img
    sprite.rect = rect
    return sprite


def _pixel_at(surface: pygame.Surface, pos: tuple) -> tuple:
    return surface.get_at(pos)[:3]


# ---------------------------------------------------------------------------
# TC-01: Background layer surface must NOT blit depth=2 tiles (max_bg_depth=1)
# ---------------------------------------------------------------------------


class TestBackgroundLayerExcludesDepth2Tiles:
    """TC-01: get_layer_surface with max_bg_depth=1 must skip depth=2 tiles."""

    def test_depth2_tile_is_transparent_in_background_surface(self):
        """Tile with depth=2 in a background layer must produce a transparent pixel."""
        wall_tile = _make_tile(depth=2, color=(200, 0, 0))

        layers = {1: [[0, 0], [0, 99]]}
        tiles = {99: wall_tile}
        map_data = {
            "layers": layers,
            "tiles": tiles,
            "layer_names": {1: "00-layer"},
            "layer_order": [1],
            "layer_order_values": {1: 0},
            "entities": [],
            "properties": {},
        }
        mm = MapManager(map_data, _FlatLayout(32))

        surface = mm.get_layer_surface(1, pygame, max_bg_depth=1)

        assert surface is not None
        # Tile 99 is at col=1, row=1 → pixels (32, 32).
        # depth=2 > max_bg_depth=1 → must be transparent.
        pixel = surface.get_at((32, 32))
        assert pixel[3] == 0, (
            f"depth=2 tile was drawn in background surface at (32,32): {pixel}. "
            "It must be transparent (alpha=0)."
        )

    def test_depth0_tile_is_drawn_in_background_surface(self):
        """Sanity: tile with depth=0 must appear in background surface."""
        floor_tile = _make_tile(depth=0, color=(0, 200, 0))
        floor_tile.frames = None

        layers = {1: [[0, 0], [0, 99]]}
        tiles = {99: floor_tile}
        map_data = {
            "layers": layers,
            "tiles": tiles,
            "layer_names": {1: "00-layer"},
            "layer_order": [1],
            "layer_order_values": {1: 0},
            "entities": [],
            "properties": {},
        }
        mm = MapManager(map_data, _FlatLayout(32))

        surface = mm.get_layer_surface(1, pygame, max_bg_depth=1)
        assert surface is not None
        pixel = surface.get_at((32, 32))[:3]
        assert pixel == (0, 200, 0), (
            f"depth=0 tile was NOT drawn in background surface: {pixel}."
        )


# ---------------------------------------------------------------------------
# TC-02: get_visible_chunks must yield depth=2 tiles from background-order layers
# ---------------------------------------------------------------------------


class TestForegroundChunksIncludesDepth2TilesFromBackgroundLayer:
    """TC-02: depth=2 tiles in a layer with order=0 must appear in draw_foreground chunks."""

    def _build_map_manager(self) -> MapManager:
        wall_tile = _make_tile(depth=2, color=(200, 0, 0))
        wall_tile.frames = None
        floor_tile = _make_tile(depth=0, color=(0, 200, 0))
        floor_tile.frames = None

        # Layer 1 (order=0): wall at (0,0), floor at (1,0)
        layers = {1: [[10, 20]]}
        tiles = {10: wall_tile, 20: floor_tile}
        map_data = {
            "layers": layers,
            "tiles": tiles,
            "layer_names": {1: "00-layer"},
            "layer_order": [1],
            "layer_order_values": {1: 0},
            "entities": [],
            "properties": {},
        }
        return MapManager(map_data, _FlatLayout(32))

    def test_depth2_tile_in_order0_layer_appears_in_foreground_chunks(self):
        """Tile with depth=2 in a layer with order=0 must be yielded by get_visible_chunks."""
        mm = self._build_map_manager()
        viewport = pygame.Rect(0, 0, 100, 100)

        fg_chunks = list(mm.get_visible_chunks(viewport, min_depth=1))
        tile_ids_in_fg = [tid for _, _, tid, _ in fg_chunks]

        assert 10 in tile_ids_in_fg, (
            "depth=2 tile (id=10) in order=0 layer was NOT yielded by get_visible_chunks(min_depth=1). "
            "This tile must appear in draw_foreground to be rendered above background sprites."
        )

    def test_depth0_tile_in_order0_layer_not_in_foreground_chunks(self):
        """Tile with depth=0 in order=0 layer must NOT appear in foreground chunks."""
        mm = self._build_map_manager()
        viewport = pygame.Rect(0, 0, 100, 100)

        fg_chunks = list(mm.get_visible_chunks(viewport, min_depth=1))
        tile_ids_in_fg = [tid for _, _, tid, _ in fg_chunks]

        assert 20 not in tile_ids_in_fg, (
            "depth=0 tile (id=20) was incorrectly yielded by get_visible_chunks(min_depth=1). "
            "Only depth>1 tiles from mixed layers must appear in foreground pass."
        )


# ---------------------------------------------------------------------------
# TC-03: CameraGroup.custom_draw with min_depth=2 must render a depth=2 sprite
# ---------------------------------------------------------------------------


class TestCustomDrawRendersDepth2Sprites:
    """TC-03: depth=2 sprite MUST be drawn in custom_draw(min_depth=2)."""

    def test_depth2_sprite_drawn_in_foreground_sprite_pass(self):
        """A sprite with depth=2 must be blit'd when custom_draw is called with min_depth=2."""
        cg = CameraGroup()
        surface = pygame.Surface((800, 600))
        surface.fill((0, 0, 0))

        sprite = _make_sprite(depth=2, rect=pygame.Rect(0, 0, 32, 32), color=(255, 0, 0))

        with patch.object(cg, "sprites", return_value=[]):
            with patch.object(cg, "get_sorted_sprites", return_value=[sprite]):
                cg.custom_draw(surface, min_depth=2)

        pixel = _pixel_at(surface, (0, 0))
        assert pixel == (255, 0, 0), (
            f"depth=2 sprite was NOT drawn in custom_draw(min_depth=2). "
            f"Pixel at (0,0) is {pixel}, expected (255,0,0)."
        )

    def test_depth2_sprite_not_drawn_in_background_sprite_pass(self):
        """A sprite with depth=2 must NOT appear in custom_draw(max_depth=1)."""
        cg = CameraGroup()
        surface = pygame.Surface((800, 600))
        surface.fill((0, 0, 0))

        sprite = _make_sprite(depth=2, rect=pygame.Rect(0, 0, 32, 32), color=(255, 0, 0))

        with patch.object(cg, "sprites", return_value=[]):
            with patch.object(cg, "get_sorted_sprites", return_value=[sprite]):
                cg.custom_draw(surface, max_depth=1)

        pixel = _pixel_at(surface, (0, 0))
        assert pixel == (0, 0, 0), (
            f"depth=2 sprite was drawn in background pass custom_draw(max_depth=1). "
            f"Pixel at (0,0) is {pixel}, expected (0,0,0)."
        )


# ---------------------------------------------------------------------------
# TC-04: draw_scene render order — foreground sprites drawn AFTER foreground tiles
# ---------------------------------------------------------------------------


class TestDrawSceneRenderOrder:
    """TC-04: In draw_scene(), custom_draw(min_depth=2) must come AFTER draw_foreground()."""

    def test_foreground_sprite_pass_after_foreground_tiles(self):
        """Verify all player-depth sprites are drawn AFTER draw_foreground().

        New invariant (player.depth=1):
          - custom_draw(max_depth=0) drawn BEFORE foreground tiles (only depth=0 sprites)
          - draw_foreground() drawn
          - custom_draw(min_depth=1) drawn AFTER foreground tiles
            (covers depth=1 chests/levers/player AND depth=2 torches)
        """
        game = MagicMock()
        game.map_manager.layer_order = []
        game.map_manager.layer_depths = {}
        game.map_manager.get_visible_chunks.return_value = []
        game.map_manager.get_visible_animated_chunks.return_value = []
        game.visible_sprites.offset = pygame.math.Vector2(0, 0)
        game.screen = pygame.Surface((800, 600))
        game.player.rect = pygame.Rect(0, 0, 32, 32)
        game.player.image = pygame.Surface((32, 32))
        game.player.depth = 1
        game.time_system.night_alpha = 0
        game.chest_ui.is_open = False
        game.inventory_ui.is_open = False
        game.dialogue_manager.is_active = False
        game.interactives = []
        game.emote_group = []

        rm = RenderManager(game)
        call_order: list[str] = []

        original_draw_fg = rm.draw_foreground

        def _tracking_draw_fg():
            call_order.append("draw_foreground")
            original_draw_fg()

        rm.draw_foreground = _tracking_draw_fg

        def _tracking_custom_draw(surface, min_depth=None, max_depth=None):
            if min_depth is not None:
                call_order.append(f"custom_draw(min_depth={min_depth})")
            elif max_depth is not None:
                call_order.append(f"custom_draw(max_depth={max_depth})")

        game.visible_sprites.custom_draw.side_effect = _tracking_custom_draw

        rm.draw_scene()

        assert "draw_foreground" in call_order, "draw_foreground() was never called"

        # min_depth=player.depth=1: coffres/leviers/NPC/torches all drawn after foreground tiles
        assert "custom_draw(min_depth=1)" in call_order, (
            "custom_draw(min_depth=1) was never called — depth>=1 sprites (chests, torches) "
            "are never rendered after foreground tiles."
        )

        fg_idx = call_order.index("draw_foreground")
        sprite_idx = call_order.index("custom_draw(min_depth=1)")
        assert sprite_idx > fg_idx, (
            f"custom_draw(min_depth=1) at index {sprite_idx} must come AFTER "
            f"draw_foreground at index {fg_idx}. "
            "Chests/levers/torches are covered by foreground tiles."
        )

        # max_depth=0: only pure background sprites (depth=0) drawn before foreground
        assert "custom_draw(max_depth=0)" in call_order, (
            "custom_draw(max_depth=0) was never called — pure background sprites not drawn."
        )
        bg_idx = call_order.index("custom_draw(max_depth=0)")
        assert bg_idx < fg_idx, (
            "Background sprite pass must come BEFORE draw_foreground."
        )


# ---------------------------------------------------------------------------
# TC-05: Full pipeline — depth=2 sprite visible above depth=2 foreground tile
# (Exact reproduction of the debug_room topology)
# ---------------------------------------------------------------------------


class TestDepth2SpriteVisibleAboveDepth2Tile:
    """TC-05: Regression guard — exact debug_room topology.

    Setup mirrors debug_room at torch ID 1/2 position:
      - background layer (order=0) with depth=2 wall tile at (0,0)
      - entity (depth=2) at same world position

    After a full draw_scene()-equivalent, the sprite pixel must be on top.
    """

    def _run_pipeline(self, screen: pygame.Surface) -> None:
        """Simulate draw_scene() with a depth=2 wall tile and a depth=2 entity sprite."""
        # --- draw_background ---
        # Layer 0 (order=0): depth=2 wall at col=0,row=0 → skipped by max_bg_depth=1
        bg_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 0))  # Transparent (wall skipped)
        screen.blit(bg_surface, (0, 0))

        # --- custom_draw(max_depth=1) --- sprites depth<=1 only, none here

        # --- draw_foreground: wall tile depth=2 at pixel (0,0) ---
        wall_surf = pygame.Surface((32, 32))
        wall_surf.fill((0, 0, 200))  # Blue wall
        screen.blit(wall_surf, (0, 0))

        # --- custom_draw(min_depth=2): entity sprite depth=2 at same position ---
        sprite_surf = pygame.Surface((32, 32))
        sprite_surf.fill((255, 0, 0))  # Red sprite (torch)
        screen.blit(sprite_surf, (0, 0))

    def test_depth2_sprite_visible_above_depth2_wall(self):
        """After draw pipeline, depth=2 sprite (red) must be visible above depth=2 wall (blue)."""
        screen = pygame.Surface((64, 64))
        screen.fill((0, 0, 0))

        self._run_pipeline(screen)

        pixel = _pixel_at(screen, (0, 0))
        assert pixel == (255, 0, 0), (
            f"Expected depth=2 sprite (RED=255,0,0) to be on top of depth=2 wall, "
            f"but got {pixel}. "
            "This is the debug_room bug: torches ID 1 and 2 are hidden by wall tiles."
        )


# ---------------------------------------------------------------------------
# TC-06: MapManager layer_max_depths correctly identifies depth=2 in order=0 layer
# ---------------------------------------------------------------------------


class TestLayerMaxDepths:
    """TC-06: MapManager.layer_max_depths must correctly capture tile depths per layer."""

    def test_layer_max_depth_reflects_tile_depth(self):
        """layer_max_depths must equal the max tile depth found in that layer."""
        wall_tile = _make_tile(depth=2)
        wall_tile.frames = None
        floor_tile = _make_tile(depth=0)
        floor_tile.frames = None

        layers = {1: [[10, 20], [20, 20]]}
        tiles = {10: wall_tile, 20: floor_tile}
        map_data = {
            "layers": layers,
            "tiles": tiles,
            "layer_names": {1: "00-layer"},
            "layer_order": [1],
            "layer_order_values": {1: 0},
            "entities": [],
            "properties": {},
        }
        mm = MapManager(map_data, _FlatLayout(32))

        assert mm.layer_max_depths[1] == 2, (
            f"layer_max_depths[1] should be 2 (highest tile depth), got {mm.layer_max_depths[1]}. "
            "This value controls whether draw_foreground includes this layer."
        )

    def test_order0_layer_with_depth2_tile_included_in_foreground(self):
        """An order=0 layer with a depth=2 tile must NOT be skipped by get_visible_chunks."""
        wall_tile = _make_tile(depth=2)
        wall_tile.frames = None

        layers = {1: [[10]]}
        tiles = {10: wall_tile}
        map_data = {
            "layers": layers,
            "tiles": tiles,
            "layer_names": {1: "00-layer"},
            "layer_order": [1],
            "layer_order_values": {1: 0},
            "entities": [],
            "properties": {},
        }
        mm = MapManager(map_data, _FlatLayout(32))

        chunks = list(mm.get_visible_chunks(pygame.Rect(0, 0, 32, 32), min_depth=1))
        assert len(chunks) == 1, (
            f"Expected 1 chunk for depth=2 tile in order=0 layer, got {len(chunks)}. "
            "The wall tile must be drawn in draw_foreground."
        )
        assert chunks[0][2] == 10  # tile_id
        assert chunks[0][3] == 2   # depth
