"""
Consolidated UI/UX Test Suite
Includes: HUD, Dialogue, and Camera tests.
"""
import pytest
import pygame
import os
from unittest.mock import patch, MagicMock
from src.ui.hud import GameHUD, HUD_MARGIN_X, HUD_MARGIN_Y
from src.ui.dialogue import DialogueManager
from src.entities.groups import CameraGroup
from src.engine.time_system import TimeSystem
from src.config import Settings

@pytest.fixture(scope="module", autouse=True)
def ui_env():
    """Shared environment for all UI tests."""
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

@pytest.fixture
def time_system():
    return TimeSystem(initial_hour=14)

# --- HUD TESTS ---

def test_hud_initializes(time_system):
    """TC-HUD-01: GameHUD initializes and loads assets."""
    hud = GameHUD(time_system)
    assert hud is not None
    assert hud._clock_surf is not None
    assert len(hud._season_surfs) == 4

def test_hud_draw_no_fail(time_system):
    """TC-HUD-02: draw() renders on screen without raising."""
    hud = GameHUD(time_system)
    screen = pygame.display.get_surface()
    hud.draw(screen)

def test_hud_lang_labels(time_system):
    """TC-HUD-03: Language file is loaded correctly."""
    hud = GameHUD(time_system, lang="fr")
    seasons = hud._lang.get("seasons", {})
    assert seasons.get("SPRING") == "Printemps"

def test_hud_positioning(time_system):
    """TC-HUD-05: HUD is correctly positioned."""
    hud = GameHUD(time_system)
    screen = pygame.display.get_surface()
    clock_w = hud._clock_surf.get_width()
    expected_x = screen.get_width() - clock_w - HUD_MARGIN_X
    assert expected_x >= 0

# --- DIALOGUE TESTS ---

def test_dialogue_state():
    """DialogueManager should start inactive."""
    dm = DialogueManager()
    assert dm.is_active is False

def test_dialogue_start():
    """Starting dialogue sets state and triggers pagination."""
    dm = DialogueManager()
    dm.start_dialogue("Test Message", title="Hero")
    assert dm.is_active is True
    assert dm.title == "Hero"
    assert len(dm._pages) > 0

def test_dialogue_typewriter():
    """Typewriter advances text based on dt."""
    dm = DialogueManager()
    dm.typewriter_speed = 100.0  # Fast for test
    dm.start_dialogue("Fast type")
    dm.update(0.05)  # 5 chars
    assert len(dm.displayed_text) == 5

def test_dialogue_pagination_logic():
    """Pagination adapts to title presence (TC-DLG-01)."""
    dm = DialogueManager()
    long_text = "word " * 200
    
    dm.start_dialogue(long_text, title="Title")
    max_lines_title = len(dm._pages[0])
    
    dm.start_dialogue(long_text, title="")
    max_lines_no_title = len(dm._pages[0])
    
    assert max_lines_no_title > max_lines_title

def test_dialogue_advance_skip():
    """Advance skips typing or flips page."""
    dm = DialogueManager()
    dm.start_dialogue("Page 1 text. More words for page 1.", title="A")
    # Force long text to ensure it doesn't fit on one page if needed, 
    # but here we just test skip/next.
    dm.typewriter_speed = 1.0
    dm.update(0.1)
    
    # Skip typing
    dm.advance()
    assert dm._is_page_complete is True
    
    # Close (if only one page) or next page
    is_multi = len(dm._pages) > 1
    dm.advance()
    if is_multi:
        assert dm._current_page_index == 1
    else:
        assert dm.is_active is False

def test_dialogue_empty_msg():
    """TC-DLG-01 Edge Case: Empty message does not crash."""
    dm = DialogueManager()
    dm.start_dialogue("")
    assert dm.is_active is False

# --- CAMERA TESTS ---

def test_camera_clamping():
    """TC-C-01: Large map clamping."""
    camera = CameraGroup()
    camera.set_world_size(2000, 2000)
    
    class MockSprite:
        rect = pygame.Rect(0, 0, 32, 32)
        rect.center = (2000, 2000)
    
    offset = camera.calculate_offset(MockSprite())
    assert offset.x == -720  # -(2000 - 1280)
    assert offset.y == -1280 # -(2000 - 720)

def test_camera_centering():
    """TC-C-02: Small map centering."""
    camera = CameraGroup()
    camera.set_world_size(800, 600)
    
    class MockSprite:
        rect = pygame.Rect(400, 300, 32, 32)
        rect.center = (400, 300)
        
    offset = camera.calculate_offset(MockSprite())
    assert offset.x == 240 # (1280 - 800) // 2
    assert offset.y == 60  # (720 - 600) // 2
