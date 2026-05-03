<!-- Generated: 2026-05-01 | Files scanned: 34 | Token estimate: ~390 -->

# Game Engine Architecture

## System Flow
`main.py` → `Game.__init__()` → `Game.run()` (Main Loop)
`Game._handle_events()` → Input dispatch → `InteractionManager` → UI handlers
`Game._update(dt)` → `Player.update` → `NPC.update` → `TimeSystem.update` → `LightingManager`
`Game._draw()` → `_draw_scene()` → `_draw_background()` → `CameraGroup.custom_draw()` (Y-sorted) → `_draw_foreground()` → `_draw_hud()` → UI overlays

## Core Components

| Module | File | Lines | Role |
|---|---|---|---|
| **Game** | `src/engine/game.py` | 854 | Central orchestrator, state machine, entity spawning, event loop |
| **InteractionManager** | `src/engine/interaction.py` | 343 | Proximity/facing checks for objects, NPCs, pickups, emotes |
| **MapManager** | `src/map/manager.py` | ~130 | Layer surfaces, TMJ state, collision tile queries, window positions |
| **TmjParser** | `src/map/tmj_parser.py` | 258 | TMJ/TSX parsing → structured `map_data` dict |
| **CameraGroup** | `src/entities/groups.py` | 90 | Y-sorted rendering, camera offset, clamped scroll |
| **AssetManager** | `src/engine/asset_manager.py` | 95 | Singleton image/font cache with per-map clear |
| **I18nManager** | `src/engine/i18n.py` | 76 | Singleton translation lookup via nested key paths |

## Key Subsystems

### UI & HUD Components
- **Monolithic UI classes** decoupled from configuration via `_constants.py` modules (`src/ui/*_constants.py`).
- **InventoryUI** (`src/ui/inventory.py`, ~350 lines): Grid + equipment slots, D&D state machine, tab switching, item info zone.
- **ChestUI** (`src/ui/chest.py`, ~250 lines): Chest ↔ Inventory transfer, page-based scrolling (18-slot pages), D&D across panels.
- **TitleScreen** (`src/ui/title_screen.py`): Main menu state machine, logo composite rendering.
- **PauseScreen** (`src/ui/pause_screen.py`): In-game pause, save/resume/quit states.
- **Inventory** (`src/engine/inventory_system.py`, 84 lines): 28-slot padded list (`None` fill), equipment dict (`head/chest/legs/feet/weapon/shield`), `add/remove/equip/unequip` operations.

### Dialogue & Speech
- **DialogueManager** (`src/ui/dialogue.py`, 271 lines): Typewriter, paginated text, 9-patch HUD overlay for signs.
- **SpeechBubble** (`src/ui/speech_bubble.py`, ~150 lines): NPC nine-patch bubble above entity, name plate, paginated text, auto-wrap 224px.

### Entities
- **InteractiveEntity** (`src/entities/interactive.py`, 272 lines): Chests, levers, doors, signs, animated decor. Animated state machine (`is_on`), `day_night_driven` auto-lighting cycle, halo lighting, `restore_state` from WorldState.
- **NPC** (`src/entities/npc.py`, 90 lines): Random AI patrol, interact trigger, speech bubble integration.
- **Player** (`src/entities/player.py`, 75 lines): Input, directional animation, emote trigger.
- **PickupItem** (`src/entities/pickup.py`, 29 lines): Static collectible, looted state synced to WorldState.
- **EmoteManager** (`src/entities/emote.py`, 33 lines): `!` / `?` emote sprites above player.

### Engine Support
- **LightingManager** (`src/engine/lighting.py`, 269 lines): Night overlay, additive torch masks, window beam shafts (slanted per time-of-day).
- **TimeSystem** (`src/engine/time_system.py`, 60 lines): In-game clock, seasons, `night_alpha`, `brightness`.
- **AudioManager** (`src/engine/audio.py`, 160 lines): BGM/SFX via pygame mixer (32 channels), mute toggle, spatial ambient audio with minimum volume falloff, missing file fallback for dynamic sounds.
- **LootTable** (`src/engine/loot_table.py`, 69 lines): JSON-driven chest contents, stack splitting, slot overflow trimming.
- **WorldState** (`src/engine/world_state.py`, 13 lines): `{map_name}_{tiled_id}` keyed dict for cross-map persistence.

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE 2.5.7 (SDL 2.32.10)
- **Data Format**: Tiled (TMJ/TSX), JSON (settings, i18n, loot tables)
- **Test Suite**: Pytest 9.0.3, 492 tests, 90% coverage — domain-based layout: `tests/{engine,entities,graphics,map,ui}/` (16 consolidated files)
- **Architecture Pattern**: Component-based entities, Singleton managers, Centralized Game Loop, UI configuration constants extraction
