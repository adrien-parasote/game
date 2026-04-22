import pytest
import pygame
from src.engine.world_state import WorldState
from src.entities.interactive import InteractiveEntity
from src.engine.game import Game
from unittest.mock import patch, mock_open

class TestWorldState:
    def test_make_key(self):
        """WS-001: make_key generates correct string format"""
        assert WorldState.make_key("00-spawn.tmj", 58) == "00-spawn_58"
        assert WorldState.make_key("01-castel.tmj", 12) == "01-castel_12"

    def test_set_get_roundtrip(self):
        """WS-002: set and get functions correctly persist and return state"""
        ws = WorldState()
        key = "test_map_01"
        ws.set(key, {'is_on': True})
        assert ws.get(key) == {'is_on': True}

    def test_get_inexistent_key(self):
        """WS-003: get inexistent key returns None"""
        ws = WorldState()
        assert ws.get("nonexistent_key") is None

    @patch('src.entities.interactive.SpriteSheet')
    def test_restore_state_saved_on(self, mock_spritesheet):
        mock_spritesheet.return_value.valid = False
        mock_spritesheet.return_value.last_cols = 4
        """WS-004: Entity spawn with saved ON state overrwrites initial state"""
        # Create an object initially set to OFF
        entity = InteractiveEntity(
            pos=(0, 0),
            groups=[pygame.sprite.Group()],
            sub_type="chest",
            sprite_sheet="dummy.png",
            start_row=0,
            end_row=3,
            is_on=False,  # Initially OFF
            is_animated=False
        )
        assert entity.is_on is False
        assert getattr(entity, 'frame_index', -1) == 0.0

        # Restore ON state
        entity.restore_state({'is_on': True})
        assert entity.is_on is True
        assert getattr(entity, 'frame_index', -1) == 3.0

    @patch('src.entities.interactive.SpriteSheet')
    def test_restore_state_saved_off(self, mock_spritesheet):
        mock_spritesheet.return_value.valid = False
        mock_spritesheet.return_value.last_cols = 4
        """WS-005: Entity spawn with saved OFF state overrwrites initial state"""
        # Create an object initially set to ON
        entity = InteractiveEntity(
            pos=(0, 0),
            groups=[pygame.sprite.Group()],
            sub_type="chest",
            sprite_sheet="dummy.png",
            start_row=0,
            end_row=3,
            is_on=True,  # Initially ON
            is_animated=False
        )
        assert entity.is_on is True
        assert getattr(entity, 'frame_index', -1) == 3.0

        # Restore OFF state
        entity.restore_state({'is_on': False})
        assert entity.is_on is False
        assert getattr(entity, 'frame_index', -1) == 0.0

    @patch('src.entities.interactive.SpriteSheet')
    def test_standard_interact_saves_state(self, mock_spritesheet):
        mock_spritesheet.return_value.valid = False
        mock_spritesheet.return_value.last_cols = 4
        """WS-006: Standard interact saves state to the WorldState registry in Game."""
        # Need to simulate game interaction
        # We can create an entity, assign a _world_state_key, and check if game._handle_interactions updates state
        # The easiest approach is to mock a Game and player.
        with patch('src.engine.game.Game._load_map'):
            game = Game()
            game.world_state.clear()
            
            entity = InteractiveEntity(
                pos=(100, 100),
                groups=[game.interactives],
                sub_type="chest",
                sprite_sheet="dummy.png",
                is_on=False,
                is_animated=False
            )
            entity._world_state_key = "test_map_42"
            entity.direction_str = "up"
            
            # Place player adjacently and facing it
            game.player.pos = pygame.math.Vector2(100, 130)
            game.player.current_state = 'up'
            game.player.is_moving = False
            
            # Mock pygame keys
            from src.config import Settings
            keys = {Settings.INTERACT_KEY: True, pygame.K_SPACE: False}
            with patch('pygame.key.get_pressed', return_value=keys):
                game._handle_interactions()
                
            # It should have flipped to ON and saved
            assert entity.is_on is True
            assert game.world_state.get("test_map_42") == {'is_on': True}

    @patch('src.map.tmj_parser.TmjParser.load_map')
    @patch('src.engine.game.os.path.exists', return_value=True)
    def test_map_reload_maintains_state(self, mock_exists, mock_load_map):
        """WS-007: Map reload maintains state, testing A -> B -> A lifecycle"""
        fake_map_data = {
            "width": 10,
            "height": 10,
            "layers": {},
            "tiles": {},
            "spawn_player": None,
            "entities": [
                {
                    "id": 99,
                    "x": 0, "y": 0,
                    "type": "11-interactive_object",
                    "properties": {"entity_type": "interactive", "sub_type": "chest", "is_on": False}
                }
            ]
        }
        mock_load_map.return_value = fake_map_data
        
        with patch('builtins.open', mock_open(read_data='{"maps": [{"fileName": "A.tmj"}]}')):
            game = Game()
            game._load_map("A.tmj")
            
            # Assume there is one chest in the interactives group
            chest = list(game.interactives)[0]
            assert chest.is_on is False
            
            # Player turns it on
            chest._world_state_key = WorldState.make_key("A.tmj", 99)
            chest.is_on = True
            game.world_state.set(chest._world_state_key, {'is_on': True})
            
            # Player transitions to map B.
            # Then back to Map A
            game._load_map("B.tmj")
            game._load_map("A.tmj")
            
            reloaded_chest = list(game.interactives)[0]
            # State should be restored to ON despite JSON saying False
            assert reloaded_chest.is_on is True

    @patch('src.entities.interactive.SpriteSheet')
    def test_interaction_chaining_saves_state(self, mock_spritesheet):
        mock_spritesheet.return_value.valid = False
        mock_spritesheet.return_value.last_cols = 4
        """WS-008: Interaction chaining via toggle_entity_by_id saves state"""
        with patch('src.engine.game.Game._load_map'):
            game = Game()
            game.world_state.clear()
            
            entity = InteractiveEntity(
                pos=(100, 100),
                groups=[game.interactives],
                sub_type="door",
                sprite_sheet="dummy.png",
                is_on=False,
                is_animated=False,
                element_id="secret_door"
            )
            entity._world_state_key = "test_map_door_43"

            # Trigger remotely
            game.toggle_entity_by_id("secret_door")
            
            assert entity.is_on is True
            assert game.world_state.get("test_map_door_43") == {'is_on': True}
