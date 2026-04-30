import pytest
import pygame
from unittest.mock import patch, MagicMock, call
from src.engine.audio import AudioManager


@pytest.fixture
def audio_manager():
    with patch('pygame.mixer.Sound'), patch('pygame.mixer.music'):
        am = AudioManager()
        yield am


# --- Init ---

def test_audio_manager_init_success(audio_manager):
    """Normal init: is_enabled should be True."""
    assert audio_manager.is_enabled is True


def test_audio_manager_init_mixer_failure():
    """Init should set is_enabled=False when mixer raises."""
    with patch('pygame.mixer.get_init', return_value=False), \
         patch('pygame.mixer.init', side_effect=pygame.error("no audio")):
        am = AudioManager()
    assert am.is_enabled is False


# --- toggle_mute ---

def test_audio_mute_toggle(audio_manager):
    """First toggle mutes."""
    assert audio_manager.is_muted is False
    audio_manager.toggle_mute()
    assert audio_manager.is_muted is True


def test_audio_unmute_restores_volumes(audio_manager):
    """Second toggle unmutes and calls update_volumes."""
    audio_manager.toggle_mute()   # mute
    with patch.object(audio_manager, 'update_volumes') as mock_update:
        audio_manager.toggle_mute()  # unmute
    mock_update.assert_called_once()
    assert audio_manager.is_muted is False


# --- preload_sfx ---

def test_preload_sfx_no_dir(audio_manager):
    """preload_sfx should return early when sfx_dir does not exist."""
    with patch('os.path.exists', return_value=False):
        audio_manager.preload_sfx()  # should not raise


def test_preload_sfx_load_error(audio_manager):
    """preload_sfx should log a warning when a sound file fails to load."""
    with patch('os.path.exists', return_value=True), \
         patch('os.listdir', return_value=['bad.ogg']), \
         patch('pygame.mixer.Sound', side_effect=pygame.error('bad file')):
        audio_manager.preload_sfx()  # should not raise


# --- play_bgm ---

def test_audio_play_bgm(audio_manager):
    """Normal BGM play."""
    with patch('os.path.exists', return_value=True):
        audio_manager.play_bgm("test_music")
        assert audio_manager.current_bgm == "test_music"


def test_play_bgm_disabled():
    """play_bgm does nothing when is_enabled is False."""
    with patch('pygame.mixer.get_init', return_value=False), \
         patch('pygame.mixer.init', side_effect=pygame.error("no audio")):
        am = AudioManager()
    am.play_bgm("music")  # should not raise
    assert am.current_bgm is None


def test_play_bgm_empty_name(audio_manager):
    """play_bgm returns early when name is empty."""
    audio_manager.play_bgm("")
    assert audio_manager.current_bgm is None


def test_play_bgm_same_track_already_playing(audio_manager):
    """play_bgm does nothing when the same track is already playing."""
    audio_manager.current_bgm = "loop"
    with patch('pygame.mixer.music.get_busy', return_value=True):
        audio_manager.play_bgm("loop")
    # current_bgm unchanged, no load attempted
    assert audio_manager.current_bgm == "loop"


def test_play_bgm_file_not_found(audio_manager):
    """play_bgm logs an error when the file does not exist."""
    with patch('os.path.exists', return_value=False):
        audio_manager.play_bgm("missing")
    assert audio_manager.current_bgm is None


def test_play_bgm_load_error(audio_manager):
    """play_bgm handles pygame.error during music.load gracefully."""
    with patch('os.path.exists', return_value=True), \
         patch('pygame.mixer.music.load', side_effect=pygame.error("bad")):
        audio_manager.play_bgm("broken")
    assert audio_manager.current_bgm is None


# --- stop_bgm ---

def test_stop_bgm_when_playing(audio_manager):
    """stop_bgm clears current_bgm and fades out."""
    audio_manager.current_bgm = "track"
    with patch('pygame.mixer.music.get_busy', return_value=True) as _, \
         patch('pygame.mixer.music.fadeout') as mock_fadeout:
        audio_manager.stop_bgm(fade_ms=200)
    mock_fadeout.assert_called_once_with(200)
    assert audio_manager.current_bgm is None


def test_stop_bgm_when_not_playing(audio_manager):
    """stop_bgm does nothing when music is not busy."""
    audio_manager.current_bgm = "track"
    with patch('pygame.mixer.music.get_busy', return_value=False), \
         patch('pygame.mixer.music.fadeout') as mock_fadeout:
        audio_manager.stop_bgm()
    mock_fadeout.assert_not_called()
    # current_bgm unchanged because music was not playing
    assert audio_manager.current_bgm == "track"


def test_stop_bgm_disabled():
    """stop_bgm returns early when is_enabled is False."""
    with patch('pygame.mixer.get_init', return_value=False), \
         patch('pygame.mixer.init', side_effect=pygame.error("no audio")):
        am = AudioManager()
    am.stop_bgm()  # should not raise


# --- play_sfx ---

def test_audio_play_sfx(audio_manager):
    """SFX load-on-demand from disk."""
    with patch('os.path.exists', return_value=True):
        audio_manager.play_sfx("test_sound")
    assert "test_sound" in audio_manager.sounds


def test_play_sfx_disabled():
    """play_sfx does nothing when is_enabled is False."""
    with patch('pygame.mixer.get_init', return_value=False), \
         patch('pygame.mixer.init', side_effect=pygame.error("no audio")):
        am = AudioManager()
    am.play_sfx("sound")  # should not raise


def test_play_sfx_empty_name(audio_manager):
    """play_sfx returns early when name is empty."""
    audio_manager.play_sfx("")  # should not raise


def test_play_sfx_load_error(audio_manager):
    """play_sfx logs error when on-demand load fails."""
    with patch('os.path.exists', return_value=True), \
         patch('pygame.mixer.Sound', side_effect=pygame.error("bad")):
        audio_manager.play_sfx("boom")  # should not raise


def test_play_sfx_file_not_found(audio_manager):
    """play_sfx logs error when file missing."""
    with patch('os.path.exists', return_value=False):
        audio_manager.play_sfx("ghost")  # should not raise


# --- update_volumes ---

def test_update_volumes(audio_manager):
    """update_volumes sets music and sound volumes."""
    mock_sound = MagicMock()
    audio_manager.sounds['hit'] = mock_sound
    with patch('pygame.mixer.music.set_volume') as mock_set:
        audio_manager.update_volumes()
    mock_set.assert_called_once()
    mock_sound.set_volume.assert_called()


def test_update_volumes_disabled():
    """update_volumes returns early when is_enabled is False."""
    with patch('pygame.mixer.get_init', return_value=False), \
         patch('pygame.mixer.init', side_effect=pygame.error("no audio")):
        am = AudioManager()
    am.update_volumes()  # should not raise
