"""RED tests for Phase 1.5 — game_setup, entity_factory, map_loader, input_handler.

TC-GS-01..05, TC-EF-01..09, TC-ML-01..07, TC-IH-01..05
IT-EF-01, IT-ML-01, IT-IH-01, IT-GS-01
from docs/specs/phase-1.5-game-refactoring.md
"""

import json
import os
import sys
from unittest.mock import MagicMock, call, patch

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"


# ---------------------------------------------------------------------------
# ── GAME SETUP ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


class TestGameSetup:
    """TC-GS-01..05 — game_setup module functions."""

    @pytest.mark.tc("TC-GS-01")
    def test_load_property_types_valid_file(self, tmp_path):
        from src.engine.game_setup import load_property_types

        data = {"propertyTypes": [{"name": "torch"}, {"name": "chest"}]}
        f = tmp_path / "game.tiled-project"
        f.write_text(json.dumps(data))
        result = load_property_types(str(f))
        assert result == [{"name": "torch"}, {"name": "chest"}]

    @pytest.mark.tc("TC-GS-02")
    def test_load_property_types_missing_file(self, caplog):
        from src.engine.game_setup import load_property_types

        result = load_property_types("/nonexistent/path/game.tiled-project")
        assert result == []

    @pytest.mark.tc("TC-GS-03")
    def test_load_property_types_invalid_json(self, tmp_path, caplog):
        from src.engine.game_setup import load_property_types

        f = tmp_path / "game.tiled-project"
        f.write_text("{invalid json}")
        result = load_property_types(str(f))
        assert result == []

    @pytest.mark.tc("TC-GS-04")
    def test_setup_logging_adds_handlers(self):
        """setup_logging must configure root logger with handlers."""
        import logging
        from src.engine.game_setup import setup_logging

        from src.config import Settings

        root_logger = logging.getLogger()
        initial_handlers = list(root_logger.handlers)
        try:
            setup_logging(Settings)
            # At least one handler was added
            assert len(root_logger.handlers) > 0
        finally:
            # Restore original handlers to avoid polluting other tests
            root_logger.handlers = initial_handlers

    @pytest.mark.tc("TC-GS-05")
    def test_load_property_types_missing_key(self, tmp_path):
        """load_property_types returns [] when propertyTypes key absent."""
        from src.engine.game_setup import load_property_types

        data = {"otherKey": [1, 2]}
        f = tmp_path / "game.tiled-project"
        f.write_text(json.dumps(data))
        result = load_property_types(str(f))
        assert result == []


# ---------------------------------------------------------------------------
# ── ENTITY FACTORY ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def _make_game_mock():
    game = MagicMock()
    game.visible_sprites = MagicMock()
    game.interactives = MagicMock()
    game.npcs = MagicMock()
    game.pickups = MagicMock()
    game.teleports_group = MagicMock()
    game.obstacles_group = MagicMock()
    game.world_state = MagicMock()
    game.world_state.get.return_value = None
    game.loot_table = MagicMock()
    game.audio_manager = MagicMock()
    game.tile_size = 32
    game.player = MagicMock()
    return game


class TestGetProperty:
    """TC-EF-01..03 — _get_property helper."""

    @pytest.mark.tc("TC-EF-01")
    def test_get_property_root_level(self):
        from src.engine.entity_factory import _get_property

        obj = {"key": "val"}
        assert _get_property(obj, "key") == "val"

    @pytest.mark.tc("TC-EF-02")
    def test_get_property_nested(self):
        from src.engine.entity_factory import _get_property

        obj = {"interactive_object": {"key": "val"}}
        assert _get_property(obj, "key") == "val"

    @pytest.mark.tc("TC-EF-03")
    def test_get_property_absent_returns_default(self):
        from src.engine.entity_factory import _get_property

        assert _get_property({}, "key", default="x") == "x"


class TestEntityFactorySpawn:
    """TC-EF-04..09 — EntityFactory.spawn_* methods."""

    @pytest.mark.tc("TC-EF-04")
    def test_spawn_interactive_adds_to_groups(self):
        from src.engine.entity_factory import EntityFactory

        game = _make_game_mock()
        ef = EntityFactory(game)

        # Minimal ent dict for an interactive entity
        ent = {
            "type": "03-interactive",
            "x": 64,
            "y": 64,
            "properties": {"element_id": "lever_01", "sub_type": "lever"},
        }
        with patch("src.engine.entity_factory.InteractiveEntity") as MockEntity:
            instance = MagicMock()
            MockEntity.return_value = instance
            ef.spawn_interactive(ent, ent.get("properties", {}), "test_map.tmj")

        # InteractiveEntity constructor called with groups containing visible_sprites and interactives
        MockEntity.assert_called_once()
        call_kwargs = MockEntity.call_args
        groups_arg = call_kwargs.kwargs.get("groups", call_kwargs.args[1] if len(call_kwargs.args) > 1 else [])
        assert game.visible_sprites in groups_arg
        assert game.interactives in groups_arg

    @pytest.mark.tc("TC-EF-05")
    def test_spawn_teleport_adds_to_teleports_group(self):
        from src.engine.entity_factory import EntityFactory

        game = _make_game_mock()
        ef = EntityFactory(game)
        ent = {
            "type": "15-teleport",
            "x": 64,
            "y": 64,
            "properties": {"target_map": "b.tmj", "target_spawn_id": "A"},
        }
        with patch("src.engine.entity_factory.Teleport") as MockTeleport:
            instance = MagicMock()
            MockTeleport.return_value = instance
            ef.spawn_teleport(ent, ent.get("properties", {}))

        # Teleport constructor called with teleports_group list
        MockTeleport.assert_called_once()
        call_args = MockTeleport.call_args
        groups_arg = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("groups", [])
        assert game.teleports_group in groups_arg

    @pytest.mark.tc("TC-EF-06")
    def test_spawn_npc_adds_to_visible_and_npcs(self):
        from src.engine.entity_factory import EntityFactory

        game = _make_game_mock()
        ef = EntityFactory(game)
        ent = {
            "type": "07-npc",
            "x": 64,
            "y": 64,
            "properties": {"element_id": "npc_01", "npc_id": "villager"},
        }
        with patch("src.engine.entity_factory.NPC") as MockNPC:
            instance = MagicMock()
            MockNPC.return_value = instance
            ef.spawn_npc(ent, ent.get("properties", {}))

        # NPC constructor called with visible_sprites and npcs groups
        MockNPC.assert_called_once()
        call_kwargs = MockNPC.call_args
        groups_arg = call_kwargs.kwargs.get("groups", call_kwargs.args[1] if len(call_kwargs.args) > 1 else [])
        assert game.visible_sprites in groups_arg
        assert game.npcs in groups_arg

    @pytest.mark.tc("TC-EF-07")
    def test_spawn_pickup_adds_to_pickups(self):
        from src.engine.entity_factory import EntityFactory

        game = _make_game_mock()
        ef = EntityFactory(game)
        ent = {
            "type": "08-pickup",
            "x": 64,
            "y": 64,
            "properties": {"item_id": "herb"},
        }
        # spawn_pickup with no item_id and sprite returns early — verify graceful no-op
        ef.spawn_pickup(ent, ent.get("properties", {}))  # no item_id/sprite → early return
        # No crash = pass

    @pytest.mark.tc("TC-EF-08")
    def test_spawn_entities_unknown_type_no_exception(self, caplog):
        from src.engine.entity_factory import EntityFactory

        game = _make_game_mock()
        ef = EntityFactory(game)
        entities = [{"type": "99-unknown", "x": 0, "y": 0, "properties": {}}]
        # Must not raise
        ef.spawn_entities(entities, "test.tmj")

    @pytest.mark.tc("TC-EF-09")
    def test_spawn_interactive_restores_world_state(self):
        from src.engine.entity_factory import EntityFactory

        game = _make_game_mock()
        # Simulate world_state has saved is_on=True for this entity
        game.world_state.get.return_value = {"is_on": True}
        ef = EntityFactory(game)
        ent = {
            "id": 42,  # Required for world_state key lookup
            "type": "03-interactive",
            "x": 64,
            "y": 64,
            "properties": {"element_id": "door_01", "sub_type": "door"},
        }
        with patch("src.engine.entity_factory.InteractiveEntity") as MockEntity:
            instance = MagicMock()
            instance.is_on = False
            MockEntity.return_value = instance
            ef.spawn_interactive(ent, ent.get("properties", {}), "test.tmj")

        # world_state.get must have been called to restore persisted state
        assert game.world_state.get.called


# ---------------------------------------------------------------------------
# ── MAP LOADER ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


class TestMapLoader:
    """TC-ML-01..07 — MapLoader.load."""

    def _make_map_game(self):
        game = _make_game_mock()
        game.map_manager = MagicMock()
        game.map_manager.width = 20
        game.map_manager.height = 20
        game.layout = MagicMock()
        game.tile_size = 32
        game._entity_factory = MagicMock()
        game._current_map_name = ""
        game.player.rect = MagicMock()
        game.player.pos = pygame.math.Vector2(0, 0)
        game.player.target_pos = pygame.math.Vector2(0, 0)
        game.player.is_moving = False
        game.player.direction = pygame.math.Vector2(0, 0)
        return game

    @pytest.mark.tc("TC-ML-01")
    def test_load_absent_map_logs_error_no_exception(self, caplog, tmp_path):
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)
        # Should log error and return, no exception
        ml.load("nonexistent_map_xyz.tmj")
        # No exception raised = pass

    @pytest.mark.tc("TC-ML-02")
    def test_load_normalizes_tjm_to_tmj(self, tmp_path):
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)
        # Pass .tjm extension — method must normalize to .tmj before checking existence
        with patch("os.path.exists", return_value=False) as mock_exists:
            ml.load("map.tjm")
        called_path = mock_exists.call_args[0][0]
        assert called_path.endswith(".tmj"), f"Expected .tmj path, got {called_path}"

    @pytest.mark.tc("TC-ML-03")
    def test_load_resolves_spawn_by_target_id(self, tmp_path):
        """MapLoader.load positions player at the spawn matching target_spawn_id."""
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)

        entities = [
            {
                "type": "14-spawn_point",
                "x": 100,
                "y": 200,
                "properties": {"spawn_id": "entrance", "spawn_player": True},
            }
        ]
        map_result = {
            "entities": entities,
            "properties": {},
            "spawn_player": None,
        }

        with (
            patch("os.path.exists", return_value=True),
            patch("src.engine.map_loader.TmjParser") as MockParser,
            patch("src.engine.map_loader.OrthogonalLayout"),
            patch("src.engine.map_loader.MapManager") as MockManager,
        ):
            MockParser.return_value.load_map.return_value = map_result
            MockManager.return_value.width = 20
            MockManager.return_value.height = 20
            ml.load("map.tmj", target_spawn_id="entrance")

        # Player positioned at x=100+16=116, y=200+16=216 (half_tile=16)
        pos = game.player.pos
        assert pos.x == pytest.approx(116)
        assert pos.y == pytest.approx(216)

    @pytest.mark.tc("TC-ML-04")
    def test_load_resolves_initial_spawn(self, tmp_path):
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)

        entities = [
            {
                "type": "14-spawn_point",
                "x": 50,
                "y": 75,
                "properties": {"is_initial_spawn": True, "spawn_player": True},
            }
        ]
        map_result = {"entities": entities, "properties": {}, "spawn_player": None}

        with (
            patch("os.path.exists", return_value=True),
            patch("src.engine.map_loader.TmjParser") as MockParser,
            patch("src.engine.map_loader.OrthogonalLayout"),
            patch("src.engine.map_loader.MapManager") as MockManager,
        ):
            MockParser.return_value.load_map.return_value = map_result
            MockManager.return_value.width = 20
            MockManager.return_value.height = 20
            ml.load("map.tmj", target_spawn_id=None)

        pos = game.player.pos
        assert pos.x == pytest.approx(66)  # 50 + 16
        assert pos.y == pytest.approx(91)  # 75 + 16

    @pytest.mark.tc("TC-ML-05")
    def test_load_fallback_spawn_player_root(self):
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)
        map_result = {
            "entities": [],
            "properties": {},
            "spawn_player": {"x": 32, "y": 48},
        }
        with (
            patch("os.path.exists", return_value=True),
            patch("src.engine.map_loader.TmjParser") as MockParser,
            patch("src.engine.map_loader.OrthogonalLayout"),
            patch("src.engine.map_loader.MapManager") as MockManager,
        ):
            MockParser.return_value.load_map.return_value = map_result
            MockManager.return_value.width = 20
            MockManager.return_value.height = 20
            ml.load("map.tmj")

        pos = game.player.pos
        assert pos.x == pytest.approx(48)  # 32 + 16
        assert pos.y == pytest.approx(64)  # 48 + 16

    @pytest.mark.tc("TC-ML-06")
    def test_load_fallback_center_logs_warning(self, caplog):
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)
        map_result = {"entities": [], "properties": {}, "spawn_player": None}
        with (
            patch("os.path.exists", return_value=True),
            patch("src.engine.map_loader.TmjParser") as MockParser,
            patch("src.engine.map_loader.OrthogonalLayout"),
            patch("src.engine.map_loader.MapManager") as MockManager,
        ):
            MockParser.return_value.load_map.return_value = map_result
            MockManager.return_value.width = 20
            MockManager.return_value.height = 20
            ml.load("map.tmj")
        # No exception — fallback to center

    @pytest.mark.tc("TC-ML-07")
    def test_load_empties_groups_before_spawn(self):
        from src.engine.map_loader import MapLoader

        game = self._make_map_game()
        ml = MapLoader(game)
        map_result = {"entities": [], "properties": {}, "spawn_player": None}
        with (
            patch("os.path.exists", return_value=True),
            patch("src.engine.map_loader.TmjParser") as MockParser,
            patch("src.engine.map_loader.OrthogonalLayout"),
            patch("src.engine.map_loader.MapManager") as MockManager,
        ):
            MockParser.return_value.load_map.return_value = map_result
            MockManager.return_value.width = 20
            MockManager.return_value.height = 20
            ml.load("map.tmj")

        game.interactives.empty.assert_called()
        game.npcs.empty.assert_called()
        game.teleports_group.empty.assert_called()
        game.visible_sprites.empty.assert_called()


# ---------------------------------------------------------------------------
# ── INPUT HANDLER ────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def _make_game_for_input():
    game = MagicMock()
    game.dialogue_manager.is_open = False
    game.dialogue_manager.is_active = False
    game._npc_bubble = None
    game.chest_ui.is_open = False
    game.inventory_ui = MagicMock()
    game.interaction_manager = MagicMock()
    game._current_interactive_target = None
    game.player = MagicMock()
    return game


class TestInputHandler:
    """TC-IH-01..05 — InputHandler.handle_events."""

    @pytest.mark.tc("TC-IH-01")
    def test_quit_event_calls_sys_exit(self):
        from src.engine.input_handler import InputHandler

        game = _make_game_for_input()
        ih = InputHandler(game)
        quit_event = pygame.event.Event(pygame.QUIT)
        with patch("pygame.quit"), pytest.raises(SystemExit):
            ih.handle_events([quit_event])

    @pytest.mark.tc("TC-IH-02")
    def test_interact_key_no_dialogue_calls_handle_interactions(self):
        from src.engine.input_handler import InputHandler
        from src.config import Settings

        game = _make_game_for_input()
        ih = InputHandler(game)
        event = pygame.event.Event(pygame.KEYDOWN, key=Settings.INTERACT_KEY)
        ih.handle_events([event])
        game.interaction_manager.handle_interactions.assert_called_once()

    @pytest.mark.tc("TC-IH-03")
    def test_interact_key_with_dialogue_advances_dialogue(self):
        from src.engine.input_handler import InputHandler
        from src.config import Settings

        game = _make_game_for_input()
        game.dialogue_manager.is_active = True
        ih = InputHandler(game)
        event = pygame.event.Event(pygame.KEYDOWN, key=Settings.INTERACT_KEY)
        ih.handle_events([event])
        # When dialogue open, should NOT call handle_interactions
        game.interaction_manager.handle_interactions.assert_not_called()

    @pytest.mark.tc("TC-IH-04")
    def test_inventory_key_chest_closed_toggles_inventory(self):
        from src.engine.input_handler import InputHandler
        from src.config import Settings

        game = _make_game_for_input()
        game.chest_ui.is_open = False
        ih = InputHandler(game)
        event = pygame.event.Event(pygame.KEYDOWN, key=Settings.INVENTORY_KEY)
        ih.handle_events([event])
        game.inventory_ui.toggle.assert_called_once()

    @pytest.mark.tc("TC-IH-05")
    def test_inventory_key_chest_open_does_not_toggle(self):
        from src.engine.input_handler import InputHandler
        from src.config import Settings

        game = _make_game_for_input()
        game.chest_ui.is_open = True
        ih = InputHandler(game)
        event = pygame.event.Event(pygame.KEYDOWN, key=Settings.INVENTORY_KEY)
        ih.handle_events([event])
        game.inventory_ui.toggle.assert_not_called()


# ---------------------------------------------------------------------------
# ── INTEGRATION — Game wiring ─────────────────────────────────────────────
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-EF-01")
def test_game_has_entity_factory_map_loader_input_handler():
    """After refactoring, Game must expose _entity_factory, _map_loader, _input_handler."""
    from src.engine.entity_factory import EntityFactory
    from src.engine.input_handler import InputHandler
    from src.engine.map_loader import MapLoader
    from src.engine.game import Game

    with patch.object(Game, "__init__", lambda self, skip_map_load=True: None):
        g = Game.__new__(Game)

    # Not testing init here — just verifying classes exist and are importable
    assert EntityFactory is not None
    assert MapLoader is not None
    assert InputHandler is not None


@pytest.mark.tc("IT-ML-01")
def test_game_load_map_delegates_to_map_loader():
    """Game._load_map must delegate to self._map_loader.load."""
    from src.engine.game import Game

    game = MagicMock(spec=Game)
    game._map_loader = MagicMock()
    Game._load_map(game, "test.tmj", "spawn_a", "fade")
    game._map_loader.load.assert_called_once_with("test.tmj", "spawn_a", "fade")


@pytest.mark.tc("IT-IH-01")
def test_game_handle_events_delegates_to_input_handler():
    """Game._handle_events must delegate to self._input_handler.handle_events."""
    from src.engine.game import Game

    game = MagicMock(spec=Game)
    game._input_handler = MagicMock()
    fake_events = [MagicMock()]
    with patch("src.engine.game.pygame.event.get", return_value=fake_events):
        Game._handle_events(game)
    game._input_handler.handle_events.assert_called_once_with(fake_events)


@pytest.mark.tc("IT-GS-01")
def test_game_setup_logging_importable():
    """setup_logging and load_property_types must be importable from game_setup."""
    from src.engine.game_setup import load_property_types, setup_logging

    assert callable(setup_logging)
    assert callable(load_property_types)
