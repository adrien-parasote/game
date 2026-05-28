<!-- Generated: 2026-05-27 | Last doc-update: 2026-05-27 (Steps 1-11 remédiation) | Files scanned: 73 | Token estimate: ~1400 -->

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
| **RenderManager** | `src/engine/render_manager.py` | 521 | Scene rendering (background/foreground/HUD/occlusion/wading). `draw_foreground()→OccludingRect`. Frame-anim pre-computed 1x/frame. |
| **InteractionManager** | `src/engine/interaction.py` | 400 | Proximity/facing checks (objects, NPCs, pickups, chests, emotes, teleporters) |
| **EntityFactory** | `src/engine/entity_factory.py` | 265 | Entity spawning (interactive, teleport, NPC, pickup). Pattern: `EntityFactory(game: Any)`. |
| **MapLoader** | `src/engine/map_loader.py` | 115 | Map loading pipeline (parse, BGM, cleanup, spawn, player position) |
| **InputHandler** | `src/engine/input_handler.py` | 55 | Pygame event dispatch (interact, inventory, dialogue) |
| **CollisionChecker** | `src/engine/collision_checker.py` | 80 | Tile + entity collision checks |
| **SaveManager** | `src/engine/save_manager.py` | 271 | JSON save/load (3 slots), thumbnails. Path: `pygame.system.get_pref_path("adrien","game")` + fallback `saves/` |
| **GameEvents** | `src/engine/game_events.py` | 59 | `GameEvent` dataclass + `GameEventType` enum. Factory: `new_game()`, `load_requested(n)`, `pause_requested()`, etc. |
| **MapManager** | `src/map/manager.py` | 191 | Layer surfaces, TMJ state, collision tile queries |
| **TmjParser** | `src/map/tmj_parser.py` | 263 | TMJ/TSX parsing → structured `map_data` dict |
| **CameraGroup** | `src/entities/groups.py` | 121 | Y-sorted rendering, camera offset, dirty-flag sort cache |
| **AssetManager** | `src/engine/asset_manager.py` | 76 | Singleton image/font cache with per-map clear |
| **I18nManager** | `src/engine/i18n.py` | 58 | Singleton translation lookup via nested key paths |

## Key Subsystems

### UI & HUD
- **Constants**: All UI modules have `_constants.py`. Shared colors in `src/ui/ui_colors.py`. Protocols: `chest_protocol.py`, `inventory_protocol.py`.
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
- **PickupItem** (`src/entities/pickup.py`, 45L): Static collectible, looted state.
- **EmoteManager** (`src/entities/emote.py`, 62L): `!` / `?` / `frustration` emote sprites.

### Engine Support
- **LightingManager** (`src/engine/lighting.py`, 300L): Night overlay, additive torch masks, slanted window beam shafts.
- **TimeSystem** (`src/engine/time_system.py`, ~140L): In-game clock, seasons, `night_alpha`, `brightness`. `_total_minutes @property` auto-refreshes cache.
- **AudioManager** (`src/engine/audio.py`, 248L): BGM/SFX (32 channels), mute toggle, spatial ambient.
- **LootTable** (`src/engine/loot_table.py`, 130L): JSON-driven chest contents, stack splitting.
- **WorldState** (`src/engine/world_state.py`, 22L): `{map_name}_{tiled_id}` keyed dict for cross-map persistence.

## Documentation & Tooling
```
docs/
  specs/            21 implementation specs (Stream Coding v6.0 — Linked Test Functions + Deep Links)
  ADRs/             8 ADRs (ADR-001..008). ADR-008: FRect non-migration.
  strategic/        MASTER_ROADMAP.md, game_vision.md, best_practices_remediation_blueprint.md
  traceability.md   Auto-generated (scripts/tc_report.py)
  codemaps/         Architecture maps (this directory)
scripts/
  autotiles/        Autotile pipeline
  tc_report.py      Spec↔Test traceability (CLI + --markdown)
  profile_game.py   Performance profiling
.agents/
  learnings/        6 domain files (methodology_and_docs, game_engine, audio_engine, ui, testing, map_rendering)
  learnings.md      Index by domain
```

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE 2.5.7 (SDL 2.32.10)
- **Data**: Tiled (TMJ/TSX), JSON (settings, i18n, loot tables, saves)
- **Tests**: Pytest 9.0.3 — **1094 tests** across `tests/{engine,entities,graphics,map,ui,scripts}/`
- **Traceability**: `@pytest.mark.tc("DOMAIN-TYPE-ID")` markers — `docs/traceability.md`
- **Pyright**: basic mode, `reportOptional*` suppressed. 0 errors/warnings.
- **Path handling**: `pathlib.Path` throughout `src/` (55 `os.path.join` migrated, Step 11). `os` retained for `os.path.exists`/`makedirs`/`listdir`.
- **Perf wins (commit `4a2e55e`)**: `_cached_world_time` (–335 allocs/frame), `_is_on_cache` (–334x brightness/frame), `_frame_anim_by_layer` (–311 generator calls/frame), surface pool (–3+ SRCALPHA allocs/frame). See `docs/game/ADRs/ADR-PERF-001..004`.
- **Best practices (commit `f63574d`)**: DT clamp 100ms, text pre-render cache (HUD/Inventory/Chest), `@override` annotations, type aliases, `pathlib.Path`.
