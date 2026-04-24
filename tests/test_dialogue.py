import pytest
import pygame
from src.ui.dialogue import DialogueManager
from src.config import Settings

@pytest.fixture
def dialogue_env():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    # Ensure settings are loaded
    Settings.load()
    yield
    pygame.quit()

def test_dialogue_initializes(dialogue_env):
    """DialogueManager should start in inactive state."""
    dm = DialogueManager()
    assert dm.is_active is False
    assert dm.message == ""

def test_dialogue_start(dialogue_env):
    """Starting a dialogue should activate the manager and set text."""
    dm = DialogueManager()
    dm.start_dialogue("Test Message")
    assert dm.is_active is True
    assert dm.message == "Test Message"
    assert dm.displayed_text == ""
    assert dm._page_char_index == 0.0

def test_dialogue_typewriter(dialogue_env):
    """Typewriter effect should advance text based on dt and speed."""
    dm = DialogueManager()
    # Force speed for deterministic test: 20 chars/sec
    dm.typewriter_speed = 20.0
    dm.start_dialogue("Hello World")
    
    # 0.1s * 20 chars/sec = 2 chars
    dm.update(0.1)
    assert dm.displayed_text == "He"
    
    # Another 0.2s = 4 more chars (6 total)
    dm.update(0.2)
    assert dm.displayed_text == "Hello "
    
    # Finish it
    dm.update(1.0)
    assert dm.displayed_text == "Hello World"
    assert dm._page_char_index >= len(dm.displayed_text)

def test_dialogue_advance_skip(dialogue_env):
    """Advance should skip typing if in progress."""
    dm = DialogueManager()
    dm.typewriter_speed = 1.0 # Very slow
    dm.start_dialogue("Wait for it...")
    dm.update(0.1)
    assert len(dm.displayed_text) < len("Wait for it...")
    
    # First advance: finish current page text
    dm.advance()
    assert dm.displayed_text == "Wait for it..."
    assert dm.is_active is True
    
    # Second advance: close (since it's only one page)
    dm.advance()
    assert dm.is_active is False

def test_dialogue_paging_logic_reset(dialogue_env):
    """Verify that _pages is reset on start."""
    dm = DialogueManager()
    dm.start_dialogue("Initial")
    # Manually inject dummy pages
    dm._pages = [["Line 1"], ["Line 2"]]
    
    dm.start_dialogue("New")
    assert dm.message == "New"
    # New message should have its own pages
    assert dm._pages != [["Line 1"], ["Line 2"]]
