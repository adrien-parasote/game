import pygame
import pytest
from src.entities.groups import CameraGroup

@pytest.fixture
def setup_pygame():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    yield
    pygame.quit()

def test_y_sorting(setup_pygame):
    """TC-R-01: Sprites with larger Y are drawn later."""
    group = CameraGroup()
    
    # Sprite A (Bottom=216) - Rect(84, 184, 32, 32). Center is (100, 200)
    s1 = pygame.sprite.Sprite(group)
    s1.image = pygame.Surface((32, 32))
    s1.rect = s1.image.get_rect(center=(100, 200))
    
    # Sprite B (Bottom=116)
    s2 = pygame.sprite.Sprite(group)
    s2.image = pygame.Surface((32, 32))
    s2.rect = s2.image.get_rect(center=(100, 100))
    
    sorted_sprites = group.get_sorted_sprites()
    # s2 should be first (Y=100 < Y=200)
    assert sorted_sprites[0] == s2
    assert sorted_sprites[1] == s1

def test_frustum_culling_sprites(setup_pygame):
    """TC-R-02: Sprites outside the viewport are not blitted."""
    group = CameraGroup()
    group.set_world_size(2000, 2000)
    screen = pygame.display.get_surface()
    
    # Sprite in view
    s_in = pygame.sprite.Sprite(group)
    s_in.image = pygame.Surface((32, 32))
    s_in.rect = s_in.image.get_rect(center=(100, 100))
    
    # Sprite out of view (X=1500 > 1280)
    s_out = pygame.sprite.Sprite(group)
    s_out.image = pygame.Surface((32, 32))
    s_out.rect = s_out.image.get_rect(center=(1500, 100))
    
    class SurfaceWrapper:
        def __init__(self, surface):
            self.surface = surface
            self.blitted_rects = []
        def blit(self, source, dest, area=None, special_flags=0):
            self.blitted_rects.append(dest)
            return self.surface.blit(source, dest, area, special_flags)
        def get_rect(self):
            return self.surface.get_rect()
            
    wrapper = SurfaceWrapper(screen)
    group.offset = pygame.math.Vector2(0, 0) # No offset
    group.custom_draw(wrapper)
    
    # Only s_in should be blitted
    assert len(wrapper.blitted_rects) == 1

def test_visual_anchoring(setup_pygame):
    """TC-R-03: Visual Anchoring of tall sprites."""
    group = CameraGroup()
    group.offset = pygame.math.Vector2(0, 0)
    
    # Sprite: Image is 32x48, Rect is 32x32 at (0,0)
    s = pygame.sprite.Sprite(group)
    s.image = pygame.Surface((32, 48))
    s.rect = pygame.Rect(0, 0, 32, 32)
    s.rect.topleft = (100, 100) # bottomright = (132, 132)
    
    screen = pygame.display.get_surface()
    
    class SurfaceWrapper:
        def __init__(self, surface):
            self.surface = surface
            self.blitted_rects = []
        def blit(self, source, dest, area=None, special_flags=0):
            # dest is the topleft position passed to blit
            self.blitted_rects.append(dest)
            return self.surface.blit(source, dest, area, special_flags)
        def get_rect(self):
            return self.surface.get_rect()
            
    wrapper = SurfaceWrapper(screen)
    group.custom_draw(wrapper)
    
    # We expect the image to be drawn so it extends 16px upwards from the rect.
    # topleft should be (100, 100 - 16) = (100, 84).
    # Since offset is (0,0), it should be printed at (100, 84).
    assert len(wrapper.blitted_rects) == 1
    assert wrapper.blitted_rects[0] == (100, 84)
