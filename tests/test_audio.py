import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.audio import AudioManager
from src.config import Settings

@pytest.fixture
def mock_mixer():
    with patch("pygame.mixer.init"), \
         patch("pygame.mixer.music.load"), \
         patch("pygame.mixer.music.play"), \
         patch("pygame.mixer.music.set_volume"), \
         patch("pygame.mixer.music.fadeout"), \
         patch("pygame.mixer.music.get_busy", return_value=True), \
         patch("pygame.mixer.Sound") as mock_sound:
        yield mock_sound

def test_audio_manager_singleton_bgm(mock_mixer):
    """Verify that playing the same BGM doesn't restart it."""
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", return_value=[]):
        manager = AudioManager()
        
        # First play
        manager.play_bgm("castle")
        assert manager.current_bgm == "castle"
        pygame.mixer.music.play.assert_called_once()
        
        # Second play with same name
        pygame.mixer.music.play.reset_mock()
        manager.play_bgm("castle")
        # Should NOT call play again
        pygame.mixer.music.play.assert_not_called()

def test_audio_manager_change_bgm(mock_mixer):
    """Verify that playing a different BGM restarts it."""
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", return_value=[]):
        manager = AudioManager()
        
        manager.play_bgm("castle")
        pygame.mixer.music.play.assert_called_with(loops=-1, fade_ms=500)
        
        manager.play_bgm("dungeon")
        assert manager.current_bgm == "dungeon"
        assert pygame.mixer.music.play.call_count == 2

def test_audio_manager_sfx_volume(mock_mixer):
    """Verify SFX volume is set correctly."""
    mock_sound_instance = MagicMock()
    mock_mixer.return_value = mock_sound_instance
    
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", return_value=["01-lever.ogg"]):
        Settings.SFX_VOLUME = 0.8
        manager = AudioManager()
        
        manager.play_sfx("01-lever")
        mock_sound_instance.set_volume.assert_called_with(0.8)
        mock_sound_instance.play.assert_called_once()
