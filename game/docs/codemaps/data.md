<!-- Generated: 2026-05-27 | Last doc-update: 2026-05-27 (Steps 1-11 remédiation) | Files scanned: 73 | Token estimate: ~900 -->

# Data & Dependencies Architecture

## Configuration & Data Files
- **Settings** (`settings.json`): Screen, debug flags, colors, key bindings → `src/config.py`.
- **Localization** (`assets/langs/fr.json`): Nested JSON `"npc.farmer.dialogue"` → string → `I18nManager`.
- **Loot Tables** (`assets/data/loot_table.json`): `{item_id, min_qty, max_qty, chance}`. Max 20 stacks; overflow trimmed with WARNING.
- **Gameplay Data** (`gameplay.json`): Item registry — `item_id → {name, description, icon, type, equip_slot, stack_max}`.
- **Property Types** (`assets/data/propertytypes.json`): Enum metadata for Tiled object property validation.
- **Maps** (`assets/tiled/maps/*.tmj`): Tilemap JSON — layers, objects, properties.
- **Tilesets** (`assets/tiled/tilesets/*.tsx`): Spritesheet grid definitions (XML).

## Game Events (`GameEvent`, `src/engine/game_events.py`)
```python
GameEvent.new_game()           # type=NEW_GAME
GameEvent.load_requested(n)    # type=LOAD_REQUESTED, slot_id=n
GameEvent.quit()               # type=QUIT
GameEvent.pause_requested()    # type=PAUSE_REQUESTED
GameEvent.resume()             # type=RESUME
GameEvent.save_requested(n)    # type=SAVE_REQUESTED, slot_id=n
GameEvent.goto_title()         # type=GOTO_TITLE
GameEvent.none()               # type=NONE
```

## Inventory Data Model

### Player Inventory (`src/engine/inventory_system.py`)
```
slots: list[Item | None]   # Fixed size = 28, padded with None
equipment: dict            # {"HEAD"|"BAG"|"BELT"|"LEFT_HAND"|"UPPER_BODY"|"LOWER_BODY"|"RIGHT_HAND"|"SHOES": Item|None}
```

### Item
```
item_id: str  |  name: str  |  quantity: int  |  description: str
icon: str     |  item_type: str  |  slot: str  |  stackable: bool
```

### Chest Contents (`LootTable`)
```
entity.loot_items: list[dict | None]   # fixed-size ≤20, None = empty slot
# dict: {"item_id": str, "quantity": int}
```

## Save Data Model (`src/engine/save_manager.py`)
- **Slots**: 3 → `pygame.system.get_pref_path("adrien","game")/slot_[N].json` + `slot_[N]_thumb.png`
  - Fallback: `saves/` if `get_pref_path` fails. Paths built with `pathlib.Path`.
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
- **SlotInfo**: `{slot_id, saved_at, playtime_seconds, map_name, map_display_name, player_name, level}`
- **Operations**: `save(slot_id, game)`, `load(slot_id)→SaveData|None`, `delete(slot_id)`, `list_slots()→list[SlotInfo|None]`, `save_thumbnail()`, `load_thumbnail()`
- **Validation**: `_validate_slot_id(n)` raises `ValueError` if `n` not in `1..3`

## World State (`src/engine/world_state.py`)
- **Key**: `f"{map_name}_{tiled_id}"` via `WorldState.make_key()`
- **Stored**:
  - `InteractiveEntity`: `{is_on: bool, loot_items: list | None}`
  - `NPC`: `{x: int, y: int, facing: str}`
  - `PickupItem`: `{looted: bool, qty: int}`
- **Lifecycle**: set on `interact()` / pickup; restored in `restore_state()` at spawn.

## Asset Directory
```
assets/
  images/
    sprites/    4-direction spritesheets (Player, NPCs, Interactives)
    HUD/        Dialogue overlay, speech bubbles (9-patch), clock
    ui/         Inventory/Chest backgrounds, slot images, cursors, arrows
    menu/       Title logo, menu buttons, save slot sprites
    items/      Item icons (Item.icon)
  audio/
    bgm/        .ogg background music
    sfx/        .ogg sound effects
  fonts/        .ttf (Tech, Noble, Narrative)
  tiled/
    maps/       .tmj files
    tilesets/   .tsx files
  langs/        fr.json
  data/         loot_table.json, propertytypes.json
saves/          slot_[N].json + thumb (runtime, gitignored)
```
