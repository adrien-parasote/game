import os
import pygame
import pytest
import tempfile
from src.engine.asset_manager import AssetManager
from src.map.manager import MapManager
from src.map.layout import LayoutStrategy
from src.engine.interaction import InteractionManager
from types import SimpleNamespace

# Initialize pygame in headless mode for tests
@pytest.fixture(autouse=True)
def init_pygame():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.display.quit()

# Helper LayoutStrategy for MapManager tests
class DummyLayout(LayoutStrategy):
    def __init__(self, tile_size=32):
        self.tile_size = tile_size
    def to_screen(self, x, y):
        return x * self.tile_size, y * self.tile_size

def test_asset_manager_caches_images(tmp_path):
    # Create a temporary image file
    img_path = tmp_path / "test.png"
    surface = pygame.Surface((10, 10))
    surface.fill((255, 0, 0))
    pygame.image.save(surface, str(img_path))

    am = AssetManager()
    # First load should read from disk
    img1 = am.get_image(str(img_path))
    assert isinstance(img1, pygame.Surface)
    # Second load should hit cache (same object)
    img2 = am.get_image(str(img_path))
    assert img1 is img2

def test_map_manager_layer_surface_caching(tmp_path):
    # Setup a simple tileset with a single tile image
    img_path = tmp_path / "tile.png"
    tile_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
    tile_surface.fill((0, 255, 0, 255))
    pygame.image.save(tile_surface, str(img_path))

    # Prepare map data structure expected by MapManager
    tile_id = 1
    map_data = {
        "layers": {0: [[tile_id]]},  # 1x1 layer with our tile
        "tiles": {
            tile_id: SimpleNamespace(
                image=pygame.image.load(str(img_path)).convert_alpha(),
                collidable=False,
                depth=0,
                occluded_image=None,
            )
        },
    }
    layout = DummyLayout()
    manager = MapManager(map_data, layout)

    surface1 = manager.get_layer_surface(0, pygame)
    assert isinstance(surface1, pygame.Surface)
    # Cached surface should be returned on second call
    surface2 = manager.get_layer_surface(0, pygame)
    assert surface1 is surface2
    # Verify that the tile was blitted correctly (pixel color matches)
    pixel = surface1.get_at((16, 16))  # centre of the tile
    assert pixel[:3] == (0, 255, 0)

def test_interaction_verify_orientation_cases():
    # Mock objects for orientation tests
    class DummyObj:
        def __init__(self, direction):
            self.direction_str = direction
            self.sub_type = ""  # not a door
            self.pos = pygame.math.Vector2(100, 100)

    im = InteractionManager(game=SimpleNamespace())
    # Object at 100, 100
    obj_pos = pygame.math.Vector2(100, 100)
    
    # 1. Player ABOVE object (y=64 < 100), facing DOWN. Object faces UP. -> True
    p_pos = pygame.math.Vector2(100, 64)
    obj = DummyObj('up')
    obj.pos = obj_pos
    assert im._verify_orientation(obj, 'down', p_pos) is True

    # 2. Player BELOW object (y=136 > 100), facing UP. Object faces DOWN. -> True
    p_pos2 = pygame.math.Vector2(100, 136)
    obj2 = DummyObj('down')
    obj2.pos = obj_pos
    assert im._verify_orientation(obj2, 'up', p_pos2) is True

    # 3. Player LEFT of object (x=64 < 100), facing RIGHT. Object faces LEFT. -> True
    p_pos3 = pygame.math.Vector2(64, 100)
    obj3 = DummyObj('left')
    obj3.pos = obj_pos
    assert im._verify_orientation(obj3, 'right', p_pos3) is True

    # 4. Wrong orientation should be False
    assert im._verify_orientation(obj3, 'left', p_pos3) is False
