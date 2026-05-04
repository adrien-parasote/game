import pytest
import pygame
from unittest.mock import Mock, patch
from src.ui.save_menu import SaveMenuOverlay, SaveSlotUI
from src.engine.save_manager import SlotInfo

@pytest.fixture
def mock_screen():
    screen = Mock()
    screen.get_size.return_value = (1280, 720)
    return screen

@pytest.fixture
def mock_save_manager():
    sm = Mock()
    sm.list_slots.return_value = [
        SlotInfo(slot_id=1, saved_at="2025-01-01 12:00", playtime_seconds=3600.0, map_name="Test Map", map_display_name="Mocked Map", player_name="Hero", level=5),
        None,
        None
    ]
    sm.load_thumbnail.return_value = pygame.Surface((82, 82))
    return sm

@pytest.mark.tc("TC-006")
def test_save_slot_ui_draw_empty():
    pygame.font.init()
    mock_am = Mock()
    mock_am.get_font.return_value = pygame.font.SysFont(None, 24)
    slot_ui = SaveSlotUI(mock_am)
    surface = pygame.Surface((800, 120))
    
    # Draw empty slot
    slot_ui.draw(surface, pygame.Rect(0, 0, 800, 120), 1, None, None, False)
    # The draw logic completes without crashing

@pytest.mark.tc("TC-007")
def test_save_slot_ui_draw_filled():
    pygame.font.init()
    mock_am = Mock()
    mock_am.get_font.return_value = pygame.font.SysFont(None, 24)
    slot_ui = SaveSlotUI(mock_am)
    surface = pygame.Surface((800, 120))
    info = SlotInfo(slot_id=1, saved_at="2025-01-01 12:00", playtime_seconds=3600.0, map_name="Test Map", map_display_name="Mocked Map", player_name="Hero", level=5)
    thumb = pygame.Surface((50, 50))  # Test thumbnail scaling logic
    
    # Draw filled slot
    slot_ui.draw(surface, pygame.Rect(0, 0, 800, 120), 1, info, thumb, True)
    # The draw logic completes without crashing

@pytest.mark.tc("TC-008")
def test_save_menu_overlay_init(mock_screen, mock_save_manager):
    pygame.font.init()
    with patch("src.ui.save_menu.SaveSlotUI") as mock_slot_ui:
        mock_slot_ui.return_value.get_size.return_value = (800, 120)
        menu = SaveMenuOverlay(mock_screen, mock_save_manager, "Test Title")
        menu.refresh()
        assert len(menu._slots_info) == 3
        assert menu._slots_info[0].map_name == "Test Map"

@pytest.mark.tc("TC-009")
def test_save_menu_overlay_get_clicked_slot(mock_screen, mock_save_manager):
    pygame.font.init()
    with patch("src.ui.save_menu.SaveSlotUI") as mock_slot_ui:
        mock_slot_ui.return_value.get_size.return_value = (800, 120)
        menu = SaveMenuOverlay(mock_screen, mock_save_manager, "Test Title")
        menu.refresh()
        
        # Mock an event outside slots
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
        assert menu.get_clicked_slot(event) is None
        
        # Mock an event inside slot 0
        menu.slot_rects = [pygame.Rect(0, 0, 800, 120)]
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 60))
        assert menu.get_clicked_slot(event) == 0

@pytest.mark.tc("TC-010")
def test_save_menu_overlay_update_and_draw(mock_screen, mock_save_manager):
    pygame.font.init()
    with patch("src.ui.save_menu.SaveSlotUI") as mock_slot_ui:
        mock_slot_ui.return_value.get_size.return_value = (800, 120)
        menu = SaveMenuOverlay(mock_screen, mock_save_manager, "Test Title")
        menu.refresh()
        menu.slot_rects = [pygame.Rect(0, 0, 800, 120)] * 3
        
        with patch("pygame.mouse.get_pos", return_value=(400, 60)):
            menu.update(0.016)
            assert menu._hovered_slot == 0
            
        menu.draw()
        mock_screen.blit.assert_called()

@pytest.mark.tc("TC-011")
def test_save_menu_overlay_back_clicked(mock_screen, mock_save_manager):
    pygame.font.init()
    with patch("src.ui.save_menu.SaveSlotUI") as mock_slot_ui:
        mock_slot_ui.return_value.get_size.return_value = (800, 120)
        menu = SaveMenuOverlay(mock_screen, mock_save_manager, "Test Title")
        menu.back_btn_rect = pygame.Rect(10, 10, 100, 50)
        
        # Click outside
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
        assert not menu.is_back_clicked(event)
        
        # Click inside
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 30))
        assert menu.is_back_clicked(event)
        
        # Other button click
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(50, 30))
        assert not menu.is_back_clicked(event)
