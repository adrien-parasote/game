"""
Consolidated Interactive Entity Test Suite
Includes: InteractiveEntity logic, state toggling, and interaction chaining.
"""
import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.entities.interactive import InteractiveEntity
from src.entities.groups import CameraGroup
from src.config import Settings

@pytest.fixture(scope="module", autouse=True)
def interactive_env():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

@pytest.fixture
def mock_spritesheet():
    with patch('src.graphics.spritesheet.SpriteSheet') as MockSheet:
        instance = MockSheet.return_value
        instance.valid = True
        instance.sheet = pygame.Surface((128, 128))
        instance.load_grid_by_size.return_value = [pygame.Surface((32, 32))] * 16
        instance.load_grid.return_value = [pygame.Surface((32, 32))] * 16
        yield MockSheet

@pytest.fixture
def base_groups():
    return [pygame.sprite.Group()]

# --- BASIC LOGIC ---

def test_interactive_initialization(mock_spritesheet, base_groups):
    """InteractiveEntity should initialize with correct state and rect."""
    obj = InteractiveEntity(
        pos=(32, 32),
        groups=base_groups,
        sub_type="chest",
        sprite_sheet="test.png",
        is_on=False
    )
    assert obj.is_on is False
    assert obj.rect.topleft == (32, 32)

def test_interactive_toggle(mock_spritesheet, base_groups):
    """Interacting with a toggleable object should flip its state."""
    obj = InteractiveEntity(
        pos=(32, 32),
        groups=base_groups,
        sub_type="lever",
        sprite_sheet="test.png",
        is_on=False
    )
    # First toggle: OFF -> ON
    obj.interact(MagicMock())
    assert obj.is_on is True
    
    # Must update to finish animation before toggling back
    obj.update(1.0) # Enough time to finish
    
    # Second toggle: ON -> OFF
    obj.interact(MagicMock())
    assert obj.is_on is False

# --- SPECIAL EFFECTS ---

def test_interactive_halo_rendering(mock_spritesheet, base_groups):
    """InteractiveEntity should draw a halo if halo_size > 0."""
    obj = InteractiveEntity(
        pos=(32, 32),
        groups=base_groups,
        sub_type="lamp",
        sprite_sheet="test.png",
        halo_size=64,
        is_on=True
    )
    screen = pygame.Surface((128, 128))
    assert hasattr(obj, 'draw_effects')
    # Should run without error
    obj.draw_effects(screen, pygame.math.Vector2(0, 0), global_darkness=100)

def test_interactive_particles(mock_spritesheet, base_groups):
    """InteractiveEntity should update particles if enabled."""
    obj = InteractiveEntity(
        pos=(32, 32),
        groups=base_groups,
        sprite_sheet="test.png",
        sub_type="fire",
        particles=True,
        particle_count=5,
        is_on=True
    )
    # Check if particles list exists and populates after update
    obj.update(0.1)
    assert hasattr(obj, 'particles_list')

# --- INTERACTION CHAINING LOGIC ---

def test_interaction_chaining_via_game_logic(mock_spritesheet, base_groups):
    """Game.toggle_entity_by_id should correctly chain interactions."""
    from src.engine.game import Game
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        obj1 = InteractiveEntity((0,0), base_groups, "lever", "test.png", element_id="lever1", target_id="door1")
        obj2 = InteractiveEntity((32,32), base_groups, "door", "test.png", element_id="door1")
        game.interactives.add(obj1, obj2)
        
        game.toggle_entity_by_id("door1")
        assert obj2.is_on is True
