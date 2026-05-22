import json
import logging
import logging.handlers
import os

import pygame

from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.audio import AudioManager
from src.engine.entity_factory import EntityFactory
from src.engine.game_events import GameEvent
from src.engine.game_setup import setup_logging as _setup_logging_fn
from src.engine.i18n import I18nManager
from src.engine.input_handler import InputHandler
from src.engine.interaction import InteractionManager
from src.engine.lighting import LightingManager
from src.engine.loot_table import LootTable
from src.engine.map_loader import MapLoader
from src.engine.render_manager import RenderManager
from src.engine.time_system import TimeSystem
from src.engine.world_state import WorldState
from src.entities.groups import CameraGroup
from src.entities.player import Player
from src.ui.chest import ChestUI
from src.ui.dialogue import DialogueManager
from src.ui.hud import GameHUD
from src.ui.inventory import InventoryUI
from src.ui.speech_bubble import SpeechBubble


def _get_property(props: dict, key: str, default=None):
    """
    Look for a property in the resolved Tiled properties dictionary.
    Handles common paths for Tiled 1.10+ nested class structures.
    """
    if key in props:
        return props[key]

    # Check common nested paths (interactive_object -> sprite)
    io = props.get("interactive_object", {})
    if isinstance(io, dict):
        if key in io:
            return io[key]
        sp = io.get("sprite", {})
        if isinstance(sp, dict) and key in sp:
            return sp[key]

    sp = props.get("sprite", {})
    if isinstance(sp, dict) and key in sp:
        return sp[key]

    return default


class Game:
    """Main game class that manages the core loop and state."""

    def __init__(self, skip_map_load: bool = False):
        self._init_display()
        self._init_groups()
        self._init_systems()
        self._init_player()

        # First load reads the default map from world.world
        default_map = self._get_initial_map()

        if not skip_map_load:
            self._load_map(default_map)

    def _init_display(self):
        self._setup_logging()

        # 1. Initialize Localization
        self.i18n = I18nManager()
        self.i18n.load(Settings.LOCALE)
        pygame.init()
        logging.info(f"Initializing Game Engine v{Settings.VERSION}...")

        # Display initialization with Fullscreen support
        display_flags = pygame.FULLSCREEN if Settings.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT), display_flags
        )
        pygame.display.set_caption(f"{Settings.GAME_TITLE} (v{Settings.VERSION})")
        pygame.mouse.set_visible(False)  # Hidden globally; glove drawn by UI when open
        self.clock = pygame.time.Clock()

        # Load Constants from Settings
        self.tile_size = Settings.TILE_SIZE
        self.map_size = Settings.MAP_SIZE
        self.is_fullscreen = Settings.FULLSCREEN
        self.last_fps_update = 0

    def _init_groups(self):
        # Setup Groups
        self.visible_sprites = CameraGroup()
        self.npcs = pygame.sprite.Group()
        self.interactives = pygame.sprite.Group()
        self.obstacles_group = pygame.sprite.Group()
        self.teleports_group = pygame.sprite.Group()
        self.emote_group = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()
        # Entities whose open state overrides tile walkability beneath them.
        # Used by CollisionChecker to allow crossing non-walkable tiles (e.g. water)
        # when a passable bridge/drawbridge entity is open (is_on=True, is_passable=True).
        self.walkable_override_entities: set = set()

        # P12: Pre-allocated viewport rect (avoids 2 Rect allocs per frame in _update)
        self._viewport_world_rect = pygame.Rect(
            0, 0, Settings.WINDOW_WIDTH + 256, Settings.WINDOW_HEIGHT + 256
        )
        # P6: Set of active torch entities (halos > 0, is_on=True) — updated on state change only
        self._active_torches: set = set()
        # Initialized to None; set by MapLoader.load() on each map transition
        self.anim_map_manager = None
        # Intra-map walk state — None when inactive, Vector2 target when walk is in progress
        # Spec: docs/specs/intra-map-teleport.md § 4.4.1
        self._intra_walk_target: pygame.math.Vector2 | None = None
        # Lazy-initialized on first scripted walk (player must exist first).
        # See _start_intra_walk for creation.
        self._player_transparent: pygame.Surface | None = None

    def _init_systems(self):
        # Time System
        self.time_system = TimeSystem(initial_hour=Settings.INITIAL_HOUR)
        self.hud = GameHUD(self.time_system)
        self.lighting_manager = LightingManager(
            self.time_system, self.screen.get_size()
        )

        # World State
        self.world_state = WorldState()

        # Loot Table (chest contents)
        self.loot_table = LootTable()
        property_types = self._load_property_types()
        self.loot_table.load(os.path.join("assets", "data", "loot_table.json"), property_types)

        # Dialogue System (signs / interactive objects)
        self.dialogue_manager = DialogueManager()

        # Speech bubble (NPC PNG dialogues)
        self.speech_bubble = SpeechBubble(max_width_px=288)
        am = AssetManager()
        self.speech_bubble.set_font(
            am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        )
        self.speech_bubble.set_name_font(
            am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NARRATIVE)
        )
        # Active NPC bubble state: {npc, text, page} or None
        self._npc_bubble: dict | None = None
        # Pending NPC dialogue (npc, message) while moving
        self._pending_npc_dialogue: tuple | None = None

        # Audio System
        self.audio_manager = AudioManager()

        # Interaction System
        self.interaction_manager = InteractionManager(self)

        # Phase 1.5 modules
        self._entity_factory = EntityFactory(self)
        self._map_loader = MapLoader(self)
        self._input_handler = InputHandler(self)

        # Render System
        self.render_manager = RenderManager(self)

        logging.info(
            f"Screen setup: {Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT} (Fullscreen: {self.is_fullscreen})"
        )

    def _init_player(self):
        # Player is persisted across maps
        self.player = Player(
            (0, 0), self.visible_sprites, speed=Settings.PLAYER_SPEED, element_id="player"
        )
        self.player.audio_manager = self.audio_manager
        self.player.game = self
        self.player.emote_manager.emote_group = self.emote_group
        self.player.walkable_func = self.interaction_manager.is_walkable

        # Inventory System
        self.inventory_ui = InventoryUI(self.player)
        self.chest_ui = ChestUI()

    def _get_initial_map(self) -> str:
        default_map = "00-spawn.tmj"

        # Debug Room Priority
        debug_room = "99-debug_room.tmj"
        debug_path = os.path.join("assets", "tiled", "maps", debug_room)
        if Settings.DEBUG and os.path.exists(debug_path):
            logging.info(f"Debug Mode active: Loading {debug_room} as initial map.")
            default_map = debug_room
        else:
            world_path = os.path.join("assets", "tiled", "maps", "world.world")
            if os.path.exists(world_path):
                try:
                    with open(world_path, encoding="utf-8") as f:
                        world_data = json.load(f)
                        default_map = world_data.get("maps", [{}])[0].get(
                            "fileName", "00-spawn.tmj"
                        )
                except Exception as e:
                    logging.error(f"Failed to read world.world: {e}")
        return default_map

    def _load_map(
        self, map_name: str, target_spawn_id: str | None = None, transition_type: str = "instant"
    ):
        """Delegate to MapLoader.load (Phase 1.5 refactoring)."""
        self._map_loader.load(map_name, target_spawn_id, transition_type)

    def _start_initial_ambients(self, player_pos: pygame.math.Vector2) -> None:
        """Delegate to MapLoader._start_initial_ambients (Phase 1.5)."""
        self._map_loader._start_initial_ambients(player_pos)

    def _spawn_entities(self, entities: list, map_name: str = "") -> None:
        """Delegate to EntityFactory.spawn_entities (Phase 1.5)."""
        self._entity_factory.spawn_entities(entities, map_name)

    def _trigger_dialogue(self, element_id: str, title: str = ""):
        """Fetch localized message and start dialogue (signs / objects → bottom box)."""
        map_base = self._current_map_name.split(".")[0]
        full_key = f"{map_base}-{element_id}"
        msg = self.i18n.get(f"dialogues.{full_key}")
        if msg:
            self.dialogue_manager.start_dialogue(msg, title=title)
        else:
            logging.warning(f"Dialogue key not found: {full_key}")

    def _trigger_npc_bubble(self, npc, element_id: str) -> None:
        """Fetch localized message and attach a speech bubble to *npc*."""
        map_base = self._current_map_name.split(".")[0]
        full_key = f"{map_base}-{element_id}"
        msg = self.i18n.get(f"dialogues.{full_key}")
        if not msg:
            logging.warning(f"NPC bubble key not found: {full_key}")
            return
        self._npc_bubble = {"npc": npc, "text": msg, "page": 0}
        logging.info(f"NPC bubble started for '{element_id}': {msg[:40]}...")

    def _advance_npc_bubble(self) -> None:
        """Advance NPC bubble page or close it on last page."""
        if self._npc_bubble is None or not self.speech_bubble.font:
            return
        # Compute total pages using SpeechBubble logic
        total_pages = self.speech_bubble.get_total_pages(self._npc_bubble["text"])
        if self._npc_bubble["page"] < total_pages - 1:
            self._npc_bubble["page"] += 1
        else:
            self._npc_bubble = None
            for npc in self.npcs:
                if npc.state == "interact":
                    npc.state = "idle"

    def transition_map(self, target_map: str, target_spawn_id: str, transition_type: str):
        """Handle screen fading and triggering map load cleanly."""
        target_map = target_map.replace(".tjm", ".tmj")

        map_path = os.path.join("assets", "tiled", "maps", target_map)
        if not os.path.exists(map_path) and target_map != "00-spawn.tmj":
            # Safety checks for bad targets
            logging.error(f"Fading failed, map missing: {map_path}")
            return

        fade_surf = pygame.Surface(self.screen.get_size())
        fade_surf.fill((0, 0, 0))

        if transition_type == "fade":
            # Fade Out
            for alpha in range(0, 256, 15):
                dt = self.clock.tick(Settings.FPS) / 1000.0
                self.time_system.update(dt)  # Flow of time continues

                self.render_manager.draw_scene()
                fade_surf.set_alpha(alpha)
                self.screen.blit(fade_surf, (0, 0))
                pygame.display.update()

        # Load exactly at climax of transition
        self._load_map(target_map, target_spawn_id, transition_type)

        if transition_type == "fade":
            # Fade In
            for alpha in range(255, -1, -15):
                dt = self.clock.tick(Settings.FPS) / 1000.0
                self.time_system.update(dt)

                self.render_manager.draw_scene()
                fade_surf.set_alpha(alpha)
                self.screen.blit(fade_surf, (0, 0))
                pygame.display.update()

        self.clock.tick(Settings.FPS)  # Reset dt so next frame logic doesn't jump

    # ---------------------------------------------------------------------------
    # Intra-map teleport — spec: docs/specs/intra-map-teleport.md § 4.3–4.4
    # ---------------------------------------------------------------------------

    def intra_map_teleport(self, target_spawn_id: str, transition_type: str) -> None:
        """Reposition the player within the current map without reloading it.

        Preserves all entity groups, world state, and audio.
        transition_type 'instant': snap to spawn. 'walk': scripted lerp to spawn.

        Spec: docs/specs/intra-map-teleport.md § 4.3
        """
        spawn_pos = self._map_loader.resolve_spawn_by_id(target_spawn_id)
        if spawn_pos is None:
            logging.error(
                f"intra_map_teleport: spawn '{target_spawn_id}' not found — abort"
            )
            return

        if transition_type == "walk":
            self._start_intra_walk(pygame.math.Vector2(spawn_pos))
        else:
            self._map_loader._position_player(spawn_pos)

    def _start_intra_walk(self, target: pygame.math.Vector2) -> None:
        """Arm the scripted walk to *target* (pixel coords).

        Sets target_pos on the player so player.move(dt) drives the translation.
        Sets is_moving=True and computes initial facing from delta direction.

        Spec: docs/specs/intra-map-teleport.md § 4.4.2
        """
        # Lazy-init the transparent surface (player must exist, sized to its image).
        # Created once and reused across all scripted walks.
        if self._player_transparent is None:
            self._player_transparent = pygame.Surface(
                self.player.image.get_size(), pygame.SRCALPHA
            )
            self._player_transparent.fill((0, 0, 0, 0))

        self._intra_walk_target = target
        self.player.target_pos = pygame.math.Vector2(target)
        self.player.is_moving = True
        # Set initial facing — G4: facing follows walk direction
        delta = target - self.player.pos
        if delta.magnitude() > 0:
            if abs(delta.x) >= abs(delta.y):
                self.player.current_state = "right" if delta.x > 0 else "left"
            else:
                self.player.current_state = "up" if delta.y < 0 else "down"


    def _tick_intra_walk(self, dt: float) -> None:
        """Monitor walk completion and maintain player facing each frame.

        Delegates actual translation to player.move(dt) (via visible_sprites.update).
        Terminates when player.is_moving becomes False (player arrived at target_pos).

        Spec: docs/specs/intra-map-teleport.md § 4.4.3
        """
        if self._intra_walk_target is None:
            return

        # Arrival: player.move() cleared is_moving when it reached target_pos
        if not self.player.is_moving:
            self._intra_walk_target = None
            self.player.direction = pygame.math.Vector2(0, 0)
            # player.image is restored automatically next frame by _update_animation
            return

        # Keep facing updated based on remaining distance vector (G4)
        delta = self._intra_walk_target - self.player.pos
        if delta.magnitude() > 0:
            if abs(delta.x) >= abs(delta.y):
                self.player.current_state = "right" if delta.x > 0 else "left"
            else:
                self.player.current_state = "up" if delta.y < 0 else "down"

    def run(self):
        """Main game loop optimized for 60 FPS."""
        while True:
            self._handle_events()

            # Update (Fixed 60 FPS)
            dt = self.clock.tick(Settings.FPS) / 1000.0
            self._update(dt)

            # Draw complete sequence
            self._draw()

    def run_frame(self, dt: float) -> GameEvent:
        """Single-frame tick for use by GameStateManager (tick-by-tick mode)."""
        self._handle_events()
        self._update(dt)
        self._draw()
        return GameEvent.none()

    def get_state(self) -> dict:
        """Return full game state dict for serialization by SaveManager."""
        inv = self.player.inventory
        return {
            "map_name": getattr(self, "_current_map_name", ""),
            "player_pos": (self.player.pos.x, self.player.pos.y),
            "player_facing": self.player.current_state,
            "player_level": self.player.level,
            "player_hp": self.player.hp,
            "player_max_hp": self.player.max_hp,
            "player_gold": self.player.gold,
            "time_total_minutes": self.time_system._total_minutes,
            "inventory_slots": inv.slots,
            "inventory_equipment": inv.equipment,
            "world_state": self.world_state._state,
        }

    def _handle_events(self):
        """Delegate to InputHandler.handle_events (Phase 1.5 refactoring)."""
        self._input_handler.handle_events(pygame.event.get())

    def _update(self, dt: float):
        """Update game state by dt."""
        # --- Logical Pause for Dialogue/Inventory ---
        self.emote_group.update(dt)

        pending_npc = getattr(self, "_pending_npc_dialogue", None)
        if pending_npc is not None:
            npc, res = pending_npc
            npc.update(dt)
            if not npc.is_moving:
                self._trigger_npc_bubble(npc, res)
                self._pending_npc_dialogue = None
            return

        if self._npc_bubble is not None or self.dialogue_manager.is_active:
            if self.dialogue_manager.is_active:
                self.dialogue_manager.update(dt)
        elif self.inventory_ui.is_open:
            self.inventory_ui.update(dt)
        elif self.chest_ui.is_open:
            self._update_chest_state(dt)
        else:
            self._update_core_state(dt)

        now = pygame.time.get_ticks()
        if now - self.last_fps_update > 1000:
            fps = self.clock.get_fps()
            pygame.display.set_caption(
                f"{Settings.GAME_TITLE} (v{Settings.VERSION}) - {fps:.1f} FPS"
            )
            self.last_fps_update = now

    def _update_chest_state(self, dt: float):
        # Allow player movement and interactions while chest UI open
        self.interaction_manager.update(dt)
        self.player.input()
        self.interaction_manager.handle_interactions()

        was_moving = self.player.is_moving
        self.visible_sprites.update(dt)
        self.interaction_manager.check_teleporters(was_moving)
        # No time_system update or other world updates
        self.audio_manager.flush_ambient()

    def _update_core_state(self, dt: float):
        # Update Time
        self.time_system.update(dt)
        self.interaction_manager.update(dt)

        # Walk-transition intercept — G2: all inputs blocked during scripted walk
        # Spec: docs/specs/intra-map-teleport.md § 4.5
        if self._intra_walk_target is not None:
            self._tick_intra_walk(dt)
            self.visible_sprites.update(dt)
            # Swap player.image to the pre-built transparent surface so the player is
            # invisible during the scripted walk. Done post-update so _update_animation
            # doesn't override it. Avoids contaminating the shared spritesheet frames.
            if self._intra_walk_target is not None:  # still walking (not arrived this frame)
                self.player.image = self._player_transparent
            # Skip player.input(), interactions, and teleporter checks
        else:
            # Normal input path
            self.player.input()
            self.interaction_manager.handle_interactions()

            was_moving = self.player.is_moving
            self.visible_sprites.update(dt)
            self.interaction_manager.check_teleporters(was_moving)

        # P12: CPU Freeze optimization for NPCs — reuse pre-allocated rect
        off_x = int(self.visible_sprites.offset.x)
        off_y = int(self.visible_sprites.offset.y)
        self._viewport_world_rect.update(
            -off_x - 128,
            -off_y - 128,
            Settings.WINDOW_WIDTH + 256,
            Settings.WINDOW_HEIGHT + 256,
        )

        # P13: One get_ticks() call shared across all interactive entities
        ticks_ms = pygame.time.get_ticks()

        for npc in self.npcs:
            npc.is_visible = self._viewport_world_rect.colliderect(npc.rect)
            npc.update(dt)

        for obj in self.interactives:
            obj.update(dt, ticks_ms=ticks_ms)

        # Resolve ambient sound volumes from this frame's proposals.
        self.audio_manager.flush_ambient()

        if self.anim_map_manager:
            self.anim_map_manager.update(int(dt * 1000))

    def _draw(self):
        """Render complete scene. Display update is owned by the main loop."""
        self.render_manager.draw_scene()

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        try:
            pygame.display.toggle_fullscreen()
            self.is_fullscreen = not self.is_fullscreen
        except pygame.error as e:
            logging.warning(f"Native toggle_fullscreen failed: {e}. Falling back to set_mode.")
            self.is_fullscreen = not self.is_fullscreen
            display_flags = pygame.FULLSCREEN if self.is_fullscreen else 0
            self.screen = pygame.display.set_mode(
                (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT), display_flags
            )
            self.lighting_manager.resize(self.screen.get_size())
        logging.info(f"Fullscreen toggled: {self.is_fullscreen}")

    def _load_property_types(self) -> dict:
        """Load item property types from propertytypes.json."""
        path = os.path.join("assets", "data", "propertytypes.json")
        if not os.path.exists(path):
            logging.error(f"Item property types file not found: {path}")
            return dict()  # noqa: P6 — legitimate error handler (file not found)
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load item property types from {path}: {e}")
            return dict()  # noqa: P6 — legitimate error handler (json parse failure)

    def _setup_logging(self):
        """Delegate to game_setup.setup_logging (Phase 1.5 refactoring)."""
        _setup_logging_fn(Settings)
