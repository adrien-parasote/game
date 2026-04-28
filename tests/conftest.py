import pytest
import pygame
import os
from unittest.mock import MagicMock, patch
from src.config import Settings

from src.engine.asset_manager import AssetManager

@pytest.fixture(autouse=True)
def setup_headless_pygame():
    """Initialize pygame in headless mode for all tests."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.display.get_init():
        pygame.display.init()
    pygame.display.set_mode((1280, 720))
    Settings.load()
    
    # Clear caches to avoid stale pygame objects (like Fonts) between tests
    AssetManager().clear_cache()
    
    yield

@pytest.fixture
def mock_font():
    """Mock pygame font (Font and SysFont) to avoid real loading and allow size asserts."""
    font_instance = MagicMock()
    font_instance.size.side_effect = lambda text: (len(text) * 10, 20)
    font_instance.get_linesize.return_value = 20
    font_instance.render.return_value = pygame.Surface((10, 10))
    
    with patch('pygame.font.Font', return_value=font_instance), \
         patch('pygame.font.SysFont', return_value=font_instance):
        yield font_instance

@pytest.fixture
def mock_screen():
    """Provide a mock screen surface."""
    return pygame.Surface((1280, 720))
