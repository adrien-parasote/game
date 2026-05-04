<!-- Generated: 2026-05-04 | Files scanned: 49 | Token estimate: ~520 -->

# Game Engine Architecture

## System Flow
`main.py` → `GameStateManager.__init__()` → `GameStateManager.run()` (Main Loop)
`GameStateManager._process_global_events()` → Cross-state keys (quit, fullscreen, audio toggle)
`GameStateManager._handle_title(events)` → `TitleScreen.handle_event()` → `GameEvent` → transition
`GameStateManager._handle_playing(events, dt)` → filters ESC → re-posts events → `Game.run_frame(dt)` → `GameEvent`
`GameStateManager._handle_paused(events, dt)` → `PauseScreen.handle_event()` → save/resume/goto_title
`Game._update(dt)` → `Player.update` → `NPC.update` → `TimeSystem.update` → `LightingManager`
`Game._draw()` → `RenderManager.draw_scene()` → `_draw_background()` → `CameraGroup.custom_draw()` (Y-sorted) → `_draw_foreground()` → `_draw_hud()` → UI overlays

## Core Components

| Module | File | Lines | Role |
|---|---|---|---|
| **GameStateManager** | `src/engine/game_state_manager.py` | 300 | Top-level state machine (TITLE/PLAYING/PAUSED), global event routing, save/load orchestration |
| **Game** | `src/engine/game.py` | 762 | Gameplay orchestrator, entity spawning, event dispatch, map transitions |
| **RenderManager** | `src/engine/render_manager.py` | 109 | Scene rendering pipeline (background, foreground, HUD, overlays) |
| **InteractionManager** | `src/engine/interaction.py` | 440 | Proximity/facing checks for objects, NPCs, pickups, chests, emotes, teleporters |
| **SaveManager** | `src/engine/save_manager.py` | 218 | JSON save/load (3 slots), inventory + world state serialization, PNG thumbnails |
| **GameEvents** | `src/engine/game_events.py` | 59 | `GameEvent` dataclass + `GameEventType` enum. Factory methods: `new_game()`, `load_requested(slot_id)`, `quit()`, `pause_requested()`, `resume()`, `save_requested(slot_id)`, `goto_title()` |
| **MapManager** | `src/map/manager.py` | 185 | Layer surfaces, TMJ state, collision tile queries, window positions |
| **TmjParser** | `src/map/tmj_parser.py` | 231 | TMJ/TSX parsing → structured `map_data` dict |
| **CameraGroup** | `src/entities/groups.py` | 82 | Y-sorted rendering, camera offset, clamped scroll |
| **AssetManager** | `src/engine/asset_manager.py` | 76 | Singleton image/font cache with per-map clear |
| **I18nManager** | `src/engine/i18n.py` | 58 | Singleton translation lookup via nested key paths |

## Key Subsystems

### UI & HUD Components
- **Constants Architecture**: All UI and Engine modules have dedicated `_constants.py` modules for layout, color, and behavior values (`src/ui/inventory_constants.py`, `src/engine/lighting_constants.py`, `src/engine/game_state_constants.py`, `src/entities/interactive_constants.py`, `src/ui/dialogue_constants.py`). Shared UI colors are centralized in `src/ui/ui_colors.py`. Codebase is 100% localized to English.
- **InventoryUI** (`src/ui/inventory.py`, 502L): Grid + equipment slots, D&D state machine, tab switching, item info zone.
- **ChestUI** (`src/ui/chest.py`, 393L) + mixins: `chest_layout.py` (slot geometry), `chest_draw.py` (rendering), `chest_transfer.py` (item movement logic). Chest ↔ Inventory transfer, paged scrolling (18-slot pages), D&D across panels.
- **TitleScreen** (`src/ui/title_screen.py`, 431L): Main menu state machine (MAIN_MENU/LOAD_MENU/OPTIONS). Renders dynamic title using `title_screen_constants.py`. **33 fire halos** (`BACKGROUND_LIGHTS`, BLEND_RGB_ADD, flicker) + **25 bioluminescent mushrooms** (`MUSHROOM_LIGHTS`, slow breath `sin*0.15`). Resolution-independent: logical 1280×720 mapped via `_light_scale_x/y` from `screen.get_size()`. Returns `GameEvent`.
- **PauseScreen** (`src/ui/pause_screen.py`, 276L): In-game pause overlay (MAIN/SAVE_MENU states), save/resume/goto_title, gaussian blur halo hover. `notify_save_result(bool)` for feedback.
- **SaveMenuOverlay** (`src/ui/save_menu.py`, 207L): Reusable save/load slot overlay. `refresh()` populates `_slots_info` from `SaveManager.list_slots()`. `get_clicked_slot(event)→int|None`. `SaveSlotUI` renders individual slot with background sprite, PNG thumbnail, additive halo.
- **GameHUD** (`src/ui/hud.py`, 88L): In-game HUD (time, health).
- **Inventory** (`src/engine/inventory_system.py`, 133L): 28-slot padded list (`None` fill), equipment dict (8 slots), `add/remove/equip/unequip`.

### Dialogue & Speech
- **DialogueManager** (`src/ui/dialogue.py`, 271L): Typewriter, paginated text, 9-patch HUD overlay. Uses `dialogue_constants.py`.
- **SpeechBubble** (`src/ui/speech_bubble.py`, 263L): NPC nine-patch bubble, name plate, paginated text, auto-wrap 224px.

### Entities
- **InteractiveEntity** (`src/entities/interactive.py`, 429L): Chests, levers, doors, signs, animated decor. Animated state machine (`is_on`), `day_night_driven` auto-lighting, halo lighting, `restore_state` from WorldState. Uses `interactive_constants.py`.
- **NPC** (`src/entities/npc.py`, 148L): Random AI patrol, interact trigger, pending dialogue queue (waits for movement to finish).
- **Player** (`src/entities/player.py`, 122L): Input, directional animation, emote trigger.
- **PickupItem** (`src/entities/pickup.py`, 45L): Static collectible, looted state synced to WorldState.
- **EmoteManager** (`src/entities/emote.py`, 62L): `!` / `?` / `frustration` emote sprites above player.

### Engine Support
- **LightingManager** (`src/engine/lighting.py`, 269L): Night overlay, additive torch masks, slanted window beam shafts (continuous cosine blending at dawn/dusk). Uses `lighting_constants.py`.
- **TimeSystem** (`src/engine/time_system.py`, 124L): In-game clock, seasons, `night_alpha`, `brightness`.
- **AudioManager** (`src/engine/audio.py`, 248L): BGM/SFX via pygame mixer (32 channels), mute toggle, spatial ambient audio with `ambient_channels` dict + 20% floor volume, footstep normalization.
- **LootTable** (`src/engine/loot_table.py`, 130L): JSON-driven chest contents, stack splitting, slot overflow trimming.
- **WorldState** (`src/engine/world_state.py`, 22L): `{map_name}_{tiled_id}` keyed dict for cross-map persistence.

## Documentation & Tooling
```
docs/
  specs/            18 implementation specs (Stream Coding v6.0 — Linked Test Functions + Deep Links)
  traceability.md   Auto-generated spec↔test coverage matrix (scripts/tc_report.py) — 143/143 (100%)
  CODEMAPS/         Architecture maps (this directory)
  strategic/        MASTER_ROADMAP.md, game_vision.md, blueprint.md
  ADRs/             3 Architecture Decision Records
scripts/
  tc_report.py          Spec↔Test traceability report (CLI + --markdown export)
  calibrate_halos.py    Outil interactif calibration halos (FULLSCREEN|SCALED) → calibration_result.py
  apply_calibration.py  Inject calibration_result.py → title_screen_constants.py
  get_version.py        Version bumping utility
  profile_game.py       Performance profiling
.agents/
  learnings/        5 domain learning files (workflow_optimization, game_engine, audio_engine, ui, testing)
  rules/            coding-standards.md + language rules
```

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE 2.5.7 (SDL 2.32.10)
- **Data Format**: Tiled (TMJ/TSX), JSON (settings, i18n, loot tables, saves)
- **Test Suite**: Pytest 9.0.3, **532 tests**, **92% coverage** — domain-based layout: `tests/{engine,entities,graphics,map,ui}/` (34 files across 5 domains)
- **Traceability**: `@pytest.mark.tc("TC-ID")` markers — 143 TC IDs across 15 specs, 100% spec coverage. Registered in `pyproject.toml`.
- **Architecture Pattern**: Component-based entities, Singleton managers, Centralized Game Loop, UI configuration constants extraction (`_constants.py` files), ChestUI mixin decomposition, GameEvent dataclass factory pattern
