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

def test_dialogue_manager_advance_and_update():
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))
    
    with patch('src.engine.asset_manager.AssetManager.get_font', return_value=mock_font), \
         patch('pygame.image.load', return_value=pygame.Surface((100, 100))), \
         patch('os.path.exists', return_value=True):
        dm = DialogueManager()
        dm.font_message = mock_font
        dm.dialogue_box = pygame.Surface((400, 200)) # Restore valid dimensions
        
        # Long text that generates multiple pages
        dm.start_dialogue("Long text to span multiple pages. " * 50)
        
        # We can check how many pages were generated
        assert len(dm._pages) >= 2
        assert dm._is_page_complete is False
        assert dm.displayed_text == ""
        
        dm.update(0.1) # 100ms
        assert len(dm.displayed_text) > 0
        assert not dm._is_page_complete
        
        # Test skip to end of page
        dm.advance()
        assert dm._is_page_complete is True
        
        # Test next page
        dm.advance()
        assert dm._current_page_index == 1
        assert dm._is_page_complete is False
        
        # Advance through all remaining pages
        max_attempts = len(dm._pages) * 2
        attempts = 0
        while dm.is_active and attempts < max_attempts:
            dm.advance()
            attempts += 1
            
        assert dm.is_active is False
        assert dm.message == ""

def test_dialogue_manager_draw():
    mock_font = MagicMock()
    mock_font.get_linesize.return_value = 20
    mock_font.size.side_effect = lambda text: (len(text) * 10, 20)
    mock_font.render.return_value = pygame.Surface((100, 20))
    
    with patch('src.engine.asset_manager.AssetManager.get_font', return_value=mock_font), \
         patch('pygame.image.load', return_value=pygame.Surface((100, 100))), \
         patch('os.path.exists', return_value=True):
        dm = DialogueManager()
        dm.font_message = mock_font
        dm.font_title = mock_font
        dm.dialogue_box = pygame.Surface((400, 200))
        dm.next_arrow = pygame.Surface((10, 10))
        
        dm.start_dialogue("Test drawing logic.", title="NPC")
        
        # Test drawing before page complete (dynamic text)
        dm.update(0.1)
        screen = MagicMock()
        dm.draw(screen)
        assert screen.blit.call_count > 0
        
        # Test drawing after page complete (pre-rendered page)
        screen.reset_mock()
        dm.advance()
        dm.draw(screen)
        assert screen.blit.call_count > 0

