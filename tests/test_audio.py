import pytest
from unittest.mock import patch, MagicMock
from src.engine.audio import AudioManager

@pytest.fixture
def audio_manager():
    with patch('pygame.mixer.Sound'), patch('pygame.mixer.music'):
        am = AudioManager()
        yield am

def test_audio_play_sfx(audio_manager):
    with patch('os.path.exists', return_value=True):
        audio_manager.play_sfx("test_sound")
        # Check if sound was loaded and played
        assert "test_sound" in audio_manager.sounds

def test_audio_play_bgm(audio_manager):
    with patch('os.path.exists', return_value=True):
        audio_manager.play_bgm("test_music")
        assert audio_manager.current_bgm == "test_music"

def test_audio_mute_toggle(audio_manager):
    assert audio_manager.is_muted is False
    audio_manager.toggle_mute()
    assert audio_manager.is_muted is True
