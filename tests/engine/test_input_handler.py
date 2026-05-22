"""Tests for InputHandler (input_handler.py)."""

import sys
from unittest.mock import MagicMock, call, patch

import pygame
import pytest

from src.config import Settings
from src.engine.input_handler import InputHandler


def _make_game():
    """Minimal game mock satisfying InputHandler's interface."""
    game = MagicMock()
    game.inventory_ui.is_open = False
    game.chest_ui.is_open = False
    game.dialogue_manager.is_active = False
    game._npc_bubble = None
    game.npcs = []
    return game


class TestInputHandlerDispatch:
    def test_quit_event_exits(self):
        """pygame.QUIT → pygame.quit() + sys.exit()."""
        game = _make_game()
        handler = InputHandler(game)
        event = pygame.event.Event(pygame.QUIT)
        with patch("pygame.quit") as mock_quit, patch("sys.exit") as mock_exit:
            handler._dispatch(event)
            assert mock_quit.call_count == 1
            assert mock_exit.call_count == 1

    def test_keydown_interact_delegates(self):
        """KEYDOWN INTERACT_KEY → _handle_interact_key called."""
        game = _make_game()
        handler = InputHandler(game)
        event = pygame.event.Event(pygame.KEYDOWN, {"key": Settings.INTERACT_KEY})
        handler._dispatch(event)
        assert game.interaction_manager.handle_interactions.call_count == 1

    def test_inventory_open_routes_event(self):
        """Ligne 54 : quand inventory_ui.is_open, handle_input est appelé."""
        game = _make_game()
        game.inventory_ui.is_open = True
        handler = InputHandler(game)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (0, 0), "button": 1})
        handler._dispatch(event)
        assert game.inventory_ui.handle_input.call_count == 1
        assert game.inventory_ui.handle_input.call_args == call(event)

    def test_chest_open_routes_event(self):
        """Ligne 57 : quand chest_ui.is_open, handle_event est appelé."""
        game = _make_game()
        game.chest_ui.is_open = True
        handler = InputHandler(game)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (0, 0), "button": 1})
        handler._dispatch(event)
        assert game.chest_ui.handle_event.call_count == 1
        assert game.chest_ui.handle_event.call_args == call(event)


class TestHandleInteractKey:
    def test_inventory_open_short_circuits(self):
        """Ligne 71 : inventory ouvert → retour immédiat sans interact."""
        game = _make_game()
        game.inventory_ui.is_open = True
        handler = InputHandler(game)
        handler._handle_interact_key()
        assert game.interaction_manager.handle_interactions.call_count == 0

    def test_npc_bubble_advances(self):
        """Ligne 74-75 : _npc_bubble present → _advance_npc_bubble appelé."""
        game = _make_game()
        game._npc_bubble = MagicMock()
        handler = InputHandler(game)
        handler._handle_interact_key()
        assert game._advance_npc_bubble.call_count == 1

    def test_dialogue_advances(self):
        """Ligne 78 : dialogue actif → _advance_box_dialogue."""
        game = _make_game()
        game.dialogue_manager.is_active = True
        handler = InputHandler(game)
        handler._handle_interact_key()
        assert game.dialogue_manager.advance.call_count == 1

    def test_normal_interact(self):
        """Ligne 81 : aucun UI ouvert → handle_interactions."""
        game = _make_game()
        handler = InputHandler(game)
        handler._handle_interact_key()
        assert game.interaction_manager.handle_interactions.call_count == 1


class TestHandleInventoryKey:
    def test_toggle_when_nothing_open(self):
        """toggle() appelé quand inventory/chest/dialogue tous fermés."""
        game = _make_game()
        handler = InputHandler(game)
        handler._handle_inventory_key()
        assert game.inventory_ui.toggle.call_count == 1

    def test_no_toggle_when_dialogue_open(self):
        game = _make_game()
        game.dialogue_manager.is_active = True
        handler = InputHandler(game)
        handler._handle_inventory_key()
        assert game.inventory_ui.toggle.call_count == 0

    def test_no_toggle_when_chest_open(self):
        game = _make_game()
        game.chest_ui.is_open = True
        handler = InputHandler(game)
        handler._handle_inventory_key()
        assert game.inventory_ui.toggle.call_count == 0


class TestAdvanceBoxDialogue:
    def test_npc_reverts_to_idle_on_dialogue_end(self):
        """Ligne 89 : NPC en état 'interact' revient à 'idle' quand dialogue terminé."""
        game = _make_game()
        game.dialogue_manager.is_active = False  # dialogue vient de se terminer
        npc = MagicMock()
        npc.state = "interact"
        game.npcs = [npc]
        handler = InputHandler(game)
        handler._advance_box_dialogue()
        assert npc.state == "idle"
