import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.interaction import InteractionManager
from src.config import Settings
from src.entities.player import Player
from src.entities.npc import NPC
from src.entities.interactive import InteractiveEntity
from src.engine.audio import AudioManager
from src.entities.groups import CameraGroup
'\nTests for InteractionManager logic.\n'

@pytest.fixture(scope='module', autouse=True)
def interaction_env():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

@pytest.fixture
def mock_game():
    game = MagicMock()
    game.player = MagicMock(spec=Player)
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.npcs = pygame.sprite.Group()
    game.interactives = pygame.sprite.Group()
    return game

def test_interaction_cooldown_interactions(mock_game):
    """InteractionManager should respect cooldown timer."""
    im = InteractionManager(mock_game)
    im._interaction_cooldown = 0.5
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
        mock_game._trigger_dialogue.assert_not_called()
    im.update(0.6)
    assert im._interaction_cooldown == 0

def test_npc_interaction_trigger_interactions(mock_game):
    """Interacting with NPC in front of player should trigger dialogue."""
    im = InteractionManager(mock_game)
    npc = MagicMock(spec=NPC)
    npc.rect = pygame.Rect(100, 132, 32, 32)
    npc.interact.return_value = 'npc_msg'
    npc.name = 'Test NPC'
    mock_game.npcs.add(npc)
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    npc.interact.assert_called_once_with(mock_game.player)
    mock_game._trigger_dialogue.assert_called_once_with('npc_msg', title='Test NPC')

def test_object_interaction_facing_interactions(mock_game):
    """Interaction with object should require correct orientation."""
    im = InteractionManager(mock_game)
    obj = MagicMock(spec=InteractiveEntity)
    obj.direction_str = 'down'
    obj.sub_type = 'chest'
    obj.interact.return_value = None
    mock_game.interactives.add(obj)
    mock_game.player.pos = pygame.math.Vector2(100, 140)
    obj.pos = pygame.math.Vector2(100, 120)
    mock_game.player.current_state = 'up'
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    assert obj.interact.call_count == 1
    obj.interact.reset_mock()
    mock_game.player.pos = pygame.math.Vector2(100, 100)
    mock_game.player.current_state = 'down'
    im._interaction_cooldown = 0
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    assert obj.interact.call_count == 0

def test_door_relaxation_logic_interactions(mock_game):
    """Open doors can be closed from the 'wrong' side."""
    im = InteractionManager(mock_game)
    door = MagicMock(spec=InteractiveEntity)
    door.pos = pygame.math.Vector2(100, 120)
    door.direction_str = 'down'
    door.sub_type = 'door'
    door.is_on = True
    mock_game.interactives.add(door)
    mock_game.player.current_state = 'down'
    mock_game.player.pos = pygame.math.Vector2(100, 100)
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    assert door.interact.call_count == 1

def test_interaction_manager_failed_emote_interactions_extended(mock_game):
    im = InteractionManager(mock_game)
    im._check_npc_interactions = MagicMock(return_value=False)
    im._check_object_interactions = MagicMock(return_value=False)
    im._check_pickup_interactions = MagicMock(return_value=False)
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        Settings.ENABLE_FAILED_INTERACTION_EMOTE = True
        im.handle_interactions()
        assert mock_game.player.playerEmote.called

def test_interaction_manager_npc_interaction_interactions_extended(mock_game):
    im = InteractionManager(mock_game)
    npc = MagicMock()
    npc.rect = pygame.Rect(90, 120, 32, 32)
    mock_game.npcs = [npc]
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
        assert npc.interact.called

def test_interaction_manager_proximity_emotes_interactions_extended(mock_game):
    im = InteractionManager(mock_game)
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 110)
    obj.direction_str = 'up'
    obj.sub_type = 'chest'
    obj.is_on = False
    mock_game.interactives = [obj]
    im.update(0.1)
    assert mock_game.player.playerEmote.called

def test_audio_manager_sfx_audio_interaction():
    with patch('pygame.mixer.Sound'):
        am = AudioManager()
        am.play_sfx('test_sfx')
        am.play_sfx('missing_sfx')

def test_audio_manager_bgm_audio_interaction():
    with patch('pygame.mixer.music.load'):
        with patch('pygame.mixer.music.play'):
            with patch('os.path.exists', return_value=True):
                am = AudioManager()
                am.play_bgm('test_bgm')
                assert am.current_bgm == 'test_bgm'

def test_interaction_manager_failed_interaction_audio_interaction():
    game = MagicMock()
    game.player.rect.center = (100, 100)
    game.player.current_facing = 'down'
    game.player.is_moving = False
    game.npcs = pygame.sprite.Group()
    game.interactives = pygame.sprite.Group()
    game.pickups = pygame.sprite.Group()
    game.emote_group = MagicMock()
    with patch('pygame.key.get_pressed', return_value={pygame.K_SPACE: True, Settings.INTERACT_KEY: True}):
        with patch('src.config.Settings.ENABLE_FAILED_INTERACTION_EMOTE', True):
            im = InteractionManager(game)
            im.handle_interactions()
            game.player.playerEmote.assert_called_with('question')
'\nConsolidated Interactive Entity Test Suite\nIncludes: InteractiveEntity logic, state toggling, and interaction chaining.\n'

@pytest.fixture(scope='module', autouse=True)
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

def test_interactive_initialization_interactive_entities(mock_spritesheet, base_groups):
    """InteractiveEntity should initialize with correct state and rect."""
    obj = InteractiveEntity(pos=(32, 32), groups=base_groups, sub_type='chest', sprite_sheet='test.png', is_on=False)
    assert obj.is_on is False
    assert obj.rect.topleft == (32, 32)

def test_interactive_toggle_interactive_entities(mock_spritesheet, base_groups):
    """Interacting with a toggleable object should flip its state."""
    obj = InteractiveEntity(pos=(32, 32), groups=base_groups, sub_type='lever', sprite_sheet='test.png', is_on=False)
    obj.interact(MagicMock())
    assert obj.is_on is True
    obj.update(1.0)
    obj.interact(MagicMock())
    assert obj.is_on is False

def test_interactive_halo_rendering_interactive_entities(mock_spritesheet, base_groups):
    """InteractiveEntity should draw a halo if halo_size > 0."""
    obj = InteractiveEntity(pos=(32, 32), groups=base_groups, sub_type='lamp', sprite_sheet='test.png', halo_size=64, is_on=True)
    screen = pygame.Surface((128, 128))
    assert hasattr(obj, 'draw_effects')
    obj.draw_effects(screen, pygame.math.Vector2(0, 0), global_darkness=100)

def test_interactive_particles_interactive_entities(mock_spritesheet, base_groups):
    """InteractiveEntity should update particles if enabled."""
    obj = InteractiveEntity(pos=(32, 32), groups=base_groups, sprite_sheet='test.png', sub_type='fire', particles=True, particle_count=5, is_on=True)
    obj.update(0.1)
    assert hasattr(obj, 'particles_list')

def test_interaction_chaining_via_game_logic_interactive_entities(mock_spritesheet, base_groups):
    """Game.toggle_entity_by_id should correctly chain interactions."""
    from src.engine.game import Game
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        obj1 = InteractiveEntity((0, 0), base_groups, 'lever', 'test.png', element_id='lever1', target_id='door1')
        obj2 = InteractiveEntity((32, 32), base_groups, 'door', 'test.png', element_id='door1')
        game.interactives.add(obj1, obj2)
        game.toggle_entity_by_id('door1')
        assert obj2.is_on is True