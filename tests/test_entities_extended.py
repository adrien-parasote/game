import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.entities.npc import NPC
from src.entities.interactive import InteractiveEntity

def test_npc_behavior():
    game = MagicMock()
    # Mock spritesheet and images
    game.asset_manager.get_image.return_value = pygame.Surface((128, 128))
    
    npc = NPC(pos=(100, 100), groups=pygame.sprite.Group(), element_id="villager_1")
    npc.name = "villager"
    
    # Test random movement attempt
    npc.update(0.016)
    
def test_interactive_entity_states():
    game = MagicMock()
    game.asset_manager.get_image.return_value = pygame.Surface((128, 128))
    
    obj = InteractiveEntity(
        pos=(200, 200),
        groups=[MagicMock()],
        sub_type="chest",
        sprite_sheet="chest.png",
        is_on=False,
        sfx="chest_open",
        element_id="chest_1"
    )
    
    assert obj.is_on is False
    
    # Toggle
    obj.interact(MagicMock())
    assert obj.is_on is True
    
    # Update animation
    obj.update(0.1)
