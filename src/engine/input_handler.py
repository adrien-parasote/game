"""InputHandler: processes pygame events and dispatches game actions.

Extracted from Game._handle_events (game.py L560-L596) as part of
Phase 1.5 refactoring.

Deep links:
  - Origin: src/engine/game.py#L560-L596
  - Spec: docs/specs/phase-1.5-game-refactoring.md
"""

import sys
from typing import Any

import pygame

from src.config import Settings


class InputHandler:
    """Dispatches pygame events to appropriate game subsystems.

    Args:
        game: Game context (Any — ADR-004 pattern). Must expose:
              dialogue_manager, _npc_bubble, chest_ui, inventory_ui,
              interaction_manager, npcs, _advance_npc_bubble.
    """

    def __init__(self, game: Any) -> None:
        self.game = game

    def handle_events(self, events: list) -> None:
        """Process a list of pygame events.

        Args:
            events: List of pygame.event.Event objects (e.g. from pygame.event.get()).
        """
        for event in events:
            self._dispatch(event)

    # -----------------------------------------------------------------------
    # Private
    # -----------------------------------------------------------------------

    def _dispatch(self, event: pygame.event.Event) -> None:
        """Route a single event to the correct handler."""
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)

        if self.game.inventory_ui.is_open:
            self.game.inventory_ui.handle_input(event)

        if self.game.chest_ui.is_open:
            self.game.chest_ui.handle_event(event)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle KEYDOWN events: interact, dialogue, inventory."""
        if event.key == Settings.INTERACT_KEY:
            self._handle_interact_key()
            return

        if event.key == Settings.INVENTORY_KEY:
            self._handle_inventory_key()

    def _handle_interact_key(self) -> None:
        """Route INTERACT_KEY press based on current UI state."""
        if self.game._npc_bubble is not None:
            self.game._advance_npc_bubble()
            return

        if self.game.dialogue_manager.is_active:
            self._advance_box_dialogue()
            return

        self.game.interaction_manager.handle_interactions()

    def _advance_box_dialogue(self) -> None:
        """Advance the box dialogue and resume NPCs on completion."""
        self.game.dialogue_manager.advance()
        if not self.game.dialogue_manager.is_active:
            for npc in self.game.npcs:
                if npc.state == "interact":
                    npc.state = "idle"

    def _handle_inventory_key(self) -> None:
        """Toggle inventory unless chest or dialogue is open."""
        dialogue_open = self.game.dialogue_manager.is_active
        bubble_open = self.game._npc_bubble is not None
        chest_open = self.game.chest_ui.is_open

        if not dialogue_open and not bubble_open and not chest_open:
            self.game.inventory_ui.toggle()
