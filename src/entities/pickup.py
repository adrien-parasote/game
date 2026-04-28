import pygame
import os
import logging
from .base import BaseEntity
from src.graphics.spritesheet import SpriteSheet
from src.config import Settings

class PickupItem(BaseEntity):
    """
    World entity that can be picked up by the player.
    """
    def __init__(self, pos: tuple, groups: list[pygame.sprite.Group], 
                 item_id: str, sprite_sheet: str, quantity: int = 1, element_id: str = None):
        super().__init__(pos, groups, element_id=element_id)
        self.item_id = item_id
        self.quantity = quantity
        
        # Load Sprite
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", sprite_sheet)
        sheet = SpriteSheet(sheet_path)
        if sheet.valid:
            # Pickups use the first frame (index 0) of their spritesheet
            frames = sheet.load_grid(1, 1, width=Settings.TILE_SIZE, height=Settings.TILE_SIZE)
            self.image = frames[0]
        else:
            logging.error(f"PickupItem: Could not load sprite {sprite_sheet}")
            self.image = pygame.Surface((Settings.TILE_SIZE, Settings.TILE_SIZE))
            self.image.fill((255, 0, 255)) # Magenta placeholder
            
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(self.rect.center)
        self.type = "object" # For identification in InteractionManager
