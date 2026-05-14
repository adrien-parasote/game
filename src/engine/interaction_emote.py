# src/engine/interaction_emote.py
"""Mixin for handling proximity emotes in the interaction manager."""

from src.engine.spatial_utils import facing_toward

_RANGE_SQ_48: float = 48.0**2
_RANGE_SQ_16: float = 16.0**2


class InteractionEmoteMixin:
    """Handles triggering emotes when near interactive objects, pickups, or NPCs."""

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
                valid_position = is_aligned and facing_toward(p_pos, p_state, obj.pos)
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
            if is_on_top or (is_aligned and facing_toward(p_pos, p_state, pickup.pos)):
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
            if is_aligned and facing_toward(p_pos, p_state, npc.pos):
                if npc != getattr(self, "_last_proximity_target", None):
                    self.game.player.playerEmote("interact")
                    self._emote_cooldown = 0.8
                    self._last_proximity_target = npc
                return

        self._last_proximity_target = None
