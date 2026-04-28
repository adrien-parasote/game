import pygame
import logging
from src.config import Settings

class InteractionManager:
    """
    Manages spatial interactions between the player and world entities (NPCs, Objects).
    Decouples interaction logic from the core Game class.
    """
    
    def __init__(self, game):
        self.game = game
        self._interaction_cooldown = 0
        self._emote_cooldown = 0 # Cooldown between proximity emote triggers
        self._last_proximity_target = None # Tracks the last entity we emoted for
        
    def update(self, dt: float):
        """Update timers and check for nearby interactives to trigger indicators."""
        if self._interaction_cooldown > 0:
            self._interaction_cooldown = max(0, self._interaction_cooldown - dt)
        if self._emote_cooldown > 0:
            self._emote_cooldown = max(0, self._emote_cooldown - dt)
            
        self._check_proximity_emotes()

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
                self.game.player.playerEmote('question')

    def _check_proximity_emotes(self):
        """Trigger 'interact' emote when near an interactive object or NPC."""
        # Only check if cooldown is over to avoid spamming
        if self._emote_cooldown > 0:
            return
            
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state
        range_dist = 48.0 # 48 pixels
        
        # Check Objects
        for obj in self.game.interactives:
            if p_pos.distance_to(obj.pos) < range_dist:
                is_aligned = abs(p_pos.x - obj.pos.x) < 20 or abs(p_pos.y - obj.pos.y) < 20
                
                valid_position = False
                if getattr(obj, "activate_from_anywhere", False):
                    valid_position = is_aligned and self._facing_toward(p_pos, p_state, obj.pos)
                else:
                    valid_position = is_aligned and self._verify_orientation(obj, p_state, p_pos)
                    
                if valid_position:
                    # Suppress emote if the object is open/activated and is a container/barrier type
                    if obj.is_on and getattr(obj, "sub_type", "") in ["chest", "door"]:
                        continue
                        
                    if obj != getattr(self, '_last_proximity_target', None):
                        self.game.player.playerEmote('interact')
                        self._emote_cooldown = 0.8 # 0.6s animation + 0.2s pause
                        self._last_proximity_target = obj
                    return
                
        # Check Pickups
        for pickup in self.game.pickups:
            if p_pos.distance_to(pickup.pos) < range_dist:
                if pickup != getattr(self, '_last_proximity_target', None):
                    self.game.player.playerEmote('question')
                    self._emote_cooldown = 0.8
                    self._last_proximity_target = pickup
                return

        # Check NPCs
        for npc in self.game.npcs:
            if p_pos.distance_to(npc.pos) < range_dist:
                is_aligned = abs(p_pos.x - npc.pos.x) < 20 or abs(p_pos.y - npc.pos.y) < 20
                is_facing = self._facing_toward(p_pos, p_state, npc.pos)
                if is_aligned and is_facing:
                    if npc != getattr(self, '_last_proximity_target', None):
                        self.game.player.playerEmote('interact')
                        self._emote_cooldown = 0.8 # 0.6s animation + 0.2s pause
                        self._last_proximity_target = npc
                    return
                
        # Reset if nothing is in range
        self._last_proximity_target = None



    def _check_npc_interactions(self) -> bool:
        """Check for nearby NPCs in front of the player."""
        dir_vector = self._get_player_facing_vector()
        target_pos = self.game.player.pos + dir_vector * Settings.TILE_SIZE
        target_rect = pygame.Rect(target_pos.x - 16, target_pos.y - 16, 32, 32)
        
        for npc in self.game.npcs:
            if npc.rect.colliderect(target_rect):
                res = npc.interact(self.game.player)
                if res:
                    title = getattr(npc, 'name', '')
                    self.game._trigger_dialogue(res, title=title)
                return True
        return False

    def _check_object_interactions(self):
        """Check for nearby interactive objects based on proximity and orientation."""
        p_pos = self.game.player.pos
        p_state = self.game.player.current_state
        
        for obj in self.game.interactives:
            dist = p_pos.distance_to(obj.pos)
            valid_orientation = False
            
            # Adjacent + directional check for specific objects
            if getattr(obj, "activate_from_anywhere", False):
                if dist < 48.0 and self._facing_toward(p_pos, p_state, obj.pos):
                    valid_orientation = True
                    
            # Standard Directional Logic
            if not valid_orientation and dist < 45.0:
                valid_orientation = self._verify_orientation(obj, p_state, p_pos)
                
            if valid_orientation:
                res = obj.interact(self.game.player)
                
                if getattr(obj, "sfx", None):
                    self.game.audio_manager.play_sfx(obj.sfx, getattr(obj, "element_id", None))
                
                if res:
                    self.game._trigger_dialogue(res)
                else:
                    # Save state for toggleable objects
                    if hasattr(obj, '_world_state_key'):
                        self.game.world_state.set(obj._world_state_key, {'is_on': obj.is_on})
                    
                    target = getattr(obj, "target_id", None)
                    if target:
                        self.game.toggle_entity_by_id(target, depth=1)
                return True
        return False

    def _check_pickup_interactions(self) -> bool:
        """Check for nearby pickup items."""
        p_pos = self.game.player.pos
        range_dist = 48.0
        
        for pickup in self.game.pickups:
            if p_pos.distance_to(pickup.pos) < range_dist:
                # Try to add to inventory
                remaining = self.game.player.inventory.add_item(pickup.item_id, pickup.quantity)
                
                # Update pickup quantity based on what was actually added
                picked_up = pickup.quantity - remaining
                pickup.quantity = remaining
                
                if picked_up > 0:
                    logging.info(f"Picked up {picked_up}x {pickup.item_id}")
                
                if pickup.quantity <= 0:
                    # Item fully picked up
                    pickup.kill()
                else:
                    # Inventory full or partial pickup
                    self.game.player.playerEmote('frustration')
                    logging.info(f"Inventory full, {pickup.quantity}x {pickup.item_id} left on ground.")
                
                return True
        return False

    def _get_player_facing_vector(self) -> pygame.math.Vector2:
        """Get unit vector based on player facing direction."""
        p_state = self.game.player.current_state
        if p_state == 'down': return pygame.math.Vector2(0, 1)
        if p_state == 'up': return pygame.math.Vector2(0, -1)
        if p_state == 'left': return pygame.math.Vector2(-1, 0)
        if p_state == 'right': return pygame.math.Vector2(1, 0)
        return pygame.math.Vector2(0, 0)

    def _facing_toward(self, player_pos: pygame.math.Vector2, facing: str, obj_pos: pygame.math.Vector2) -> bool:
        """Return True if the player is looking in the direction of obj_pos from player_pos."""
        dx = obj_pos.x - player_pos.x
        dy = obj_pos.y - player_pos.y
        if abs(dx) >= abs(dy):  # horizontal dominant axis
            return (facing == 'right' and dx > 0) or (facing == 'left' and dx < 0)
        # vertical dominant axis
        return (facing == 'down' and dy > 0) or (facing == 'up' and dy < 0)

    def _verify_orientation(self, obj, p_state: str, p_pos: pygame.math.Vector2) -> bool:
        """Verify if player is correctly oriented toward an object to interact."""
        # o_dir is the direction the object faces (its front).
        # To interact with its front, the player must be on that side, facing the opposite way.
        o_dir = getattr(obj, "direction_str", "down")
        o_pos = obj.pos
        
        # Enforce orthogonal alignment
        x_aligned = abs(p_pos.x - o_pos.x) < 20
        y_aligned = abs(p_pos.y - o_pos.y) < 20
        
        # DEBUG LOGGING (to trace the exact reason for failure)
        # logging.info(f"[Verify] o_dir={o_dir}, p_state={p_state}, x_aligned={x_aligned}, y_aligned={y_aligned}, p_pos={p_pos}, o_pos={o_pos}")
        
        # Standard directional check (player must be at the object's front)
        if o_dir == 'up' and p_state == 'down' and p_pos.y < o_pos.y and x_aligned:
            return True
        if o_dir == 'down' and p_state == 'up' and p_pos.y > o_pos.y and x_aligned:
            return True
        if o_dir == 'left' and p_state == 'right' and p_pos.x < o_pos.x and y_aligned:
            return True
        if o_dir == 'right' and p_state == 'left' and p_pos.x > o_pos.x and y_aligned:
            return True
        
        # Relaxation for open doors (allow walking through/closing from the opposite side)
        if obj.sub_type == 'door' and getattr(obj, "is_on", False):
            if o_dir == 'up' and p_state == 'up' and p_pos.y > o_pos.y and x_aligned:
                return True
            if o_dir == 'down' and p_state == 'down' and p_pos.y < o_pos.y and x_aligned:
                return True
            if o_dir == 'left' and p_state == 'left' and p_pos.x > o_pos.x and y_aligned:
                return True
            if o_dir == 'right' and p_state == 'right' and p_pos.x < o_pos.x and y_aligned:
                return True
            
        return False
