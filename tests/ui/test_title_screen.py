"""
Tests RED — TitleScreen (TC-009 à TC-013) + GameStateManager (TC-014 à TC-018)
Spec: docs/specs/game-flow-spec.md#4-test-case-specifications
"""
import pygame
import pytest
from unittest.mock import MagicMock, patch, call
from src.engine.game_events import GameEvent, GameEventType
from src.ui.title_screen import TitleScreen
from src.engine.game_state_manager import GameStateManager, GameState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_key_event(key):
    """Crée un événement KEYDOWN pygame minimal."""
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = key
    return event


def _make_mouse_event(pos):
    """Crée un événement MOUSEBUTTONDOWN pygame minimal."""
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = pos
    return event


# ── Fixtures TitleScreen ───────────────────────────────────────────────────────

@pytest.fixture
def mock_screen():
    surf = MagicMock(spec=pygame.Surface)
    surf.get_size.return_value = (1280, 720)
    surf.get_rect.return_value = pygame.Rect(0, 0, 1280, 720)
    return surf


@pytest.fixture
def mock_save_manager():
    sm = MagicMock()
    sm.list_slots.return_value = [None, None, None]
    return sm


@pytest.fixture
def title_screen(mock_screen, mock_save_manager):
    """TitleScreen avec assets Pygame mockés — bypass _load_assets."""
    mock_surf = MagicMock()
    mock_surf.get_rect.return_value = pygame.Rect(0, 0, 400, 86)
    mock_surf.get_size.return_value = (1024, 182)
    mock_surf.get_width.return_value = 720
    mock_surf.get_height.return_value = 160

    ts = TitleScreen.__new__(TitleScreen)
    ts._screen = mock_screen
    ts._save_manager = mock_save_manager
    ts.state = "MAIN_MENU"
    ts._slots = [None, None, None]
    ts._hovered_btn = None
    ts._hovered_slot = None
    ts._sw = 1280
    ts._sh = 720
    # Stub assets needed by _compute_layout and draw()
    ts._panel_raw = mock_surf
    ts._panel = mock_surf
    ts._panel_load = mock_surf
    ts._logo_surf = mock_surf

    with patch("pygame.transform.smoothscale", return_value=mock_surf):
        TitleScreen._compute_layout(ts)
    return ts


# ── TC-009 : Nouvelle Partie ──────────────────────────────────────────────────

def test_title_click_new_game_returns_event(title_screen):
    """TC-009 : clic sur bouton Nouvelle Partie → GameEvent NEW_GAME."""
    # Positionner la souris sur le bouton Nouvelle Partie (index 0)
    btn_rect = title_screen.button_rects[0]
    event = _make_mouse_event(btn_rect.center)

    result = title_screen.handle_event(event)

    assert result is not None
    assert result.type == GameEventType.NEW_GAME


# ── TC-010 : Charger → LOAD_MENU ─────────────────────────────────────────────

def test_title_click_charger_transitions_to_load_menu(title_screen):
    """TC-010 : clic Charger → state interne == LOAD_MENU."""
    btn_rect = title_screen.button_rects[1]  # index 1 = Charger
    event = _make_mouse_event(btn_rect.center)

    title_screen.handle_event(event)

    assert title_screen.state == "LOAD_MENU"


# ── TC-011 : Quitter ──────────────────────────────────────────────────────────

def test_title_click_quitter_returns_quit_event(title_screen):
    """TC-011 : clic Quitter → GameEvent QUIT."""
    btn_rect = title_screen.button_rects[3]  # index 3 = Quitter
    event = _make_mouse_event(btn_rect.center)

    result = title_screen.handle_event(event)

    assert result is not None
    assert result.type == GameEventType.QUIT


# ── TC-012 : ESC depuis LOAD_MENU → MAIN_MENU ────────────────────────────────

def test_title_esc_from_load_menu_returns_to_main(title_screen):
    """TC-012 : K_ESCAPE depuis LOAD_MENU → retour MAIN_MENU."""
    # Simuler transition vers LOAD_MENU
    title_screen.state = "LOAD_MENU"

    event = _make_key_event(pygame.K_ESCAPE)
    title_screen.handle_event(event)

    assert title_screen.state == "MAIN_MENU"


# ── TC-013 : clic slot 2 en LOAD_MENU → LOAD_GAME ────────────────────────────

def test_title_click_slot_in_load_menu_returns_load_event(title_screen, mock_save_manager):
    """TC-013 : clic slot 2 en LOAD_MENU → GameEvent LOAD_GAME slot_id=2."""
    from src.engine.save_manager import SlotInfo
    mock_save_manager.list_slots.return_value = [
        None,
        SlotInfo(slot_id=2, saved_at="2026-05-02T14:00:00",
                 playtime_seconds=3600, map_name="00-spawn.tmj"),
        None,
    ]
    title_screen.state = "LOAD_MENU"
    title_screen._refresh_slots()  # recalcule les slots affichés

    slot_rect = title_screen.slot_rects[1]  # index 1 = slot_id 2
    event = _make_mouse_event(slot_rect.center)

    result = title_screen.handle_event(event)

    assert result is not None
    assert result.type == GameEventType.LOAD_GAME
    assert result.slot_id == 2


# ═══════════════════════════════════════════════════════════════════════════════
# GameStateManager Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_gsm():
    """GameStateManager avec Game et TitleScreen entièrement mockés."""
    with patch("src.engine.game_state_manager.Game") as MockGame, \
         patch("src.engine.game_state_manager.TitleScreen") as MockTitle, \
         patch("src.engine.game_state_manager.PauseScreen") as MockPause, \
         patch("src.engine.game_state_manager.SaveManager") as MockSM:

        mock_game_inst = MagicMock()
        mock_game_inst.run_frame.return_value = GameEvent.none()
        MockGame.return_value = mock_game_inst

        mock_title_inst = MagicMock()
        MockTitle.return_value = mock_title_inst

        mock_pause_inst = MagicMock()
        MockPause.return_value = mock_pause_inst

        mock_sm_inst = MagicMock()
        mock_sm_inst.list_slots.return_value = [None, None, None]
        MockSM.return_value = mock_sm_inst

        gsm = GameStateManager()
        gsm._game = mock_game_inst
        gsm._title_screen = mock_title_inst
        gsm._pause_screen = mock_pause_inst
        gsm._save_manager = mock_sm_inst

    return gsm


# ── TC-014 : pygame.QUIT → pygame.quit() ─────────────────────────────────────

def test_gsm_pygame_quit_exits(mock_gsm):
    """TC-014 : pygame.QUIT → pygame.quit() appelé + sys.exit()."""
    quit_event = MagicMock()
    quit_event.type = pygame.QUIT

    with patch("pygame.quit") as mock_pq, \
         patch("sys.exit") as mock_exit:
        mock_gsm._process_global_events([quit_event])
        mock_pq.assert_called_once()
        mock_exit.assert_called_once()


# ── TC-015 : ESC en PLAYING → PAUSED ─────────────────────────────────────────

def test_gsm_esc_in_playing_transitions_to_paused(mock_gsm):
    """TC-015 : K_ESCAPE en PLAYING → state == PAUSED."""
    mock_gsm.state = GameState.PLAYING

    esc_event = _make_key_event(pygame.K_ESCAPE)

    mock_gsm._process_global_events([esc_event])

    assert mock_gsm.state == GameState.PAUSED


# ── TC-016 : ESC en PAUSED → PLAYING ─────────────────────────────────────────

def test_gsm_esc_in_paused_transitions_to_playing(mock_gsm):
    """TC-016 : K_ESCAPE en PAUSED → state == PLAYING."""
    mock_gsm.state = GameState.PAUSED

    esc_event = _make_key_event(pygame.K_ESCAPE)

    mock_gsm._process_global_events([esc_event])

    assert mock_gsm.state == GameState.PLAYING


# ── TC-017 : _transition_to_playing(None) → _load_map ────────────────────────

def test_gsm_transition_to_playing_new_game_calls_load_map(mock_gsm):
    """TC-017 : _transition_to_playing(None) → game._load_map() avec default_map."""
    mock_gsm._transition_to_playing(slot_id=None)

    mock_gsm._game._load_map.assert_called_once()
    assert mock_gsm.state == GameState.PLAYING


# ── TC-018 : _transition_to_playing(1) → save_manager.load(1) ───────────────

def test_gsm_transition_to_playing_load_slot(mock_gsm):
    """TC-018 : _transition_to_playing(1) → save_manager.load(1) appelé, state=PLAYING."""
    from src.engine.save_manager import SaveData
    mock_data = SaveData(
        version="0.4.0",
        saved_at="2026-05-02",
        playtime_seconds=0,
        player={"map_name": "00-spawn.tmj", "x": 0.0, "y": 0.0,
                "facing": "down", "level": 1, "hp": 100, "max_hp": 100, "gold": 0},
        time_system={"total_minutes": 0.0},
        inventory={"slots": [None]*28, "equipment": {
            "HEAD": None, "BAG": None, "BELT": None, "LEFT_HAND": None,
            "UPPER_BODY": None, "LOWER_BODY": None, "RIGHT_HAND": None, "SHOES": None
        }},
        world_state={}
    )
    mock_gsm._save_manager.load.return_value = mock_data

    mock_gsm._transition_to_playing(slot_id=1)

    mock_gsm._save_manager.load.assert_called_once_with(1)
    assert mock_gsm.state == GameState.PLAYING
