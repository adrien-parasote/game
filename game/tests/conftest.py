import os
from unittest.mock import patch

import pygame
import pytest
from src.config import Settings


@pytest.fixture(scope="session", autouse=True)
def setup_pygame():
    """Initialize headless pygame once for the entire session."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    # Create a dummy screen for tests requiring a display surface
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def reset_asset_manager():
    """Reset the AssetManager singleton before each test to prevent state leakage."""
    from src.engine.asset_manager import AssetManager

    AssetManager._instance = None
    yield
    AssetManager._instance = None


@pytest.fixture
def mock_spritesheet():
    """Global mock for spritesheet loading to prevent missing file errors."""
    with (
        patch(
            "src.graphics.spritesheet.SpriteSheet.load_grid",
            return_value=[pygame.Surface((32, 48)) for _ in range(16)],
        ),
        patch(
            "src.graphics.spritesheet.SpriteSheet.load_grid_by_size",
            return_value=[pygame.Surface((32, 32)) for _ in range(16)],
        ),
        patch("src.graphics.spritesheet.SpriteSheet.__init__", return_value=None),
    ):
        yield


# assert True (legacy bypass)
