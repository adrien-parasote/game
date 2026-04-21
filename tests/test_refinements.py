import pytest
import pygame
from unittest.mock import Mock, patch
from src.engine.game import Game, _get_property

@pytest.fixture
def mock_pygame_display():
    with patch('pygame.display.set_mode'), \
         patch('pygame.display.set_caption'), \
         patch('pygame.display.get_surface'):
        yield

class TestRefinements:
    
    def test_strict_teleport_detection(self, mock_pygame_display):
        """TC-006: Only detect teleporters via property type='teleport'."""
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}):
            game = Game()
            game.teleports_group = pygame.sprite.Group()
            
            # 1. Legacy Check (Should FAIL to spawn as teleporter)
            legacy_ent = {
                "type": "13-teleport",
                "x": 0, "y": 0, "width": 32, "height": 32,
                "properties": {} # No custom type property
            }
            game._spawn_entities([legacy_ent])
            assert len(game.teleports_group) == 0
            
            # 2. Proper Property Check (Should SUCCEED)
            proper_ent = {
                "type": "object",
                "x": 32, "y": 32, "width": 32, "height": 32,
                "properties": {"type": "teleport"}
            }
            game._spawn_entities([proper_ent])
            assert len(game.teleports_group) == 1

    def test_teleport_required_direction_any(self, mock_pygame_display):
        """TC-010: Teleport with 'any' direction triggers from all directions."""
        from src.entities.teleport import Teleport
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}):
            game = Game()
            tp = Teleport(pygame.Rect(0, 0, 32, 32), [], "map.tmj", "spawn", "instant", "any")
            game.teleports_group.add(tp)
            
            # mock player move finished
            game.player.rect.center = (16, 16)
            game.player.current_state = "up"
            
            with patch.object(game, 'transition_map') as mock_trans:
                game._check_teleporters(was_moving=True)
                mock_trans.assert_called()

    def test_teleport_required_direction_strict(self, mock_pygame_display):
        """TC-008, TC-009: Teleport direction guard."""
        from src.entities.teleport import Teleport
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}):
            game = Game()
            tp = Teleport(pygame.Rect(0, 0, 32, 32), [], "map.tmj", "spawn", "instant", "down")
            game.teleports_group.add(tp)
            
            game.player.rect.center = (16, 16)
            
            # Facing up -> No trigger
            game.player.current_state = "up"
            with patch.object(game, 'transition_map') as mock_trans:
                game._check_teleporters(was_moving=True)
                mock_trans.assert_not_called()
                
            # Facing down -> Trigger
            game.player.current_state = "down"
            with patch.object(game, 'transition_map') as mock_trans:
                game._check_teleporters(was_moving=True)
                mock_trans.assert_called()

    def test_activation_directional_adjacency(self, mock_pygame_display):
        """TC-007: activate_from_anywhere requires facing."""
        from src.entities.interactive import InteractiveEntity
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}), \
             patch('src.entities.interactive.SpriteSheet') as mock_sheet_class:
            
            # Setup mock sheet to return a valid surface on get_size()
            mock_sheet = mock_sheet_class.return_value
            mock_sheet.valid = True
            mock_sheet.sheet = pygame.Surface((128, 128))
            mock_sheet.load_grid_by_size.return_value = [pygame.Surface((32, 32))] * 16
            mock_sheet.last_cols = 4 # for InteractiveEntity getattr logic
            
            game = Game()
            # Object at (100, 100)
            obj = InteractiveEntity((100, 100), [], "lamp", "sheet.png", activate_from_anywhere=True)
            game.interactives.add(obj)
            
            # Player at (132, 100) -> To the right of object. Must face LEFT.
            game.player.pos = pygame.math.Vector2(132, 100)
            
            # Case 1: Facing RIGHT (away) -> Fail
            game.player.current_state = "right"
            with patch.object(obj, 'interact') as mock_interact, \
                 patch('pygame.key.get_pressed', return_value={pygame.K_e: True, pygame.K_SPACE: False}):
                import src.config as config
                config.Settings.INTERACT_KEY = pygame.K_e
                game._interaction_cooldown = 0
                game.player.is_moving = False
                game._handle_interactions()
                mock_interact.assert_not_called()
                
            # Case 2: Facing LEFT (toward) -> Success
            game.player.current_state = "left"
            game._interaction_cooldown = 0
            with patch.object(obj, 'interact') as mock_interact, \
                 patch('pygame.key.get_pressed', return_value={pygame.K_e: True, pygame.K_SPACE: False}):
                game._handle_interactions()
                mock_interact.assert_called()
    def test_is_on_initialization(self, mock_pygame_display):
        """Bug Fix: Verify is_on=True correctly initializes frame and physics."""
        from src.entities.interactive import InteractiveEntity
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}), \
             patch('src.entities.interactive.SpriteSheet') as mock_sheet_class:
            
            mock_sheet = mock_sheet_class.return_value
            mock_sheet.valid = True
            mock_sheet.sheet = pygame.Surface((128, 128))
            mock_sheet.load_grid_by_size.return_value = [pygame.Surface((32, 32))] * 16
            mock_sheet.last_cols = 4
            
            obstacles = pygame.sprite.Group()
            
            # Case 1: Door starting ON (and is_passable=True)
            door = InteractiveEntity((100, 100), [], "door", "sheet.png", 
                                     is_on=True, is_passable=True, 
                                     start_row=0, end_row=3, obstacles_group=obstacles)
            
            # Should be at end_row
            assert door.frame_index == 3.0
            # Should NOT be in obstacles because it's ON and passable
            assert door not in obstacles
            
            # Case 2: Chest starting ON (is_passable=False)
            chest = InteractiveEntity((200, 200), [], "chest", "sheet.png", 
                                      is_on=True, is_passable=False, 
                                      start_row=0, end_row=3, obstacles_group=obstacles)
            # Should be at end_row
            assert chest.frame_index == 3.0
            # Should BE in obstacles because it's not passable even if ON
            assert chest in obstacles

    def test_interaction_right_direction(self, mock_pygame_display):
        """Bug Fix: Verify right-facing interaction coordinate check."""
        from src.entities.interactive import InteractiveEntity
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}), \
             patch('src.entities.interactive.SpriteSheet') as mock_sheet_class:
            
            mock_sheet = mock_sheet_class.return_value
            mock_sheet.valid = True
            mock_sheet.sheet = pygame.Surface((128, 128))
            mock_sheet.load_grid_by_size.return_value = [pygame.Surface((32, 32))] * 16
            mock_sheet.last_cols = 4
            
            game = Game()
            # Object facing RIGHT (position=1) at (100, 100)
            # This means it's interactable from its Western side (x < obj_x)
            obj = InteractiveEntity((100, 100), [], "chest", "sheet.png", position=1)
            game.interactives.add(obj)
            
            # Player at (80, 116) -> To the LEFT (West) of object. Facing RIGHT.
            # dist = 116 - 80 = 36 (< 45)
            game.player.pos = pygame.math.Vector2(80, 116)
            game.player.current_state = "right"
            
            game._interaction_cooldown = 0
            game.player.is_moving = False
            with patch.object(obj, 'interact') as mock_interact, \
                 patch('pygame.key.get_pressed', return_value={pygame.K_e: True, pygame.K_SPACE: False}):
                import src.config as config
                config.Settings.INTERACT_KEY = pygame.K_e
                game._handle_interactions()
                mock_interact.assert_called()

    def test_teleport_intent_trigger(self, mock_pygame_display):
        """Bug Fix: Verify teleport triggers on intent (movement start)."""
        from src.entities.teleport import Teleport
        with patch('src.engine.game.os.path.exists', return_value=True), \
             patch('src.map.tmj_parser.TmjParser.load_map', return_value={"entities": []}):
            game = Game()
            tp = Teleport(pygame.Rect(0, 0, 32, 32), [], "map.tmj", "spawn", "instant", "any")
            game.teleports_group.add(tp)
            
            # Scenario: Player is ALREADY on the tile, and STARTS moving
            game.player.rect.center = (16, 16)
            game.player.is_moving = True # Moving now
            
            with patch.object(game, 'transition_map') as mock_trans:
                # was_moving=False, is_moving=True -> Intent trigger
                game._check_teleporters(was_moving=False)
                mock_trans.assert_called()
