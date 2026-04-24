import pygame
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.config import Settings
from src.entities.player import Player
from src.engine.audio import AudioManager

pygame.init()
screen = pygame.display.set_mode((800, 600))

class MockGame:
    def __init__(self):
        self.screen = screen
        self.audio_manager = AudioManager()
        self.visible_sprites = pygame.sprite.Group() # Simplistic for mock
        self.visible_sprites.offset = pygame.math.Vector2(0, 0)
        self.emote_group = pygame.sprite.Group()
        self.player = Player((400, 300), self.visible_sprites)
        self.player.audio_manager = self.audio_manager
        self.player.emote_manager.emote_group = self.emote_group

def test_emote():
    game = MockGame()
    print("Triggering interact emote...")
    game.player.playerEmote('interact')
    
    clock = pygame.time.Clock()
    for _ in range(120): # 2 seconds
        dt = clock.tick(60) / 1000.0
        game.emote_group.update(dt)
        
        screen.fill((30, 30, 30))
        # Draw player
        pygame.draw.rect(screen, (0, 255, 0), game.player.rect)
        
        # Draw emotes
        for sprite in game.emote_group:
            screen.blit(sprite.image, sprite.rect)
            
        pygame.display.flip()
        
    print("Test complete.")
    pygame.quit()

if __name__ == "__main__":
    # This requires assets to be present.
    try:
        test_emote()
    except Exception as e:
        print(f"Error: {e}")
        pygame.quit()
