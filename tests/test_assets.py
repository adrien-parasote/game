import pytest
import pygame
import os
from unittest.mock import MagicMock, patch
from src.engine.asset_manager import AssetManager
from src.engine.audio import AudioManager

@pytest.fixture(autouse=True)
def init_pygame():
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.display.quit()

def test_asset_manager_singleton_caching(tmp_path):
    am = AssetManager()
    am.clear_cache()
    img_path = tmp_path / 'test.png'
    surface = pygame.Surface((10, 10))
    pygame.image.save(surface, str(img_path))
    
    img1 = am.get_image(str(img_path))
    img2 = am.get_image(str(img_path))
    assert img1 is img2

def test_asset_manager_invalid_path():
    am = AssetManager()
    with pytest.raises(FileNotFoundError):
        am.get_image('non_existent.png')

def test_asset_manager_placeholder_fallback():
    am = AssetManager()
    img = am.get_image('missing.png', fallback=True)
    assert img.get_at((0, 0)) == (255, 0, 255, 255)

def test_audio_manager_play_bgm():
    am = AudioManager()
    am.play_bgm('non_existent_bgm')
    assert pygame.mixer.music.get_busy() == False

def test_audio_manager_toggle_mute():
    am = AudioManager()
    initial_mute = am.is_muted
    am.toggle_mute()
    assert am.is_muted == (not initial_mute)
    am.toggle_mute()
    assert am.is_muted == initial_mute

def test_audio_manager_sfx_cache():
    am = AudioManager()
    am.play_sfx('test_sfx', 'obj_1')
