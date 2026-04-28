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
            "question": 3,
            "frustration": 4
        }
        
        # Load spritesheet
        sheet_path = os.path.join("assets", "images", "sprites", "04-emotes.png")
        if not os.path.exists(sheet_path):
            # Fallback if path is different (per user request assets/sprites/04-emotes.png)
            sheet_path = os.path.join("assets", "sprites", "04-emotes.png")
            
        try:
            sheet = SpriteSheet(sheet_path)
            # 5 columns (one per emote) and 8 rows (animation frames)
            self.frames_grid = sheet.load_grid(cols=5, rows=8)
        except Exception as e:
            logging.error(f"Failed to load emote spritesheet: {e}")
            self.frames = []

    def trigger(self, name: str):
        """Trigger an emote by name. Replaces any existing emote."""
        if self.emote_group is None:
            logging.warning("EmoteManager: emote_group not set.")
            return
            
        index = self.emote_map.get(name)
        if index is None or not self.frames_grid or index >= len(self.frames_grid):
            logging.warning(f"EmoteManager: Emote '{name}' not found or index out of range.")
            return
            
        # Replace existing emotes (clear the group for this player)
        logging.debug(f"Triggering emote: {name} (index {index})")
        self.emote_group.empty()
        
        # Get all frames for this emote (column)
        emote_frames = [self.frames_grid[index + i * 5] for i in range(8)]
        
        # Create the new emote sprite
        EmoteSprite(emote_frames, self.player, self.emote_group)

        
        # Play sound
        if hasattr(self.player, "audio_manager"):
            self.player.audio_manager.play_sfx("03-emote", source_id="player_emote")
