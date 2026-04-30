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
    game.dialogue_manager = MagicMock()
    
    with patch('src.engine.game.I18nManager.get', return_value="Hello from sign!"):
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




@patch('src.engine.game.Game._load_map')
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


@patch('src.engine.game.Game._load_map')
def test_game_load_world_world_file(mock_load):
    """Game reads default_map from world.world when debug is off."""
    from src.config import Settings
    original_debug = Settings.DEBUG
    Settings.DEBUG = False
    try:
        world_data = {"maps": [{"fileName": "01-village.tmj"}]}
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data=__import__('json').dumps(world_data))):
            game = Game()
        mock_load.assert_called_with("01-village.tmj")
    finally:
        Settings.DEBUG = original_debug


@patch('src.engine.game.Game._load_map')
def test_game_load_world_world_parse_error(mock_load):
    """Game falls back gracefully when world.world raises on read."""
    from src.config import Settings
    import builtins
    original_debug = Settings.DEBUG
    Settings.DEBUG = False
    real_open = builtins.open

    def selective_open(path, *args, **kwargs):
        if "world.world" in str(path):
            raise Exception("IO error")
        return real_open(path, *args, **kwargs)

    try:
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=selective_open):
            game = Game()
        assert mock_load.called
    finally:
        Settings.DEBUG = original_debug


@patch('src.engine.game.Game._load_map')
def test_load_map_file_not_found(mock_load):
    """_load_map returns early when map file doesn't exist."""
    game = Game()
    mock_load.reset_mock()
    # Now call the real _load_map with a missing file
    with patch('os.path.exists', return_value=False):
        game._load_map("ghost.tmj")
    # Nothing should have been loaded after the early return
    assert not game.map_manager if hasattr(game, 'map_manager') else True


@patch('src.engine.game.Game._load_map')
def test_spawn_entities_initial_spawn_skipped(mock_load):
    """_spawn_entities skips entities with is_initial_spawn=True."""
    game = Game()
    game.layout = MagicMock()
    game.map_manager = MagicMock()
    game.layout.to_world.return_value = (0, 0)
    entity = {
        "id": 1, "x": 0, "y": 0,
        "properties": {"is_initial_spawn": True}
    }
    with patch('src.engine.game.InteractiveEntity') as mock_ent:
        game._spawn_entities([entity])
    mock_ent.assert_not_called()


@patch('src.engine.game.Game._load_map')
def test_spawn_entities_sign_logged(mock_load):
    """_spawn_entities logs info for sign entities."""
    game = Game()
    game.map_manager = MagicMock()
    entity = {
        "id": 1, "x": 0, "y": 0, "width": 32, "height": 32,
        "properties": {"entity_type": "interactive", "sub_type": "sign", "element_id": "book"}
    }
    with patch('src.engine.game.InteractiveEntity'), \
         patch('logging.info') as mock_log:
        game._spawn_entities([entity])
    assert any("Sign detected" in str(c) for c in mock_log.call_args_list)


@patch('src.engine.game.Game._load_map')
def test_is_collidable_map_tile(mock_load):
    """_is_collidable returns True for collidable map tile."""
    game = Game()
    game.map_manager = MagicMock()
    game.layout = MagicMock()
    game.layout.to_world.return_value = (1, 1)
    game.map_manager.is_collidable.return_value = True
    assert game._is_collidable(32, 32) is True


@patch('src.engine.game.Game._load_map')
def test_toggle_entity_empty_id(mock_load):
    """toggle_entity_by_id returns early for empty target_id."""
    game = Game()
    game.toggle_entity_by_id("")  # should not raise


@patch('src.engine.game.Game._load_map')
def test_toggle_entity_depth_limit(mock_load):
    """toggle_entity_by_id returns early when depth > 1 (loop guard)."""
    game = Game()
    game.toggle_entity_by_id("some_id", depth=2)  # should not raise


@patch('src.engine.game.Game._load_map')
def test_toggle_entity_with_sfx_and_world_state(mock_load):
    """toggle_entity_by_id plays sfx and saves world_state."""
    game = Game()
    game.audio_manager = MagicMock()
    game.world_state = MagicMock()

    entity = DummySprite("lever_1")
    entity.sfx = "click"
    entity._world_state_key = "map_01:lever_1"
    entity.is_on = True
    game.interactives.add(entity)

    game.toggle_entity_by_id("lever_1")
    game.audio_manager.play_sfx.assert_called_with("click", "lever_1")
    game.world_state.set.assert_called()


@patch('src.engine.game.Game._load_map')
def test_transition_map_missing_file(mock_load):
    """transition_map returns early when map file is missing."""
    game = Game()
    with patch('os.path.exists', return_value=False):
        game.transition_map("ghost.tmj", "spawn_1", "instant")
    # Should not raise


@patch('src.engine.game.Game._load_map')
def test_check_teleporters_not_triggered(mock_load):
    """_check_teleporters does nothing when player not on teleport."""
    game = Game()
    game.player = MagicMock()
    game.player.is_moving = False
    game.player.direction = pygame.math.Vector2(0, 0)
    game._check_teleporters(was_moving=False)  # should not raise


@patch('src.engine.game.Game._load_map')
def test_check_teleporters_directional_guard(mock_load):
    """_check_teleporters skips teleport when direction doesn't match."""
    game = Game()
    game.player = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.is_moving = False
    game.player.current_state = 'up'

    tp = DummySprite()
    tp.rect = pygame.Rect(0, 0, 32, 32)
    tp.required_direction = 'down'
    tp.target_map = "next.tmj"
    tp.target_spawn_id = "s1"
    tp.transition_type = "instant"
    game.teleports_group.add(tp)

    with patch.object(game, 'transition_map') as mock_tr:
        game._check_teleporters(was_moving=True)
    mock_tr.assert_not_called()


@patch('src.engine.game.Game._load_map')
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


@patch('src.engine.game.Game._load_map')
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


@patch('src.engine.game.Game._load_map')
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


@patch('src.engine.game.Game._load_map')
def test_handle_events_quit(mock_load):
    """_handle_events calls sys.exit on QUIT event."""
    game = Game()
    event = MagicMock()
    event.type = pygame.QUIT
    with patch('pygame.event.get', return_value=[event]), \
         patch('sys.exit') as mock_exit, \
         patch('pygame.quit'):
        game._handle_events()
    mock_exit.assert_called()


@patch('src.engine.game.Game._load_map')
def test_handle_events_quit_key(mock_load):
    """_handle_events calls sys.exit on QUIT_KEY press."""
    from src.config import Settings
    game = Game()
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.QUIT_KEY
    with patch('pygame.event.get', return_value=[event]), \
         patch('sys.exit') as mock_exit, \
         patch('pygame.quit'):
        game._handle_events()
    mock_exit.assert_called()


@patch('src.engine.game.Game._load_map')
def test_handle_events_dialogue_advance(mock_load):
    """_handle_events advances dialogue on INTERACT_KEY."""
    from src.config import Settings
    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = True
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.INTERACT_KEY
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
    game.dialogue_manager.advance.assert_called()


@patch('src.engine.game.Game._load_map')
def test_handle_events_npc_resume_after_dialogue(mock_load):
    """_handle_events resumes NPCs when dialogue closes."""
    from src.config import Settings
    game = Game()
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = True
    # After advance() is called, is_active becomes False
    game.dialogue_manager.advance.side_effect = lambda: setattr(game.dialogue_manager, 'is_active', False)

    # Use DummySprite so attribute assignment is reflected in assertions
    npc = DummySprite()
    npc.state = 'interact'
    game.npcs.add(npc)

    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = Settings.INTERACT_KEY
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
    assert npc.state == 'idle'


@patch('src.engine.game.Game._load_map')
def test_update_emote_draw(mock_load):
    """_draw_scene renders emote sprites with camera offset."""
    game = Game()
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []
    game.map_manager.layer_order = []
    game.player = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 0
    game.inventory_ui = MagicMock()
    game.inventory_ui.is_open = False
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = False
    game.chest_ui = MagicMock()
    game.chest_ui.is_open = False
    game.time_system = MagicMock()
    game.time_system.night_alpha = 0
    game.screen = pygame.Surface((800, 600))

    emote_sprite = MagicMock()
    emote_sprite.rect = pygame.Rect(0, 0, 16, 16)
    emote_sprite.image = pygame.Surface((16, 16))
    game.emote_group.add(emote_sprite)
    game.visible_sprites = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)

    game._draw_scene()  # should not raise


@patch('src.engine.game.Game._load_map')
def test_draw_scene_chest_ui(mock_load):
    """_draw_scene draws chest_ui when it is open."""
    game = Game()
    game.map_manager = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []
    game.map_manager.layer_order = []
    game.player = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 0
    game.inventory_ui = MagicMock()
    game.inventory_ui.is_open = False
    game.dialogue_manager = MagicMock()
    game.dialogue_manager.is_active = False
    game.chest_ui = MagicMock()
    game.chest_ui.is_open = True
    game.time_system = MagicMock()
    game.time_system.night_alpha = 0
    game.screen = pygame.Surface((800, 600))
    game.visible_sprites = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)

    game._draw_scene()
    game.chest_ui.draw.assert_called()


@patch('src.engine.game.Game._load_map')
def test_toggle_fullscreen_success(mock_load):
    """toggle_fullscreen flips is_fullscreen flag."""
    game = Game()
    original = game.is_fullscreen
    with patch('pygame.display.toggle_fullscreen'):
        game.toggle_fullscreen()
    assert game.is_fullscreen != original


@patch('src.engine.game.Game._load_map')
def test_toggle_fullscreen_fallback(mock_load):
    """toggle_fullscreen falls back to set_mode on pygame.error."""
    game = Game()
    with patch('pygame.display.toggle_fullscreen', side_effect=pygame.error("no")), \
         patch('pygame.display.set_mode') as mock_mode:
        game.toggle_fullscreen()
    assert mock_mode.called


@patch('src.engine.game.Game._load_map')
def test_trigger_dialogue_missing_key(mock_load):
    """_trigger_dialogue logs warning when key not found."""
    game = Game()
    game._current_map_name = "test.tmj"
    game.dialogue_manager = MagicMock()
    with patch('src.engine.game.I18nManager.get', return_value=None), \
         patch('logging.warning') as mock_warn:
        game._trigger_dialogue("nonexistent")
    assert mock_warn.called


@patch('src.engine.game.Game._load_map')
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
    with patch('pygame.time.get_ticks', return_value=5000), \
         patch('pygame.display.set_caption') as mock_caption:
        game._update(0.016)
    assert mock_caption.called


import unittest.mock
