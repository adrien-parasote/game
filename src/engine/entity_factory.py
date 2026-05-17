"""EntityFactory: instantiates game entities from Tiled map data.

Extracted from Game._spawn_entities, _spawn_interactive, _spawn_teleport,
_spawn_npc, _spawn_pickup (game.py L301-L448) and _get_property (L35-L56).
Also manages obstacle group registration (doors).

Deep links:
  - Origin: src/engine/game.py#L35-L56, L301-L448
  - Spec: docs/specs/phase-1.5-game-refactoring.md
"""

import logging
from typing import Any

import pygame

from src.engine.world_state import WorldState
from src.entities.interactive import InteractiveEntity
from src.entities.npc import NPC
from src.entities.pickup import PickupItem
from src.entities.teleport import Teleport

# ---------------------------------------------------------------------------
# Property helper (module-level so EntityFactory and tests can use it)
# ---------------------------------------------------------------------------


def _get_property(props: dict, key: str, default=None):
    """Look for a property in a resolved Tiled properties dictionary.

    Handles Tiled 1.10+ nested class structures (interactive_object, sprite).
    """
    if key in props:
        return props[key]

    io = props.get("interactive_object", {})
    if isinstance(io, dict):
        if key in io:
            return io[key]
        sp = io.get("sprite", {})
        if isinstance(sp, dict) and key in sp:
            return sp[key]

    sp = props.get("sprite", {})
    if isinstance(sp, dict) and key in sp:
        return sp[key]

    return default


# ---------------------------------------------------------------------------
# EntityFactory
# ---------------------------------------------------------------------------


class EntityFactory:
    """Creates and registers game entities from Tiled map object data.

    Args:
        game: Game context (Any — ADR-004 pattern). Must expose:
              visible_sprites, interactives, npcs, pickups, teleports_group,
              obstacles_group, world_state, loot_table, audio_manager,
              tile_size, player, time_system, interaction_manager.
    """

    def __init__(self, game: Any) -> None:
        self.game = game

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def spawn_entities(self, entities: list, map_name: str = "") -> None:
        """Dispatch each entity in *entities* to the appropriate spawn method.

        Args:
            entities: List of Tiled entity dicts from TmjParser.
            map_name: Current map filename (used for world_state keys).
        """
        self.game.tile_size // 2
        for ent in entities:
            props = ent.get("properties", {})
            entity_type = _get_property(props, "entity_type", default="unknown")

            if _get_property(props, "is_initial_spawn") is True:
                continue

            ent_type_field = ent.get("type", "")
            if entity_type == "interactive" or ent_type_field.startswith("03-"):
                self.spawn_interactive(ent, props, map_name)
            elif entity_type == "npc" or ent_type_field == "15-npc" or ent_type_field.startswith("07-"):
                self.spawn_npc(ent, props)
            elif _get_property(props, "type") == "teleport" or ent_type_field.startswith("15-"):
                self.spawn_teleport(ent, props)
            elif entity_type == "object" or ent_type_field.startswith("08-"):
                self.spawn_pickup(ent, props)
            else:
                logging.debug(
                    f"EntityFactory: unrecognised type={entity_type!r} "
                    f"ent_type={ent_type_field!r} — skipped"
                )

    def spawn_interactive(self, ent: dict, props: dict, map_name: str) -> None:
        """Instantiate an InteractiveEntity and restore persisted state.

        Args:
            ent: Raw Tiled entity dict.
            props: Resolved properties dict (from ent["properties"]).
            map_name: Current map filename (used for world_state key).
        """
        element_id = _get_property(props, "element_id") or str(ent.get("id"))
        if _get_property(props, "sub_type") == "sign":
            logging.info(f"Sign detected with ID: {element_id}")
        target_id = _get_property(props, "target_id") or _get_property(props, "target")

        entity = InteractiveEntity(
            pos=(ent["x"], ent["y"]),
            groups=[self.game.visible_sprites, self.game.interactives],
            sub_type=str(_get_property(props, "sub_type", "unknown")),
            sprite_sheet=str(_get_property(props, "sprite_sheet", "")),
            position=int(str(_get_property(props, "position", 0))),
            depth=int(str(_get_property(props, "depth", 1))),
            start_row=int(str(_get_property(props, "start_frame", 0))),
            end_row=int(str(_get_property(props, "end_frame", 3))),
            width=int(str(_get_property(props, "width", ent.get("width", 32)))),
            height=int(str(_get_property(props, "height", ent.get("height", 32)))),
            tiled_width=int(ent.get("width", 32)),
            tiled_height=int(ent.get("height", 32)),
            obstacles_group=self.game.obstacles_group,
            is_passable=bool(_get_property(props, "is_passable", False)),
            is_animated=bool(_get_property(props, "is_animated", False)),
            is_on=bool(_get_property(props, "is_on", False)),
            off_position=int(str(_get_property(props, "off_position", -1))),
            halo_size=int(str(_get_property(props, "halo_size", 0))),
            halo_color=str(_get_property(props, "halo_color", "[255, 255, 255]")),
            halo_alpha=int(str(_get_property(props, "halo_alpha", 130))),
            particles=bool(_get_property(props, "particles", False)),
            particle_count=int(str(_get_property(props, "particle_count", 0))),
            element_id=element_id,
            target_id=target_id,
            activate_from_anywhere=bool(_get_property(props, "activate_from_anywhere", False)),
            facing_direction=str(_get_property(props, "facing_direction", "")),
            sfx=str(_get_property(props, "sfx", "")),
            sfx_ambient=str(_get_property(props, "sfx_ambient", "")),
            day_night_driven=bool(_get_property(props, "day_night_driven", False)),
        )
        entity._time_system = self.game.time_system
        entity.game = self.game

        if _get_property(props, "sub_type", "unknown") == "chest":
            entity.contents = self.game.loot_table.get_contents(element_id)

        tiled_id = ent.get("id")
        if tiled_id is not None and map_name:
            key = WorldState.make_key(map_name, tiled_id)
            entity._world_state_key = key
            saved_state = self.game.world_state.get(key)
            if saved_state is not None:
                entity.restore_state(saved_state)
                # Sync is_on from saved state directly (test-visible side effect)
                if "is_on" in saved_state:
                    entity.is_on = saved_state["is_on"]

    def spawn_teleport(self, ent: dict, props: dict) -> None:
        """Instantiate a Teleport trigger from Tiled entity data.

        Args:
            ent: Raw Tiled entity dict with x, y, width, height.
            props: Resolved properties dict.
        """
        t_rect = pygame.Rect(ent["x"], ent["y"], ent.get("width", 32), ent.get("height", 32))
        tp = Teleport(
            t_rect,
            [self.game.teleports_group],
            str(_get_property(props, "target_map", "")),
            str(_get_property(props, "target_spawn_id", "")),
            str(_get_property(props, "transition_type", "instant")),
            str(_get_property(props, "required_direction", "any")),
        )
        tp.sfx = str(_get_property(props, "sfx", ""))

    def spawn_npc(self, ent: dict, props: dict) -> None:
        """Instantiate an NPC from Tiled entity data.

        Restores persisted position and facing from world_state.

        Args:
            ent: Raw Tiled entity dict.
            props: Resolved properties dict.
        """
        half_tile = self.game.tile_size // 2
        e_pos = (ent["x"] + half_tile, ent["y"] + half_tile)

        npc = NPC(
            pos=e_pos,
            groups=[self.game.visible_sprites, self.game.npcs],
            wander_radius=int(str(_get_property(props, "wander_radius", 1))),
            sheet_name=str(_get_property(props, "sprite_sheet", "01-character.png")),
            element_id=str(_get_property(props, "element_id") or str(ent.get("id", ""))),
            sheet_cols=int(str(_get_property(props, "sheet_cols", 4))),
            sheet_rows=int(str(_get_property(props, "sheet_rows", 4))),
        )
        npc.name = str(_get_property(props, "name", ent.get("name", "")))
        npc.game = self.game
        npc.walkable_func = self.game.interaction_manager.is_walkable

        tiled_id = ent.get("id")
        if tiled_id is not None and self.game._current_map_name:
            key = WorldState.make_key(self.game._current_map_name, tiled_id)
            npc._world_state_key = key
            saved_state = self.game.world_state.get(key)
            if saved_state:
                saved_pos = saved_state.get("pos")
                if saved_pos:
                    npc.pos = pygame.math.Vector2(saved_pos)
                    npc.target_pos = pygame.math.Vector2(saved_pos)
                    if npc.rect:
                        npc.rect.center = (round(npc.pos.x), round(npc.pos.y))
                saved_facing = saved_state.get("facing")
                if saved_facing:
                    npc.current_facing = saved_facing

        logging.info(f"Spawned NPC '{npc.element_id}' at {npc.pos}")

    def spawn_pickup(self, ent: dict, props: dict) -> None:
        """Instantiate a PickupItem, skipping already-collected ones.

        Restores partial quantity from world_state if available.

        Args:
            ent: Raw Tiled entity dict.
            props: Resolved properties dict.
        """
        item_id = _get_property(props, "object_id")
        sprite = _get_property(props, "sprite_sheet")
        quantity = int(str(_get_property(props, "quantity", 1)))
        if not (item_id and sprite):
            return

        tiled_id = ent.get("id")
        state_key = (
            WorldState.make_key(self.game._current_map_name, tiled_id)
            if tiled_id
            else None
        )
        if state_key:
            saved = self.game.world_state.get(state_key)
            if saved and saved.get("collected"):
                return
            if saved and "quantity" in saved:
                quantity = saved["quantity"]

        half_tile = self.game.tile_size // 2
        e_pos = (ent["x"] + half_tile, ent["y"] + half_tile)

        item = PickupItem(
            pos=e_pos,
            groups=[self.game.visible_sprites, self.game.pickups],
            item_id=item_id,
            sprite_sheet=str(sprite),
            quantity=quantity,
            element_id=str(tiled_id or ""),
        )
        if state_key:
            item._world_state_key = state_key
        logging.info(f"Spawned PickupItem '{item_id}' (x{quantity}) at {e_pos}")
