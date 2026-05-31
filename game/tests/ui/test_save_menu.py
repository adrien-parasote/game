from unittest.mock import MagicMock, Mock, patch

import pygame
import pytest
from src.engine.save_manager import SlotInfo
from src.ui.save_menu import SaveMenuOverlay, SaveSlotUI


@pytest.fixture
def mock_screen():
    screen = Mock()
    screen.get_size.return_value = (1280, 720)
    return screen


@pytest.fixture
def mock_save_manager():
    sm = Mock()
    sm.list_slots.return_value = [
        SlotInfo(
            slot_id=1,
            saved_at="2025-01-01 12:00",
            playtime_seconds=3600.0,
            map_name="Test Map",
            map_display_name="Mocked Map",
            player_name="Hero",
            level=5,
        ),
        None,
        None,
    ]
    sm.load_thumbnail.return_value = pygame.Surface((82, 82))
    return sm


@pytest.mark.tc("SAVE-U-006")
def test_save_slot_ui_draw_empty():
    pygame.font.init()
    mock_am = Mock()
    mock_am.get_font.return_value = pygame.font.SysFont(None, 24)
    # get_image must return a real Surface (not a Mock) to avoid TypeError in smoothscale
    mock_am.get_image.return_value = pygame.Surface((427, 200))
    slot_ui = SaveSlotUI(mock_am)
    surface = pygame.Surface((800, 120))

    # Draw empty slot
    slot_ui.draw(surface, pygame.Rect(0, 0, 800, 120), 1, None, None, False)
    # The draw logic completes without crashing


@pytest.mark.tc("SAVE-U-007")
def test_save_slot_ui_draw_filled():
    pygame.font.init()
    mock_am = Mock()
    mock_am.get_font.return_value = pygame.font.SysFont(None, 24)
    mock_am.get_image.return_value = pygame.Surface((427, 200))
    slot_ui = SaveSlotUI(mock_am)
    surface = pygame.Surface((800, 120))
    info = SlotInfo(
        slot_id=1,
        saved_at="2025-01-01 12:00",
        playtime_seconds=3600.0,
        map_name="Test Map",
        map_display_name="Mocked Map",
        player_name="Hero",
        level=5,
    )
    thumb = pygame.Surface((50, 50))  # Test thumbnail scaling logic

    # Draw filled slot
    slot_ui.draw(surface, pygame.Rect(0, 0, 800, 120), 1, info, thumb, True)
    # The draw logic completes without crashing


@pytest.mark.tc("SAVE-U-008")
def test_save_menu_overlay_init(mock_screen, mock_save_manager):
    pygame.font.init()
    with patch("src.ui.save_menu.SaveSlotUI") as mock_slot_ui:
        mock_slot_ui.return_value.get_size.return_value = (800, 120)
        menu = SaveMenuOverlay(mock_screen, mock_save_manager, "Test Title")
        menu.refresh()
        assert len(menu._slots_info) == 3
        assert menu._slots_info[0] is not None
        assert menu._slots_info[0].map_name == "Test Map"


@pytest.mark.tc("SAVE-U-009")
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


@pytest.mark.tc("SAVE-U-010")
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


@pytest.mark.tc("SAVE-U-011")
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


class TestSaveMenuCoverage:

    def test_save_slot_ui_init_loads_bg(self):
        """SaveSlotUI init: covers L29-33 with mock AssetManager."""
        from src.ui.save_menu import SaveSlotUI
        am = MagicMock()
        am.get_font.return_value = pygame.font.SysFont(None, 24)
        with patch("pygame.image.load") as mock_load:
            mock_load.return_value = MagicMock()
            mock_load.return_value.convert_alpha.return_value = pygame.Surface((427, 200))
            with patch("pygame.transform.smoothscale", return_value=pygame.Surface((427, 200))):
                slot = SaveSlotUI(am=am)
        assert slot is not None

    def test_save_menu_overlay_init(self):
        """SaveMenuOverlay init covers L75-76."""
        from src.ui.save_menu import SaveMenuOverlay
        screen = pygame.Surface((800, 600))
        sm = MagicMock()
        sm.list_saves.return_value = []
        with patch("pygame.image.load", return_value=MagicMock(
            convert_alpha=lambda: pygame.Surface((800, 600))
        )):
            with patch("pygame.transform.smoothscale", return_value=pygame.Surface((800, 600))):
                overlay = SaveMenuOverlay(screen=screen, save_manager=sm, title="Sauvegardes")
        assert overlay is not None
