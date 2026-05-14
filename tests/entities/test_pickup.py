import pytest
import pygame
import json
import logging
from unittest.mock import MagicMock, patch
from src.config import Settings

class TestPickupCoverage:

    def test_auto_adds_png(self):
        with patch("src.entities.pickup.SpriteSheet") as M:
            M.return_value.valid = False
            from src.entities.pickup import PickupItem
            PickupItem(pos=(0, 0), groups=[], item_id="h", sprite_sheet="herb", quantity=1)
            path = M.call_args[0][0]
            assert path.endswith(".png")

    def test_valid_spritesheet_sets_image(self):
        surf = pygame.Surface((32, 32))
        with patch("src.entities.pickup.SpriteSheet") as M:
            M.return_value.valid = True
            M.return_value.load_grid.return_value = [surf]
            from src.entities.pickup import PickupItem
            item = PickupItem(pos=(0, 0), groups=[], item_id="h", sprite_sheet="herb.png", quantity=1)
            assert item.image is not None

