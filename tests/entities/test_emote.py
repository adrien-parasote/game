"""Behavioural tests for EmoteManager (emote.py)."""

import logging
from unittest.mock import MagicMock, patch

import pygame
import pytest


@pytest.fixture(autouse=True)
def pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


def _make_manager_with_frames():
    """Return an EmoteManager with mocked spritesheet frames."""
    from src.entities.emote import EmoteManager

    fake_frames = [pygame.Surface((16, 16)) for _ in range(40)]  # 5 cols × 8 rows
    with patch("src.entities.emote.SpriteSheet") as mock_ss:
        mock_ss.return_value.load_grid.return_value = fake_frames
        player = MagicMock()
        manager = EmoteManager(player)
    return manager, fake_frames


class TestEmoteManagerInit:
    def test_emote_map_contains_known_emotes(self):
        """EmoteManager provides at least the standard emote names."""
        manager, _ = _make_manager_with_frames()
        for name in ("love", "bored", "interact", "question", "frustration"):
            assert name in manager.emote_map

    def test_handles_missing_sheet_gracefully(self, caplog):
        """Missing spritesheet logs error and doesn't crash."""
        from src.entities.emote import EmoteManager
        with patch("src.entities.emote.SpriteSheet", side_effect=FileNotFoundError("missing")):
            player = MagicMock()
            with caplog.at_level(logging.ERROR):
                manager = EmoteManager(player)
        assert manager is not None


class TestEmoteTrigger:
    def test_trigger_no_group_logs_warning(self, caplog):
        """trigger() without emote_group set logs a warning and returns early."""
        manager, _ = _make_manager_with_frames()
        manager.emote_group = None
        with caplog.at_level(logging.WARNING):
            manager.trigger("love")
        assert any("emote_group" in r.message for r in caplog.records)

    def test_trigger_unknown_name_logs_warning(self, caplog):
        """trigger() with unknown emote name logs a warning."""
        manager, _ = _make_manager_with_frames()
        manager.emote_group = MagicMock()
        with caplog.at_level(logging.WARNING):
            manager.trigger("nonexistent_emote")
        assert any("not found" in r.message for r in caplog.records)

    def test_trigger_clears_existing_emotes(self):
        """trigger() empties the emote_group before creating a new sprite."""
        manager, _ = _make_manager_with_frames()
        group = pygame.sprite.Group()
        manager.emote_group = group
        manager.player.rect = pygame.Rect(100, 200, 16, 32)

        manager.trigger("love")
        # Should have emptied and re-added one sprite
        assert len(group.sprites()) == 1

    def test_trigger_plays_sfx(self):
        """trigger() calls audio_manager.play_sfx with the emote SFX."""
        manager, _ = _make_manager_with_frames()
        group = pygame.sprite.Group()
        manager.emote_group = group
        audio = MagicMock()
        manager.player.audio_manager = audio
        manager.player.rect = pygame.Rect(100, 200, 16, 32)

        manager.trigger("love")
        audio.play_sfx.assert_called_once_with("03-emote", source_id="player_emote")
