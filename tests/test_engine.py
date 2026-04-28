import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.game import Game
from src.engine.asset_manager import AssetManager

@patch('src.engine.game.Game._load_map')
def test_game_initialization(mock_load):
    game = Game()
    assert game.player is not None
    assert game.i18n.current_locale == "fr"
    assert not game.inventory_ui.is_open

@patch('os.path.exists', return_value=True)
@patch('src.map.tmj_parser.TmjParser.load_map')
def test_game_actual_load_map(mock_load_map, mock_exists):
    mock_load_map.return_value = {
        "width": 10, "height": 10,
        "properties": {"bgm": "test.ogg"},
        "entities": [
            {
                "id": 1, "type": "14-spawn_point", "x": 16, "y": 16,
                "properties": {"spawn_id": "spawn_2"}
            },
            {
                "id": 2, "x": 32, "y": 32,
                "properties": {"entity_type": "interactive", "sub_type": "door", "element_id": "d1"}
            },
            {
                "id": 3, "x": 48, "y": 48,
                "properties": {"type": "teleport", "target_map": "next.tmj"}
            },
            {
                "id": 4, "x": 64, "y": 64,
                "properties": {"entity_type": "npc", "sprite_sheet": "npc.png", "element_id": "n1"}
            },
            {
                "id": 5, "x": 80, "y": 80,
                "properties": {"entity_type": "object", "object_id": "apple", "sprite_sheet": "apple.png"}
            }
        ]
    }
    
    with patch('src.engine.audio.AudioManager.play_bgm') as mock_bgm, \
         patch('src.engine.game.InteractiveEntity'), \
         patch('src.engine.game.NPC'), \
         patch('src.engine.game.Teleport'), \
         patch('src.engine.game.PickupItem'):
         
        game = Game()
        assert mock_bgm.called
        
        # Test specific spawn load
        game._load_map("test.tmj", "spawn_2")
        assert game.player.pos.x == 32 # 16 + 16 (half tile)
        assert game.player.pos.y == 32

@patch('src.engine.game.Game._load_map')
def test_game_ui_toggles(mock_load):
    game = Game()
    from src.config import Settings
    
    # Toggle inventory via events
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.INVENTORY_KEY
    
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
        assert game.inventory_ui.is_open
        
    # Toggle back
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
        assert not game.inventory_ui.is_open

@patch('src.engine.game.Game._load_map')
def test_game_entity_spawning(mock_load):
    game = Game()
    # Mock a Tiled object
    mock_obj = {
        "name": "chest_1",
        "x": 100, "y": 100,
        "width": 32, "height": 32,
        "properties": {
            "entity_type": "interactive",
            "sub_type": "chest",
            "is_on": False
        }
    }
    
    with patch('src.engine.game.InteractiveEntity') as mock_ent:
        game._spawn_entities([mock_obj])
        assert mock_ent.called

def test_asset_manager_cache():
    am = AssetManager()
    am.clear_cache()
    # Mock font loading
    with patch('pygame.font.SysFont') as mock_sys:
        f1 = am.get_font(None, 20)
        f2 = am.get_font(None, 20)
        assert mock_sys.call_count == 1

def test_asset_manager_image():
    am = AssetManager()
    am.clear_cache()
    
    # 1. Fallback generation (file not found)
    with patch('os.path.exists', return_value=False):
        surf = am.get_image('fake.png', fallback=True)
        assert surf.get_size() == (32, 32)
        # Should raise error without fallback
        with pytest.raises(FileNotFoundError):
            am.get_image('fake2.png', fallback=False)
            
    # 2. Pygame error fallback
    with patch('os.path.exists', return_value=True), \
         patch('pygame.image.load', side_effect=pygame.error("Invalid format")):
        surf = am.get_image('bad.png', fallback=True)
        assert surf.get_size() == (32, 32)
        with pytest.raises(pygame.error):
            am.get_image('bad2.png', fallback=False)
            
    # 3. Successful load and cache hit
    mock_surf = pygame.Surface((10, 10))
    with patch('os.path.exists', return_value=True), \
         patch('pygame.image.load') as mock_load:
        
        mock_load.return_value.convert_alpha.return_value = mock_surf
        surf1 = am.get_image('good.png')
        surf2 = am.get_image('good.png')
        
        assert surf1 == mock_surf
        assert surf1 == surf2
        assert mock_load.call_count == 1

def test_asset_manager_font_error():
    am = AssetManager()
    am.clear_cache()
    with patch('pygame.font.Font', side_effect=Exception("Font missing")):
        font = am.get_font('missing.ttf', 12)
        assert font is not None # Returns fallback None font
@patch('src.engine.game.Game._load_map')
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

@patch('src.engine.game.Game._load_map')
def test_game_draw_loop(mock_load):
    game = Game()
    # Mock subsystems
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []
    game.player = MagicMock()
    game.player.pos = pygame.math.Vector2(0, 0)
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.inventory_ui = MagicMock()
    game.dialogue_manager = MagicMock()
    game.screen = pygame.Surface((800, 600))
    
    # _draw takes no arguments
    game._draw()
    
    assert game.map_manager.get_visible_chunks.called

@patch('src.engine.game.Game._load_map')
def test_game_trigger_dialogue(mock_load):
    game = Game()
    game._current_map_name = "test_map.tmj"
    game.hud._lang = {"dialogues": {"test_map-sign_1": "Hello from sign!"}}
    game.dialogue_manager = MagicMock()
    
    game._trigger_dialogue("sign_1", "Test Title")
    game.dialogue_manager.start_dialogue.assert_called_with("Hello from sign!", title="Test Title")

class DummySprite(pygame.sprite.Sprite):
    def __init__(self, element_id=""):
        super().__init__()
        self.element_id = element_id
        self.target_id = None
        self.is_on = False
        self.sfx = None
        self.rect = pygame.Rect(0, 0, 32, 32)
        self.interact_called = False
    def interact(self, player):
        self.interact_called = True

@patch('src.engine.game.Game._load_map')
def test_game_toggle_entity(mock_load):
    game = Game()
    game.audio_manager = MagicMock()
    game.world_state = MagicMock()
    
    mock_entity = DummySprite("door_1")
    mock_entity.target_id = "switch_1"
    mock_entity.is_on = True
    
    mock_entity2 = DummySprite("switch_1")
    
    game.interactives.add(mock_entity, mock_entity2)
    
    # Test toggling
    game.toggle_entity_by_id("door_1")
    assert mock_entity.interact_called
    assert mock_entity2.interact_called # Because door_1 targets switch_1

@patch('src.engine.game.Game._load_map')
def test_game_check_teleporters(mock_load):
    game = Game()
    game.player = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.is_moving = False
    game.player.current_state = 'any'
    
    mock_teleport = DummySprite()
    mock_teleport.target_map = "next_map.tmj"
    mock_teleport.target_spawn_id = "spawn_2"
    mock_teleport.transition_type = "fade"
    
    game.teleports_group.add(mock_teleport)
    
    with patch.object(game, 'transition_map') as mock_transition:
        game._check_teleporters(was_moving=True)
        mock_transition.assert_called_with("next_map.tmj", "spawn_2", "fade")

@patch('src.engine.game.Game._load_map')
def test_game_transition_map_fade(mock_load):
    game = Game()
    game.clock = MagicMock()
    game.clock.tick.return_value = 16
    game.time_system = MagicMock()
    game.time_system.night_alpha = 0
    game.screen = pygame.Surface((800, 600))
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []
    
    with patch('os.path.exists', return_value=True):
        game.transition_map("next_map.tmj", "spawn_2", "fade")
        assert mock_load.called

@patch('src.engine.game.Game._load_map')
def test_game_is_collidable(mock_load):
    game = Game()
    game.map_manager = MagicMock()
    game.layout = MagicMock()
    game.layout.to_world.return_value = (0, 0)
    
    # 1. Map boundary collision
    game.map_manager.check_collision.return_value = True
    assert game._is_collidable(pygame.math.Vector2(0, 0), MagicMock()) is True
    game.map_manager.check_collision.return_value = False
    
    # 2. Obstacles collision
    mock_obs = DummySprite()
    mock_obs.rect = pygame.Rect(-10, -10, 20, 20)
    game.obstacles_group.add(mock_obs)
    
    requester = MagicMock()
    assert game._is_collidable(pygame.math.Vector2(0, 0), requester) is True
    
    # 3. NPC collision
    mock_obs.rect = pygame.Rect(100, 100, 20, 20) # Move obstacle out
    mock_npc = DummySprite()
    mock_npc.rect = pygame.Rect(-10, -10, 20, 20)
    game.npcs.add(mock_npc)
    assert game._is_collidable(pygame.math.Vector2(0, 0), requester) is True
    
    # 4. Player collision
    mock_npc.rect = pygame.Rect(100, 100, 20, 20) # Move NPC out
    game.player = MagicMock()
    game.player.rect = pygame.Rect(-10, -10, 20, 20)
    assert game._is_collidable(pygame.math.Vector2(0, 0), requester) is True

@patch('src.engine.game.Game._load_map')
def test_game_draw_layers(mock_load):
    game = Game()
    game.map_manager = MagicMock()
    game.map_manager.layer_order = ["layer_0", "layer_1"]
    
    # Mock pre-rendered surfaces
    surf = pygame.Surface((32, 32))
    game.map_manager.get_layer_surface.return_value = surf
    game.map_manager.is_foreground_layer.side_effect = lambda layer, limit: layer == "layer_1"
    game.map_manager.get_visible_chunks.return_value = [pygame.Rect(0, 0, 32, 32)]
    
    game.visible_sprites = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = pygame.Surface((800, 600))
    game.player = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1
    
    # Background (should hit layer_0)
    game._draw_background()
    assert game.map_manager.get_layer_surface.called
    
    # Foreground (should hit layer_1 and interactives)
    game.map_manager.tiles = {
        1: MagicMock(image=pygame.Surface((32, 32)), occluded_image=pygame.Surface((32, 32)))
    }
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 2)] # px, py, tile_id, depth
    
    mock_interactive = DummySprite()
    mock_interactive.is_light_source = True
    mock_interactive.draw_effects = MagicMock()
    game.interactives.add(mock_interactive)
    game.time_system = MagicMock()
    game.time_system.night_alpha = 100
    game.player.image = pygame.Surface((32, 32))
    game.inventory_ui = MagicMock()
    
    game._draw_scene()
    assert mock_interactive.draw_effects.called



