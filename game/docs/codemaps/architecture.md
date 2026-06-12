<!-- Generated: 2026-05-27 | Last doc-update: 2026-06-12 (player_constants, emote_constants, extended constants layer) | Files scanned: 75 | Token estimate: ~1450 -->

# Game Engine Architecture

## System Flow
`main.py` → `GameStateManager.__init__()` → `GameStateManager.run()` (Main Loop)
`GameStateManager._process_global_events()` → Cross-state keys (quit, fullscreen, audio toggle)
`GameStateManager._handle_title(events)` → `TitleScreen.handle_event()` → `GameEvent` → transition
`GameStateManager._handle_playing(events, dt)` → filters ESC → re-posts events → `Game.run_frame(dt)` → `GameEvent`
`GameStateManager._handle_paused(events, dt)` → `PauseScreen.handle_event()` → save/resume/goto_title
`Game._update(dt)` → `Player.update` → `NPC.update` → `TimeSystem.update` → `LightingManager`
`Game._draw()` → `RenderManager.draw_scene()` → `_draw_background()` → `CameraGroup.custom_draw(max_depth=player.depth)` → `_draw_foreground() → OccludingRect` → `CameraGroup.custom_draw(min_depth=player.depth+1)` → `_draw_hud()` → UI overlays

## Core Components

| Module | File | Lines | Role |
|---|---|---|---|
| **GameStateManager** | `src/engine/game_state_manager.py` | 309 | State machine (TITLE/PLAYING/PAUSED), global event routing, save/load orchestration |
| **Game** | `src/engine/game.py` | 420 | Gameplay orchestrator, thin wrappers to sub-managers |
| **RenderManager** | `src/engine/render_manager.py` | 597 | Scene rendering (background/foreground/HUD/occlusion/wading). `draw_foreground()→OccludingRect(Rect,depth,Surface\|None)`. `_create_composite_occlusion_surface()` applies `BLEND_RGBA_MULT` directly on composite. `_occ_composite_cache` caches partial-occlusion composites by camera offset & rect count. |
| **InteractionManager** | `src/engine/interaction.py` | 400 | Proximity/facing checks (objects, NPCs, pickups, chests, emotes, teleporters) |
| **EntityFactory** | `src/engine/entity_factory.py` | 265 | Entity spawning (interactive, teleport, NPC, pickup). Pattern: `EntityFactory(game: Any)`. |
| **MapLoader** | `src/engine/map_loader.py` | 115 | Map loading pipeline (parse, BGM, cleanup, spawn, player position) |
| **InputHandler** | `src/engine/input_handler.py` | 55 | Pygame event dispatch (interact, inventory, dialogue) |
| **CollisionChecker** | `src/engine/collision_checker.py` | 80 | Tile + entity collision checks |
| **SaveManager** | `src/engine/save_manager.py` | 271 | JSON save/load (3 slots), thumbnails. Path: `pygame.system.get_pref_path("adrien","game")` + fallback `saves/` |
| **GameEvents** | `src/engine/game_events.py` | 59 | `GameEvent` dataclass + `GameEventType` enum. Factory: `new_game()`, `load_requested(n)`, `pause_requested()`, etc. |
| **MapManager** | `src/map/manager.py` | 191 | Layer surfaces, TMJ state, collision tile queries. `get_foreground_layer_surface()` pre-renders static foreground tiles per layer. `get_vertical_move_props(tx, ty)` returns stair properties for a tile. `_fg_occlusion_grid` caches foreground occlusion rects per layer. |
| **TmjParser** | `src/map/tmj_parser.py` | 263 | TMJ/TSX parsing → structured `map_data` dict |
| **CameraGroup** | `src/entities/groups.py` | 121 | Y-sorted rendering, camera offset, dirty-flag sort cache. `stair_y_offset` shifts sprite render position when moving on stairs. `current_stair_offset` (float) drives interpolated visual Y shift per frame. |
| **AssetManager** | `src/engine/asset_manager.py` | 125 | Singleton image/font cache with per-map clear. `get_occlusion_mask(tile_surf)→Surface\|None`: BLEND_RGBA_MULT modulation mask cached by `id(tile_surf)`, built once at load time (A=OCCLUSION_ALPHA where opaque, A=255 where transparent). Cleared in `clear_cache()`. |
| **I18nManager** | `src/engine/i18n.py` | 58 | Singleton translation lookup via nested key paths |

## Key Subsystems

### UI & HUD
- **Constants pattern**: Every module has a `*_constants.py` sibling (imported by its module, never cross-imported). Shared colors only in `src/ui/ui_colors.py`. Protocols: `chest_protocol.py`, `inventory_protocol.py`.
- `dialogue_constants.py`: margins, Y offsets, colors, scale factors (14 constants)
- `speech_bubble_constants.py`: tile dict, layout dims, name-plate geometry (8 constants + `TILES` dict)
- `inventory_constants.py`: asset paths, grid coords, drag/animation constants (26 constants)
- `chest_constants.py`: asset paths, panel layout, arrow zones, draw constants (imports from `ui_colors`)
- **InventoryUI** (`src/ui/inventory.py`, 404L) + `inventory_draw.py` (247L): Grid + equipment slots, D&D state machine.
- **ChestUI** (`src/ui/chest.py`, 343L) + `chest_layout.py`, `chest_draw.py` (280L), `chest_transfer.py`. Paged scrolling (18-slot pages).
- **TitleScreen** (`src/ui/title_screen.py`, 431L): MAIN_MENU/LOAD_MENU/OPTIONS. 33 fire halos + 25 bioluminescent mushrooms. Returns `GameEvent`.
- **PauseScreen** (`src/ui/pause_screen.py`, 264L): Pre-render cache pattern — button surfaces computed once at `__init__`, zero `Surface()` in `draw()`.
- **SaveMenuOverlay** (`src/ui/save_menu.py`, 380L): Reusable save/load slot overlay. `refresh()` populates `_slots_info` + `_cached_title_surfs`.
- **GameHUD** (`src/ui/hud.py`, 90L): Time, health display. Pre-rendered text cache (Step 2).
- **Inventory** (`src/engine/inventory_system.py`, 133L): 28-slot padded list, equipment dict (8 slots).

### Dialogue & Speech
- **DialogueManager** (`src/ui/dialogue.py`, 271L): Typewriter, paginated text, 9-patch HUD overlay.
- **SpeechBubble** (`src/ui/speech_bubble.py`, 263L): NPC nine-patch bubble, name plate, auto-wrap 224px.

### Entities
- **InteractiveEntity** (`src/entities/interactive.py`, ~470L): Chests/levers/doors/signs/decor. Animated state machine, `day_night_driven`, halo lighting.
- **NPC** (`src/entities/npc.py`, 148L): Random AI patrol, interact trigger.
- **Player** (`src/entities/player.py`, 122L): Input, directional animation.
- **BaseEntity** (`src/entities/base.py`): Grid movement, `start_move()` interception, `_vertical_move`, `current_stair_offset`, `stair_start_offset`, `stair_target_offset`, `stair_move_distance` (stair interpolation fields), `_apply_stair_interception()`, `update_stair_offset()`.
- **PickupItem** (`src/entities/pickup.py`, 45L): Static collectible, looted state.
- **EmoteManager** (`src/entities/emote.py`, 62L): `!` / `?` / `frustration` emote sprites.
- **player_constants.py** (`src/entities/player_constants.py`): 9 constants — spritesheet grid (`PLAYER_SPRITESHEET_COLS/ROWS`), animation (`PLAYER_ANIM_FRAME_DURATION`, `PLAYER_FRAMES_PER_ROW`, `PLAYER_ROW_OFFSETS`), audio (`PLAYER_FOOTSTEP_FRAMES`, `PLAYER_FOOTSTEP_VOLUME`), starting stats (`PLAYER_INITIAL_LEVEL/HP/GOLD`).
- **emote_constants.py** (`src/entities/emote_constants.py`): `EMOTE_RISE_PX = 15` — vertical rise in px during emote display animation.

### Engine Support
- **LightingManager** (`src/engine/lighting.py`, 300L): Night overlay, additive torch masks, slanted window beam shafts.
- **TimeSystem** (`src/engine/time_system.py`, ~140L): In-game clock, seasons, `night_alpha`, `brightness`. `_total_minutes @property` auto-refreshes cache.
- **AudioManager** (`src/engine/audio.py`, 248L): BGM/SFX (32 channels), mute toggle, spatial ambient.
- **LootTable** (`src/engine/loot_table.py`, 130L): JSON-driven chest contents, stack splitting.
- **WorldState** (`src/engine/world_state.py`, 22L): `{map_name}_{tiled_id}` keyed dict for cross-map persistence.
- **engine_constants.py** (`src/engine/engine_constants.py`): `COLOR_PLACEHOLDER_MAGENTA/BLUE` (debug fallback colors), `SPRITESHEET_FALLBACK_SIZE` (32×32), `SPRITESHEET_FALLBACK_FRAME_COUNT` (16), `GRASS_MAX_DEPTH` (1), `TILED_PROJECT_PATH`. Imported by `spritesheet.py` and `map/manager.py`.

## Documentation & Tooling
```
docs/
  specs/            21 implementation specs (Stream Coding v6.0 — Linked Test Functions + Deep Links)
  ADRs/             8 ADRs (ADR-001..008). ADR-008: FRect non-migration.
  strategic/        MASTER_ROADMAP.md, game_vision.md, best_practices_remediation_blueprint.md
  traceability.md   Auto-generated (scripts/dev/tc_report.py)
  codemaps/         Architecture maps (this directory)
scripts/
  assets/           Asset processing (banners, diagonal walls)
  autotiles/        Autotile pipeline (rpgmaker, blob autotiles)
  calibration/      Calibration tools (halos)
  build/            Build & release tools (release.py, get_version.py)
  dev/              Development utilities (check_lengths.py, tc_report.py, profile_game.py)
  sc-commit.sh      Commit helper script (Stream Coding sandbox)
.agents/
  learnings/        6 domain files (methodology_and_docs, game_engine, audio_engine, ui, testing, map_rendering)
  learnings.md      Index by domain
```

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE 2.5.7 (SDL 2.32.10)
- **Data**: Tiled (TMJ/TSX), JSON (settings, i18n, loot tables, saves)
- **Tests**: Pytest 9.0.3 — **1126 tests** across `tests/{engine,entities,graphics,map,ui,scripts}/`
- **Traceability**: `@pytest.mark.tc("DOMAIN-TYPE-ID")` markers — `docs/traceability.md`
- **Pyright**: basic mode, `reportOptional*` suppressed. 0 errors/warnings.
- **Path handling**: `pathlib.Path` throughout `src/` (55 `os.path.join` migrated, Step 11). `os` retained for `os.path.exists`/`makedirs`/`listdir`.
- **Perf wins (commit `4a2e55e`)**: `_cached_world_time` (–335 allocs/frame), `_is_on_cache` (–334x brightness/frame), `_frame_anim_by_layer` (–311 generator calls/frame), surface pool (–3+ SRCALPHA allocs/frame). See `game/docs/ADRs/ADR-PERF-001..004`.
- **Best practices (commit `f63574d`)**: DT clamp 100ms, text pre-render cache (HUD/Inventory/Chest), `@override` annotations, type aliases, `pathlib.Path`.
