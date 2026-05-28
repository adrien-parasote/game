# ADR-002 — Save Format: JSON on Disk

**Date:** 2026-05-02  
**Status:** ✅ Accepted

## Context

We need to decide how to serialize and store the active game state across 3 save slots.

## Evaluated Options

| Option | Pros | Cons |
|---|---|---|
| **JSON (Selected)** | Highly readable, native Python parsing, zero external dependencies, inspectable during debugging | Slightly slower to parse than binary formats (negligible for 3 slots) |
| `pickle` | Fast, native serialization | Serious security concerns (arbitrary code execution), fragile under class refactoring, non-human-readable |
| SQLite | Robust for complex relational datasets | Over-engineered for our flat schema needs; zero relations exist |

## Decision

JSON format. Save files will be stored under the `saves/` folder at the root of the project. This directory is included in `.gitignore`.

## Schema Structure of `saves/slot_[N].json`

```json
{
  "version": "0.4.0",
  "saved_at": "2026-05-02T14:30:00",
  "playtime_seconds": 3600,
  "player": {
    "map_name": "01-castle_hall.tmj",
    "x": 320,
    "y": 480,
    "facing": "down"
  },
  "time_system": {
    "elapsed_seconds": 7200.0,
    "season_index": 0
  },
  "inventory": {
    "slots": [
      {"item_id": "sword_iron", "quantity": 1},
      null,
      {"item_id": "potion_health", "quantity": 3}
    ],
    "equipment": {
      "HEAD": null,
      "LEFT_HAND": {"item_id": "sword_iron", "quantity": 1},
      "RIGHT_HAND": null,
      "UPPER_BODY": null,
      "LOWER_BODY": null,
      "SHOES": null,
      "BAG": null,
      "BELT": null
    }
  },
  "world_state": {
    "castle_hall_chest_01": {"is_on": true, "loot_items": []},
    "forest_lever_03": {"is_on": false, "loot_items": null}
  }
}
```

## Consequences

- `SaveManager` is solely responsible for serialization and deserialization.
- `Item` must expose `to_dict() -> dict` and `from_dict(d: dict) -> Item`.
- `Inventory` must expose `to_dict()` and `from_dict()`.
- `TimeSystem` must expose `to_dict()` and `from_dict()`.
- Scheme versioning (`version` key) is included to facilitate future migrations.
