import pytest
from unittest.mock import patch, MagicMock
import pygame
from src.engine.game import Game
from src.entities.interactive import InteractiveEntity

@pytest.fixture
def dummy_display():
    pygame.init()
    pygame.display.set_mode((100, 100))
    yield
    pygame.quit()

@pytest.fixture
def base_props():
    return {
        "id": 42,
        "x": 10,
        "y": 10,
        "properties": {
            "is_animated": True,
            "target": "door_1",
            "sprite": {
                "sprite_sheet": "chest.png",
                "entity_type": "interactive"
            },
            "interactive_object": {
                "is_on": False,
                "sprite": {
                    "sub_type": "torch",
                    "halo_size": 20
                }
            }
        }
    }

def test_get_nested_prop(base_props):
    # Tests the _get_property standalone
    from src.engine.game import _get_property
    
    props = base_props["properties"]
    
    # 1. Direct hit
    assert _get_property(props, "is_animated") is True
    # 2. interactive_object -> sprite
    assert _get_property(props, "sub_type") == "torch"
    assert _get_property(props, "halo_size") == 20
    # 3. sprite
    assert _get_property(props, "sprite_sheet") == "chest.png"
    assert _get_property(props, "entity_type") == "interactive"
    # 4. interactive_object
    assert _get_property(props, "is_on") is False
    # 5. Default fallback
    assert _get_property(props, "non_existent", "hello") == "hello"

def test_interactive_entity_target_args(dummy_display):
    groups = [pygame.sprite.Group()]
    entity = InteractiveEntity(
        pos=(0,0), groups=groups, sub_type="test", sprite_sheet="test.png",
        target_id="chest_01", target="door_01"
    )
    assert hasattr(entity, "target_id")
    assert entity.target_id == "chest_01"
    assert hasattr(entity, "target")
    assert entity.target == "door_01"

@patch("src.map.tmj_parser.TmjParser")
def test_game_spawn_nested_interactive(mock_parser_class, dummy_display):
    # Mock parser results
    mock_parser = MagicMock()
    mock_parser.load_map.return_value = {
        "width": 10, "height": 10, "spawn_player": {"x": 50, "y": 50},
        "entities": [
            {
                "id": 99,
                "x": 32, "y": 32,
                "properties": {
                    "sprite": {
                        "entity_type": "interactive",
                        "sprite_sheet": "00-doors.png"
                    },
                    "interactive_object": {
                        "is_passable": True
                    },
                    # Missing target_id directly, should fallback to entity id
                    "target": "chest_abc"
                }
            }
        ]
    }
    mock_parser_class.return_value = mock_parser
    
    game = Game()
    # Check that interactive entity was spawned
    assert len(game.interactives) == 1
    entity = game.interactives.sprites()[0]
    
    assert entity.sub_type == "unknown"  # Not provided in mockup
    assert entity.is_passable is True    # Found in nested props
    assert getattr(entity, "target_id", None) == "99"  # Fallback to Tiled id as string
    assert getattr(entity, "target", None) == "chest_abc"
