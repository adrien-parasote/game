<!-- Generated: 2026-05-01 | Files scanned: 33 | Token estimate: ~380 -->

# Data & Dependencies Architecture

## Configuration & Data Files
- **Settings** (`settings.json`): Screen size, debug flags, colors, cursor sizes. Parsed by `src/config.py` (89 lines, 93% cov).
- **Localization** (`assets/langs/fr.json`): Nested JSON `"npc.farmer.dialogue"` → string. Loaded by `I18nManager`.
- **Loot Tables** (`assets/data/loot_table.json`): Per-chest entries: `{item_id, min_qty, max_qty, chance}`. Max 20 stacks per chest; overflow trimmed with WARNING log.
- **Gameplay Data** (`gameplay.json`): Item registry — `item_id → {name, description, icon, type, slot, stackable}`.
- **Property Types** (`assets/data/propertytypes.json`): Enum metadata for Tiled object properties validation.
- **Maps** (`assets/tiled/maps/*.tmj`): Tilemap JSON — layers, objects, properties.
- **Tilesets** (`assets/tiled/tilesets/*.tsx`): Spritesheet grid definitions (XML).

## Inventory Data Model

### Player Inventory (`Inventory`, `src/engine/inventory_system.py`)
```
slots: list[Item | None]   # Fixed size = capacity (28), padded with None
equipment: dict            # {"head": Item|None, "chest": Item|None, "legs": Item|None,
                           #  "feet": Item|None, "weapon": Item|None, "shield": Item|None}
```

### Item
```
Item.item_id: str
Item.name: str
Item.quantity: int
Item.description: str
Item.icon: str        # filename in assets/images/items/
Item.item_type: str   # "consumable" | "equipment" | ...
Item.slot: str        # equipment slot name (if equippable)
Item.stackable: bool
```

### Chest Contents (`LootTable`)
```
chest_contents[element_id] = [{"item_id": str, "quantity": int}, ...]  # ≤20 stacks
```
Stored on `InteractiveEntity` as `entity.loot_items: list[dict | None]` — fixed-size list, `None` = empty slot.

## World State Persistence (`WorldState`, `src/engine/world_state.py`)
- **Key format**: `f"{map_name}_{tiled_id}"` via `WorldState.make_key(map_name, tiled_id)`
- **Stored states**:
  - `InteractiveEntity` (chest/lever/door/sign): `{is_on: bool, loot_items: list | None}`
  - `NPC`: `{x: int, y: int, facing: str}`
  - `PickupItem`: `{looted: bool, qty: int}`
- **Lifecycle**: Populated on entity `interact()` or pickup collection; restored in `restore_state()` at spawn.

## Dependencies
- **Python 3.13+** (Type-hinting, Dataclasses, IntEnum)
- **Pygame-CE 2.5.7** (Renderer, Event Loop, Audio Mixer, SDL 2.32.10)
- **Pytest 9.0.3 + pytest-cov 7.1.0**: 436 tests, 92% overall coverage

## Asset Directory Map
```
assets/
  images/
    sprites/          4-direction spritesheets (Player, NPCs, Interactives)
    HUD/              Dialogue overlay, speech bubbles (9-patch), clock
    ui/               Inventory/Chest backgrounds, slot images, cursors, arrows
    items/            Item icons (referenced by Item.icon)
  audio/
    bgm/              .ogg background music
    sfx/              .ogg sound effects
  fonts/              .ttf (Tech, Noble, Narrative styles)
  tiled/
    maps/             .tmj map files
    tilesets/         .tsx tileset definitions
  langs/              fr.json (localization)
  data/               loot_table.json, propertytypes.json
```
