import pygame
import pytest
from src.entities.groups import CameraGroup
from src.config import Settings

class MockSprite(pygame.sprite.Sprite):
    def __init__(self, y_pos):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.rect = self.image.get_rect(topleft=(0, y_pos))
        self.pos = pygame.math.Vector2(0, y_pos)

def test_camera_group_sorting():
    # We need to initialize pygame logic for surfaces
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    group = CameraGroup()
    s1 = MockSprite(200)
    s2 = MockSprite(100)
    s3 = MockSprite(150)
    
    group.add(s1, s2, s3)
    
    # Check if sorting works as expected (s2, s3, s1)
    sorted_sprites = group.get_sorted_sprites()
    assert sorted_sprites[0] == s2
    assert sorted_sprites[1] == s3
    assert sorted_sprites[2] == s1
    
    pygame.quit()

def test_camera_offset_calculation():
    pygame.display.set_mode((800, 600), pygame.HIDDEN)
    group = CameraGroup()
    group.set_world_size(2000, 2000)
    
    # Target in center of map (400, 300)
    # Camera should offset by -(target - screen_center)
    # Screen center is (400, 300)
    # Offset should be (0, 0)
    target = MockSprite(300)
    target.rect.center = (400, 300)
    
    offset = group.calculate_offset(target)
    assert offset == pygame.math.Vector2(0, 0)
    
    # Move target to (500, 400)
    target.rect.center = (500, 400)
    offset = group.calculate_offset(target)
    # Screen center is (400, 300)
    # Offset = (400 - 500, 300 - 400) = (-100, -100)
    assert offset == pygame.math.Vector2(-100, -100)
    
    pygame.quit()

from src.entities.player import Player
from src.entities.base import BaseEntity

def test_player_movement():
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    # Player at (16, 16) - Center of first 32px tile
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 32)) for _ in range(16)]):
        layer_path = 'src.graphics.spritesheet.SpriteSheet'
        with patch(layer_path + '.__init__', return_value=None):
            player = Player((16, 16), speed=100)
    
    # 1. Trigger move Right
    player.direction.x = 1
    player.update(0.01) # Start move
    assert player.is_moving is True
    # If TileSize=32, target is 16 + 32 = 48
    assert player.target_pos == pygame.math.Vector2(48, 16)
    
    # 2. Complete move
    player.update(1.0) # Move far enough
    assert player.is_moving is False
    assert player.pos == pygame.math.Vector2(48, 16)
    
    pygame.quit()

from unittest.mock import MagicMock

def test_camera_group_culling():
    pygame.display.set_mode((100, 100), pygame.HIDDEN)
    group = CameraGroup()
    
    # Sprite 1: Inside the 100x100 view (offset is 0,0)
    s_in = MockSprite(10) # Rect(0, 10, 32, 32)
    # Sprite 2: Outside the view
    s_out = MockSprite(200) # Rect(0, 200, 32, 32)
    
    group.add(s_in, s_out)
    group.offset = pygame.math.Vector2(0, 0)
    
    # Mock surface
    mock_surface = MagicMock()
    mock_surface.get_size.return_value = (100, 100)
    mock_surface.get_rect.return_value = pygame.Rect(0, 0, 100, 100)
    
    group.custom_draw(mock_surface)
    
    # Verify blit calls
    # Should be called once for s_in, zero for s_out
    assert mock_surface.blit.call_count == 1
    
    pygame.quit()

from unittest.mock import patch

def test_player_input_grid_logic():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 32)) for _ in range(16)]):
        layer_path = 'src.graphics.spritesheet.SpriteSheet'
        with patch(layer_path + '.__init__', return_value=None):
            player = Player((32, 32))
    
    class MockKeys(dict):
        def __getitem__(self, key):
            return self.get(key, False)
            
    # Mock keys: UP and RIGHT held
    mock_keys = MockKeys()
    mock_keys[Settings.MOVE_UP] = True
    mock_keys[Settings.MOVE_RIGHT] = True
    
    with patch('pygame.key.get_pressed', return_value=mock_keys):
        player.input()
        player.update(0.01) # Trigger start_move
        
    # Expected: Vertical priority (UP)
    assert player.direction.y == -1
    assert player.direction.x == 0
    
    # Verify move triggered
    assert player.is_moving is True
    # Start: 16 -> Target: 16 - 32 = -16. Clamped to 16.
    assert player.target_pos.y == 16 

    # 2. Mock keys: RIGHT only
    player.is_moving = False
    mock_keys_right = MockKeys({Settings.MOVE_RIGHT: True})
    with patch('pygame.key.get_pressed', return_value=mock_keys_right):
        player.input()
        player.update(0.01)
    assert player.direction.x == 1
    assert player.direction.y == 0
    
    # 3. Mock keys: None
    player.is_moving = False
    mock_keys_none = MockKeys()
    with patch('pygame.key.get_pressed', return_value=mock_keys_none):
        player.input()
    assert player.direction.x == 0
    assert player.direction.y == 0
    
    pygame.quit()

def test_camera_clamping_logic():
    # Setup: 800x600 screen
    pygame.display.set_mode((800, 600), pygame.HIDDEN)
    group = CameraGroup()
    
    # 1. Large World (2000x2000)
    # width=2000, height=2000
    group.set_world_size(2000, 2000)
    
    # Target spawn at center (400, 300) -> Offset should be (0,0) as it's the start
    target = MockSprite(300)
    target.rect.center = (400, 300)
    group.calculate_offset(target)
    assert group.offset == pygame.math.Vector2(0, 0)
    
    # Target at left edge (10, 300) -> Offset still 0
    target.rect.center = (10, 300)
    group.calculate_offset(target)
    assert group.offset == pygame.math.Vector2(0, 0)
    
    # Target at far right (1990, 300) 
    # Max offset should be -(2000 - 800) = -1200
    target.rect.center = (1990, 300)
    group.calculate_offset(target)
    assert group.offset.x == -1200
    
    # 2. Small World (400x400)
    # Should be centered in 800x600 screen
    # Offset X = (800 - 400) // 2 = 200
    # Offset Y = (600 - 400) // 2 = 100
    group.set_world_size(400, 400)
    group.calculate_offset(target)
    assert group.offset == pygame.math.Vector2(200, 100)
    
    pygame.quit()

def test_entity_boundary_clamping():
    pygame.init()
    pygame.display.set_mode((800, 600), pygame.HIDDEN)
    
    # Reset Setting to default 32 for accurate testing regardless of test order
    from src.config import Settings
    Settings.MAP_SIZE = 32
    
    # World size = 32 * 32 = 1024
    # Entity size = 32 -> Half = 16
    
    # 1. West Boundary: Start at 16, move Left. Target should be 16.
    ent = BaseEntity((16, 100))
    ent.speed = 1000 # Fast for instant reach in tests
    ent.direction.x = -1
    ent.move(1.0) # Start and finish move
    assert ent.pos.x == 16
    
    # 2. East Boundary: Start at 1008 (Center of last tile), move Right. Max = 1024 - 16 = 1008.
    ent = BaseEntity((1008, 100))
    ent.speed = 1000
    ent.direction.x = 1
    ent.move(1.0)
    assert ent.pos.x == 1008
    
    # 3. North Boundary
    ent = BaseEntity((100, 16))
    ent.speed = 1000
    ent.direction.y = -1
    ent.move(1.0)
    assert ent.pos.y == 16
    
    # 4. South Boundary
    ent = BaseEntity((100, 1008))
    ent.speed = 1000
    ent.direction.y = 1
    ent.move(1.0)
    assert ent.pos.y == 1008
    
    pygame.quit()

def test_player_hitbox_dimensions():
    """TC-B-03: Player hitbox size must be exactly 32x32."""
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 48)) for _ in range(16)]):
        layer_path = 'src.graphics.spritesheet.SpriteSheet'
        with patch(layer_path + '.__init__', return_value=None):
            player = Player((16, 16))
            
    # The physical rect used for collisions/movement must remain 32x32
    assert player.rect.size == (32, 32)
    # The image is 32x48
    assert player.image.get_size() == (32, 48)
    
    pygame.quit()
