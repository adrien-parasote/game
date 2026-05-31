from unittest.mock import patch

import pygame
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

    def test_image_rescaled_when_width_differs_from_tile_size(self):
        """Ligne 51 : smoothscale déclenché quand la frame n'est pas TILE_SIZE×TILE_SIZE."""
        small_surf = pygame.Surface((16, 16))  # délibérément plus petit que TILE_SIZE (32)
        with patch("src.entities.pickup.SpriteSheet") as M:
            M.return_value.valid = True
            M.return_value.load_grid.return_value = [small_surf]
            from src.entities.pickup import PickupItem
            item = PickupItem(pos=(0, 0), groups=[], item_id="coin", sprite_sheet="coin.png", quantity=1)
        assert item.image.get_width() == Settings.TILE_SIZE
        assert item.image.get_height() == Settings.TILE_SIZE
