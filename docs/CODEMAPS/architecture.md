<!-- Generated: 2026-05-15 | Last doc-update: 2026-05-15 | Files scanned: 70 | Token estimate: ~610 -->

# Game Engine Architecture

## System Flow
`main.py` → `GameStateManager.__init__()` → `GameStateManager.run()` (Main Loop)
`GameStateManager._process_global_events()` → Cross-state keys (quit, fullscreen, audio toggle)
`GameStateManager._handle_title(events)` → `TitleScreen.handle_event()` → `GameEvent` → transition
`GameStateManager._handle_playing(events, dt)` → filters ESC → re-posts events → `Game.run_frame(dt)` → `GameEvent`
`GameStateManager._handle_paused(events, dt)` → `PauseScreen.handle_event()` → save/resume/goto_title
`Game._update(dt)` → `Player.update` → `NPC.update` → `TimeSystem.update` → `LightingManager`
`Game._draw()` → `RenderManager.draw_scene()` → `_draw_background()` → `CameraGroup.custom_draw(max_depth=player.depth)` (Y-sorted, below-player entities) → `_draw_foreground()` (foreground-order layers + tiles with depth>player) → `CameraGroup.custom_draw(min_depth=player.depth+1)` (above-player entities) → `_draw_hud()` → UI overlays

## Core Components

| Module | File | Lines | Role |
|---|---|---|---|
| **GameStateManager** | `src/engine/game_state_manager.py` | 309 | Top-level state machine (TITLE/PLAYING/PAUSED), global event routing, save/load orchestration |
| **Game** | `src/engine/game.py` | 420 | Gameplay orchestrator, thin wrappers delegating to sub-managers. Phase 1.5 refactored. |
| **RenderManager** | `src/engine/render_manager.py` | 109 | Scene rendering pipeline (background, foreground, HUD, overlays) |
| **InteractionManager** | `src/engine/interaction.py` | 400 | Proximity/facing checks for objects, NPCs, pickups, chests, emotes, teleporters. Typed `game: Any` (no hard coupling to `Game`) |
| **EntityFactory** | `src/engine/entity_factory.py` | 265 | Entity spawning (interactive, teleport, NPC, pickup). Extracted from `Game` in Phase 1.5. Pattern: `EntityFactory(game: Any)`. |
| **MapLoader** | `src/engine/map_loader.py` | ~115 | Map loading pipeline (parse, BGM, cleanup, spawn, player position). Extracted from `Game` in Phase 1.5. |
| **InputHandler** | `src/engine/input_handler.py` | ~55 | Pygame event dispatch (interact, inventory, dialogue). Extracted from `Game` in Phase 1.5. |
| **CollisionChecker** | `src/engine/collision_checker.py` | ~80 | Tile + entity collision checks. Extracted from `Game` in Phase 1.5. |
| **SaveManager** | `src/engine/save_manager.py` | 222 | JSON save/load (3 slots), inventory + world state serialization, PNG thumbnails |
| **GameEvents** | `src/engine/game_events.py` | 59 | `GameEvent` dataclass + `GameEventType` enum. Factory methods: `new_game()`, `load_requested(slot_id)`, `quit()`, `pause_requested()`, `resume()`, `save_requested(slot_id)`, `goto_title()` |
| **MapManager** | `src/map/manager.py` | 191 | Layer surfaces, TMJ state, collision tile queries, window positions |
| **TmjParser** | `src/map/tmj_parser.py` | 263 | TMJ/TSX parsing → structured `map_data` dict |
| **CameraGroup** | `src/entities/groups.py` | ~121 | Y-sorted rendering, camera offset, clamped scroll, dirty-flag sort cache |
| **AssetManager** | `src/engine/asset_manager.py` | 76 | Singleton image/font cache with per-map clear |
| **I18nManager** | `src/engine/i18n.py` | 58 | Singleton translation lookup via nested key paths |

## Key Subsystems

### UI & HUD Components
- **Constants Architecture**: All UI and Engine modules have dedicated `_constants.py` modules. Complete list: `src/ui/pause_screen_constants.py`, `src/ui/save_menu_constants.py` (new), `src/ui/hud_constants.py`, `src/ui/chest_constants.py`, `src/ui/dialogue_constants.py`, `src/ui/inventory_constants.py`, `src/engine/lighting_constants.py`, `src/engine/game_state_constants.py`, `src/entities/interactive_constants.py`. Shared UI colors in `src/ui/ui_colors.py`. Codebase is 100% English-only (all French comments eliminated as of 2026-05-07).
- **Protocol Files**: `src/ui/chest_protocol.py`, `src/ui/inventory_protocol.py` — shared type protocols for mixin composition.
- **InventoryUI** (`src/ui/inventory.py`, 404L) + `inventory_draw.py` (247L): Grid + equipment slots, D&D state machine, tab switching, item info zone.
- **ChestUI** (`src/ui/chest.py`, 343L) + mixins: `chest_layout.py` (slot geometry), `chest_draw.py` (280L, rendering), `chest_transfer.py` (item movement logic). Chest ↔ Inventory transfer, paged scrolling (18-slot pages), D&D across panels.
- **TitleScreen** (`src/ui/title_screen.py`, 431L): Main menu state machine (MAIN_MENU/LOAD_MENU/OPTIONS). Renders dynamic title using `title_screen_constants.py`. **33 fire halos** (`BACKGROUND_LIGHTS`, BLEND_RGB_ADD, flicker) + **25 bioluminescent mushrooms** (`MUSHROOM_LIGHTS`, slow breath `sin*0.15`). Resolution-independent: logical 1280×720 mapped via `_light_scale_x/y` from `screen.get_size()`. Returns `GameEvent`.
- **PauseScreen** (`src/ui/pause_screen.py`, 264L): In-game pause overlay (MAIN/SAVE_MENU states), save/resume/goto_title. **Pre-render cache pattern**: button label surfaces (`_rendered_idle`, `_rendered_hover`) computed once at `__init__` via `_make_engraved_surface()` and `_make_halo_surface()` — zero `Surface()` / `gaussian_blur()` calls inside `draw()`. Constants from `pause_screen_constants.py`. `notify_save_result(bool)` for feedback.
- **SaveMenuOverlay** (`src/ui/save_menu.py`, 380L): Reusable save/load slot overlay. `refresh()` populates `_slots_info` + `_cached_title_surfs` (pre-rendered title surfaces, one per slot) from `SaveManager.list_slots()`. `get_clicked_slot(event)→int|None`. `SaveSlotUI` renders individual slot with background sprite (size driven by `SAVE_SLOT_BG_W/H` constants), PNG thumbnail, additive halo. **Back button** (engraved label + icon, hover glow) — label width measured via `font.size()`, no Surface allocation. All constants in `save_menu_constants.py`.
- **GameHUD** (`src/ui/hud.py`, 90L): In-game HUD (time, health). `I18nManager` cached at `__init__` (`self._i18n`) — not constructed per frame.
- **Inventory** (`src/engine/inventory_system.py`, 133L): 28-slot padded list (`None` fill), equipment dict (8 slots), `add/remove/equip/unequip`.

### Dialogue & Speech
- **DialogueManager** (`src/ui/dialogue.py`, 271L): Typewriter, paginated text, 9-patch HUD overlay. Uses `dialogue_constants.py` (`DIALOGUE_SHADOW_COLOR`, `DIALOGUE_TEXT_COLOR` — parchment palette).
- **SpeechBubble** (`src/ui/speech_bubble.py`, 263L): NPC nine-patch bubble, name plate, paginated text, auto-wrap 224px.

### Entities
- **InteractiveEntity** (`src/entities/interactive.py`, 429L): Chests, levers, doors, signs, animated decor. Animated state machine (`is_on`), `day_night_driven` auto-lighting, halo lighting, `restore_state` from WorldState. Uses `interactive_constants.py`.
- **NPC** (`src/entities/npc.py`, 148L): Random AI patrol, interact trigger, pending dialogue queue (waits for movement to finish).
- **Player** (`src/entities/player.py`, 122L): Input, directional animation, emote trigger.
- **PickupItem** (`src/entities/pickup.py`, 45L): Static collectible, looted state synced to WorldState.
- **EmoteManager** (`src/entities/emote.py`, 62L): `!` / `?` / `frustration` emote sprites above player.

### Engine Support
- **LightingManager** (`src/engine/lighting.py`, 300L): Night overlay, additive torch masks, slanted window beam shafts (continuous cosine blending at dawn/dusk). Beam colors driven by `BEAM_COLOR_MOON`/`BEAM_COLOR_SUN` constants in `lighting_constants.py`.
- **TimeSystem** (`src/engine/time_system.py`, 124L): In-game clock, seasons, `night_alpha`, `brightness`.
- **AudioManager** (`src/engine/audio.py`, 248L): BGM/SFX via pygame mixer (32 channels), mute toggle, spatial ambient audio with `ambient_channels` dict + 20% floor volume, footstep normalization.
- **LootTable** (`src/engine/loot_table.py`, 130L): JSON-driven chest contents, stack splitting, slot overflow trimming.
- **WorldState** (`src/engine/world_state.py`, 22L): `{map_name}_{tiled_id}` keyed dict for cross-map persistence.

## Documentation & Tooling
```
docs/
  specs/            32 implementation specs (Stream Coding v6.0 — Linked Test Functions + Deep Links)
  traceability.md   Auto-generated spec↔test coverage matrix (scripts/tc_report.py — run to refresh)
  codemaps/         Architecture maps (this directory)
  strategic/        MASTER_ROADMAP.md, game_vision.md, perf-constants-audit-strategy.md (archivé→ ADR-006)
  ADRs/             6 Architecture Decision Records (ADR-001 à ADR-006)
  research/         Research docs (unit_test_optimization.md)
scripts/
  autotiles/            Autotile pipeline scripts (blob/animated/static)
  assets/               Asset processing (banners, sprites)
  calibration/          Interactive halo calibration tools
  tc_report.py          Spec↔Test traceability report (CLI + --markdown export)
  release.py            Repository release automation (SemVer, tag, push)
  get_version.py        Version bumping utility
  profile_game.py       Performance profiling
.agents/
  learnings/        6 domain learning files (methodology_and_docs, game_engine, audio_engine, ui, testing, map_rendering)
  rules/            coding-standards.md + language rules
  learnings.md      Index des learnings par domaine
```

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE 2.5.7 (SDL 2.32.10)
- **Data Format**: Tiled (TMJ/TSX), JSON (settings, i18n, loot tables, saves)
- **Test Suite**: Pytest 9.0.3, **783 tests** — domain-based layout: `tests/{engine,entities,graphics,map,ui,scripts}/` (6 domains)
- **Traceability**: `@pytest.mark.tc("TC-ID")` markers — voir `docs/traceability.md` (auto-généré). Registered in `pyproject.toml`.
- **Architecture Pattern**: Component-based entities, Singleton managers, Centralized Game Loop, UI configuration constants extraction (`_constants.py` files), **Pre-render cache pattern** (static button/label surfaces pre-computed at init, zero allocation in draw loop), ChestUI mixin decomposition, GameEvent dataclass factory pattern, Context Injection (`SomeManager(game: Any)`) pour sous-managers Phase 1.5
