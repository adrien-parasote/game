"""MapLoader: loads Tiled maps, positions player, spawns entities.

Extracted from Game._load_map (game.py L186-L285) and _start_initial_ambients
(L286-L299) as part of Phase 1.5 refactoring.

Deep links:
  - Origin: src/engine/game.py#L186-L299
  - Spec: docs/specs/phase-1.5-game-refactoring.md
"""

import logging
import os
from typing import Any

import pygame

from src.map.layout import OrthogonalLayout
from src.map.manager import MapManager
from src.map.tmj_parser import TmjParser


class MapLoader:
    """Loads a Tiled map file and positions the player at the correct spawn.

    Args:
        game: Game context (Any — ADR-004 pattern). Must expose:
              tile_size, visible_sprites, interactives, npcs, obstacles_group,
              teleports_group, pickups, player, audio_manager, world_state,
              layout, map_manager, map_size, _entity_factory, _current_map_name.
    """

    def __init__(self, game: Any) -> None:
        self.game = game

    def load(
        self,
        map_name: str,
        target_spawn_id: str | None = None,
        transition_type: str = "instant",
    ) -> None:
        """Unload current entities and load a new map from Tiled.

        Normalizes .tjm → .tmj extension (known typo in existing maps).
        Logs error and returns early if map file is not found.

        Args:
            map_name: Filename of the map (e.g. "village.tmj").
            target_spawn_id: spawn_id to teleport to; None uses initial spawn.
            transition_type: Transition animation type (currently unused).
        """
        map_name = map_name.replace(".tjm", ".tmj")
        map_path = os.path.join("assets", "tiled", "maps", map_name)

        if not os.path.exists(map_path):
            logging.error(f"Target map not found: {map_path}")
            return

        parser = TmjParser()
        map_result = parser.load_map(map_path)

        self.game.layout = OrthogonalLayout(self.game.tile_size)
        self.game.map_manager = MapManager(map_result, self.game.layout)

        bgm = map_result.get("properties", {}).get("bgm")
        if bgm:
            self.game.audio_manager.play_bgm(bgm)

        self.game.map_size = max(
            self.game.map_manager.width, self.game.map_manager.height
        )

        world_width_px = self.game.map_manager.width * self.game.tile_size
        world_height_px = self.game.map_manager.height * self.game.tile_size
        self.game.visible_sprites.set_world_size(world_width_px, world_height_px)

        self._save_npc_states()
        self._clear_groups()

        self.game._current_map_name = map_name
        self.game._entity_factory.spawn_entities(
            map_result.get("entities", []), map_name
        )

        spawn_pos = self._resolve_spawn(
            map_result, target_spawn_id, world_width_px, world_height_px
        )

        self._position_player(spawn_pos)
        logging.info(f"Loaded map {map_name}, player spawned at {spawn_pos}")

        self._start_initial_ambients(pygame.math.Vector2(spawn_pos))

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _save_npc_states(self) -> None:
        """Persist NPC positions before unloading the map."""
        for npc in self.game.npcs:
            if getattr(npc, "_world_state_key", None):
                self.game.world_state.set(
                    npc._world_state_key,
                    {"pos": (npc.pos.x, npc.pos.y), "facing": npc.current_facing},
                )

    def _clear_groups(self) -> None:
        """Empty all entity groups and keep only the player in visible_sprites."""
        self.game.interactives.empty()
        self.game.npcs.empty()
        self.game.obstacles_group.empty()
        self.game.teleports_group.empty()
        self.game.pickups.empty()
        self.game._npc_bubble = None
        self.game.visible_sprites.empty()
        self.game.visible_sprites.add(self.game.player)

    def _resolve_spawn(
        self,
        map_result: dict,
        target_spawn_id: str | None,
        world_width_px: int,
        world_height_px: int,
    ) -> tuple[int, int]:
        """Find the player spawn coordinates from map entities.

        Priority:
          1. Entity matching target_spawn_id (if provided).
          2. Entity with is_initial_spawn=True.
          3. Root spawn_player dict.
          4. World center (fallback, logs warning).
        """
        half_tile = self.game.tile_size // 2
        center = (world_width_px // 2, world_height_px // 2)

        for ent in map_result.get("entities", []):
            ent_type = ent.get("type", "")
            props = ent.get("properties", {})
            is_spawn = ent_type == "14-spawn_point" or props.get("spawn_player") is True
            if not is_spawn:
                continue
            if target_spawn_id and props.get("spawn_id") == target_spawn_id:
                return (ent["x"] + half_tile, ent["y"] + half_tile)
            if not target_spawn_id and (
                props.get("is_initial_spawn") is True
                or props.get("is_initial_pawn") is True
            ):
                return (ent["x"] + half_tile, ent["y"] + half_tile)

        if target_spawn_id is None:
            spawn_dict = map_result.get("spawn_player")
            if spawn_dict:
                return (spawn_dict["x"] + half_tile, spawn_dict["y"] + half_tile)
            logging.warning(
                f"No valid spawn_player found on map "
                f"{self.game._current_map_name}. Defaulting to center."
            )

        return center

    def _position_player(self, spawn_pos: tuple[int, int]) -> None:
        """Teleport the player to spawn_pos (pixel coordinates)."""
        self.game.player.pos = pygame.math.Vector2(spawn_pos)
        self.game.player.target_pos = pygame.math.Vector2(spawn_pos)
        if self.game.player.rect:
            self.game.player.rect.center = (int(spawn_pos[0]), int(spawn_pos[1]))
        self.game.player.is_moving = False
        self.game.player.direction = pygame.math.Vector2(0, 0)

    def _start_initial_ambients(self, player_pos: pygame.math.Vector2) -> None:
        """Prime ambient sounds for all active interactive entities on map load."""
        for entity in self.game.interactives:
            sfx = getattr(entity, "sfx_ambient", "")
            if not sfx or not entity.is_on:
                continue
            dist = entity.pos.distance_to(player_pos)
            self.game.audio_manager.propose_ambient(sfx, dist)
        self.game.audio_manager.flush_ambient()
