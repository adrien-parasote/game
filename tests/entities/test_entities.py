import pytest
import pygame
from unittest.mock import patch, MagicMock
from src.entities.player import Player
from src.entities.npc import NPC
from src.entities.base import BaseEntity
from src.config import Settings
from src.entities.interactive import InteractiveEntity
from src.entities.emote import EmoteManager
from src.entities.emote_sprite import EmoteSprite

"""
Consolidated Entity Logic Test Suite
Includes: BaseEntity, Player, NPC, InteractiveEntity, and Emote logic.
"""

@pytest.fixture
def mock_spritesheet():
    """Mock SpriteSheet to avoid disk I/O and handle headless mode."""
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 48)) for _ in range(16)]):
        with patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None):
            yield

# --- BaseEntity Tests ---

def test_entity_initialization():
    """Entity should start at correct position with fixed size."""
    ent = BaseEntity((16, 16))
    assert ent.pos == pygame.math.Vector2(16, 16)
    assert ent.rect.size == (32, 32)

def test_grid_movement_logic():
    """Entity should snap to grid targets."""
    # Prevent MAP_SIZE pollution from other tests
    original_map_size = Settings.MAP_SIZE
    Settings.MAP_SIZE = 100
    try:
        ent = BaseEntity((16, 16))
        ent.speed = 1000
        ent.direction = pygame.math.Vector2(1, 0)
        ent.move(0.01)
        assert ent.is_moving is True
        assert ent.target_pos == pygame.math.Vector2(48, 16)
        ent.move(1.0)
        assert ent.is_moving is False
        assert ent.pos == pygame.math.Vector2(48, 16)
    finally:
        Settings.MAP_SIZE = original_map_size

def test_boundary_clamping():
    """Entity should not move outside map boundaries."""
    Settings.MAP_SIZE = 32
    ent = BaseEntity((16, 100))
    ent.direction = pygame.math.Vector2(-1, 0)
    ent.move(1.0)
    assert ent.pos.x == 16
    ent = BaseEntity((1008, 100))
    ent.direction = pygame.math.Vector2(1, 0)
    ent.move(1.0)
    assert ent.pos.x == 1008

# --- Player & NPC Tests ---

def test_player_input_priority(mock_spritesheet):
    """Player input should prioritize vertical movement."""
    player = Player((16, 16))
    class MockKeys:
        def __getitem__(self, k):
            return k in (Settings.MOVE_UP, Settings.MOVE_RIGHT)
    with patch('pygame.key.get_pressed', return_value=MockKeys()):
        player.input()
        player.update(0.01)
    assert player.direction.y == -1
    assert player.direction.y == -1
    assert player.direction.x == 0

def test_player_footstep_audio(mock_spritesheet):
    """Player plays footstep sound based on terrain material when animation frame hits 1 or 3."""
    player = Player((16, 16))
    player.audio_manager = MagicMock()
    mock_game = MagicMock()
    # Provide a mock map manager that returns "stone"
    mock_game.map_manager.get_terrain_material_at.return_value = "stone"
    player._game = mock_game  # We'll inject this during interaction or update
    
    player.is_moving = True
    player.frame_index = 0.9  # about to cross 1.0
    
    with patch('src.engine.game.Game', return_value=mock_game):
        player.game = mock_game
        # Fast animation speed -> 1.0/0.15 = 6.66 fps
        # With dt=0.02, frame_index += 0.133, so 0.9 + 0.133 = 1.033 -> triggers frame 1
        player._update_animation(0.02)
        
    player.audio_manager.play_sfx.assert_called_with("04-footstep_stone", source_id="player", volume_multiplier=0.3)
    
    # Passing frame 2 shouldn't trigger
    player.audio_manager.play_sfx.reset_mock()
    player.frame_index = 1.9
    player._update_animation(0.02)
    player.audio_manager.play_sfx.assert_not_called()
    
    # Passing frame 3 should trigger
    player.frame_index = 2.9
    player._update_animation(0.02)
    player.audio_manager.play_sfx.assert_called_with("04-footstep_stone", source_id="player", volume_multiplier=0.3)

    # If no material found, fallback to "04-footstep"
    player.audio_manager.play_sfx.reset_mock()
    mock_game.map_manager.get_terrain_material_at.return_value = None
    player.frame_index = 0.9
    player._update_animation(0.02)
    player.audio_manager.play_sfx.assert_called_with("04-footstep", source_id="player", volume_multiplier=0.3)

def test_npc_ai_state_machine(mock_spritesheet):
    """NPC transitions between idle and wandering."""
    npc = NPC((48, 48), wander_radius=5)
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    with patch('random.choice', return_value=pygame.math.Vector2(1, 0)):
        npc.update(0.01)
    assert npc.state == 'wander'
    assert npc.is_moving is True


def test_npc_interact_faces_initiator_horizontal(mock_spritesheet):
    """NPC faces initiator when horizontal delta is dominant."""
    npc = NPC((48, 48), wander_radius=5)
    initiator = MagicMock()
    # Initiator is to the right of NPC
    initiator.pos = pygame.math.Vector2(200, 48)
    result = npc.interact(initiator)
    assert npc.state == 'interact'
    assert npc.current_facing == 'right'
    assert result == npc.element_id


def test_npc_interact_faces_initiator_left(mock_spritesheet):
    """NPC faces left when initiator is to the left."""
    npc = NPC((48, 48), wander_radius=5)
    initiator = MagicMock()
    initiator.pos = pygame.math.Vector2(0, 48)  # left
    npc.interact(initiator)
    assert npc.current_facing == 'left'


def test_npc_interact_faces_initiator_down(mock_spritesheet):
    """NPC faces down when initiator is below."""
    npc = NPC((48, 48), wander_radius=5)
    initiator = MagicMock()
    initiator.pos = pygame.math.Vector2(48, 200)  # below
    npc.interact(initiator)
    assert npc.current_facing == 'down'


def test_npc_interact_faces_initiator_up(mock_spritesheet):
    """NPC faces up when initiator is above."""
    npc = NPC((48, 48), wander_radius=5)
    initiator = MagicMock()
    initiator.pos = pygame.math.Vector2(48, 0)  # above
    npc.interact(initiator)
    assert npc.current_facing == 'up'


def test_npc_interact_freezes_ai(mock_spritesheet):
    """NPC in interact state skips process_ai."""
    npc = NPC((48, 48), wander_radius=5)
    npc.state = 'interact'
    npc._action_timer = 100.0  # would normally trigger
    npc._action_cooldown = 0
    npc.process_ai(0.1)  # should do nothing
    # Timer is NOT incremented by process_ai (it returns early)
    assert npc._action_timer == 100.0


def test_npc_start_move_zero_direction(mock_spritesheet):
    """start_move returns early when direction is zero vector."""
    npc = NPC((48, 48), wander_radius=5)
    npc.direction = pygame.math.Vector2(0, 0)
    npc.start_move()  # should not raise, is_moving stays False
    assert npc.is_moving is False


def test_npc_start_move_radius_exceeded(mock_spritesheet):
    """start_move blocks move when target exceeds wander_radius."""
    npc = NPC((48, 48), wander_radius=0)  # radius = 0 tiles
    npc.state = 'wander'
    npc.direction = pygame.math.Vector2(1, 0)
    npc.start_move()
    assert npc.state == 'idle'
    assert npc.direction == pygame.math.Vector2(0, 0)


def test_npc_start_move_blocked_by_collision_reverts_idle(mock_spritesheet):
    """start_move reverts to idle when move is blocked by collision (line 75)."""
    npc = NPC((48, 48), wander_radius=10)
    npc.state = 'wander'
    npc.direction = pygame.math.Vector2(1, 0)
    # Patch super().start_move() so is_moving stays False (simulates collision)
    with patch.object(type(npc).__bases__[0], 'start_move', lambda self: None):
        npc.start_move()
    assert npc.state == 'idle'


def test_npc_process_ai_outside_radius_stays_idle(mock_spritesheet):
    """process_ai keeps NPC idle when chosen direction exceeds radius."""
    npc = NPC((48, 48), wander_radius=0)
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    # Force a direction that would exceed radius
    with patch('random.choice', return_value=pygame.math.Vector2(1, 0)):
        npc.process_ai(0.01)
    assert npc.state == 'idle'


def test_npc_process_ai_directions_left(mock_spritesheet):
    """process_ai sets facing to left."""
    npc = NPC((200, 200), wander_radius=10)
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    with patch('random.choice', return_value=pygame.math.Vector2(-1, 0)):
        npc.process_ai(0.01)
    assert npc.current_facing == 'left'


def test_npc_process_ai_directions_up(mock_spritesheet):
    """process_ai sets facing to up."""
    npc = NPC((200, 200), wander_radius=10)
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    with patch('random.choice', return_value=pygame.math.Vector2(0, -1)):
        npc.process_ai(0.01)
    assert npc.current_facing == 'up'


def test_npc_process_ai_stay_idle_choice(mock_spritesheet):
    """process_ai keeps NPC idle when zero vector is chosen."""
    npc = NPC((48, 48), wander_radius=5)
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    with patch('random.choice', return_value=pygame.math.Vector2(0, 0)):
        npc.process_ai(0.01)
    assert npc.state == 'idle'


def test_npc_animation_idle_frame(mock_spritesheet):
    """Animation frame stays at 0 when not moving."""
    npc = NPC((48, 48), wander_radius=5)
    npc.is_moving = False
    npc.frame_index = 2.5
    npc._update_animation(0.1)
    assert npc.frame_index == 0.0


def test_npc_update_invisible_skips(mock_spritesheet):
    """update() returns early when is_visible is False."""
    npc = NPC((48, 48), wander_radius=5)
    npc.is_visible = False
    npc._action_timer = 100.0
    npc.update(1.0)  # should not raise or process AI
    # Timer stays unchanged (no update ran)
    assert npc._action_timer == 100.0


def test_npc_interact_timer_reverts_to_idle(mock_spritesheet):
    """NPC reverts from interact to idle when interact timer expires."""
    npc = NPC((48, 48), wander_radius=5)
    npc.state = 'interact'
    npc._action_timer = 0.0
    npc._action_cooldown = 0.1
    npc.update(0.5)  # timer (0.5) >= cooldown (0.1)
    assert npc.state == 'idle'

# --- InteractiveEntity Tests ---

def test_interactive_entity_states():
    """InteractiveEntity should toggle state on interaction."""
    obj = InteractiveEntity(
        pos=(200, 200), groups=[], sub_type='chest', 
        sprite_sheet='chest.png', is_on=False, element_id='chest_1'
    )
    assert obj.is_on is False
    obj.interact(MagicMock())
    assert obj.is_on is True

def test_interactive_entity_missing_sprite():
    """InteractiveEntity should fallback to dummy surfaces if sprite is missing."""
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid_by_size', return_value=[]), \
         patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None), \
         patch('os.path.exists', return_value=False):
        obj = InteractiveEntity(
            pos=(100, 100), groups=[], sub_type='sign',
            sprite_sheet='', is_on=False
        )
        assert len(obj.frames) == 16

def test_interactive_entity_halo_and_particles():
    """Verify halo creation and particle updates."""
    obj = InteractiveEntity(
        pos=(100, 100), groups=[], sub_type='torch',
        sprite_sheet='torch.png', is_on=True, halo_size=50,
        particles=True, particle_count=10
    )
    assert len(obj.light_mask_cache) == 10
    assert obj.is_light_source is True
    
    # Run update to generate particles and flicker
    obj.update(0.16)
    assert obj.f_alpha > 0
    # Add a particle manually to test drawing and decay
    obj.particles_list.append({
        'x': 100, 'y': 100, 'vx': 0, 'vy': -1,
        'life': 1.0, 'max_life': 1.0, 'size': 2, 'phase': 0
    })
    obj.update(0.16) # Decays life
    
    surf = pygame.Surface((200, 200))
    obj.draw_effects(surf, pygame.math.Vector2(0, 0), global_darkness=100)
    assert len(obj.particles_list) > 0 # Should still be alive

def test_interactive_entity_door_obstacles():
    """Doors should manage the obstacles group based on their state."""
    obstacles = pygame.sprite.Group()
    obj = InteractiveEntity(
        pos=(100, 100), groups=[], sub_type='door',
        sprite_sheet='door.png', is_on=False, obstacles_group=obstacles,
        is_passable=True
    )
    # Closed door is an obstacle
    assert obj in obstacles
    
    # Open door removes from obstacle
    obj.restore_state({'is_on': True})
    assert obj.is_on is True
    assert obj not in obstacles

    # Close door adds back
    obj.restore_state({'is_on': False})
    assert obj in obstacles

# --- Emote System Tests (Step 3 TDD) ---

def test_emote_manager_initialization():
    player = MagicMock()
    with patch('src.entities.emote.SpriteSheet'):
        em = EmoteManager(player)
        assert 'interact' in em.emote_map
        assert 'frustration' in em.emote_map


def test_emote_manager_fallback_path():
    """EmoteManager tries fallback path when primary doesn't exist."""
    player = MagicMock()
    def exists_side_effect(path):
        return "sprites" in path and "04-emotes" in path  # fallback path only
    with patch('os.path.exists', side_effect=exists_side_effect), \
         patch('src.entities.emote.SpriteSheet') as mock_sheet:
        mock_sheet.return_value.load_grid.return_value = [pygame.Surface((16, 16))] * 40
        em = EmoteManager(player)
    assert hasattr(em, 'frames_grid')


def test_emote_manager_spritesheet_error():
    """EmoteManager handles SpriteSheet load error gracefully."""
    player = MagicMock()
    with patch('os.path.exists', return_value=True), \
         patch('src.entities.emote.SpriteSheet', side_effect=Exception("bad sheet")):
        em = EmoteManager(player)
    assert em.frames == []


def test_emote_trigger_no_group():
    """trigger() returns early and logs warning when emote_group is None."""
    player = MagicMock()
    with patch('src.entities.emote.SpriteSheet') as mock_sheet:
        mock_sheet.return_value.load_grid.return_value = [pygame.Surface((16, 16))] * 40
        em = EmoteManager(player)
    em.emote_group = None
    em.trigger('love')  # should not raise


def test_emote_trigger_unknown_name():
    """trigger() returns early when emote name is unknown."""
    player = MagicMock()
    group = MagicMock()
    with patch('src.entities.emote.SpriteSheet') as mock_sheet:
        mock_sheet.return_value.load_grid.return_value = [pygame.Surface((16, 16))] * 40
        em = EmoteManager(player)
    em.emote_group = group
    em.trigger('nonexistent')  # should not raise
    group.empty.assert_not_called()


def test_emote_manager_chaining():
    """Triggering a new emote should clear the previous one (TC-EM-01)."""
    player = MagicMock()
    player.audio_manager = MagicMock()
    group = MagicMock()
    with patch('src.entities.emote.SpriteSheet') as mock_sheet:
        mock_sheet.return_value.load_grid.return_value = [pygame.Surface((16, 16))] * 40
        em = EmoteManager(player)
        em.emote_group = group
        em.trigger('love')
        assert group.empty.called # Overlap killing verified

def test_emote_sprite_duration():
    """Emote duration should be 0.6s by default (TC-EM-02)."""
    frames = [pygame.Surface((16, 16))] * 8
    target = MagicMock()
    target.rect = pygame.Rect(0, 0, 32, 32)
    group = pygame.sprite.Group()
    es = EmoteSprite(frames, target, group)
    assert es.duration == 0.6
    es.update(0.3)
    assert es in group
    es.update(0.4)
    assert es not in group # Expired after 0.7s total
# --- Teleport & Pickup Tests ---

def test_teleport_logic():
    from src.entities.teleport import Teleport
    rect = pygame.Rect(0, 0, 32, 32)
    tp = Teleport(rect, [], "target.tmj", "spawn_1", "fade")
    assert tp.target_map == "target.tmj"
    assert tp.target_spawn_id == "spawn_1"

def test_pickup_logic():
    from src.entities.pickup import PickupItem
    pickup = PickupItem((100, 100), [], "potion_red", "potion_red.png", 5)
    assert pickup.item_id == "potion_red"
    assert pickup.quantity == 5
