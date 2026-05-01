<!-- Generated: 2026-05-01 | Files scanned: 32 | Token estimate: ~300 -->

# Data & Dependencies Architecture

## Configuration & Data Files
- **Settings** (`settings.json`): Global configs (screen size, debug flags, colors, cursor sizes). Parsed by `src/config.py`.
- **Localization** (`assets/langs/fr.json`): Nested JSON dictionary mapping keys (`"npc.farmer.dialogue"`) to strings.
- **Loot Tables** (`assets/data/loot_table.json`): Definitions for chest contents/drops (`item_id`, min/max quantity, chance).
- **Property Types** (`assets/data/propertytypes.json`): Enums and validation metadata used by Tiled object properties.
- **Maps** (`assets/tiled/maps/*.tmj`): Tilemap definitions, object properties, layers (JSON).
- **Tilesets** (`assets/tiled/tilesets/*.tsx`): Spritesheet grid configurations (XML).

## World State Persistence
- **WorldState** (`src/engine/world_state.py`): Dictionary tracking map-independent state.
- **Key Strategy**: `f"{map_name}_{entity.id}"`.
- **Stored States**: 
  - Chests (is_on: boolean)
  - Doors/Levers (is_on: boolean)
  - NPCs (x, y, facing: int/string)
  - Pickups (looted: boolean, qty: int)

## Dependencies & Integrations
- **Python 3.13+** (Type-hinting, Dataclasses)
- **Pygame-CE** (Community Edition): Renderer, Event Loop, Audio Mixer.
- **Pytest**: Used extensively for TDD logic validation (coverage 80%+).

## Asset Directory Map
- `assets/images/sprites/`: 4x4 Spritesheets for Player/NPCs.
- `assets/images/HUD/`: Dialogue UI, Speech bubbles (nine-patch), Time/Date displays.
- `assets/images/ui/`: Inventory background, slots, cursor.
- `assets/audio/bgm/`, `sfx/`: `.ogg` audio files.
- `assets/fonts/`: `.ttf` (Tech, Noble, Narrative styles).
