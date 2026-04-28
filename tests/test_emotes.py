import pygame
from unittest.mock import MagicMock, patch
from src.entities.emote import EmoteManager

def test_emote_manager_initialization():
    player = MagicMock()
    with patch('src.entities.emote.SpriteSheet'):
        em = EmoteManager(player)
        assert "interact" in em.emote_map
        assert em.emote_map["interact"] == 2

def test_emote_manager_trigger():
    player = MagicMock()
    player.audio_manager = MagicMock()
    group = MagicMock()
    with patch('src.entities.emote.SpriteSheet') as mock_sheet:
        mock_sheet.return_value.load_grid.return_value = [pygame.Surface((16, 16))] * 40
        em = EmoteManager(player)
        em.emote_group = group
        
        em.trigger("love")
        assert group.empty.called

def test_emote_sprite():
    from src.entities.emote_sprite import EmoteSprite
    frames = [pygame.Surface((16, 16))] * 8
    target = MagicMock()
    target.rect = pygame.Rect(0, 0, 32, 32)
    group = pygame.sprite.Group()
    
    es = EmoteSprite(frames, target, group)
    assert es in group
    es.update(0.1)
    assert es.elapsed == 0.1
    
    es.update(1.0)
    assert es not in group # Expired
