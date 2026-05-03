import pytest
import pygame
from unittest.mock import Mock, patch
from src.engine.game_state_manager import GameStateManager, GameState
from src.engine.game_events import GameEvent

@pytest.fixture
def mock_game():
    game = Mock()
    game.screen = Mock()
    game.screen.get_size.return_value = (1280, 720)
    game.screen.subsurface.return_value = Mock()
    game.screen.subsurface.return_value.copy.return_value = Mock()
    game.player = Mock()
    game.player.rect.center = (100, 100)
    game.visible_sprites = Mock()
    game.visible_sprites.offset = pygame.math.Vector2(50, 50)
    game.audio_manager = Mock()
    return game

@pytest.fixture
def mock_save_manager():
    sm = Mock()
    sm.list_slots.return_value = [None, None, None]
    return sm

@pytest.fixture
def mock_title_screen():
    ts = Mock()
    return ts

@pytest.fixture
def mock_pause_screen():
    ps = Mock()
    ps._save_menu = Mock()
    return ps

@pytest.fixture
def gsm(mock_game, mock_save_manager, mock_title_screen, mock_pause_screen):
    with patch("src.engine.game_state_manager.TitleScreen", return_value=mock_title_screen), \
         patch("src.engine.game_state_manager.PauseScreen", return_value=mock_pause_screen), \
         patch("src.engine.game_state_manager.Game", return_value=mock_game), \
         patch("src.engine.game_state_manager.SaveManager", return_value=mock_save_manager):
        manager = GameStateManager()
        return manager

@pytest.mark.tc("GF-019")
def test_initial_state(gsm):
    assert gsm.state == GameState.TITLE

@pytest.mark.tc("GF-020")
def test_handle_title_new_game(gsm, mock_title_screen):
    mock_title_screen.handle_event.return_value = GameEvent.new_game()
    gsm._handle_title([Mock()], 0.016)
    assert gsm.state == GameState.PLAYING

@pytest.mark.tc("GF-021")
def test_handle_title_load_game(gsm, mock_title_screen, mock_save_manager, mock_game):
    mock_title_screen.handle_event.return_value = GameEvent.load_requested(1)
    mock_save_manager.load.return_value = Mock(player={"map_name": "Test Map"}, inventory={}, world_state={}, time_system={}, map="Test Map")
    
    # We pass a valid pygame Event to avoid TypeError in post()
    test_event = pygame.event.Event(pygame.USEREVENT)
    mock_game.player.inventory.capacity = 20
    gsm._handle_title([test_event], 0.016)
    
    assert gsm.state == GameState.PLAYING
    mock_save_manager.load.assert_called_with(1)

@pytest.mark.tc("GF-022")
def test_handle_title_quit(gsm, mock_title_screen):
    mock_title_screen.handle_event.return_value = GameEvent.quit()
    with patch("pygame.quit"), patch("sys.exit") as mock_exit:
        gsm._handle_title([Mock()], 0.016)
        mock_exit.assert_called_once()

@pytest.mark.tc("GF-023")
def test_handle_playing_pause_requested(gsm, mock_game):
    gsm.state = GameState.PLAYING
    mock_game.run_frame.return_value = GameEvent.pause_requested()
    
    test_event = pygame.event.Event(pygame.USEREVENT)
    gsm._handle_playing([test_event], 0.016)
    
    assert gsm.state == GameState.PAUSED

@pytest.mark.tc("GF-024")
def test_handle_paused_resume(gsm, mock_pause_screen):
    gsm.state = GameState.PAUSED
    mock_pause_screen.handle_event.return_value = GameEvent.resume()
    gsm._handle_paused([Mock()], 0.016)
    assert gsm.state == GameState.PLAYING

@pytest.mark.tc("GF-025")
def test_handle_paused_save_requested(gsm, mock_pause_screen, mock_save_manager, mock_game):
    gsm.state = GameState.PAUSED
    mock_pause_screen.handle_event.return_value = GameEvent.save_requested(1)
    with patch("pygame.transform.smoothscale", return_value=Mock()):
        gsm._handle_paused([Mock()], 0.016)
        mock_save_manager.save.assert_called_once_with(1, mock_game)
        mock_save_manager.save_thumbnail.assert_called_once()
        mock_pause_screen.notify_save_result.assert_called_with(True)

@pytest.mark.tc("GF-026")
def test_handle_paused_goto_title(gsm, mock_pause_screen, mock_title_screen, mock_game):
    gsm.state = GameState.PAUSED
    mock_pause_screen.handle_event.return_value = GameEvent.goto_title()
    gsm._handle_paused([Mock()], 0.016)
    assert gsm.state == GameState.TITLE
    assert mock_title_screen.state == "MAIN_MENU"
    assert mock_pause_screen.state == "MAIN"
    mock_game.audio_manager.stop_bgm.assert_called()

@pytest.mark.tc("GF-027")
def test_save_to_first_free_slot(gsm, mock_save_manager, mock_game):
    mock_save_manager.list_slots.return_value = [Mock(), None, Mock()]
    with patch("pygame.transform.smoothscale", return_value=Mock()):
        gsm._save_to_first_free_slot()
        mock_save_manager.save.assert_called_with(2, mock_game)

@pytest.mark.tc("GF-028")
def test_save_to_first_free_slot_all_full(gsm, mock_save_manager, mock_game):
    mock_save_manager.list_slots.return_value = [Mock(), Mock(), Mock()]
    with patch("pygame.transform.smoothscale", return_value=Mock()):
        gsm._save_to_first_free_slot()
        # Fallback to slot 1
        mock_save_manager.save.assert_called_with(1, mock_game)

@pytest.mark.tc("GF-029")
@pytest.mark.tc("GF-030")
def test_on_escape(gsm):
    gsm.state = GameState.PLAYING
    gsm._on_escape()
    assert gsm.state == GameState.PAUSED

    gsm._on_escape()
    assert gsm.state == GameState.PLAYING

@pytest.mark.tc("GF-031")
def test_transition_to_playing_no_save_data(gsm, mock_save_manager, mock_game):
    mock_save_manager.load.return_value = None
    gsm._transition_to_playing(1)
    mock_game._load_map.assert_called()
    assert gsm.state == GameState.PLAYING

@pytest.mark.tc("GF-032")
def test_handle_events_filtering(gsm, mock_game):
    # Just to run through run() with ESC
    pygame.event.clear() # Clear queue
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    
    # Should filter it out and not post it back
    gsm._handle_playing([event], 0.016)
    
    # Assert queue is empty
    assert not pygame.event.get()
