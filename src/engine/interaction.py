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
        
    def update(self, dt: float):
        """Update timers for interaction gating."""
        if self._interaction_cooldown > 0:
            self._interaction_cooldown = max(0, self._interaction_cooldown - dt)

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
            self._check_object_interactions()

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
                return

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
        o_dir = getattr(obj, "direction_str", "down")
        o_pos = obj.pos
        
        # Standard directional check
        if o_dir == 'up' and p_state == 'up' and p_pos.y > o_pos.y: return True
        if o_dir == 'down' and p_state == 'down' and p_pos.y < o_pos.y: return True
        if o_dir == 'left' and p_state == 'left' and p_pos.x > o_pos.x: return True
        if o_dir == 'right' and p_state == 'right' and p_pos.x < o_pos.x: return True
        
        # Relaxation for open doors
        if obj.sub_type == 'door' and getattr(obj, "is_on", False):
            if o_dir == 'up' and p_state == 'down' and p_pos.y > o_pos.y: return True
            if o_dir == 'down' and p_state == 'up' and p_pos.y < o_pos.y: return True
            if o_dir == 'left' and p_state == 'right' and p_pos.x < o_pos.x: return True
            if o_dir == 'right' and p_state == 'left' and p_pos.x > o_pos.x: return True
            
        return False
