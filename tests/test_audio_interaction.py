import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.audio import AudioManager
from src.engine.interaction import InteractionManager
from src.config import Settings

def test_audio_manager_sfx():
    with patch('pygame.mixer.Sound'):
        am = AudioManager()
        am.play_sfx("test_sfx")
        # Should not crash even if file missing
        am.play_sfx("missing_sfx")

def test_audio_manager_bgm():
    with patch('pygame.mixer.music.load'):
        with patch('pygame.mixer.music.play'):
            with patch('os.path.exists', return_value=True):
                am = AudioManager()
                am.play_bgm("test_bgm")
                assert am.current_bgm == "test_bgm"

def test_interaction_manager_failed_interaction():
    game = MagicMock()
    game.player.rect.center = (100, 100)
    game.player.current_facing = 'down'
    game.player.is_moving = False
    game.npcs = pygame.sprite.Group()
    game.interactives = pygame.sprite.Group()
    game.pickups = pygame.sprite.Group()
    game.emote_group = MagicMock()
    
    with patch('pygame.key.get_pressed', return_value={pygame.K_SPACE: True, Settings.INTERACT_KEY: True}):
        with patch('src.config.Settings.ENABLE_FAILED_INTERACTION_EMOTE', True):
            im = InteractionManager(game)
            im.handle_interactions() # Nothing to interact with
            game.player.playerEmote.assert_called_with('question')
