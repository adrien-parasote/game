import pygame

class EmoteSprite(pygame.sprite.Sprite):
    """
    A sprite representing an emote bubble that rises 15px over its lifetime.
    """
    def __init__(self, frames: list[pygame.Surface], player, groups: pygame.sprite.Group, duration: float = 0.6):
        super().__init__(groups)
        self.frames = frames
        self.image = self.frames[0]
        self.player = player
        self.rect = self.image.get_rect(centerx=player.rect.centerx, bottom=player.rect.top)
        self.duration = duration
        self.elapsed = 0.0
        self.animation_speed = len(self.frames) / self.duration


    def update(self, dt: float):
        """Update the position relative to the player and handle self-destruction."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.kill()
            return

        # Animation logic
        frame_idx = int(self.elapsed * self.animation_speed)
        if frame_idx < len(self.frames):
            self.image = self.frames[frame_idx]

        # Linear interpolation for the rise effect
        progress = self.elapsed / self.duration
        rise_offset = progress * 15
        
        # Follow player + rise offset
        self.rect.centerx = self.player.rect.centerx
        self.rect.bottom = self.player.rect.top - int(rise_offset)

