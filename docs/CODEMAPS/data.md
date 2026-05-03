<!-- Generated: 2026-05-04 | Files scanned: 49 | Token estimate: ~400 -->

# Data & Dependencies Architecture

## Configuration & Data Files
- **Settings** (`settings.json`): Screen size, debug flags, colors, cursor sizes, font sizes, key bindings. Parsed by `src/config.py`.
- **Localization** (`assets/langs/fr.json`): Nested JSON `"npc.farmer.dialogue"` → string. Loaded by `I18nManager`.
- **Loot Tables** (`assets/data/loot_table.json`): Per-chest entries: `{item_id, min_qty, max_qty, chance}`. Max 20 stacks per chest; overflow trimmed with WARNING log.
- **Gameplay Data** (`gameplay.json`): Item registry — `item_id → {name, description, icon, type, equip_slot, stack_max}`.
- **Property Types** (`assets/data/propertytypes.json`): Enum metadata for Tiled object properties validation.
- **Maps** (`assets/tiled/maps/*.tmj`): Tilemap JSON — layers, objects, properties.
- **Tilesets** (`assets/tiled/tilesets/*.tsx`): Spritesheet grid definitions (XML).

## Game Events Model (`GameEvent`, `src/engine/game_events.py`)
```python
@dataclass
class GameEvent:
    type: GameEventType
    slot_id: int | None = None

# Factory methods (all return GameEvent instances)
GameEvent.new_game()           # type=NEW_GAME
GameEvent.load_requested(n)    # type=LOAD_REQUESTED, slot_id=n
GameEvent.quit()               # type=QUIT
GameEvent.pause_requested()    # type=PAUSE_REQUESTED
GameEvent.resume()             # type=RESUME
GameEvent.save_requested(n)    # type=SAVE_REQUESTED, slot_id=n
GameEvent.goto_title()         # type=GOTO_TITLE
GameEvent.none()               # type=NONE (no-op)
```

## Inventory Data Model

### Player Inventory (`Inventory`, `src/engine/inventory_system.py`)
```
slots: list[Item | None]   # Fixed size = capacity (28), padded with None
equipment: dict            # {"HEAD": Item|None, "BAG": Item|None, "BELT": Item|None,
                           #  "LEFT_HAND": Item|None, "UPPER_BODY": Item|None,
                           #  "LOWER_BODY": Item|None, "RIGHT_HAND": Item|None, "SHOES": Item|None}
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


## Save Data Model (`SaveManager`, `src/engine/save_manager.py`)
- **Slots**: 3 slots → `saves/slot_N.json` + `saves/slot_N_thumb.png`
- **Format** (version `0.4.0`):
```json
{
  "version": "0.4.0",
  "saved_at": "YYYY-MM-DDTHH:MM:SS",
  "playtime_seconds": 3600.0,
  "player": {"map_name": str, "x": float, "y": float, "facing": str, "level": int, "hp": int, "max_hp": int, "gold": int},
  "time_system": {"total_minutes": float},
  "inventory": {"slots": [...], "equipment": {...}},
  "world_state": {"key": {"is_on": bool}}
}
```
- **SlotInfo dataclass**: `{slot_id, saved_at, playtime_seconds, map_name, player_name, level}`
- **Operations**: `save(slot_id, game)`, `load(slot_id)→SaveData|None`, `delete(slot_id)`, `list_slots()→list[SlotInfo|None]`, `save_thumbnail(slot_id, surface)`, `load_thumbnail(slot_id)→Surface|None`
- **Validation**: `_validate_slot_id(n)` — raises `ValueError` if `n` not in `1..3`

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
- **Pytest 9.0.3 + pytest-cov 7.1.0**: 513 tests, 91% overall coverage

## Asset Directory Map
```
assets/
  images/
    sprites/          4-direction spritesheets (Player, NPCs, Interactives)
    HUD/              Dialogue overlay, speech bubbles (9-patch), clock
    ui/               Inventory/Chest backgrounds, slot images, cursors, arrows
    menu/             Title logo parts, menu buttons, panel, save slot sprites
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
saves/                slot_N.json + slot_N_thumb.png (runtime, gitignored)
```
