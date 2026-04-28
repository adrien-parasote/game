import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.ui.dialogue import DialogueManager
from src.config import Settings

@pytest.fixture
def mock_pygame_font():
    pygame.font.init()
    yield
    pygame.font.quit()

def test_dialogue_manager_paging(mock_pygame_font):
    dm = DialogueManager()
    # Mock font rendering to avoid Surface errors
    dm.font_message = MagicMock()
    dm.font_message.size.return_value = (10, 10)
    dm.font_message.get_linesize.return_value = 20
    dm.font_title = MagicMock()
    dm.dialogue_box = pygame.Surface((800, 200))
    
    long_text = "This is a very long text. " * 20
    dm.start_dialogue(long_text, "Test Title")
    
    assert dm.is_active
    assert len(dm._pages) > 0
    
    # Advance through pages
    initial_page = dm._current_page_index
    dm.advance() # Skip typewriter
    assert dm._is_page_complete
    
    dm.advance() # Next page (if any)
    # If there was only one page, it would close
    if dm.is_active:
        assert dm._current_page_index > initial_page

def test_dialogue_manager_update(mock_pygame_font):
    dm = DialogueManager()
    dm.font_message = MagicMock()
    dm.start_dialogue("Some text", "Title")
    
    dm.update(0.1)
    assert dm._page_char_index > 0
