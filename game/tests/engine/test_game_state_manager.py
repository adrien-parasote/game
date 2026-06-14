from unittest.mock import MagicMock, Mock, patch

import pygame
import pytest
from src.config import Settings
from src.engine.game_events import GameEvent
from src.engine.game_state_manager import GameState, GameStateManager
from src.engine.inventory_system import Inventory
from src.engine.save_manager import SaveManager
from src.engine.time_system import TimeSystem
from src.engine.world_state import WorldState


@pytest.fixture
def mock_game():
    # This fixture is retained for backward compatibility but is no longer used directly in gsm.
    # It still provides a generic mock Game instance if needed elsewhere.
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
    game.clock = Mock()
    game.clock.tick.return_value = 16
    # UI components for potential use
    game.inventory_ui = Mock()
    game.chest_ui = Mock()
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
    with (
        patch("src.engine.game_state_manager.TitleScreen", return_value=mock_title_screen),
        patch("src.engine.game_state_manager.PauseScreen", return_value=mock_pause_screen),
        patch("src.engine.game_state_manager.Game", return_value=mock_game),
        patch("src.engine.game_state_manager.SaveManager", return_value=mock_save_manager),
    ):
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
    mock_save_manager.load.return_value = Mock(
        player={"map_name": "Test Map"},
        inventory={},
        world_state={},
        time_system={},
        map="Test Map",
    )

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


@pytest.mark.tc("GF-033")
def test_transition_to_title_resets_inventory_and_chest_ui(gsm, mock_game):
    """Regression: inventory_ui and chest_ui must be closed when returning to title.

    Bug: open inventory survived menu transition → still rendered on new/loaded game.
    Fix: _transition_to_title() calls inventory_ui._init_state() and chest_ui.close().
    """
    # Patch Game to return mock_game so _transition_to_title() uses our mock
    with patch("src.engine.game_state_manager.Game", return_value=mock_game):
        gsm._transition_to_title()
    mock_game.inventory_ui._init_state.assert_called_once()
    mock_game.chest_ui.close.assert_called_once()


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


@pytest.fixture
def tmp_saves_dir(tmp_path):
    return str(tmp_path / "saves")


def _make_gsm_mock_game(tmp_saves_dir):
    """Minimal mock Game with real TimeSystem for save/load time tests."""

    game = MagicMock()
    game._current_map_name = "00-spawn.tmj"
    game.map_manager.name = "Mocked Map"
    game.player.name = "Hero"
    game.player.pos = pygame.math.Vector2(320.0, 480.0)
    game.player.current_state = "down"
    game.player.level = 1
    game.player.hp = 100
    game.player.max_hp = 100
    game.player.gold = 0
    game.player.inventory = Inventory(capacity=28)
    ts = TimeSystem(initial_hour=6)
    ts.update(120 * Settings.MINUTE_DURATION)  # advance 120 game-minutes
    game.time_system = ts
    game.world_state = WorldState()
    return game


@pytest.mark.tc("GF-031")
def test_load_game_time_restored(tmp_saves_dir):
    """Regression: loaded game time must exactly match saved time."""
    sm = SaveManager(saves_dir=tmp_saves_dir)
    mock_game = _make_gsm_mock_game(tmp_saves_dir)
    saved_minutes = mock_game.time_system._total_minutes
    sm.save(1, mock_game)

    gsm = GameStateManager()
    gsm._transition_to_title()

    with patch.object(gsm._save_manager, "load", side_effect=sm.load):
        gsm._transition_to_playing(slot_id=1)

    loaded_minutes = gsm._game.time_system._total_minutes
    assert loaded_minutes == pytest.approx(saved_minutes, rel=1e-5), (
        f"Time mismatch: loaded={loaded_minutes}, saved={saved_minutes}"
    )


@pytest.mark.tc("GF-032")
def test_handle_events_filtering(gsm, mock_game):
    # Just to run through run() with ESC
    pygame.event.clear()  # Clear queue
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    # Should filter it out and not post it back
    gsm._handle_playing([event], 0.016)

    # Assert queue is empty
    assert not pygame.event.get()


def test_run_main_loop_and_global_events(gsm):
    # Test run() exits gracefully by mocking pygame.display.update to raise a custom exception
    class BreakLoop(Exception):
        pass

    with patch("pygame.display.update", side_effect=BreakLoop), pytest.raises(BreakLoop):
        gsm.run()

    # Test _process_global_events with QUIT
    event_quit = pygame.event.Event(pygame.QUIT)
    with patch("sys.exit") as mock_exit, patch("pygame.quit") as mock_pygame_quit:
        gsm._process_global_events([event_quit])
        mock_exit.assert_called_once()
        mock_pygame_quit.assert_called_once()

    # Test _process_global_events with TOGGLE_FULLSCREEN
    from src.config import Settings

    event_fs = pygame.event.Event(pygame.KEYDOWN, key=Settings.TOGGLE_FULLSCREEN_KEY)
    gsm._process_global_events([event_fs])
    gsm._game.toggle_fullscreen.assert_called_once()

    # Test _process_global_events with ESCAPE
    event_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    with patch.object(gsm, "_on_escape") as mock_on_escape:
        gsm._process_global_events([event_esc])
        mock_on_escape.assert_called_once()


def test_handle_title_none_result(gsm, mock_title_screen):
    mock_title_screen.handle_event.return_value = None
    gsm._handle_title([Mock()], 0.016)
    mock_title_screen.update.assert_called_once()
    mock_title_screen.draw.assert_called_once()


def test_handle_paused_none_and_pause_request(gsm, mock_pause_screen):
    # Test result None
    mock_pause_screen.handle_event.return_value = None
    gsm._handle_paused([Mock()], 0.016)
    mock_pause_screen.update.assert_called_once()

    # Test PAUSE_REQUESTED in paused state
    mock_pause_screen.handle_event.return_value = GameEvent.pause_requested()
    with patch.object(gsm, "_save_to_first_free_slot") as mock_save:
        gsm._handle_paused([Mock()], 0.016)
        mock_save.assert_called_once()


def test_restore_inventory_exceptions(gsm, mock_game):
    # Setup inventory mock
    inv = Mock()
    inv.capacity = 2
    inv.slots = [None, None]
    inv.equipment = {}
    mock_game.player.inventory = inv

    # Force exception on create_item
    inv.create_item.side_effect = Exception("Test Exception")

    inv_data = {
        "slots": [{"id": "potion", "quantity": 1}],
        "equipment": {"weapon": {"id": "sword", "quantity": 1}, "armor": None},
    }

    gsm._restore_inventory(mock_game, inv_data)
    assert inv.slots[0] is None  # Did not crash, kept None
    assert inv.equipment.get("armor") is None  # Restored None
    assert "weapon" not in inv.equipment  # Did not crash on exception


def test_resolve_default_map(gsm):
    # Test world.world logic when NOT in DEBUG or debug room missing
    with (
        patch("src.config.Settings.DEBUG", False),
        patch("src.config.Settings.DEFAULT_MAP", "00-spawn.tmj"),
        patch("os.path.exists", return_value=True),
        patch("builtins.open") as mock_open,
    ):
        import io

        # Valid world.world
        mock_open.return_value = io.StringIO('{"maps": [{"fileName": "test.tmj"}]}')
        with patch("json.load", return_value={"maps": [{"fileName": "test.tmj"}]}):
            assert gsm._resolve_default_map() == "test.tmj"

        # Exception during world.world reading
        mock_open.side_effect = Exception("File read error")
        assert gsm._resolve_default_map() == "00-spawn.tmj"


def test_resolve_default_map_with_custom_default(gsm):
    # Test custom default map from Settings when NOT in DEBUG
    with (
        patch("src.config.Settings.DEBUG", False),
        patch("src.config.Settings.DEFAULT_MAP", "custom_map.tmj"),
    ):
        assert gsm._resolve_default_map() == "custom_map.tmj"


def test_resolve_default_map_with_debug_room(gsm):
    # Test debug room resolution when in DEBUG and file exists
    with (
        patch("src.config.Settings.DEBUG", True),
        patch("os.path.exists", lambda path: "99-debug_room.tmj" in path),
    ):
        assert gsm._resolve_default_map() == "debug/99-debug_room.tmj"


# (imports already at top of file)


@patch("pygame.mouse.set_visible")
def test_cursor_is_hidden_during_gameplay(mock_mouse):
    gsm = GameStateManager()
    gsm._transition_to_playing(slot_id=None)
    mock_mouse.assert_called_with(False)


# assert True (legacy bypass)

# assert True (legacy bypass)
