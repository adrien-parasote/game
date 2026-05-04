"""
GameStateManager — Main loop orchestrator, manages TITLE/PLAYING/PAUSED states.
Spec: docs/specs/game-flow-spec.md#23-srcenginegame_state_managerpy-new
ADR: docs/ADRs/ADR-001-gamestate-architecture.md
"""

import logging
import sys
from enum import Enum

import pygame

from src.config import Settings
from src.engine.game import Game
from src.engine.game_events import GameEventType
from src.engine.game_state_constants import (
    PLAYER_DEFAULT_GOLD,
    PLAYER_DEFAULT_HP,
    PLAYER_DEFAULT_LEVEL,
    PLAYER_DEFAULT_MAX_HP,
    SAVE_BGM_FADE_MS,
    THUMBNAIL_CROP_SIZE,
    THUMBNAIL_SIZE,
)
from src.engine.save_manager import SaveManager
from src.ui.pause_screen import PauseScreen
from src.ui.title_screen import TitleScreen


class GameState(Enum):
    TITLE = "title"
    PLAYING = "playing"
    PAUSED = "paused"


class GameStateManager:
    """
    Owns the main loop and orchestrates transitions between
    TitleScreen, Game (playing), and PauseScreen.
    """

    def __init__(self) -> None:
        self._game = Game(skip_map_load=True)
        self._save_manager = SaveManager()
        self._title_screen = TitleScreen(self._game.screen, self._save_manager)
        self._pause_screen = PauseScreen(self._game.screen, self._save_manager)
        self.state = GameState.TITLE
        self._default_map: str | None = None  # resolved once on new game

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Main loop — replaces Game.run()."""
        while True:
            dt = self._game.clock.tick(Settings.FPS) / 1000.0
            events = pygame.event.get()

            self._process_global_events(events)

            if self.state == GameState.TITLE:
                self._handle_title(events, dt)
            elif self.state == GameState.PLAYING:
                self._handle_playing(events, dt)
            elif self.state == GameState.PAUSED:
                self._handle_paused(events, dt)

            pygame.display.update()

    # ── Global event processing ───────────────────────────────────────────────

    def _process_global_events(self, events: list) -> None:
        """Handle cross-state events: window close, ESC, and fullscreen toggle."""
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._on_escape()
                elif event.key == Settings.TOGGLE_FULLSCREEN_KEY:
                    self._game.toggle_fullscreen()

    def _on_escape(self) -> None:
        if self.state == GameState.PLAYING:
            self._transition_to_paused()
        elif self.state == GameState.PAUSED:
            self._transition_to_playing(slot_id=None, resume=True)

    # ── State handlers ────────────────────────────────────────────────────────

    def _handle_title(self, events: list, dt: float) -> None:
        for event in events:
            result = self._title_screen.handle_event(event)
            if result is None:
                continue
            if result.type == GameEventType.NEW_GAME:
                self._transition_to_playing(slot_id=None)
            elif result.type == GameEventType.LOAD_REQUESTED:
                self._transition_to_playing(slot_id=result.slot_id)
            elif result.type == GameEventType.QUIT:
                pygame.quit()
                sys.exit()

        self._title_screen.update(dt)
        self._title_screen.draw()

    def _handle_playing(self, events: list, dt: float) -> None:
        # Inject filtered events into game (without ESC — handled globally)
        filtered = [
            e for e in events if not (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE)
        ]
        # Feed events back to pygame queue so Game._handle_events() can consume them
        for event in filtered:
            pygame.event.post(event)

        game_event = self._game.run_frame(dt)

        if game_event and game_event.type == GameEventType.PAUSE_REQUESTED:
            self._transition_to_paused()

    def _handle_paused(self, events: list, dt: float) -> None:
        # Draw the frozen game scene first (background)
        self._game._draw()

        for event in events:
            result = self._pause_screen.handle_event(event)
            if result is None:
                continue
            if result.type == GameEventType.RESUME:
                self._transition_to_playing(slot_id=None, resume=True)
            elif result.type == GameEventType.PAUSE_REQUESTED:
                # Sauvegarder button — find first free slot
                self._save_to_first_free_slot()
            elif result.type == GameEventType.SAVE_REQUESTED:
                if result.slot_id is not None:
                    self._handle_save_requested(result.slot_id)
            elif result.type == GameEventType.GOTO_TITLE:
                self._transition_to_title()

        self._pause_screen.update(dt)
        self._pause_screen.draw()

    # ── Transitions ───────────────────────────────────────────────────────────

    def _transition_to_playing(self, slot_id: int | None, resume: bool = False) -> None:
        """
        Transition to PLAYING state.
        - slot_id=None + resume=False → new game (load default map)
        - slot_id=N               → load save slot N
        - slot_id=None + resume=True → resume from pause (no map load)
        """
        pygame.mouse.set_visible(True)  # restore system cursor during gameplay
        if resume:
            self.state = GameState.PLAYING
            return

        if slot_id is None:
            # New game
            self._game._load_map(self._resolve_default_map())
        else:
            save_data = self._save_manager.load(slot_id)
            if save_data is not None:
                self._apply_save_data(save_data)
            else:
                logging.warning(f"GSM: Slot {slot_id} not found, starting new game")
                self._game._load_map(self._resolve_default_map())

        self.state = GameState.PLAYING

    def _transition_to_paused(self) -> None:
        pygame.mouse.set_visible(False)  # custom cursor takes over
        self.state = GameState.PAUSED

    def _transition_to_title(self) -> None:
        # Stop all game audio before returning to title
        self._game.audio_manager.stop_bgm(fade_ms=SAVE_BGM_FADE_MS)
        self._game.audio_manager.stop_all_ambients()
        pygame.mixer.stop()  # stop any remaining SFX channels
        pygame.mouse.set_visible(False)  # custom cursor takes over
        self._title_screen.state = "MAIN_MENU"
        self._pause_screen.state = "MAIN"
        self.state = GameState.TITLE

    # ── Save / Load helpers ───────────────────────────────────────────────────

    def _save_to_first_free_slot(self) -> None:
        """Save to first empty slot, or signal overwrite needed."""
        slots = self._save_manager.list_slots()
        for i, info in enumerate(slots):
            if info is None:
                slot_id = i + 1
                self._handle_save_requested(slot_id)
                return
        # All slots full — for now save to slot 1 (overwrite logic: Phase 1.5)
        logging.info("GSM: All slots full — overwriting slot 1")
        self._handle_save_requested(1)

    def _handle_save_requested(self, slot_id: int) -> None:
        """Execute save sequence and generate thumbnail."""
        self._save_manager.save(slot_id, self._game)

        # Draw pure game frame without UI overlays
        self._game._draw()

        # Capture a square crop centered on the player for the save thumbnail
        crop_size = THUMBNAIL_CROP_SIZE
        sw, sh = self._game.screen.get_size()
        cx, cy = sw // 2, sh // 2

        if self._game.player and self._game.player.rect:
            # player.rect is in world coordinates; camera offset converts to screen space
            px, py = self._game.player.rect.center
            offset = self._game.visible_sprites.offset
            cx = int(px + offset.x)
            cy = int(py + offset.y)

        # Clamp crop rect to screen boundaries
        cx = max(crop_size // 2, min(sw - crop_size // 2, cx))
        cy = max(crop_size // 2, min(sh - crop_size // 2, cy))

        crop_rect = pygame.Rect(cx - crop_size // 2, cy - crop_size // 2, crop_size, crop_size)
        thumb_surf = self._game.screen.subsurface(crop_rect).copy()
        # Scale down to THUMBNAIL_SIZE to fit the UI slot while keeping file size small
        thumb_surf = pygame.transform.smoothscale(thumb_surf, (THUMBNAIL_SIZE, THUMBNAIL_SIZE))

        self._save_manager.save_thumbnail(slot_id, thumb_surf)
        self._pause_screen.notify_save_result(True)
        self._pause_screen._save_menu.refresh()
        logging.info(f"GSM: Game saved to slot {slot_id} with thumbnail")

    def _apply_save_data(self, data) -> None:
        """Restore game state from SaveData."""
        game = self._game

        # Restore player stats
        game.player.level = data.player.get("level", PLAYER_DEFAULT_LEVEL)
        game.player.hp = data.player.get("hp", PLAYER_DEFAULT_HP)
        game.player.max_hp = data.player.get("max_hp", PLAYER_DEFAULT_MAX_HP)
        game.player.gold = data.player.get("gold", PLAYER_DEFAULT_GOLD)
        game.player.current_state = data.player.get("facing", "down")

        # Restore time
        game.time_system._total_minutes = data.time_system.get("total_minutes", 0.0)

        # Restore world state
        game.world_state._state = dict(data.world_state)

        # Restore inventory
        self._restore_inventory(game, data.inventory)

        # Load the saved map
        game._load_map(data.player["map_name"])

        # Position player (after map load — player rect is reset by _load_map)
        import pygame as _pg

        x = data.player.get("x", 0.0)
        y = data.player.get("y", 0.0)
        game.player.pos = _pg.math.Vector2(x, y)
        game.player.target_pos = _pg.math.Vector2(x, y)
        if game.player.rect:
            game.player.rect.center = (int(x), int(y))

    def _restore_inventory(self, game, inv_data: dict) -> None:
        """Rebuild Inventory from save dict."""
        inv = game.player.inventory
        # Reset slots
        inv.slots = [None] * inv.capacity
        for i, slot_data in enumerate(inv_data.get("slots", [])):
            if slot_data is not None and i < inv.capacity:
                try:
                    inv.slots[i] = inv.create_item(slot_data["id"], slot_data["quantity"])
                except Exception as e:
                    logging.warning(f"GSM: Could not restore slot {i}: {e}")

        # Restore equipment
        for slot_name, eq_data in inv_data.get("equipment", {}).items():
            if eq_data is None:
                inv.equipment[slot_name] = None
            else:
                try:
                    item = inv.create_item(eq_data["id"], eq_data["quantity"])
                    inv.equipment[slot_name] = item
                except Exception as e:
                    logging.warning(f"GSM: Could not restore equipment {slot_name}: {e}")

    def _resolve_default_map(self) -> str:
        """Return the initial map: debug room if Settings.DEBUG, else world.world first entry."""
        import json
        import os

        from src.config import Settings

        # Debug room takes priority over world.world
        debug_room = "99-debug_room.tmj"
        debug_path = os.path.join("assets", "tiled", "maps", debug_room)
        if Settings.DEBUG and os.path.exists(debug_path):
            return debug_room

        world_path = os.path.join("assets", "tiled", "maps", "world.world")
        if os.path.exists(world_path):
            try:
                with open(world_path, encoding="utf-8") as f:
                    world_data = json.load(f)
                    return world_data.get("maps", [{}])[0].get("fileName", "00-spawn.tmj")
            except Exception as e:
                logging.error(f"GSM: Could not read world.world: {e}")
        return "00-spawn.tmj"
