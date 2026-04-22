import pytest
import pygame
from src.ui.dialogue import DialogueManager

@pytest.fixture
def dialogue_env():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    yield
    pygame.quit()

def test_dialogue_initializes(dialogue_env):
    """DialogueManager should start in IDLE state."""
    dm = DialogueManager()
    assert dm.is_active is False
    assert dm.state == "IDLE"

def test_dialogue_start(dialogue_env):
    """Starting a dialogue should move state to SCROLLING."""
    dm = DialogueManager()
    dm.start_dialogue("Test Message")
    assert dm.is_active is True
    assert dm.state == "SCROLLING"
    assert dm._full_text == "Test Message"
    assert dm._current_text == ""

def test_dialogue_typewriter(dialogue_env):
    """Typewriter effect should advance text based on dt."""
    dm = DialogueManager()
    dm._type_speed = 0.05
    dm.start_dialogue("Hello")
    
    # 0.1s / 0.05s = 2 chars
    dm.update(0.1)
    assert dm._current_text == "He"
    
    # Another 0.2s should finish "Hello" (5 chars total)
    dm.update(0.2)
    assert dm._current_text == "Hello"
    assert dm.state == "WAITING"

def test_dialogue_close(dialogue_env):
    """Closing dialogue should return to IDLE state."""
    dm = DialogueManager()
    dm.start_dialogue("Short")
    dm.update(1.0) # Finish scrolling
    assert dm.state == "WAITING"
    
    dm.close_dialogue()
    assert dm.is_active is False
    assert dm.state == "IDLE"

def test_dialogue_skip_scrolling(dialogue_env):
    """Calling start while already scrolling should finish the text instantly (optional design choice). 
    Actually, let's implement 'advance' logic where it finishes if scrolling, closes if waiting."""
    dm = DialogueManager()
    dm.start_dialogue("Very long message that takes time")
    dm.update(0.1)
    assert dm.state == "SCROLLING"
    
    # Advance should finish text
    dm.advance()
    assert dm._current_text == "Very long message that takes time"
    assert dm.state == "WAITING"
    
    # Advance again should close
    dm.advance()
    assert dm.is_active is False
    assert dm.state == "IDLE"
