import logging
from typing import Any

import pygame

from src.config import Settings

# Pre-computed squared distance thresholds (avoids sqrt per proximity check)
_RANGE_SQ_48: float = 48.0**2  # 2304.0 — standard interaction range
_RANGE_SQ_45: float = 45.0**2  # 2025.0 — chest auto-close range
_RANGE_SQ_16: float = 16.0**2  # 256.0  — is_on_top range


class InteractionManager:
    """
    Manages spatial interactions between the player and world entities (NPCs, Objects).
    Decouples interaction logic from the core Game class.
    """

    def __init__(self, game: Any):
        self.game = game
        self._interaction_cooldown = 0
        self._emote_cooldown = 0  # Cooldown between proximity emote triggers
        self._last_proximity_target = None  # Tracks the last entity we emoted for
        self._open_chest_entity = None  # Tracks currently opened chest entity

    def update(self, dt: float):
        """Update timers and check for nearby interactives to trigger indicators."""
        if self._interaction_cooldown > 0:
            self._interaction_cooldown = max(0, self._interaction_cooldown - dt)
        if self._emote_cooldown > 0:
            self._emote_cooldown = max(0, self._emote_cooldown - dt)

        self._check_proximity_emotes()
        self._check_chest_auto_close()

    def handle_interactions(self):
        """Main entry point for checking interactions based on player input."""
        keys = pygame.key.get_pressed()

        # Check interaction input (E for Objects/NPCs)
        interact_pressed = keys[Settings.INTERACT_KEY]

        if interact_pressed and not self.game.player.is_moving:
            # Prevent interaction spam
            if self._interaction_cooldown > 0:
                return
            self._interaction_cooldown = 0.5

            # 1. NPC Interaction (Projection-based)
            if self._check_npc_interactions():
                return

            # 2. Interactive Objects (Proximity & Orientation based)
            if self._check_object_interactions():
                return

            # 3. Pickup Items
            if self._check_pickup_interactions():
                return

            # 4. Failed Interaction (Question mark)
            # Trigger 'question' emote if enabled and we are facing a collision or just pressed Action in thin air
            if Settings.ENABLE_FAILED_INTERACTION_EMOTE:
                self.game.player.playerEmote("question")

    def _check_proximity_emotes(self):
        """Trigger proximity emotes when near interactive objects, pickups or NPCs."""
        if self._emote_cooldown > 0:
            return
        if self._check_interactive_emote():
            return
        if self._check_pickup_emote():
            return
        self._check_npc_emote()

    def _check_interactive_emote(self) -> bool:
        """Trigger 'interact' emote near a valid interactive object. Returns True if triggered."""
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state

        for obj in self.game.interactives:
            sq_dist = p_pos.distance_squared_to(obj.pos)
            if sq_dist >= _RANGE_SQ_48:
                continue

            is_on_top = sq_dist < _RANGE_SQ_16 and getattr(obj, "is_passable", False)
            is_aligned = abs(p_pos.x - obj.pos.x) < 20 or abs(p_pos.y - obj.pos.y) < 20

            if is_on_top:
                valid_position = True
            elif getattr(obj, "activate_from_anywhere", False):
                valid_position = is_aligned and self._facing_toward(p_pos, p_state, obj.pos)
            else:
                valid_position = is_aligned and self._verify_orientation(obj, p_state, p_pos)

            if not valid_position:
                continue
            if obj.is_on and getattr(obj, "sub_type", "") in ("chest", "door"):
                continue
            if obj != getattr(self, "_last_proximity_target", None):
                self.game.player.playerEmote("interact")
                self._emote_cooldown = 0.8
                self._last_proximity_target = obj
            return True

        return False

    def _check_pickup_emote(self) -> bool:
        """Trigger 'question' emote near a pickup. Returns True if triggered."""
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state

        for pickup in self.game.pickups:
            sq_dist = p_pos.distance_squared_to(pickup.pos)
            if sq_dist >= _RANGE_SQ_48:
                continue
            is_on_top = sq_dist < _RANGE_SQ_16
            is_aligned = abs(p_pos.x - pickup.pos.x) < 20 or abs(p_pos.y - pickup.pos.y) < 20
            if is_on_top or (is_aligned and self._facing_toward(p_pos, p_state, pickup.pos)):
                if pickup != getattr(self, "_last_proximity_target", None):
                    self.game.player.playerEmote("question")
                    self._emote_cooldown = 0.8
                    self._last_proximity_target = pickup
                return True

        return False

    def _check_npc_emote(self):
        """Trigger 'interact' emote near an NPC. Resets target if nothing in range."""
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state

        for npc in self.game.npcs:
            if p_pos.distance_squared_to(npc.pos) >= _RANGE_SQ_48:
                continue
            is_aligned = abs(p_pos.x - npc.pos.x) < 20 or abs(p_pos.y - npc.pos.y) < 20
            if is_aligned and self._facing_toward(p_pos, p_state, npc.pos):
                if npc != getattr(self, "_last_proximity_target", None):
                    self.game.player.playerEmote("interact")
                    self._emote_cooldown = 0.8
                    self._last_proximity_target = npc
                return

        self._last_proximity_target = None

    def _check_npc_interactions(self) -> bool:
        """Check for nearby NPCs in front of the player."""
        dir_vector = self._get_player_facing_vector()
        target_pos = self.game.player.pos + dir_vector * Settings.TILE_SIZE
        target_rect = pygame.Rect(target_pos.x - 16, target_pos.y - 16, 32, 32)

        for npc in self.game.npcs:
            if npc.rect and npc.rect.colliderect(target_rect):
                res = npc.interact(self.game.player)
                if res:
                    if npc.is_moving:
                        self.game._pending_npc_dialogue = (npc, res)
                    else:
                        self.game._trigger_npc_bubble(npc, res)
                return True
        return False

    def _check_object_interactions(self):
        """Check for nearby interactive objects based on proximity and orientation."""
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state

        for obj in self.game.interactives:
            sq_dist = p_pos.distance_squared_to(obj.pos)
            valid_orientation = False

            # On top check for passable objects
            if getattr(obj, "is_passable", False) and sq_dist < _RANGE_SQ_16:
                valid_orientation = True

            # Adjacent + directional check for activate_from_anywhere objects
            if not valid_orientation and getattr(obj, "activate_from_anywhere", False):
                is_aligned = abs(p_pos.x - obj.pos.x) < 20 or abs(p_pos.y - obj.pos.y) < 20
                if (
                    sq_dist < _RANGE_SQ_48
                    and is_aligned
                    and self._facing_toward(p_pos, p_state, obj.pos)
                ):
                    valid_orientation = True

            # Standard Directional Logic
            if not valid_orientation and sq_dist < _RANGE_SQ_45:
                valid_orientation = self._verify_orientation(obj, p_state, p_pos)

            if valid_orientation:
                res = obj.interact(self.game.player)

                if getattr(obj, "sfx", None):
                    # Audio needs real distance (not squared)
                    dist = p_pos.distance_to(obj.pos)
                    vol_mult = max(0.4, 1.0 - dist / 120.0)
                    self.game.audio_manager.play_sfx(
                        str(obj.sfx),
                        str(getattr(obj, "element_id", "")),
                        volume_multiplier=vol_mult,
                    )

                if res:
                    self.game._trigger_dialogue(res)
                else:
                    if hasattr(obj, "_world_state_key"):
                        self.game.world_state.set(obj._world_state_key, {"is_on": obj.is_on})

                    target = getattr(obj, "target_id", None)
                    if target:
                        self.toggle_entity_by_id(target, depth=1)

                if getattr(obj, "sub_type", "") == "chest":
                    if obj.is_on:
                        self._open_chest_entity = obj
                        if hasattr(self.game, "chest_ui"):
                            self.game.chest_ui.open(obj, self.game.player)
                    else:
                        chest_ui = getattr(self.game, "chest_ui", None)
                        if chest_ui is not None and chest_ui.is_open:
                            chest_ui.close()
                        self._open_chest_entity = None
                        self._last_proximity_target = obj
                        self._emote_cooldown = 1.0
                return True
        return False

    def _check_pickup_interactions(self) -> bool:
        """Check for nearby pickup items."""
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state

        for pickup in self.game.pickups:
            sq_dist = p_pos.distance_squared_to(pickup.pos)
            if sq_dist >= _RANGE_SQ_48:
                continue
            is_on_top = sq_dist < _RANGE_SQ_16
            is_aligned = abs(p_pos.x - pickup.pos.x) < 20 or abs(p_pos.y - pickup.pos.y) < 20
            if not (is_on_top or (is_aligned and self._facing_toward(p_pos, p_state, pickup.pos))):
                continue

            remaining = self.game.player.inventory.add_item(pickup.item_id, pickup.quantity)
            picked_up = pickup.quantity - remaining
            pickup.quantity = remaining

            if picked_up > 0:
                logging.info(f"Picked up {picked_up}x {pickup.item_id}")

            state_key = getattr(pickup, "_world_state_key", None)
            if pickup.quantity <= 0:
                if state_key:
                    self.game.world_state.set(state_key, {"collected": True})
                pickup.kill()
            else:
                if state_key:
                    self.game.world_state.set(state_key, {"quantity": pickup.quantity})
                self.game.player.playerEmote("frustration")
                logging.info(f"Inventory full, {pickup.quantity}x {pickup.item_id} left on ground.")

            return True
        return False

    def _get_player_facing_vector(self) -> pygame.math.Vector2:
        """Get unit vector based on player facing direction."""
        p_state = self.game.player.current_state
        if p_state == "down":
            return pygame.math.Vector2(0, 1)
        if p_state == "up":
            return pygame.math.Vector2(0, -1)
        if p_state == "left":
            return pygame.math.Vector2(-1, 0)
        if p_state == "right":
            return pygame.math.Vector2(1, 0)
        return pygame.math.Vector2(0, 0)

    def _facing_toward(
        self, player_pos: pygame.math.Vector2, facing: str, obj_pos: pygame.math.Vector2
    ) -> bool:
        """Return True if the player is looking in the direction of obj_pos from player_pos."""
        dx = obj_pos.x - player_pos.x
        dy = obj_pos.y - player_pos.y
        if abs(dx) >= abs(dy):  # horizontal dominant axis
            return (facing == "right" and dx > 0) or (facing == "left" and dx < 0)
        # vertical dominant axis
        return (facing == "down" and dy > 0) or (facing == "up" and dy < 0)

    def _verify_orientation(self, obj, p_state: str, p_pos: pygame.math.Vector2) -> bool:
        """Verify if player is correctly oriented toward an object to interact."""
        # o_dir is the direction the object faces (its front).
        # To interact with its front, the player must be on that side, facing the opposite way.
        o_dir = getattr(obj, "direction_str", "down")
        o_pos = obj.pos

        # Enforce orthogonal alignment
        x_aligned = abs(p_pos.x - o_pos.x) < 20
        y_aligned = abs(p_pos.y - o_pos.y) < 20

        # Standard directional check (player must be at the object's front)
        if o_dir == "up" and p_state == "down" and p_pos.y < o_pos.y and x_aligned:
            return True
        if o_dir == "down" and p_state == "up" and p_pos.y > o_pos.y and x_aligned:
            return True
        if o_dir == "left" and p_state == "right" and p_pos.x < o_pos.x and y_aligned:
            return True
        if o_dir == "right" and p_state == "left" and p_pos.x > o_pos.x and y_aligned:
            return True

        # Relaxation for open doors (allow walking through/closing from the opposite side)
        if obj.sub_type == "door" and getattr(obj, "is_on", False):
            if o_dir == "up" and p_state == "up" and p_pos.y > o_pos.y and x_aligned:
                return True
            if o_dir == "down" and p_state == "down" and p_pos.y < o_pos.y and x_aligned:
                return True
            if o_dir == "left" and p_state == "left" and p_pos.x > o_pos.x and y_aligned:
                return True
            if o_dir == "right" and p_state == "right" and p_pos.x < o_pos.x and y_aligned:
                return True

        return False

    def _check_chest_auto_close(self) -> None:
        """Auto-close chest UI when player leaves interaction zone.

        Mirrors the full close sequence: triggers the entity closing animation,
        persists state in world_state, and hides the UI overlay.
        """
        if getattr(self, "_open_chest_entity", None) is None:
            return
        chest_ui = getattr(self.game, "chest_ui", None)
        if chest_ui is None or not chest_ui.is_open:
            return

        player_pos = self.game.player.pos
        chest = self._open_chest_entity
        if chest is None or chest.pos is None:
            return
        sq_dist = player_pos.distance_squared_to(chest.pos)
        out_of_range = sq_dist > _RANGE_SQ_45
        wrong_orientation = not self._verify_orientation(
            chest, self.game.player.current_state, player_pos
        )

        if out_of_range or wrong_orientation:
            self._close_chest(chest, chest_ui)

    def _close_chest(self, chest, chest_ui) -> None:
        """Trigger chest closing animation, play sfx, persist state, and hide UI."""
        chest.interact(self.game.player)  # toggles is_on=False + starts animation
        if getattr(chest, "sfx", None):
            dist = self.game.player.pos.distance_to(chest.pos)
            vol_mult = max(0.4, 1.0 - dist / 120.0)
            self.game.audio_manager.play_sfx(
                str(chest.sfx), str(getattr(chest, "element_id", "")), volume_multiplier=vol_mult
            )
        if hasattr(chest, "_world_state_key"):
            self.game.world_state.set(chest._world_state_key, {"is_on": chest.is_on})
        chest_ui.close()
        self._open_chest_entity = None
        # Suppress ! emote from firing immediately while player is still in proximity
        self._last_proximity_target = chest
        self._emote_cooldown = 1.0

    def is_collidable(self, px_center: float, py_center: float, requester=None) -> bool:
        """Collision checking adapter for Entity target position."""
        # 1. Check Map Tiles
        wx, wy = self.game.layout.to_world(px_center, py_center)
        if self.game.map_manager.is_collidable(int(wx), int(wy)):
            return True

        # 2. Check Dynamic Obstacles (Doors, etc.)
        for obj in self.game.obstacles_group:
            if obj == requester:
                continue
            if obj.rect and obj.rect.collidepoint(px_center, py_center):
                return True

        # 3. Check NPCs
        for npc in self.game.npcs:
            if npc == requester:
                continue
            if npc.rect and npc.rect.collidepoint(px_center, py_center):
                return True

        # 4. Check Player (if requester is an NPC)
        if self.game.player != requester:
            if self.game.player.rect and self.game.player.rect.collidepoint(px_center, py_center):
                return True

        return False

    def check_teleporters(self, was_moving: bool):
        """Active spatial check testing if interaction just resolved over teleport rect."""
        just_arrived = was_moving and not self.game.player.is_moving
        intent_active = (
            not was_moving
            and not self.game.player.is_moving
            and self.game.player.direction.magnitude() > 0
        )

        if not just_arrived and not intent_active:
            return

        for tp in self.game.teleports_group:
            # Player hits teleport zone via strict collision rect
            if (
                tp.rect is None
                or not self.game.player.rect
                or not self.game.player.rect.colliderect(tp.rect)
            ):
                continue

            req = getattr(tp, "required_direction", "any")

            if just_arrived:
                # Direction guard: on arrival, must match required direction (unless 'any')
                if req != "any" and self.game.player.current_state != req:
                    logging.debug(
                        f"Teleport skipped (Arrival) — required '{req}', player facing '{self.game.player.current_state}'"
                    )
                    continue
            elif intent_active:
                # Intent guard: do not trigger intent for 'any' portals to avoid trapping the player
                if req == "any":
                    continue
                if self.game.player.current_state != req:
                    logging.debug(
                        f"Teleport skipped (Intent) — required '{req}', player faced '{self.game.player.current_state}'"
                    )
                    continue

            logging.info(f"Teleport triggered -> {tp.target_map} / {tp.target_spawn_id}")
            if getattr(tp, "sfx", None):
                self.game.audio_manager.play_sfx(tp.sfx, str(id(tp)))

            self.game.transition_map(tp.target_map, tp.target_spawn_id, tp.transition_type)
            break

    def toggle_entity_by_id(self, target_id: str, depth: int = 0):
        """Toggle the state of any entity matching element_id == target_id."""
        if not target_id:
            return

        if depth > 1:
            logging.warning(
                f"Interaction chaining loop detected for target_id={target_id}. Breaking chain."
            )
            return

        for group in (self.game.interactives, self.game.npcs):
            for entity in group:
                if getattr(entity, "element_id", None) == target_id:
                    if hasattr(entity, "interact"):
                        entity.interact(self.game.player)

                        if getattr(entity, "sfx", None):
                            self.game.audio_manager.play_sfx(
                                str(entity.sfx), str(getattr(entity, "element_id", ""))
                            )

                        # Save state
                        if hasattr(entity, "_world_state_key"):
                            self.game.world_state.set(
                                entity._world_state_key,
                                {
                                    "is_on": entity.is_on,
                                    "light_control": getattr(entity, "light_control", "auto"),
                                },
                            )

                        next_target = getattr(entity, "target_id", None)
                        if next_target:
                            self.toggle_entity_by_id(next_target, depth + 1)
