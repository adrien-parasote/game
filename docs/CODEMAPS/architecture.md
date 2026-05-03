<!-- Generated: 2026-05-04 | Files scanned: 48 | Token estimate: ~450 -->

# Game Engine Architecture

## System Flow
`main.py` → `GameStateManager.__init__()` → `GameStateManager.run()` (Main Loop)
`GameStateManager._process_global_events()` → Cross-state keys (quit, fullscreen, audio toggle)
`GameStateManager._handle_playing()` → re-posts events → `Game._handle_events()` → `InteractionManager`
`Game._update(dt)` → `Player.update` → `NPC.update` → `TimeSystem.update` → `LightingManager`
`Game._draw()` → `RenderManager.draw_scene()` → `_draw_background()` → `CameraGroup.custom_draw()` (Y-sorted) → `_draw_foreground()` → `_draw_hud()` → UI overlays

## Core Components

| Module | File | Lines | Role |
|---|---|---|---|
| **GameStateManager** | `src/engine/game_state_manager.py` | 266 | Top-level state machine (TITLE/PLAYING/PAUSED), global event routing, save/load orchestration |
| **Game** | `src/engine/game.py` | 762 | Gameplay orchestrator, entity spawning, event dispatch, map transitions |
| **RenderManager** | `src/engine/render_manager.py` | 109 | Scene rendering pipeline (background, foreground, HUD, overlays) |
| **InteractionManager** | `src/engine/interaction.py` | 440 | Proximity/facing checks for objects, NPCs, pickups, chests, emotes, teleporters |
| **SaveManager** | `src/engine/save_manager.py` | 185 | JSON save/load (3 slots), inventory + world state serialization |
| **MapManager** | `src/map/manager.py` | ~130 | Layer surfaces, TMJ state, collision tile queries, window positions |
| **TmjParser** | `src/map/tmj_parser.py` | 258 | TMJ/TSX parsing → structured `map_data` dict |
| **CameraGroup** | `src/entities/groups.py` | 90 | Y-sorted rendering, camera offset, clamped scroll |
| **AssetManager** | `src/engine/asset_manager.py` | 95 | Singleton image/font cache with per-map clear |
| **I18nManager** | `src/engine/i18n.py` | 76 | Singleton translation lookup via nested key paths |

## Key Subsystems

### UI & HUD Components
- All UI classes have dedicated `_constants.py` modules for layout/color/size values (`src/ui/*_constants.py`).
- **InventoryUI** (`src/ui/inventory.py`, 501L): Grid + equipment slots, D&D state machine, tab switching, item info zone.
- **ChestUI** (`src/ui/chest.py`, 393L) + mixins: `chest_layout.py` (slot geometry), `chest_draw.py` (rendering), `chest_transfer.py` (item movement logic). Chest ↔ Inventory transfer, paged scrolling (18-slot pages), D&D across panels.
- **TitleScreen** (`src/ui/title_screen.py`, 382L): Main menu state machine, logo composite rendering, halo glow hover effect.
- **PauseScreen** (`src/ui/pause_screen.py`, 275L): In-game pause, save/resume/quit states, gaussian blur halo hover.
- **SaveMenuOverlay** (`src/ui/save_menu.py`, 207L): Reusable save/load slot overlay. Used by both TitleScreen (load) and PauseScreen (save). `SaveSlotUI` renders individual slot with background sprite, thumbnail, and additive halo.
- **Inventory** (`src/engine/inventory_system.py`, 84L): 28-slot padded list (`None` fill), equipment dict (8 slots), `add/remove/equip/unequip`.

### Dialogue & Speech
- **DialogueManager** (`src/ui/dialogue.py`, 270L): Typewriter, paginated text, 9-patch HUD overlay.
- **SpeechBubble** (`src/ui/speech_bubble.py`, ~150L): NPC nine-patch bubble, name plate, paginated text, auto-wrap 224px.

### Entities
- **InteractiveEntity** (`src/entities/interactive.py`, 419L): Chests, levers, doors, signs, animated decor. Animated state machine (`is_on`), `day_night_driven` auto-lighting, halo lighting, `restore_state` from WorldState.
- **NPC** (`src/entities/npc.py`, 90L): Random AI patrol, interact trigger, pending dialogue queue (waits for movement to finish).
- **Player** (`src/entities/player.py`, 75L): Input, directional animation, emote trigger.
- **PickupItem** (`src/entities/pickup.py`, 29L): Static collectible, looted state synced to WorldState.
- **EmoteManager** (`src/entities/emote.py`, 33L): `!` / `?` / `frustration` emote sprites above player.

### Engine Support
- **LightingManager** (`src/engine/lighting.py`, 268L): Night overlay, additive torch masks, slanted window beam shafts (continuous cosine blending at dawn/dusk).
- **TimeSystem** (`src/engine/time_system.py`, 60L): In-game clock, seasons, `night_alpha`, `brightness`.
- **AudioManager** (`src/engine/audio.py`, 248L): BGM/SFX via pygame mixer (32 channels), mute toggle, spatial ambient audio with `ambient_channels` dict + 20% floor volume, footstep normalization.
- **LootTable** (`src/engine/loot_table.py`, 69L): JSON-driven chest contents, stack splitting, slot overflow trimming.
- **WorldState** (`src/engine/world_state.py`, 13L): `{map_name}_{tiled_id}` keyed dict for cross-map persistence.
- **GameEvents** (`src/engine/game_events.py`): Custom pygame event constants.

## Documentation & Tooling
```
docs/
  specs/            17 implementation specs (Stream Coding v6.0 — Linked Test Functions + Deep Links)
  traceability.md   Auto-generated spec↔test coverage matrix (scripts/tc_report.py)
  CODEMAPS/         Architecture maps (this directory)
  strategic/        MASTER_ROADMAP.md, game_vision.md, blueprint.md
  ADRs/             3 Architecture Decision Records
scripts/
  tc_report.py      Spec↔Test traceability report (CLI + markdown export)
.agents/
  learnings/        5 domain learning files (workflow_optimization, game_engine, audio_engine, ui, testing)
  rules/            coding-standards.md + language rules
```

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE 2.5.7 (SDL 2.32.10)
- **Data Format**: Tiled (TMJ/TSX), JSON (settings, i18n, loot tables, saves)
- **Test Suite**: Pytest 9.0.3, **492 tests**, **90% coverage** — domain-based layout: `tests/{engine,entities,graphics,map,ui}/` (32 files across 5 domains)
- **Traceability**: `@pytest.mark.tc("TC-ID")` markers on 90 functions (115 TC IDs, 100% spec coverage). Registered in `pyproject.toml`.
- **Architecture Pattern**: Component-based entities, Singleton managers, Centralized Game Loop, UI configuration constants extraction, ChestUI mixin decomposition
