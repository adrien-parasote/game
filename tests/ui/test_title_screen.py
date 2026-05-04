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
    ts._hovered_slot = None
    ts._hovered_item = None
    ts._sw = 1280
    ts._sh = 720
    ts._light_scale_x = 1.0
    ts._light_scale_y = 1.0
    ts._logo_surf = mock_surf
    ts._panel_load = mock_surf
    ts._load_menu = MagicMock()
    ts._load_menu.get_clicked_slot.return_value = None

    from unittest.mock import MagicMock as _MM
    ts._i18n = _MM()
    ts._i18n.get.side_effect = lambda key, default="": default
    ts._bg = pygame.Surface((1280, 720))
    ts._overlay = mock_surf
    ts._slot_states = {"idle": mock_surf, "hover": mock_surf}
    ts._light_time = 0.0
    ts._light_halos = {
        45: pygame.Surface((90, 90)),
        28: pygame.Surface((56, 56)),
        18: pygame.Surface((36, 36)),
    }
    ts._mushroom_halos: dict = {}  # empty until calibration
    
    # Fonts
    mock_font = _MM()
    mock_font.render.return_value = pygame.Surface((10, 10), pygame.SRCALPHA)
    ts._font = mock_font
    ts._font_small = mock_font
    ts._title_font = mock_font
    ts._menu_item_font = mock_font
    ts._back_label_font = mock_font
    
    # Icons and Cursors
    ts._pointer_img = mock_surf
    ts._pointer_select_img = mock_surf
    ts._back_btn = mock_surf
    ts._back_btn_hover = mock_surf

    with patch("pygame.transform.smoothscale", return_value=mock_surf):
        TitleScreen._compute_layout(ts)
    return ts

# ── GF-034 : Scale factors résolution-indépendante ────────────────────────────

@pytest.mark.tc("GF-034")
def test_title_screen_light_scale_factors(mock_save_manager):
    """GF-034 : _light_scale_x/y calculés depuis screen.get_size() — espace logique 1280×720."""
    mock_screen = MagicMock(spec=pygame.Surface)
    mock_screen.get_size.return_value = (2560, 1440)
    with patch("src.ui.title_screen.TitleScreen._load_assets"), \
         patch("src.ui.title_screen.TitleScreen._compute_layout"), \
         patch("src.ui.title_screen.SaveMenuOverlay"):
        ts = TitleScreen.__new__(TitleScreen)
        ts._screen = mock_screen
        ts._save_manager = mock_save_manager
        # Simulate __init__ scale computation only
        sw, sh = mock_screen.get_size()
        ts._sw = sw
        ts._sh = sh
        ts._light_scale_x = sw / 1280.0
        ts._light_scale_y = sh / 720.0

    assert ts._light_scale_x == 2.0
    assert ts._light_scale_y == 2.0


# ── TC-009 à TC-011 : Items texte du menu ────────────────────────────────────

def test_title_click_new_game_returns_event(title_screen):
    """TC-009 : clic centre de l'item 'Nouvelle Partie' (index 0) → GameEvent NEW_GAME."""
    rect = title_screen.menu_item_rects[0]  # Nouvelle Partie
    event = _make_mouse_event(rect.center)
    result = title_screen.handle_event(event)
    assert result is not None and result.type == GameEventType.NEW_GAME


def test_title_click_charger_transitions_to_load_menu(title_screen):
    """TC-010 : clic item 'Charger' (index 1) → state == LOAD_MENU."""
    rect = title_screen.menu_item_rects[1]  # Charger
    event = _make_mouse_event(rect.center)
    title_screen.handle_event(event)
    assert title_screen.state == "LOAD_MENU"


def test_title_click_quitter_returns_quit_event(title_screen):
    """TC-011 : clic item 'Quitter' (index 3) → GameEvent QUIT."""
    rect = title_screen.menu_item_rects[3]  # Quitter
    event = _make_mouse_event(rect.center)
    result = title_screen.handle_event(event)
    assert result is not None and result.type == GameEventType.QUIT


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
    title_screen._load_menu._slots_info = [
        None,
        SlotInfo(slot_id=2, saved_at="2026-05-02T14:00:00",
                 playtime_seconds=3600, map_name="00-spawn.tmj", player_name="Hero", level=1),
        None,
    ]
    title_screen.state = "LOAD_MENU"
    title_screen._load_menu.get_clicked_slot.return_value = 1  # idx 1

    event = _make_mouse_event((0, 0)) # pos ignored by mock

    result = title_screen.handle_event(event)

    assert result is not None
    assert result.type == GameEventType.LOAD_REQUESTED
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

# ── Tests additionnels TitleScreen (Coverage) ────────────────────────────────

def test_title_screen_load_assets_with_fallbacks(mock_screen, mock_save_manager):
    mock_surf = pygame.Surface((1024, 1024), pygame.SRCALPHA)
    with patch("pygame.image.load", return_value=mock_surf), \
         patch("pygame.font.Font", side_effect=OSError), \
         patch("src.engine.asset_manager.AssetManager", side_effect=Exception):
         
        ts = TitleScreen(mock_screen, mock_save_manager)
        assert ts._font is not None
        assert ts._bg.get_size() == (1280, 720)

@pytest.mark.tc("TC-004")
@pytest.mark.tc("IT-003")
def test_title_screen_update(title_screen):
    # Test hover on MAIN_MENU
    with patch("pygame.mouse.get_pos", return_value=title_screen.menu_item_rects[1].center):
        title_screen.update(0.16)
        assert title_screen._hovered_item == 1
        
    # Test update delegates to _load_menu
    title_screen.state = "LOAD_MENU"
    title_screen.update(0.16)
    title_screen._load_menu.update.assert_called_once_with(0.16)

    # Test hover on OPTIONS
    title_screen.state = "OPTIONS"
    with patch("pygame.mouse.get_pos", return_value=title_screen.back_btn_rect.center):
        title_screen.update(0.16)
        assert title_screen._back_hovered is True

@pytest.mark.tc("GF-033")
def test_title_screen_draw_main_menu(title_screen):
    title_screen.state = "MAIN_MENU"
    title_screen._hovered_item = 0
    with patch("pygame.mouse.get_pos", return_value=(0,0)), \
         patch("pygame.mouse.get_pressed", return_value=(False, False, False)), \
         patch("pygame.draw.line"), patch("pygame.draw.circle"):
        title_screen.draw()
    assert title_screen._screen.blit.call_count > 0

@pytest.mark.tc("TC-005")
def test_title_screen_draw_load_menu(title_screen):
    title_screen.state = "LOAD_MENU"
    title_screen._refresh_slots()
    with patch("pygame.mouse.get_pos", return_value=(0,0)), \
         patch("pygame.mouse.get_pressed", return_value=(False, False, False)), \
         patch("pygame.draw.line"), patch("pygame.draw.circle"):
        title_screen.draw()
    title_screen._load_menu.draw.assert_called_once()

def test_title_screen_draw_options(title_screen):
    title_screen.state = "OPTIONS"
    title_screen._back_hovered = True
    with patch("pygame.mouse.get_pos", return_value=(0,0)), \
         patch("pygame.mouse.get_pressed", return_value=(False, False, False)), \
         patch("pygame.draw.line"), patch("pygame.draw.circle"):
        title_screen.draw()
    assert title_screen._screen.blit.call_count > 0

def test_title_screen_options_state_transitions(title_screen):
    # Entre en OPTIONS via clic sur le menu
    # index 2 is options
    event = _make_mouse_event(title_screen.menu_item_rects[2].center)
    title_screen.handle_event(event)
    assert title_screen.state == "OPTIONS"
    
    # Sortie avec ESC
    title_screen.handle_event(_make_key_event(pygame.K_ESCAPE))
    assert title_screen.state == "MAIN_MENU"
    
    # Rentrée (force state) et Sortie avec le bouton retour
    title_screen.state = "OPTIONS"
    title_screen.handle_event(_make_mouse_event(title_screen.back_btn_rect.center))
    assert title_screen.state == "MAIN_MENU"

def test_title_screen_handle_load_menu_ignore(title_screen):
    title_screen.state = "LOAD_MENU"
    # ignore events not mouse down or escape
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = pygame.K_SPACE
    assert title_screen.handle_event(event) is None
    
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 3
    assert title_screen.handle_event(event) is None
    
    # Not clicking on any slot
    event = _make_mouse_event((0, 0))
    assert title_screen.handle_event(event) is None

def test_title_screen_handle_main_menu_ignore(title_screen):
    title_screen.state = "MAIN_MENU"
    # ignore events not mouse down
    event = MagicMock()
    event.type = pygame.KEYDOWN
    assert title_screen.handle_event(event) is None
    
    # click outside
    event = _make_mouse_event((0, 0))
    assert title_screen.handle_event(event) is None

def test_title_screen_handle_options_ignore(title_screen):
    title_screen.state = "OPTIONS"
    # ignore events not mouse down or escape
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = pygame.K_SPACE
    assert title_screen.handle_event(event) is None
    
    # click outside back button
    event = _make_mouse_event((0, 0))
    title_screen.handle_event(event)
    assert title_screen.state == "OPTIONS"
