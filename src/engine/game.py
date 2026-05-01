import pygame
import sys
import logging
import logging.handlers
import os
import json
from src.entities.player import Player
from src.entities.interactive import InteractiveEntity
from src.entities.npc import NPC
from src.entities.teleport import Teleport
from src.entities.pickup import PickupItem
from src.entities.groups import CameraGroup
from src.map.manager import MapManager
from src.map.layout import OrthogonalLayout
from src.engine.time_system import TimeSystem
from src.engine.world_state import WorldState
from src.config import Settings
from src.ui.hud import GameHUD
from src.ui.dialogue import DialogueManager
from src.ui.speech_bubble import SpeechBubble
from src.engine.audio import AudioManager
from src.engine.asset_manager import AssetManager
from src.engine.interaction import InteractionManager
from src.engine.loot_table import LootTable
from src.ui.chest import ChestUI
from src.engine.i18n import I18nManager
from src.ui.inventory import InventoryUI


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
        if key in io: return io[key]
        sp = io.get("sprite", {})
        if isinstance(sp, dict) and key in sp: return sp[key]
            
    sp = props.get("sprite", {})
    if isinstance(sp, dict) and key in sp:
        return sp[key]
        
    return default


class Game:
    """Main game class that manages the core loop and state."""
    
    def __init__(self):
        # 1. Initialize Localization
        self.i18n = I18nManager()
        self.i18n.load(Settings.LOCALE)
        
        self._setup_logging()
        pygame.init()
        logging.info(f"Initializing Game Engine v{Settings.VERSION}...")
        
        # Display initialization with Fullscreen support
        display_flags = pygame.FULLSCREEN if Settings.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT), 
            display_flags
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

        
        # Local state
        self.is_fullscreen = Settings.FULLSCREEN
        self.last_fps_update = 0
        
        # Time System
        self.time_system = TimeSystem(initial_hour=Settings.INITIAL_HOUR)
        self.hud = GameHUD(self.time_system)
        
        # World State
        self.world_state = WorldState()
        
        # Loot Table (chest contents)
        self.loot_table = LootTable()
        property_types = self._load_property_types()
        self.loot_table.load(
            os.path.join("assets", "data", "loot_table.json"),
            property_types
        )
        
        # Dialogue System (signs / interactive objects)
        self.dialogue_manager = DialogueManager()

        # Speech bubble (NPC PNG dialogues)
        self.speech_bubble = SpeechBubble(max_width_px=224, padding=8, tail_gap=4)
        am = AssetManager()
        self.speech_bubble.set_font(
            am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        )
        # Active NPC bubble state: {npc, text, page} or None
        self._npc_bubble: dict | None = None
        
        # Audio System
        self.audio_manager = AudioManager()
        
        # Interaction System
        self.interaction_manager = InteractionManager(self)
        
        logging.info(f"Screen setup: {Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT} (Fullscreen: {self.is_fullscreen})")
        
        # Player is persisted across maps
        self.player = Player((0, 0), self.visible_sprites, speed=Settings.PLAYER_SPEED, element_id="player")
        self.player.audio_manager = self.audio_manager
        self.player.emote_manager.emote_group = self.emote_group
        self.player.collision_func = self._is_collidable
        
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
                    with open(world_path, "r", encoding="utf-8") as f:
                        world_data = json.load(f)
                        default_map = world_data.get("maps", [{}])[0].get("fileName", "00-spawn.tmj")
                except Exception as e:
                    logging.error(f"Failed to read world.world: {e}")
                
        self._load_map(default_map)

    def _load_map(self, map_name: str, target_spawn_id: str = None, transition_type: str = "instant"):
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
        
        # Clean entities for new map (excluding player)
        self.interactives.empty()
        self.npcs.empty()
        self.obstacles_group.empty()
        self.teleports_group.empty()
        self.pickups.empty()
        
        # Only keep player in visible sprites
        self.visible_sprites.empty()
        self.visible_sprites.add(self.player)
        
        # Spawn Entities from Map
        self._current_map_name = map_name
        self._spawn_entities(map_result.get("entities", []), map_name)
        
        # Resolve spawn exact position 
        half_tile = self.tile_size // 2
        spawn_pos = (world_width_px // 2, world_height_px // 2) # Center fallback
        
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
                logging.warning(f"No valid spawn_player found on map {map_name}. Defaulting to center.")
                
        # Force player transform
        self.player.pos = pygame.math.Vector2(spawn_pos)
        self.player.target_pos = pygame.math.Vector2(spawn_pos)
        self.player.rect.center = (int(spawn_pos[0]), int(spawn_pos[1]))
        self.player.is_moving = False
        self.player.direction = pygame.math.Vector2(0, 0)
        logging.info(f"Loaded map {map_name}, player spawned at {spawn_pos}")

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
            sub_type=_get_property(props, "sub_type", "unknown"),
            sprite_sheet=_get_property(props, "sprite_sheet", ""),
            position=int(_get_property(props, "position", 0)),
            depth=int(_get_property(props, "depth", 1)),
            start_row=int(_get_property(props, "start_frame", 0)),
            end_row=int(_get_property(props, "end_frame", 3)),
            width=int(_get_property(props, "width", ent.get("width", 32))),
            height=int(_get_property(props, "height", ent.get("height", 32))),
            tiled_width=ent.get("width", 32),
            tiled_height=ent.get("height", 32),
            obstacles_group=self.obstacles_group,
            is_passable=_get_property(props, "is_passable", False),
            is_animated=_get_property(props, "is_animated", False),
            is_on=_get_property(props, "is_on"),
            halo_size=int(_get_property(props, "halo_size", 0)),
            halo_color=_get_property(props, "halo_color", "[255, 255, 255]"),
            halo_alpha=int(_get_property(props, "halo_alpha", 130)),
            particles=_get_property(props, "particles", False),
            particle_count=int(_get_property(props, "particle_count", 0)),
            element_id=element_id,
            target_id=target_id,
            activate_from_anywhere=_get_property(props, "activate_from_anywhere", False),
            facing_direction=_get_property(props, "facing_direction"),
            sfx=_get_property(props, "sfx", "")
        )

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
            _get_property(props, "target_map", ""),
            _get_property(props, "target_spawn_id", ""),
            _get_property(props, "transition_type", "instant"),
            _get_property(props, "required_direction", "any")
        )
        tp.sfx = _get_property(props, "sfx", "")

    def _spawn_npc(self, ent: dict, props: dict, e_pos: tuple):
        """Instantiate an NPC from map data."""
        npc = NPC(
            pos=e_pos,
            groups=[self.visible_sprites, self.npcs],
            wander_radius=int(_get_property(props, "wander_radius", 1)),
            sheet_name=_get_property(props, "sprite_sheet", "01-character.png"),
            element_id=_get_property(props, "element_id") or str(ent.get("id"))
        )
        npc.name = _get_property(props, "name", ent.get("name", ""))
        npc.collision_func = self._is_collidable
        logging.info(f"Spawned NPC '{npc.element_id}' at {e_pos}")

    def _spawn_pickup(self, ent: dict, props: dict, e_pos: tuple):
        """Instantiate a PickupItem from map data, skipping already-collected ones."""
        item_id = _get_property(props, "object_id")
        sprite = _get_property(props, "sprite_sheet")
        quantity = int(_get_property(props, "quantity", 1))
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
            sprite_sheet=sprite,
            quantity=quantity,
            element_id=str(tiled_id)
        )
        if state_key:
            item._world_state_key = state_key  # Attach key for persistence on pickup
        logging.info(f"Spawned PickupItem '{item_id}' (x{quantity}) at {e_pos}")



    def _is_collidable(self, px_center: float, py_center: float, requester=None) -> bool:
        """Collision checking adapter for Entity target position."""
        # 1. Check Map Tiles
        wx, wy = self.layout.to_world(px_center, py_center)
        if self.map_manager.is_collidable(int(wx), int(wy)):
            return True
            
        # 2. Check Dynamic Obstacles (Doors, etc.)
        for obj in self.obstacles_group:
            if obj == requester: continue
            if obj.rect.collidepoint(px_center, py_center):
                return True
        
        # 3. Check NPCs
        for npc in self.npcs:
            if npc == requester: continue
            if npc.rect.collidepoint(px_center, py_center):
                return True
        
        # 4. Check Player (if requester is an NPC)
        if self.player != requester:
            if self.player.rect.collidepoint(px_center, py_center):
                return True
                
        return False

    def _draw_background(self):
        """Draw tiles with depth <= player depth (behind player) using pre-rendered surfaces."""
        cam_offset = self.visible_sprites.offset
        
        # Get all layers that should be behind the player
        for layer_id in self.map_manager.layer_order:
            # We need to know the depth of tiles in this layer. 
            # In Tiled, layers usually have a uniform depth via properties.
            # If not, we fall back to checking the first non-zero tile.
            sample_tile_id = 0
            for row in self.map_manager.layers[layer_id]:
                for tid in row:
                    if tid != 0:
                        sample_tile_id = tid
                        break
                if sample_tile_id != 0: break
            
            # Use name-based hint if available (e.g. "01-layer" -> depth 1)
            layer_name = self.map_manager.layer_names.get(layer_id, "")
            name_depth = None
            if len(layer_name) >= 3 and layer_name[:2].isdigit() and layer_name[2] == "-":
                name_depth = int(layer_name[:2])
            
            if name_depth is not None:
                depth = name_depth
            else:
                depth = getattr(self.map_manager.tiles.get(sample_tile_id), "depth", 0) if sample_tile_id else 0
            
            if depth <= self.player.depth:
                surface = self.map_manager.get_layer_surface(layer_id, pygame)
                if surface:
                    self.screen.blit(surface, (cam_offset.x, cam_offset.y))

    def _draw_foreground(self):
        """Draw tiles with depth > player depth (in front of player). Use cached occluded versions if needed."""
        cam_offset = self.visible_sprites.offset
        screen_rect = self.screen.get_rect()
        viewport_world = pygame.Rect(-cam_offset.x, -cam_offset.y, screen_rect.width, screen_rect.height)
        
        # Get visual rect anchored bottomright to physical rect for correct occlusion testing
        visual_rect = self.player.image.get_rect(bottomright=self.player.rect.bottomright)
        player_screen_rect = visual_rect.move(cam_offset.x, cam_offset.y)
        
        for px, py, tile_id, depth in self.map_manager.get_visible_chunks(viewport_world):
            if depth > self.player.depth:
                tile_data = self.map_manager.tiles[tile_id]
                screen_pos = (px + cam_offset.x, py + cam_offset.y)
                dest_rect = pygame.Rect(screen_pos[0], screen_pos[1], self.tile_size, self.tile_size)
                
                if player_screen_rect.colliderect(dest_rect):
                    # Use pre-cached occluded image
                    self.screen.blit(tile_data.occluded_image or tile_data.image, screen_pos)
                else:
                    self.screen.blit(tile_data.image, screen_pos)

    def _draw_hud(self):
        """Draw time and season HUD overlay (top-right, fixed to screen)."""
        self.hud.draw(self.screen)

    def _trigger_dialogue(self, element_id: str, title: str = ""):
        """Fetch localized message and start dialogue (signs / objects → bottom box)."""
        map_base = self._current_map_name.split('.')[0]
        full_key = f"{map_base}-{element_id}"
        msg = self.i18n.get(f"dialogues.{full_key}")
        if msg:
            self.dialogue_manager.start_dialogue(msg, title=title)
        else:
            logging.warning(f"Dialogue key not found: {full_key}")

    def _trigger_npc_bubble(self, npc, element_id: str) -> None:
        """Fetch localized message and attach a speech bubble to *npc*."""
        map_base = self._current_map_name.split('.')[0]
        full_key = f"{map_base}-{element_id}"
        msg = self.i18n.get(f"dialogues.{full_key}")
        if not msg:
            logging.warning(f"NPC bubble key not found: {full_key}")
            return
        self._npc_bubble = {"npc": npc, "text": msg, "page": 0}
        logging.info(f"NPC bubble started for '{element_id}': {msg[:40]}...")

    def _advance_npc_bubble(self) -> None:
        """Advance NPC bubble page or close it on last page."""
        if self._npc_bubble is None:
            return
        # Compute total pages the same way SpeechBubble.draw() does
        lines = self.speech_bubble._wrap_text(self._npc_bubble["text"])
        line_height = self.speech_bubble.font.get_linesize()
        max_lines = max(1, self.speech_bubble.max_width_px // line_height)
        total_pages = max(1, (len(lines) + max_lines - 1) // max_lines)
        if self._npc_bubble["page"] < total_pages - 1:
            self._npc_bubble["page"] += 1
        else:
            self._npc_bubble = None
            for npc in self.npcs:
                if npc.state == 'interact':
                    npc.state = 'idle'

    def toggle_entity_by_id(self, target_id: str, depth: int = 0):
        """Toggle the state of any entity matching element_id == target_id."""
        if not target_id:
            return
            
        if depth > 1:
            logging.warning(f"Interaction chaining loop detected for target_id={target_id}. Breaking chain.")
            return

        for group in (self.interactives, self.npcs):
            for entity in group:
                if getattr(entity, 'element_id', None) == target_id:
                    if hasattr(entity, 'interact'):
                        entity.interact(self.player)
                        
                        if getattr(entity, "sfx", None):
                            self.audio_manager.play_sfx(entity.sfx, getattr(entity, "element_id", None))
                        
                        # Save state
                        if hasattr(entity, '_world_state_key'):
                            self.world_state.set(entity._world_state_key, {'is_on': entity.is_on})
                        
                        next_target = getattr(entity, 'target_id', None)
                        if next_target:
                            self.toggle_entity_by_id(next_target, depth + 1)

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
                self.time_system.update(dt) # Flow of time continues
                
                self._draw_scene()
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
                
                self._draw_scene()
                fade_surf.set_alpha(alpha)
                self.screen.blit(fade_surf, (0, 0))
                pygame.display.update()
                
        self.clock.tick(Settings.FPS) # Reset dt so next frame logic doesn't jump

    def _check_teleporters(self, was_moving: bool):
        """Active spatial check testing if interaction just resolved over teleport rect."""
        just_arrived = was_moving and not self.player.is_moving
        intent_active = not was_moving and not self.player.is_moving and self.player.direction.magnitude() > 0
        
        if not just_arrived and not intent_active:
            return 
            
        for tp in self.teleports_group:
            # Player hits teleport zone via strict collision rect
            if not self.player.rect.colliderect(tp.rect):
                continue
            
            req = getattr(tp, 'required_direction', 'any')
            
            if just_arrived:
                # Direction guard: on arrival, must match required direction (unless 'any')
                if req != 'any' and self.player.current_state != req:
                    logging.debug(f"Teleport skipped (Arrival) — required '{req}', player facing '{self.player.current_state}'")
                    continue
            elif intent_active:
                # Intent guard: do not trigger intent for 'any' portals to avoid trapping the player
                # when they try to turn around.
                if req == 'any':
                    continue
                if self.player.current_state != req:
                    logging.debug(f"Teleport skipped (Intent) — required '{req}', player faced '{self.player.current_state}'")
                    continue
                
            logging.info(f"Teleport triggered -> {tp.target_map} / {tp.target_spawn_id}")
            if getattr(tp, 'sfx', None):
                self.audio_manager.play_sfx(tp.sfx, str(id(tp)))
                
            self.transition_map(tp.target_map, tp.target_spawn_id, tp.transition_type)
            break

    def _draw_scene(self):
        """A helper representing the entire scene rendering logic."""
        self.screen.fill(Settings.COLOR_BG)
        self.visible_sprites.calculate_offset(self.player)
        self._draw_background()
        self.visible_sprites.custom_draw(self.screen)
        self._draw_foreground()
        
        night_alpha = self.time_system.night_alpha
        if night_alpha > 0:
            if not hasattr(self, '_night_overlay') or self._night_overlay.get_size() != self.screen.get_size():
                self._night_overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            
            self._night_overlay.fill((0, 0, 0, night_alpha))
            self.screen.blit(self._night_overlay, (0, 0))
            
        cam_offset = self.visible_sprites.offset
        for obj in self.interactives:
            if hasattr(obj, 'draw_effects'):
                obj.draw_effects(self.screen, cam_offset, night_alpha)
            
        if not self.inventory_ui.is_open:
            self._draw_hud()
        
        # Draw Emotes (after HUD, with camera offset)
        for sprite in self.emote_group:
            screen_pos = (sprite.rect.x + cam_offset.x, sprite.rect.y + cam_offset.y)
            self.screen.blit(sprite.image, screen_pos)

        
        if self.dialogue_manager.is_active:
            self.dialogue_manager.draw(self.screen)

        # NPC speech bubble — drawn above NPC in screen-space
        if self._npc_bubble is not None:
            npc = self._npc_bubble["npc"]
            cam = self.visible_sprites.offset
            # Build a screen-space rect from the NPC world rect
            npc_screen_rect = npc.rect.move(cam.x, cam.y)
            self.speech_bubble.draw(
                self.screen,
                npc_screen_rect,
                self._npc_bubble["text"],
                page=self._npc_bubble["page"],
            )
            
        if self.inventory_ui.is_open:
            self.inventory_ui.draw(self.screen)
        if self.chest_ui.is_open:
            self.chest_ui.draw(self.screen)

    def run(self):
        """Main game loop optimized for 60 FPS."""
        while True:
            self._handle_events()
            
            # Update (Fixed 60 FPS)
            dt = self.clock.tick(Settings.FPS) / 1000.0
            self._update(dt)

            # Draw complete sequence
            self._draw()

    def _handle_events(self):
        """Handle all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == Settings.QUIT_KEY:
                    pygame.quit()
                    sys.exit()
                if event.key == Settings.TOGGLE_FULLSCREEN_KEY:
                    self.toggle_fullscreen()
                
                # NPC bubble advance (takes priority over box dialogue)
                if event.key == Settings.INTERACT_KEY and self._npc_bubble is not None:
                    self._advance_npc_bubble()

                # Box dialogue advance (signs, objects)
                elif event.key == Settings.INTERACT_KEY and self.dialogue_manager.is_active:
                    self.dialogue_manager.advance()
                    if not self.dialogue_manager.is_active:
                        # Resume NPCs
                        for npc in self.npcs:
                            if npc.state == 'interact':
                                npc.state = 'idle'
                                
                # Inventory Toggle
                if event.key == Settings.INVENTORY_KEY and not self.dialogue_manager.is_active and self._npc_bubble is None and not self.chest_ui.is_open:
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
            self._check_teleporters(was_moving)
            # No time_system update or other world updates
        else:
            # Update Time
            self.time_system.update(dt)
            
            # Input & Logic
            self.interaction_manager.update(dt)
                
            self.player.input()
            self.interaction_manager.handle_interactions()
            
            was_moving = self.player.is_moving
            self.visible_sprites.update(dt)
            self._check_teleporters(was_moving)
            
            # CPU Freeze optimization for NPCs -> freeze if outside enlarged viewport
            screen_rect = self.screen.get_rect()
            viewport_world = screen_rect.move(-self.visible_sprites.offset.x, -self.visible_sprites.offset.y)
            viewport_world.inflate_ip(128, 128)
            
            for npc in self.npcs:
                npc.is_visible = viewport_world.colliderect(npc.rect)
                npc.update(dt)
                
            for obj in self.interactives:
                obj.update(dt)
                
        # Dynamic Title Update (Every 1s)
        now = pygame.time.get_ticks()
        if now - self.last_fps_update > 1000:
            fps = self.clock.get_fps()
            pygame.display.set_caption(f"{Settings.GAME_TITLE} (v{Settings.VERSION}) - {fps:.1f} FPS")
            self.last_fps_update = now

    def _draw(self):
        """Draw complete scene and update display."""
        self._draw_scene()
        pygame.display.update()

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
                (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT), 
                display_flags
            )
        logging.info(f"Fullscreen toggled: {self.is_fullscreen}")

    def _load_property_types(self) -> dict:
        """Load item property types from JSON for loot table validation."""
        path = os.path.join("assets", "data", "propertytypes.json")
        if not os.path.exists(path):
            logging.error(f"Game: Property types file not found at {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Game: Failed to load property types: {e}")
            return {}

    def _setup_logging(self):
        """Configure rotating file logging and console output."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
            
        log_file = os.path.join(log_dir, "game.log")
        
        # Setup Logger
        logger = logging.getLogger()
        logger.setLevel(Settings.LOG_LEVEL)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Daily Rotating File Handler
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when='D', interval=1, backupCount=7
        )
        file_handler.setFormatter(formatter)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Avoid duplicate handlers if re-initialized
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
