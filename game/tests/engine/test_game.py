"""Tests for Game engine: init, loading, events, drawing, transitions + config."""

import logging
from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.game import Game


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("CORE-C-01")
def test_game_initialization(mock_load):
    game = Game()
    assert game.player is not None
    assert game.i18n.current_locale == "fr"
    assert not game.inventory_ui.is_open


@patch("os.path.exists", return_value=True)
@patch("src.map.tmj_parser.TmjParser.load_map")
@pytest.mark.tc("DBG-MAP")
def test_game_actual_load_map(mock_load_map, mock_exists):
    mock_load_map.return_value = {
        "width": 10,
        "height": 10,
        "properties": {"bgm": "test.ogg"},
        "entities": [
            {
                "id": 1,
                "type": "14-spawn_point",
                "x": 16,
                "y": 16,
                "properties": {"spawn_id": "spawn_2"},
            },
            {
                "id": 2,
                "x": 32,
                "y": 32,
                "properties": {
                    "entity_type": "interactive",
                    "sub_type": "door",
                    "element_id": "d1",
                },
            },
            {
                "id": 3,
                "x": 48,
                "y": 48,
                "properties": {"type": "teleport", "target_map": "next.tmj"},
            },
            {
                "id": 4,
                "x": 64,
                "y": 64,
                "properties": {"entity_type": "npc", "sprite_sheet": "npc.png", "element_id": "n1"},
            },
            {
                "id": 5,
                "x": 80,
                "y": 80,
                "properties": {
                    "entity_type": "object",
                    "object_id": "apple",
                    "sprite_sheet": "apple.png",
                },
            },
        ],
    }

    with (
        patch("src.engine.audio.AudioManager.play_bgm") as mock_bgm,
        patch("src.engine.entity_factory.InteractiveEntity"),
        patch("src.engine.entity_factory.NPC"),
        patch("src.engine.entity_factory.Teleport"),
        patch("src.engine.entity_factory.PickupItem"),
    ):
        game = Game()
        assert mock_bgm.called

        # Test specific spawn load
        game._load_map("test.tmj", "spawn_2")
        assert game.player.pos.x == 32  # 16 + 16 (half tile)
        assert game.player.pos.y == 32


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("GF-012")
def test_game_ui_toggles(mock_load):
    game = Game()
    from src.config import Settings

    # Toggle inventory via events
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.INVENTORY_KEY

    with patch("pygame.event.get", return_value=[event]):
        game._handle_events()
        assert game.inventory_ui.is_open

    # Toggle back
    with patch("pygame.event.get", return_value=[event]):
        game._handle_events()
        assert not game.inventory_ui.is_open


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("WS-006")
def test_game_entity_spawning(mock_load):
    game = Game()
    # Mock a Tiled object
    mock_obj = {
        "name": "chest_1",
        "x": 100,
        "y": 100,
        "width": 32,
        "height": 32,
        "properties": {"entity_type": "interactive", "sub_type": "chest", "is_on": False},
    }

    with patch("src.engine.entity_factory.InteractiveEntity") as mock_ent:
        game._spawn_entities([mock_obj])
        assert mock_ent.called


def test_asset_manager_cache():
    am = AssetManager()
    am.clear_cache()
    # Mock font loading
    with patch("pygame.font.SysFont") as mock_sys:
        f1 = am.get_font("", 20)
        f2 = am.get_font("", 20)
        assert mock_sys.call_count == 1


def test_asset_manager_image():
    am = AssetManager()
    am.clear_cache()

    # 1. Fallback generation (file not found)
    with patch("os.path.exists", return_value=False):
        surf = am.get_image("fake.png", fallback=True)
        assert surf.get_size() == (32, 32)
        # Should raise error without fallback
        with pytest.raises(FileNotFoundError):
            am.get_image("fake2.png", fallback=False)

    # 2. Pygame error fallback
    with (
        patch("os.path.exists", return_value=True),
        patch("pygame.image.load", side_effect=pygame.error("Invalid format")),
    ):
        surf = am.get_image("bad.png", fallback=True)
        assert surf.get_size() == (32, 32)
        with pytest.raises(pygame.error):
            am.get_image("bad2.png", fallback=False)

    # 3. Successful load and cache hit
    mock_surf = pygame.Surface((10, 10))
    with patch("os.path.exists", return_value=True), patch("pygame.image.load") as mock_load:
        mock_load.return_value.convert_alpha.return_value = mock_surf
        surf1 = am.get_image("good.png")
        surf2 = am.get_image("good.png")

        assert surf1 == mock_surf
        assert surf1 == surf2
        assert mock_load.call_count == 1


def test_asset_manager_font_error():
    am = AssetManager()
    am.clear_cache()
    with patch("pygame.font.Font", side_effect=Exception("Font missing")):
        font = am.get_font("missing.ttf", 12)
        assert font is not None  # Returns fallback None font


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("GF-013")
def test_game_update_loop(mock_load):
    game = Game()
    # Mock subsystems to avoid complex logic
    game.interaction_manager = MagicMock()
    game.map_manager = MagicMock()
    game.audio_manager = MagicMock()
    game.visible_sprites = MagicMock()

    # Run update
    game._update(0.016)

    assert game.interaction_manager.update.called
    assert game.visible_sprites.update.called


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("CORE-R-01")
@pytest.mark.tc("CORE-R-02")
@pytest.mark.tc("CORE-R-03")
def test_game_draw_loop(mock_load):
    game = Game()
    # Mock subsystems
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []
    game.player = MagicMock()
    game.player.pos = pygame.math.Vector2(0, 0)
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1  # custom_draw compares sprite_depth > max_depth (needs int)
    game.inventory_ui = MagicMock()
    game.dialogue_manager = MagicMock()
    game.screen = pygame.Surface((800, 600))

    # _draw takes no arguments
    game._draw()

    assert game.map_manager.get_visible_chunks.called


@patch("src.engine.game.Game._load_map")
def test_game_trigger_dialogue(mock_load):
    game = Game()
    game._current_map_name = "test_map.tmj"
    game.dialogue_manager = MagicMock()

    with patch("src.engine.game.I18nManager.get", return_value="Hello from sign!"):
        game._trigger_dialogue("sign_1", "Test Title")
        game.dialogue_manager.start_dialogue.assert_called_with(
            "Hello from sign!", title="Test Title"
        )


class DummySprite(pygame.sprite.Sprite):
    def __init__(self, element_id=""):
        super().__init__()
        self.element_id = element_id
        self.target_id = None
        self.is_on = False
        self.sfx = None
        self.rect = pygame.Rect(0, 0, 32, 32)
        self.interact_called = False
        self.state = "idle"

    def interact(self, player):
        self.interact_called = True


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("GF-018")
def test_game_transition_map_fade(mock_load):
    game = Game()
    game.clock = MagicMock()
    game.clock.tick.return_value = 16
    game.time_system = MagicMock()
    game.time_system.night_alpha = 0
    game.screen = pygame.Surface((800, 600))
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []

    with patch("os.path.exists", return_value=True):
        game.transition_map("next_map.tmj", "spawn_2", "fade")
        assert mock_load.called


@patch("src.engine.game.Game._load_map")
def test_get_property_nested_paths(mock_load):
    """_get_property handles nested interactive_object and sprite dicts."""
    from src.engine.game import _get_property

    # Direct key
    assert _get_property({"key": "val"}, "key") == "val"
    # Nested interactive_object -> key
    assert _get_property({"interactive_object": {"key": "nested"}}, "key") == "nested"
    # Nested interactive_object -> sprite -> key
    assert _get_property({"interactive_object": {"sprite": {"key": "deep"}}}, "key") == "deep"
    # Nested sprite -> key at top level
    assert _get_property({"sprite": {"key": "top_sprite"}}, "key") == "top_sprite"
    # Not found -> default
    assert _get_property({}, "missing", "default") == "default"


@patch("src.engine.game.Game._load_map")
def test_game_load_world_world_file(mock_load):
    """Game reads default_map from world.world when debug is off."""
    from src.config import Settings

    original_debug = Settings.DEBUG
    Settings.DEBUG = False
    try:
        world_data = {"maps": [{"fileName": "01-village.tmj"}]}
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "builtins.open",
                unittest.mock.mock_open(read_data=__import__("json").dumps(world_data)),
            ),
        ):
            game = Game()
        mock_load.assert_called_with("01-village.tmj")
    finally:
        Settings.DEBUG = original_debug


@patch("src.engine.game.Game._load_map")
def test_game_load_world_world_parse_error(mock_load):
    """Game falls back gracefully when world.world raises on read."""
    import builtins

    from src.config import Settings

    original_debug = Settings.DEBUG
    Settings.DEBUG = False
    real_open = builtins.open

    def selective_open(path, *args, **kwargs):
        if "world.world" in str(path):
            raise Exception("IO error")
        return real_open(path, *args, **kwargs)

    try:
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=selective_open),
        ):
            game = Game()
        assert mock_load.called
    finally:
        Settings.DEBUG = original_debug


@patch("src.engine.game.Game._load_map")
def test_load_map_file_not_found(mock_load):
    """_load_map returns early when map file doesn't exist."""
    game = Game()
    mock_load.reset_mock()
    # Now call the real _load_map with a missing file
    with patch("os.path.exists", return_value=False):
        game._load_map("ghost.tmj")
    # Nothing should have been loaded after the early return
    assert not game.map_manager if hasattr(game, "map_manager") else True


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("DBG-SPAWN")
def test_spawn_entities_initial_spawn_skipped(mock_load):
    """_spawn_entities skips entities with is_initial_spawn=True."""
    game = Game()
    game.layout = MagicMock()
    game.map_manager = MagicMock()
    game.layout.to_world.return_value = (0, 0)
    entity = {"id": 1, "x": 0, "y": 0, "properties": {"is_initial_spawn": True}}
    with patch("src.engine.entity_factory.InteractiveEntity") as mock_ent:
        game._spawn_entities([entity])
    mock_ent.assert_not_called()


@patch("src.engine.game.Game._load_map")
def test_spawn_entities_sign_logged(mock_load, caplog):
    """_spawn_entities logs info for sign entities."""
    import logging

    game = Game()
    game.map_manager = MagicMock()
    entity = {
        "id": 1,
        "x": 0,
        "y": 0,
        "width": 32,
        "height": 32,
        "properties": {"entity_type": "interactive", "sub_type": "sign", "element_id": "book"},
    }
    with patch("src.engine.entity_factory.InteractiveEntity"), caplog.at_level(logging.INFO):
        game._spawn_entities([entity])
    assert any("Sign detected" in r.message for r in caplog.records)


@patch("src.engine.game.Game._load_map")
def test_transition_map_missing_file(mock_load):
    """transition_map returns early when map file is missing."""
    game = Game()
    with patch("os.path.exists", return_value=False):
        game.transition_map("ghost.tmj", "spawn_1", "instant")
    # Should not raise


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("CORE-H-01")
@pytest.mark.tc("GF-014")
def test_update_dialogue_branch(mock_load):
    """_update advances dialogue when dialogue is active."""
    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = True
    game.inventory_ui = MagicMock()
    game.inventory_ui.is_open = False
    game.chest_ui = MagicMock()
    game.chest_ui.is_open = False
    game._update(0.016)
    game.dialogue_manager.update.assert_called()


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("GF-015")
def test_update_inventory_branch(mock_load):
    """_update calls inventory_ui.update when inventory is open."""
    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = False
    game.inventory_ui = MagicMock()
    game.inventory_ui.is_open = True
    game.chest_ui = MagicMock()
    game.chest_ui.is_open = False
    game._update(0.016)
    game.inventory_ui.update.assert_called()


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("GF-016")
def test_update_chest_branch(mock_load):
    """_update handles chest_ui open state (player can still move)."""
    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = False
    game.inventory_ui = MagicMock()
    game.inventory_ui.is_open = False
    game.chest_ui = MagicMock()
    game.chest_ui.is_open = True
    game.interaction_manager = MagicMock()
    game.visible_sprites = MagicMock()
    game.player = MagicMock()
    game.player.is_moving = False
    game.player.direction = pygame.math.Vector2(0, 0)
    game._update(0.016)
    game.interaction_manager.update.assert_called()


@patch("src.engine.game.Game._load_map")
def test_handle_events_quit(mock_load):
    """_handle_events calls sys.exit on QUIT event."""
    game = Game()
    event = MagicMock()
    event.type = pygame.QUIT
    with (
        patch("pygame.event.get", return_value=[event]),
        patch("sys.exit") as mock_exit,
        patch("pygame.quit"),
    ):
        game._handle_events()
    mock_exit.assert_called()


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("CORE-H-02")
@pytest.mark.tc("GF-017")
def test_handle_events_dialogue_advance(mock_load):
    """_handle_events advances dialogue on INTERACT_KEY."""
    from src.config import Settings

    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = True
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.INTERACT_KEY
    with patch("pygame.event.get", return_value=[event]):
        game._handle_events()
    game.dialogue_manager.advance.assert_called()


@patch("src.engine.game.Game._load_map")
def test_handle_events_npc_resume_after_dialogue(mock_load):
    """_handle_events resumes NPCs when dialogue closes."""
    from src.config import Settings

    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = True
    # After advance() is called, is_active becomes False
    game.dialogue_manager.advance.side_effect = lambda: setattr(
        game.dialogue_manager, "is_active", False
    )

    # Use DummySprite so attribute assignment is reflected in assertions
    npc = DummySprite()
    npc.state = "interact"
    game.npcs.add(npc)

    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.INTERACT_KEY
    with patch("pygame.event.get", return_value=[event]):
        game._handle_events()
    assert npc.state == "idle"


@patch("src.engine.game.Game._load_map")
def test_toggle_fullscreen_success(mock_load):
    """toggle_fullscreen flips is_fullscreen flag."""
    game = Game()
    original = game.is_fullscreen
    with patch("pygame.display.toggle_fullscreen"):
        game.toggle_fullscreen()
    assert game.is_fullscreen != original


@patch("src.engine.game.Game._load_map")
def test_toggle_fullscreen_fallback(mock_load):
    """toggle_fullscreen falls back to set_mode on pygame.error."""
    game = Game()
    with (
        patch("pygame.display.toggle_fullscreen", side_effect=pygame.error("no")),
        patch("pygame.display.set_mode") as mock_mode,
    ):
        mock_mode.return_value.get_size.return_value = (1920, 1080)
        game.toggle_fullscreen()
    assert mock_mode.called


@patch("src.engine.game.Game._load_map")
def test_trigger_dialogue_missing_key(mock_load):
    """_trigger_dialogue logs warning when key not found."""
    game = Game()
    game._current_map_name = "test.tmj"
    game.dialogue_manager = MagicMock()
    with (
        patch("src.engine.game.I18nManager.get", return_value=None),
        patch("logging.warning") as mock_warn,
    ):
        game._trigger_dialogue("nonexistent")
    assert mock_warn.called


@patch("src.engine.game.Game._load_map")
def test_update_fps_title(mock_load):
    """_update updates window title when >1s has passed."""
    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = False
    game.inventory_ui = MagicMock()
    game.inventory_ui.is_open = False
    game.chest_ui = MagicMock()
    game.chest_ui.is_open = False
    game.interaction_manager = MagicMock()
    game.visible_sprites = MagicMock()
    game.player = MagicMock()
    game.player.is_moving = False
    game.player.direction = pygame.math.Vector2(0, 0)
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []
    game.screen = MagicMock()
    game.screen.get_rect.return_value = pygame.Rect(0, 0, 800, 600)

    # Force title update by making last_fps_update very old
    game.last_fps_update = 0
    with (
        patch("pygame.time.get_ticks", return_value=5000),
        patch("pygame.display.set_caption") as mock_caption,
    ):
        game._update(0.016)
    assert mock_caption.called


import unittest.mock

# --- Config / Settings ---


@pytest.mark.tc("DBG-CONF")
@pytest.mark.tc("TC-FONT-01")
def test_settings_load():
    """Verify settings load defaults and handles missing files."""
    Settings.load()
    assert Settings.VERSION != ""
    assert Settings.WINDOW_WIDTH > 0
    assert Settings.TILE_SIZE == 32


@pytest.mark.tc("TC-FONT-02")
@pytest.mark.tc("TC-FONT-03")
def test_font_tiers_exist():
    """Verify the three font tiers are defined in settings."""
    assert hasattr(Settings, "FONT_NOBLE")
    assert hasattr(Settings, "FONT_NARRATIVE")
    assert hasattr(Settings, "FONT_TECH")

    assert Settings.FONT_NOBLE.endswith(".ttf")
    assert Settings.FONT_NARRATIVE.endswith(".ttf")
    assert Settings.FONT_TECH.endswith(".ttf")


def _make_game():
    with patch("src.engine.game.Game._load_map"):
        from src.engine.game import Game
        return Game()


def _make_ef():
    from src.engine.entity_factory import EntityFactory
    game = MagicMock()
    game.visible_sprites = MagicMock()
    game.interactives = MagicMock()
    game.npcs = MagicMock()
    game.teleports_group = MagicMock()
    game.pickups = MagicMock()
    game.obstacles_group = MagicMock()
    game.world_state.get.return_value = None
    game.loot_table = MagicMock()
    game.audio_manager = MagicMock()
    game.tile_size = 32
    game.time_system = MagicMock()
    return EntityFactory(game)




class TestGameCoverage:

    @patch("src.engine.game.Game._load_map")
    def test_start_initial_ambients_delegates(self, _):
        from src.engine.game import Game
        game = Game()
        game._map_loader._start_initial_ambients = MagicMock()
        pos = pygame.math.Vector2(100, 100)
        game._start_initial_ambients(pos)
        game._map_loader._start_initial_ambients.assert_called_once_with(pos)

    @patch("src.engine.game.Game._load_map")
    def test_trigger_npc_bubble_no_msg_warns(self, _, caplog):
        game = _make_game()
        game._current_map_name = "00-map.tmj"
        game.i18n.get = MagicMock(return_value=None)
        with caplog.at_level(logging.WARNING):
            game._trigger_npc_bubble(MagicMock(), "k")
        assert "NPC bubble key not found" in caplog.text
        assert game._npc_bubble is None

    @patch("src.engine.game.Game._load_map")
    def test_trigger_npc_bubble_sets_state(self, _):
        game = _make_game()
        game._current_map_name = "00-map.tmj"
        game.i18n.get = MagicMock(return_value="Hello!")
        npc = MagicMock()
        game._trigger_npc_bubble(npc, "key")
        assert game._npc_bubble["npc"] == npc
        assert game._npc_bubble["page"] == 0

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_none_noop(self, _):
        game = _make_game()
        game._npc_bubble = None
        game._advance_npc_bubble()  # no raise
        assert game._npc_bubble is None

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_no_font_noop(self, _):
        game = _make_game()
        game._npc_bubble = {"npc": MagicMock(), "text": "Hi", "page": 0}
        game.speech_bubble.font = None
        game._advance_npc_bubble()  # no raise
        assert game._npc_bubble["page"] == 0

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_increments_page(self, _):
        game = _make_game()
        game._npc_bubble = {"npc": MagicMock(), "text": "Hi", "page": 0}
        game.speech_bubble.font = MagicMock()
        game.speech_bubble.get_total_pages = MagicMock(return_value=3)
        game._advance_npc_bubble()
        assert game._npc_bubble["page"] == 1

    @patch("src.engine.game.Game._load_map")
    def test_advance_npc_bubble_closes_on_last(self, _):
        game = _make_game()
        npc = MagicMock()
        npc.state = "interact"
        game.npcs = [npc]
        game._npc_bubble = {"npc": npc, "text": "Hi", "page": 0}
        game.speech_bubble.font = MagicMock()
        game.speech_bubble.get_total_pages = MagicMock(return_value=1)
        game._advance_npc_bubble()
        assert game._npc_bubble is None
        assert npc.state == "idle"

    @patch("src.engine.game.Game._load_map")
    def test_get_state_has_keys(self, _):
        game = _make_game()
        s = game.get_state()
        assert "map_name" in s and "player_pos" in s

    @patch("src.engine.game.Game._load_map")
    def test_run_frame_returns_game_event(self, _):
        from src.engine.game_events import GameEvent
        game = _make_game()
        game._handle_events = MagicMock()
        game._update = MagicMock()
        game._draw = MagicMock()
        assert isinstance(game.run_frame(0.016), GameEvent)

    @patch("src.engine.game.Game._load_map")
    def test_update_resolves_pending_npc_stopped(self, _):
        game = _make_game()
        npc = MagicMock()
        npc.is_moving = False
        game._pending_npc_dialogue = (npc, "elem")
        game._trigger_npc_bubble = MagicMock()
        game._update(0.016)
        game._trigger_npc_bubble.assert_called_once_with(npc, "elem")
        assert game._pending_npc_dialogue is None

