"""Tests for DialogueManager optimization."""
import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.ui.dialogue import DialogueManager

def test_dialogue_manager_pre_renders_pages():
    game = MagicMock()
    game.i18n.current_locale = "en"
    
    # Mock font so sizes can be calculated
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))
    
    with patch('src.engine.asset_manager.AssetManager.get_font', return_value=mock_font), \
         patch('pygame.image.load'), \
         patch('os.path.exists', return_value=True):
        dm = DialogueManager()
        
        # Override the font manually since it loads via asset manager
        dm.font_message = mock_font
        dm.font_title = mock_font
        dm.font_prompt = mock_font
        dm.dialogue_box = pygame.Surface((400, 200)) # mock the box
        
        dm.start_dialogue("This is a test that spans multiple lines because it is very long and needs to wrap.")
        
        # After start_dialogue, _paginate should have pre-rendered the pages
        assert hasattr(dm, "_page_surfaces")
        assert len(dm._page_surfaces) > 0
        
        # Each item in _page_surfaces should be a pygame Surface
        for surf in dm._page_surfaces:
            assert isinstance(surf, pygame.Surface)
