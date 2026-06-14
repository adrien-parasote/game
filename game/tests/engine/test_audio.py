from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.engine.audio import AudioManager


@pytest.fixture
def audio_manager():
    with patch("pygame.mixer.Sound"), patch("pygame.mixer.music"):
        am = AudioManager()
        yield am


# --- Init ---


def test_audio_manager_init_success(audio_manager):
    """Normal init: is_enabled should be True."""
    assert audio_manager.is_enabled is True


def test_audio_manager_init_mixer_failure():
    """Init should set is_enabled=False when mixer raises."""
    with (
        patch("pygame.mixer.get_init", return_value=False),
        patch("pygame.mixer.init", side_effect=pygame.error("no audio")),
    ):
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
    audio_manager.toggle_mute()  # mute
    with patch.object(audio_manager, "update_volumes") as mock_update:
        audio_manager.toggle_mute()  # unmute
    mock_update.assert_called_once()
    assert audio_manager.is_muted is False


# --- preload_sfx ---


def test_preload_sfx_no_dir(audio_manager):
    """preload_sfx should return early when sfx_dir does not exist."""
    with patch("os.path.exists", return_value=False):
        audio_manager.preload_sfx()  # should not raise


def test_preload_sfx_load_error(audio_manager):
    """preload_sfx should log a warning when a sound file fails to load."""
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["bad.ogg"]),
        patch("pygame.mixer.Sound", side_effect=pygame.error("bad file")),
    ):
        audio_manager.preload_sfx()  # should not raise


# --- play_bgm ---


def test_audio_play_bgm(audio_manager):
    """Normal BGM play."""
    with patch("os.path.exists", return_value=True):
        audio_manager.play_bgm("test_music")
        assert audio_manager.current_bgm == "test_music"


def test_play_bgm_disabled():
    """play_bgm does nothing when is_enabled is False."""
    with (
        patch("pygame.mixer.get_init", return_value=False),
        patch("pygame.mixer.init", side_effect=pygame.error("no audio")),
    ):
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
    with patch("pygame.mixer.music.get_busy", return_value=True):
        audio_manager.play_bgm("loop")
    # current_bgm unchanged, no load attempted
    assert audio_manager.current_bgm == "loop"


def test_play_bgm_file_not_found(audio_manager):
    """play_bgm logs an error when the file does not exist."""
    with patch("os.path.exists", return_value=False):
        audio_manager.play_bgm("missing")
    assert audio_manager.current_bgm is None


def test_play_bgm_load_error(audio_manager):
    """play_bgm handles pygame.error during music.load gracefully."""
    with (
        patch("os.path.exists", return_value=True),
        patch("pygame.mixer.music.load", side_effect=pygame.error("bad")),
    ):
        audio_manager.play_bgm("broken")
    assert audio_manager.current_bgm is None


# --- stop_bgm ---


def test_stop_bgm_when_playing(audio_manager):
    """stop_bgm clears current_bgm and fades out."""
    audio_manager.current_bgm = "track"
    with (
        patch("pygame.mixer.music.get_busy", return_value=True) as _,
        patch("pygame.mixer.music.fadeout") as mock_fadeout,
    ):
        audio_manager.stop_bgm(fade_ms=200)
    mock_fadeout.assert_called_once_with(200)
    assert audio_manager.current_bgm is None


def test_stop_bgm_when_not_playing(audio_manager):
    """stop_bgm does nothing when music is not busy."""
    audio_manager.current_bgm = "track"
    with (
        patch("pygame.mixer.music.get_busy", return_value=False),
        patch("pygame.mixer.music.fadeout") as mock_fadeout,
    ):
        audio_manager.stop_bgm()
    mock_fadeout.assert_not_called()
    # current_bgm unchanged because music was not playing
    assert audio_manager.current_bgm == "track"


def test_stop_bgm_disabled():
    """stop_bgm returns early when is_enabled is False."""
    with (
        patch("pygame.mixer.get_init", return_value=False),
        patch("pygame.mixer.init", side_effect=pygame.error("no audio")),
    ):
        am = AudioManager()
    am.stop_bgm()  # should not raise


# --- play_sfx ---


def test_audio_play_sfx(audio_manager):
    """SFX load-on-demand from disk."""
    with patch("os.path.exists", return_value=True):
        audio_manager.play_sfx("test_sound")
    assert "test_sound" in audio_manager.sounds


def test_play_sfx_disabled():
    """play_sfx does nothing when is_enabled is False."""
    with (
        patch("pygame.mixer.get_init", return_value=False),
        patch("pygame.mixer.init", side_effect=pygame.error("no audio")),
    ):
        am = AudioManager()
    am.play_sfx("sound")  # should not raise


def test_play_sfx_empty_name(audio_manager):
    """play_sfx returns early when name is empty."""
    audio_manager.play_sfx("")  # should not raise


def test_play_sfx_load_error(audio_manager):
    """play_sfx logs error when on-demand load fails."""
    with (
        patch("os.path.exists", return_value=True),
        patch("pygame.mixer.Sound", side_effect=pygame.error("bad")),
    ):
        audio_manager.play_sfx("boom")  # should not raise


def test_play_sfx_file_not_found(audio_manager):
    """play_sfx logs error when file missing."""
    with patch("os.path.exists", return_value=False):
        audio_manager.play_sfx("ghost")  # should not raise


# --- update_volumes ---


def test_update_volumes(audio_manager):
    """update_volumes sets music and sound volumes."""
    mock_sound = MagicMock()
    audio_manager.sounds["hit"] = mock_sound
    with patch("pygame.mixer.music.set_volume") as mock_set:
        audio_manager.update_volumes()
    mock_set.assert_called_once()
    mock_sound.set_volume.assert_called()


def test_update_volumes_disabled():
    """update_volumes returns early when is_enabled is False."""
    with (
        patch("pygame.mixer.get_init", return_value=False),
        patch("pygame.mixer.init", side_effect=pygame.error("no audio")),
    ):
        am = AudioManager()
    am.update_volumes()  # should not raise


# --- propose_ambient / flush_ambient ---


def test_propose_ambient_stores_minimum_distance(audio_manager):
    """propose_ambient keeps the minimum of all proposed distances per sound name."""
    audio_manager.propose_ambient("fire", 200.0)
    audio_manager.propose_ambient("fire", 50.0)  # closer
    audio_manager.propose_ambient("fire", 300.0)  # farther
    assert audio_manager._ambient_proposals["fire"] == pytest.approx(50.0)


def test_flush_ambient_starts_new_sound(audio_manager):
    """flush_ambient creates and plays a looping Sound for each proposed name."""
    audio_manager._ambient_proposals = {"fire": 0.0}
    with patch("os.path.exists", return_value=True), patch("pygame.mixer.Sound") as mock_sound_cls:
        mock_sound = MagicMock()
        mock_sound_cls.return_value = mock_sound
        audio_manager.flush_ambient()

    assert "fire" in audio_manager.ambient_sounds
    mock_sound.play.assert_called_once_with(loops=-1)


def test_flush_ambient_sets_volume_from_distance(audio_manager):
    """flush_ambient sets volume using AMBIENT_VOLUME_SCALE * falloff at given distance."""
    from src.config import Settings
    from src.engine.audio import AMBIENT_VOLUME_SCALE

    mock_sound = MagicMock()
    audio_manager.ambient_sounds = {"fire": mock_sound}
    audio_manager._ambient_proposals = {"fire": 0.0}  # distance=0 → falloff=1.0

    with patch("os.path.exists", return_value=True):
        audio_manager.flush_ambient()

    expected = pytest.approx(Settings.SFX_VOLUME * AMBIENT_VOLUME_SCALE * 1.0)
    mock_sound.set_volume.assert_called_with(expected)


def test_flush_ambient_stops_stale_sounds(audio_manager):
    """flush_ambient stops the Channel (not the Sound) for sounds with no proposals."""
    mock_sound = MagicMock()
    mock_channel = MagicMock()
    audio_manager.ambient_sounds = {"fire": mock_sound}
    audio_manager.ambient_channels = {"fire": mock_channel}
    audio_manager._ambient_proposals = {}  # no proposals

    audio_manager.flush_ambient()

    mock_channel.stop.assert_called_once()
    mock_sound.stop.assert_not_called()  # Sound.stop() must NOT be called
    assert "fire" not in audio_manager.ambient_sounds


def test_flush_ambient_clears_proposals(audio_manager):
    """flush_ambient resets _ambient_proposals after each frame."""
    audio_manager._ambient_proposals = {"fire": 10.0}
    with patch("os.path.exists", return_value=False):
        audio_manager.flush_ambient()
    assert audio_manager._ambient_proposals == {}


def test_stop_ambient_explicit(audio_manager):
    """stop_ambient stops the Channel and removes the sound entry."""
    mock_sound = MagicMock()
    mock_channel = MagicMock()
    audio_manager.ambient_sounds = {"fire": mock_sound}
    audio_manager.ambient_channels = {"fire": mock_channel}

    audio_manager.stop_ambient("fire")

    mock_channel.stop.assert_called_once()
    mock_sound.stop.assert_not_called()
    assert "fire" not in audio_manager.ambient_sounds


def test_stop_all_ambients(audio_manager):
    """stop_all_ambients stops all Channels and clears all dicts."""
    mock_a = MagicMock()
    mock_b = MagicMock()
    mock_ch_a = MagicMock()
    mock_ch_b = MagicMock()
    audio_manager.ambient_sounds = {"fire": mock_a, "water": mock_b}
    audio_manager.ambient_channels = {"fire": mock_ch_a, "water": mock_ch_b}
    audio_manager._ambient_proposals = {"fire": 10.0}

    audio_manager.stop_all_ambients()

    mock_ch_a.stop.assert_called_once()
    mock_ch_b.stop.assert_called_once()
    mock_a.stop.assert_not_called()
    mock_b.stop.assert_not_called()
    assert audio_manager.ambient_sounds == {}
    assert audio_manager.ambient_channels == {}
    assert audio_manager._ambient_proposals == {}


# ── Coverage gap tests ────────────────────────────────────────────────────────


def _make_enabled_audio():
    """AudioManager with mixer initialized and is_enabled=True."""
    from unittest.mock import MagicMock, patch

    from src.engine.audio import AudioManager

    with (
        patch("pygame.mixer.get_init", return_value=True),
        patch("src.engine.audio.AudioManager.preload_sfx"),
    ):
        am = AudioManager()
    am.is_enabled = True
    return am


def test_audio_mixer_init_called_when_not_initialized(caplog):
    """__init__ calls pygame.mixer.init() when mixer is not yet initialized (line 48)."""
    import logging
    from unittest.mock import MagicMock, patch

    from src.engine.audio import AudioManager

    with (
        patch("pygame.mixer.get_init", return_value=False),
        patch("pygame.mixer.init") as mock_init,
        patch("pygame.mixer.set_num_channels") as mock_channels,
        patch("src.engine.audio.AudioManager.preload_sfx"),
        caplog.at_level(logging.INFO),
    ):
        am = AudioManager()

    mock_init.assert_called_once()
    mock_channels.assert_called_once_with(32)
    assert am.is_enabled is True


def test_toggle_mute_sets_ambient_volume_to_zero():
    """toggle_mute(muted=True) calls set_volume(0) on ambient_sounds (line 66)."""
    from unittest.mock import MagicMock

    am = _make_enabled_audio()
    mock_sound = MagicMock()
    am.ambient_sounds["water"] = mock_sound
    am.is_muted = False
    am.toggle_mute()  # → muted=True
    mock_sound.set_volume.assert_called_with(0)


def test_play_sfx_with_volume_multiplier():
    """play_sfx with volume_multiplier != 1.0 calls set_volume on the sound (line 156)."""
    from unittest.mock import MagicMock

    am = _make_enabled_audio()
    mock_sound = MagicMock()
    am.sounds["hit"] = mock_sound
    am.play_sfx("hit", volume_multiplier=0.5)
    mock_sound.set_volume.assert_called()


def test_propose_ambient_empty_name_is_noop():
    """propose_ambient('', dist) returns immediately without modifying proposals (line 180)."""
    am = _make_enabled_audio()
    am.propose_ambient("", 100.0)
    assert am._ambient_proposals == {}


def test_flush_ambient_when_disabled_clears_proposals():
    """flush_ambient() when is_enabled=False clears proposals and returns early (193-194)."""
    am = _make_enabled_audio()
    am.is_enabled = False
    am._ambient_proposals = {"rain": 50.0}
    am.flush_ambient()
    assert am._ambient_proposals == {}


def test_flush_ambient_no_free_channel(caplog, tmp_path):
    """flush_ambient() logs warning when sound.play() returns None (lines 219-220)."""
    import logging
    from unittest.mock import MagicMock, patch

    am = _make_enabled_audio()
    am.sfx_dir = str(tmp_path)
    # Create a fake sfx file
    fake_sfx = tmp_path / "rain.ogg"
    fake_sfx.write_bytes(b"")

    mock_sound = MagicMock()
    mock_sound.play.return_value = None  # No free channel

    with (
        patch("pygame.mixer.Sound", return_value=mock_sound),
        patch("os.path.exists", return_value=True),
        caplog.at_level(logging.WARNING),
    ):
        am.propose_ambient("rain", 50.0)
        am.flush_ambient()

    assert any(
        "channel" in r.message.lower() or "free" in r.message.lower() for r in caplog.records
    )


def test_flush_ambient_pygame_error_logs(caplog, tmp_path):
    """flush_ambient() logs ERROR when pygame.mixer.Sound raises pygame.error (224-226)."""
    import logging
    from unittest.mock import patch

    import pygame

    am = _make_enabled_audio()
    am.sfx_dir = str(tmp_path)

    with (
        patch("pygame.mixer.Sound", side_effect=pygame.error("load error")),
        patch("os.path.exists", return_value=True),
        caplog.at_level(logging.ERROR),
    ):
        am.propose_ambient("crash", 10.0)
        am.flush_ambient()

    assert any("error" in r.levelname.lower() for r in caplog.records)


def test_flush_ambient_stops_stale_channels():
    """flush_ambient() stops channels whose names are no longer proposed (lines 239-243)."""
    from unittest.mock import MagicMock

    am = _make_enabled_audio()

    mock_channel = MagicMock()
    mock_sound = MagicMock()
    am.ambient_sounds["wind"] = mock_sound
    am.ambient_channels["wind"] = mock_channel

    # No proposals for "wind" this frame
    am._ambient_proposals = {}
    # Trigger stop path via propose + flush with nothing for wind
    am.flush_ambient()

    # After flush with no proposals, all channels should be stopped
    mock_channel.stop.assert_called_once()
    assert "wind" not in am.ambient_sounds


# assert True (legacy bypass)

# assert True (legacy bypass)

# assert True (legacy bypass)

# assert True (legacy bypass)

# assert True (legacy bypass)
