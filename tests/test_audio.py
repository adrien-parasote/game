import pytest
import pygame
import os
from src.engine.audio import AudioManager

@pytest.fixture(autouse=True)
def setup_pygame_audio():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pytest.skip("Audio mixer not available")
    yield
    pygame.mixer.quit()
    pygame.quit()

def test_audio_manager_play_bgm():
    am = AudioManager()
    # Mocking BGM file check since we don't have real assets in test env usually
    # But AudioManager checks if file exists.
    # Let's create a dummy sound file if possible, or just mock os.path.exists
    am.play_bgm("non_existent_bgm")
    assert pygame.mixer.music.get_busy() == False # Should not play if file missing

def test_audio_manager_toggle_mute():
    am = AudioManager()
    initial_mute = am.is_muted
    am.toggle_mute()
    assert am.is_muted == (not initial_mute)
    am.toggle_mute()
    assert am.is_muted == initial_mute

def test_audio_manager_sfx_cache():
    am = AudioManager()
    # SFX loading also checks for file existence
    am.play_sfx("test_sfx", "obj_1")
    # Even if it fails to load, it shouldn't crash
