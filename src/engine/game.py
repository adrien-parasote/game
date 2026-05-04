import json
import logging
import logging.handlers
import os
import sys

import pygame

from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.audio import AudioManager
from src.engine.game_events import GameEvent
from src.engine.i18n import I18nManager
from src.engine.interaction import InteractionManager
from src.engine.lighting import LightingManager
from src.engine.loot_table import LootTable
from src.engine.render_manager import RenderManager
from src.engine.time_system import TimeSystem
from src.engine.world_state import WorldState
from src.entities.groups import CameraGroup
from src.entities.interactive import InteractiveEntity
from src.entities.npc import NPC
from src.entities.pickup import PickupItem
from src.entities.player import Player
from src.entities.teleport import Teleport
from src.map.layout import OrthogonalLayout
from src.map.manager import MapManager
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
        # 1. Initialize Localization
        self.i18n = I18nManager()
        self.i18n.load(Settings.LOCALE)

        self._setup_logging()
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

        # Setup Groups
        self.visible_sprites = CameraGroup()
        self.npcs = pygame.sprite.Group()
        self.interactives = pygame.sprite.Group()
        self.obstacles_group = pygame.sprite.Group()
        self.teleports_group = pygame.sprite.Group()
        self.emote_group = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()

        # P12: Pre-allocated viewport rect (avoids 2 Rect allocs per frame in _update)
        self._viewport_world_rect = pygame.Rect(
            0, 0, Settings.WINDOW_WIDTH + 256, Settings.WINDOW_HEIGHT + 256
        )
        # P6: Set of active torch entities (halos > 0, is_on=True) — updated on state change only
        self._active_torches: set = set()

        # Local state
        self.is_fullscreen = Settings.FULLSCREEN
        self.last_fps_update = 0

        # Time System
        self.time_system = TimeSystem(initial_hour=Settings.INITIAL_HOUR)
        self.hud = GameHUD(self.time_system)
        self.lighting_manager = LightingManager(
            self.time_system, (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT)
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

        # Render System
        self.render_manager = RenderManager(self)

        logging.info(
            f"Screen setup: {Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT} (Fullscreen: {self.is_fullscreen})"
        )

        # Player is persisted across maps
        self.player = Player(
            (0, 0), self.visible_sprites, speed=Settings.PLAYER_SPEED, element_id="player"
        )
        self.player.audio_manager = self.audio_manager
        self.player.game = self
        self.player.emote_manager.emote_group = self.emote_group
        self.player.collision_func = self.interaction_manager.is_collidable

        # Inventory System
        self.inventory_ui = InventoryUI(self.player)
        self.chest_ui = ChestUI()

        # First load reads the default map from world.world
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

        if not skip_map_load:
            self._load_map(default_map)

    def _load_map(
        self, map_name: str, target_spawn_id: str | None = None, transition_type: str = "instant"
    ):
        """Unload current elements and load a new map from Tiled."""
        from src.map.tmj_parser import TmjParser

        # Handle known typo in current maps
        map_name = map_name.replace(".tjm", ".tmj")

        map_path = os.path.join("assets", "tiled", "maps", map_name)
        if not os.path.exists(map_path):
            logging.error(f"Target map not found: {map_path}")
            return

        parser = TmjParser()
        map_result = parser.load_map(map_path)

        self.layout = OrthogonalLayout(self.tile_size)
        self.map_manager = MapManager(map_result, self.layout)

        bgm = map_result.get("properties", {}).get("bgm")
        if bgm:
            self.audio_manager.play_bgm(bgm)

        # Override MAP_SIZE for boundary logic in BaseEntity if needed
        self.map_size = max(self.map_manager.width, self.map_manager.height)
        Settings.MAP_SIZE = self.map_size

        # Initialize camera bounds
        world_width_px = self.map_manager.width * self.tile_size
        world_height_px = self.map_manager.height * self.tile_size
        self.visible_sprites.set_world_size(world_width_px, world_height_px)

        # Save NPC states before leaving the map
        for npc in self.npcs:
            if getattr(npc, "_world_state_key", None):
                self.world_state.set(
                    npc._world_state_key,
                    {"pos": (npc.pos.x, npc.pos.y), "facing": npc.current_facing},
                )

        # Clean entities for new map (excluding player)
        self.interactives.empty()
        self.npcs.empty()
        self.obstacles_group.empty()
        self.teleports_group.empty()
        self.pickups.empty()
        # Close any active NPC bubble to prevent dangling NPC reference
        self._npc_bubble = None

        # Only keep player in visible sprites
        self.visible_sprites.empty()
        self.visible_sprites.add(self.player)

        # Spawn Entities from Map
        self._current_map_name = map_name
        self._spawn_entities(map_result.get("entities", []), map_name)

        # Resolve spawn exact position
        half_tile = self.tile_size // 2
        spawn_pos = (world_width_px // 2, world_height_px // 2)  # Center fallback

        # Find the specific spawn point
        for ent in map_result.get("entities", []):
            ent_type = ent.get("type", "")
            props = ent.get("properties", {})
            if ent_type == "14-spawn_point" or props.get("spawn_player") is True:
                if target_spawn_id:
                    if props.get("spawn_id") == target_spawn_id:
                        spawn_pos = (ent["x"] + half_tile, ent["y"] + half_tile)
                        break
                elif props.get("is_initial_spawn") is True or props.get("is_initial_pawn") is True:
                    spawn_pos = (ent["x"] + half_tile, ent["y"] + half_tile)
                    break

        # Default fallback to `spawn_player` root map object if no specific matches
        if target_spawn_id is None and spawn_pos == (world_width_px // 2, world_height_px // 2):
            spawn_dict = map_result.get("spawn_player")
            if spawn_dict:
                spawn_pos = (spawn_dict["x"] + half_tile, spawn_dict["y"] + half_tile)
            else:
                logging.warning(
                    f"No valid spawn_player found on map {map_name}. Defaulting to center."
                )

        # Force player transform
        self.player.pos = pygame.math.Vector2(spawn_pos)
        self.player.target_pos = pygame.math.Vector2(spawn_pos)
        if self.player.rect:
            self.player.rect.center = (int(spawn_pos[0]), int(spawn_pos[1]))
        self.player.is_moving = False
        self.player.direction = pygame.math.Vector2(0, 0)
        logging.info(f"Loaded map {map_name}, player spawned at {spawn_pos}")

        # Explicitly prime ambient sounds for all active entities.
        # Sound.play() can silently return None on the first frame if the mixer
        # is busy starting the BGM; calling it here (after player pos is known)
        # ensures the distance-based volume is correct from the first frame.
        self._start_initial_ambients(pygame.math.Vector2(spawn_pos))

    def _start_initial_ambients(self, player_pos: pygame.math.Vector2) -> None:
        """Prime ambient sounds for all active interactive entities on map load.

        Called once per _load_map, after the player position is resolved.
        Uses the propose/flush model to start ambients at the correct
        distance-based volume from the very first frame.
        """
        for entity in self.interactives:
            sfx = getattr(entity, "sfx_ambient", "")
            if not sfx or not entity.is_on:
                continue
            dist = entity.pos.distance_to(player_pos)
            self.audio_manager.propose_ambient(sfx, dist)
        self.audio_manager.flush_ambient()

    def _spawn_entities(self, entities: list, map_name: str = ""):
        """Instantiate NPCs and Interactive objects from map data."""
        half_tile = self.tile_size // 2
        for ent in entities:
            props = ent.get("properties", {})
            entity_type = _get_property(props, "entity_type", default="unknown")
            e_pos = (ent["x"] + half_tile, ent["y"] + half_tile)

            if _get_property(props, "is_initial_spawn") is True:
                continue

            logging.debug(f"Processing entity ID {ent.get('id')} type={entity_type} at {e_pos}")

            if entity_type == "interactive":
                self._spawn_interactive(ent, props, map_name)
            elif _get_property(props, "type") == "teleport":
                self._spawn_teleport(ent, props)
            elif entity_type == "npc":
                self._spawn_npc(ent, props, e_pos)
            elif entity_type == "object":
                self._spawn_pickup(ent, props, e_pos)

    def _spawn_interactive(self, ent: dict, props: dict, map_name: str):
        """Instantiate a single InteractiveEntity and restore persisted state."""
        element_id = _get_property(props, "element_id") or str(ent.get("id"))
        if _get_property(props, "sub_type") == "sign":
            logging.info(f"Sign detected with ID: {element_id}")
        target_id = _get_property(props, "target_id") or _get_property(props, "target")

        entity = InteractiveEntity(
            pos=(ent["x"], ent["y"]),
            groups=[self.visible_sprites, self.interactives],
            sub_type=str(_get_property(props, "sub_type", "unknown")),
            sprite_sheet=str(_get_property(props, "sprite_sheet", "")),
            position=int(str(_get_property(props, "position", 0))),
            depth=int(str(_get_property(props, "depth", 1))),
            start_row=int(str(_get_property(props, "start_frame", 0))),
            end_row=int(str(_get_property(props, "end_frame", 3))),
            width=int(str(_get_property(props, "width", ent.get("width", 32)))),
            height=int(str(_get_property(props, "height", ent.get("height", 32)))),
            tiled_width=int(ent.get("width", 32)),
            tiled_height=int(ent.get("height", 32)),
            obstacles_group=self.obstacles_group,
            is_passable=bool(_get_property(props, "is_passable", False)),
            is_animated=bool(_get_property(props, "is_animated", False)),
            is_on=bool(_get_property(props, "is_on", False)),
            off_position=int(str(_get_property(props, "off_position", -1))),
            halo_size=int(str(_get_property(props, "halo_size", 0))),
            halo_color=str(_get_property(props, "halo_color", "[255, 255, 255]")),
            halo_alpha=int(str(_get_property(props, "halo_alpha", 130))),
            particles=bool(_get_property(props, "particles", False)),
            particle_count=int(str(_get_property(props, "particle_count", 0))),
            element_id=element_id,
            target_id=target_id,
            activate_from_anywhere=bool(_get_property(props, "activate_from_anywhere", False)),
            facing_direction=str(_get_property(props, "facing_direction", "")),
            sfx=str(_get_property(props, "sfx", "")),
            sfx_ambient=str(_get_property(props, "sfx_ambient", "")),
            day_night_driven=bool(_get_property(props, "day_night_driven", False)),
        )
        entity._time_system = self.time_system
        entity.game = self

        # Populate chest contents from loot table
        if _get_property(props, "sub_type", "unknown") == "chest":
            entity.contents = self.loot_table.get_contents(element_id)

        tiled_id = ent.get("id")
        if tiled_id is not None and map_name:
            key = WorldState.make_key(map_name, tiled_id)
            entity._world_state_key = key
            saved_state = self.world_state.get(key)
            if saved_state is not None:
                entity.restore_state(saved_state)

    def _spawn_teleport(self, ent: dict, props: dict):
        """Instantiate a Teleport trigger from map data."""
        t_rect = pygame.Rect(ent["x"], ent["y"], ent.get("width", 32), ent.get("height", 32))
        tp = Teleport(
            t_rect,
            [self.teleports_group],
            str(_get_property(props, "target_map", "")),
            str(_get_property(props, "target_spawn_id", "")),
            str(_get_property(props, "transition_type", "instant")),
            str(_get_property(props, "required_direction", "any")),
        )
        tp.sfx = str(_get_property(props, "sfx", ""))

    def _spawn_npc(self, ent: dict, props: dict, e_pos: tuple):
        """Instantiate an NPC from map data."""
        npc = NPC(
            pos=e_pos,
            groups=[self.visible_sprites, self.npcs],
            wander_radius=int(str(_get_property(props, "wander_radius", 1))),
            sheet_name=str(_get_property(props, "sprite_sheet", "01-character.png")),
            element_id=str(_get_property(props, "element_id") or str(ent.get("id", ""))),
        )
        npc.name = str(_get_property(props, "name", ent.get("name", "")))
        npc.collision_func = self.interaction_manager.is_collidable

        tiled_id = ent.get("id")
        if tiled_id is not None and self._current_map_name:
            key = WorldState.make_key(self._current_map_name, tiled_id)
            npc._world_state_key = key
            saved_state = self.world_state.get(key)
            if saved_state:
                saved_pos = saved_state.get("pos")
                if saved_pos:
                    npc.pos = pygame.math.Vector2(saved_pos)
                    npc.target_pos = pygame.math.Vector2(saved_pos)
                    if npc.rect:
                        npc.rect.center = (round(npc.pos.x), round(npc.pos.y))
                saved_facing = saved_state.get("facing")
                if saved_facing:
                    npc.current_facing = saved_facing

        logging.info(f"Spawned NPC '{npc.element_id}' at {npc.pos}")

    def _spawn_pickup(self, ent: dict, props: dict, e_pos: tuple):
        """Instantiate a PickupItem from map data, skipping already-collected ones."""
        item_id = _get_property(props, "object_id")
        sprite = _get_property(props, "sprite_sheet")
        quantity = int(str(_get_property(props, "quantity", 1)))
        if not (item_id and sprite):
            return

        # Check persisted pickup state
        tiled_id = ent.get("id")
        state_key = WorldState.make_key(self._current_map_name, tiled_id) if tiled_id else None
        if state_key:
            saved = self.world_state.get(state_key)
            if saved and saved.get("collected"):
                return  # Already fully picked up — skip spawn
            if saved and "quantity" in saved:
                quantity = saved["quantity"]  # Restore partial quantity

        item = PickupItem(
            pos=e_pos,
            groups=[self.visible_sprites, self.pickups],
            item_id=item_id,
            sprite_sheet=str(sprite),
            quantity=quantity,
            element_id=str(tiled_id or ""),
        )
        if state_key:
            item._world_state_key = state_key  # Attach key for persistence on pickup
        logging.info(f"Spawned PickupItem '{item_id}' (x{quantity}) at {e_pos}")

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
        """Handle all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                # NPC bubble advance (takes priority over box dialogue)
                if event.key == Settings.INTERACT_KEY and self._npc_bubble is not None:
                    self._advance_npc_bubble()

                # Box dialogue advance (signs, objects)
                elif event.key == Settings.INTERACT_KEY and self.dialogue_manager.is_active:
                    self.dialogue_manager.advance()
                    if not self.dialogue_manager.is_active:
                        # Resume NPCs
                        for npc in self.npcs:
                            if npc.state == "interact":
                                npc.state = "idle"

                # Inventory Toggle
                if (
                    event.key == Settings.INVENTORY_KEY
                    and not self.dialogue_manager.is_active
                    and self._npc_bubble is None
                    and not self.chest_ui.is_open
                ):
                    self.inventory_ui.toggle()

            # Inventory Input (Outside KEYDOWN, inside event loop)
            if self.inventory_ui.is_open:
                self.inventory_ui.handle_input(event)

            # Chest UI Input
            if self.chest_ui.is_open:
                self.chest_ui.handle_event(event)

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
            # Allow player movement and interactions while chest UI open
            self.interaction_manager.update(dt)
            self.player.input()
            self.interaction_manager.handle_interactions()

            was_moving = self.player.is_moving
            self.visible_sprites.update(dt)
            self.interaction_manager.check_teleporters(was_moving)
            # No time_system update or other world updates
            self.audio_manager.flush_ambient()
        else:
            # Update Time
            self.time_system.update(dt)

            # Input & Logic
            self.interaction_manager.update(dt)

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

        now = pygame.time.get_ticks()
        if now - self.last_fps_update > 1000:
            fps = self.clock.get_fps()
            pygame.display.set_caption(
                f"{Settings.GAME_TITLE} (v{Settings.VERSION}) - {fps:.1f} FPS"
            )
            self.last_fps_update = now

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
            self.lighting_manager.resize((Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT))
        logging.info(f"Fullscreen toggled: {self.is_fullscreen}")

    def _load_property_types(self) -> dict:
        """Load item property types from JSON for loot table validation."""
        path = os.path.join("assets", "data", "propertytypes.json")
        if not os.path.exists(path):
            logging.error(f"Game: Property types file not found at {path}")
            return dict()
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logging.error(f"Game: Failed to load property types: {e}")
            return dict()

    def _setup_logging(self):
        """Configure rotating file logging and console output."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, "game.log")

        # Setup Logger
        logger = logging.getLogger()
        logger.setLevel(Settings.LOG_LEVEL)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Daily Rotating File Handler
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when="D", interval=1, backupCount=7
        )
        file_handler.setFormatter(formatter)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Avoid duplicate handlers if re-initialized
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
