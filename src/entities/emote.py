import pygame
import os
import logging
from src.graphics.spritesheet import SpriteSheet
from src.entities.emote_sprite import EmoteSprite

class EmoteManager:
    """
    Manages player emotes, including loading assets and triggering animations.
    """
    def __init__(self, player):
        self.player = player
        self.emote_group = None # To be set by the Game class
        
        # Mapping names to sprite sheet indices
        self.emote_map = {
            "love": 0,
            "bored": 1,
            "interact": 2,
            "question": 3
        }
        
        # Load spritesheet
        sheet_path = os.path.join("assets", "images", "sprites", "04-emotes.png")
        if not os.path.exists(sheet_path):
            # Fallback if path is different (per user request assets/sprites/04-emotes.png)
            sheet_path = os.path.join("assets", "sprites", "04-emotes.png")
            
        try:
            sheet = SpriteSheet(sheet_path)
            # The sheet is 4 frames horizontally, 1 vertically (assumption based on 32x32 size and 4 indices)
            self.frames = sheet.load_grid(cols=4, rows=1)
        except Exception as e:
            logging.error(f"Failed to load emote spritesheet: {e}")
            self.frames = []

    def trigger(self, name: str):
        """Trigger an emote by name. Replaces any existing emote."""
        if not self.emote_group:
            logging.warning("EmoteManager: emote_group not set.")
            return
            
        index = self.emote_map.get(name)
        if index is None or index >= len(self.frames):
            logging.warning(f"EmoteManager: Emote '{name}' not found or index out of range.")
            return
            
        # Replace existing emotes (clear the group for this player)
        # In this simple implementation, we just clear the whole group 
        # since it's dedicated to player emotes in the Game class.
        self.emote_group.empty()
        
        # Create the new emote sprite
        EmoteSprite(self.frames[index], self.player, self.emote_group)

        
        # Play sound
        if hasattr(self.player, "audio_manager"):
            self.player.audio_manager.play_sfx("03-emote", source_id="player_emote")
