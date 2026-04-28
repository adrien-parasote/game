import pytest
import pygame
import os
from unittest.mock import MagicMock, patch
from src.entities.pickup import PickupItem
from src.ui.inventory import InventoryUI
from src.ui.dialogue import DialogueManager
from src.engine.game import Game
from src.config import Settings

@pytest.fixture(autouse=True)
def setup_pygame():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((800, 600))
    yield
    pygame.quit()

def test_pickup_item_initialization(tmp_path):
    # Setup dummy spritesheet for pickup
    sprite_dir = tmp_path / "assets" / "images" / "sprites"
    sprite_dir.mkdir(parents=True)
    img_path = sprite_dir / "test_item.png"
    surf = pygame.Surface((32, 32))
    pygame.image.save(surf, str(img_path))
    
    with patch('src.entities.pickup.os.path.dirname') as mock_dirname:
        # Hack to point dirname to tmp_path/src/entities
        mock_dirname.return_value = str(tmp_path / "src" / "entities")
        
        pickup = PickupItem((100, 100), [], "test_item", "test_item.png", 5)
        assert pickup.item_id == "test_item"
        assert pickup.quantity == 5
        assert pickup.type == "object"

def test_inventory_ui_basic():
    player_mock = MagicMock()
    player_mock.inventory.items = [{"item_id": "test", "quantity": 1}]
    # Mocking frames for draw preview
    player_mock.frames = [pygame.Surface((32, 32))] * 16
    
    with patch('src.ui.inventory.InventoryUI._load_asset', return_value=pygame.Surface((32, 32))):
        inv_ui = InventoryUI(player_mock)
        assert not inv_ui.is_open
        
        inv_ui.toggle()
        assert inv_ui.is_open
        
        # Process event (ESCAPE)
        inv_ui.toggle() # toggle back
        assert not inv_ui.is_open

def test_dialogue_manager_pagination():
    game_mock = MagicMock()
    game_mock.screen = pygame.Surface((800, 600))
    
    with patch('src.ui.dialogue.DialogueManager._load_assets'):
        dm = DialogueManager()
        assert not dm.is_active
        
        dm.start_dialogue("This is a very long text that should hopefully wrap.", title="Test Title")
        assert dm.is_active
        assert dm.title == "Test Title"
        
        # Fast forward
        dm.advance()
        assert dm._is_page_complete is True
        
        # Close
        dm.advance()
        assert not dm.is_active
        
def test_inventory_ui_tabs_and_hover():
    player_mock = MagicMock()
    item_mock = MagicMock()
    item_mock.quantity = 1
    item_mock.icon = None
    item_mock.id = "test"
    player_mock.inventory.get_item_at.return_value = item_mock
    player_mock.frames = [pygame.Surface((32, 32))] * 16
    
    with patch('src.ui.inventory.InventoryUI._load_asset', return_value=pygame.Surface((32, 32))):
        inv_ui = InventoryUI(player_mock)
        inv_ui.is_open = True
        
        # Test tab switching
        inv_ui.set_tab(1)
        assert inv_ui.active_tab == 1
        
        # Test hover detection
        inv_ui.update_hover((0, 0))
        
        # Test draw (smoke test)
        screen = pygame.Surface((800, 600))
        inv_ui.draw(screen)

        # Test input
        event_mouse = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
        inv_ui.handle_input(event_mouse)
        # Test input
        for key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN]:
            event_key = pygame.event.Event(pygame.KEYDOWN, key=key)
            inv_ui.handle_input(event_key)
        
        # Test tab switching
        inv_ui.handle_input(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))) # Should hit a tab area
        
        # Test draw (smoke test)
        screen = pygame.Surface((800, 600))
        inv_ui.draw(screen)

def test_game_draw_methods():
    with patch('src.engine.game.Game._load_map'):
        with patch('src.engine.game.Game._setup_logging'):
            with patch('pygame.display.set_mode', return_value=pygame.Surface((800, 600))):
                game = Game()
                # Mock subsystems
                game.map_manager = MagicMock()
                game.map_manager.tiles = {}
                game.map_manager.layers = {}
                
                screen = pygame.Surface((800, 600))
                game.screen = screen
                
                game._draw_background()
                game._draw_foreground()
                game._draw_hud()
                game._draw_scene()
