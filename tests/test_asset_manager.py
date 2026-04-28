import pytest
import pygame
import os
from src.engine.asset_manager import AssetManager

@pytest.fixture(autouse=True)
def setup_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()

def test_asset_manager_singleton_caching():
    am = AssetManager()
    # Create a dummy image for testing
    img_path = "test_image.png"
    surf = pygame.Surface((32, 32))
    pygame.image.save(surf, img_path)
    
    try:
        img1 = am.get_image(img_path)
        img2 = am.get_image(img_path)
        
        assert img1 is img2  # Cache hit (identity)
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

def test_asset_manager_invalid_path():
    am = AssetManager()
    with pytest.raises(FileNotFoundError):
        am.get_image("non_existent.png")

def test_asset_manager_placeholder_fallback():
    am = AssetManager()
    # If we want a placeholder instead of crash, we'd test that.
    # Current spec says "Log ERROR, Return pink placeholder surface" in error matrix.
    # Let's implement that behavior.
    img = am.get_image("missing.png", fallback=True)
    assert img.get_at((0, 0)) == (255, 0, 255, 255) # Pink
