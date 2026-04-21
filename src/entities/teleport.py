import pygame

class Teleport(pygame.sprite.Sprite):
    """
    Invisible logical entity representing a map teleportation zone.
    """
    def __init__(self, rect: pygame.Rect, groups: list, target_map: str, target_spawn_id: str, transition_type: str = "instant"):
        super().__init__(groups)
        self.rect = rect
        self.target_map = target_map
        self.target_spawn_id = target_spawn_id
        self.transition_type = transition_type
        # Used for collision detection but not rendered
        self.image = pygame.Surface((self.rect.width, self.rect.height))
        self.image.fill((255, 0, 255))
        self.image.set_alpha(0)
