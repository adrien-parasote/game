import logging
import os

import pygame

from src.config import Settings
from src.graphics.spritesheet import SpriteSheet

from .base import BaseEntity


class PickupItem(BaseEntity):
    """
    World entity that can be picked up by the player.
    """

    def __init__(
        self,
        pos: tuple,
        groups: list[pygame.sprite.Group],
        item_id: str,
        sprite_sheet: str,
        quantity: int = 1,
        element_id: str | None = None,
    ):
        super().__init__(pos, groups, element_id=element_id)
        self.item_id = item_id
        self.quantity = quantity

        # Ensure extension
        if not sprite_sheet.endswith(".png"):
            sprite_sheet += ".png"

        # Load Sprite
        sheet_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", sprite_sheet
        )
        if not os.path.exists(sheet_path):
            # Try icons folder as fallback
            sheet_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "assets", "images", "icons", sprite_sheet
            )

        sheet = SpriteSheet(sheet_path)
        if sheet.valid:
            # Pickups use the first frame (index 0) of their spritesheet
            frames = sheet.load_grid(1, 1)
            self.image = frames[0]
            # Ensure it's scaled to TILE_SIZE if needed
            if self.image.get_width() != Settings.TILE_SIZE:
                self.image = pygame.transform.smoothscale(
                    self.image, (Settings.TILE_SIZE, Settings.TILE_SIZE)
                )
        else:
            logging.error(
                f"PickupItem: Could not load sprite {sprite_sheet} from sprites or icons."
            )
            self.image = pygame.Surface((Settings.TILE_SIZE, Settings.TILE_SIZE))
            self.image.fill((255, 0, 255))  # Magenta placeholder

        # Hitbox is smaller than visual to ensure player always appears "in front" when standing on it
        self.rect = pygame.Rect(0, 0, 20, 10)
        self.rect.center = pos
        self.pos = pygame.math.Vector2(self.rect.center)
        self.type = "object"  # For identification in InteractionManager
