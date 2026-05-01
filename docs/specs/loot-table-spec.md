# Technical Spec — Loot Table Initialization [Implementation]

**Type:** Implementation Document  
**Version:** 1.0  
**Status:** Implemented — 2026-05-01

---

## 1. Context & Problem

The engine supports interactive chests, but their contents were previously empty or hardcoded. We need a data-driven system to populate chests at map startup using a central configuration file.

### Deliverables

1. **`LootTable` Module** (`src/engine/loot_table.py`) — A loader that parses `loot_table.json` and prepares item stacks.
2. **Data Integration** — `data/loot_table.json` for content definitions.
3. **Engine Bootstrapping** — `Game` class loads the loot table and populates `InteractiveEntity.contents` during map spawn.
4. **Validation Logic** — Ensuring all `item_id` values exist in `propertytypes.json`.

---

## 2. Assumptions

| ID | Assumption | Risk |
|----|-----------|------|
| A-01 | Chests are identified by `sub_type == 'chest'` in Tiled. | LOW |
| A-02 | The Tiled `element_id` is the primary key for loot lookup. | LOW |
| A-03 | `propertytypes.json` is the source of truth for `stack_max`. | LOW |
| A-04 | Chests have a fixed capacity of 20 slots (`Settings.CHEST_MAX_SLOTS`). | LOW |

---

## 3. Data Schema

### `assets/data/loot_table.json`
```json
{
  "element_id_from_tiled": [
    { "item_id": "potion_red", "quantity": 100 },
    { "item_id": "ether_potion", "quantity": 2 }
  ]
}
```

### `assets/data/propertytypes.json`
Used to validate `item_id` and retrieve `stack_max`. If an item is not found, it is skipped and a warning is logged.

---

## 4. Behavioral Specification

### 4.1 Initialization Sequence
1. **Startup**: `Game` loads `propertytypes.json` into a dictionary.
2. **Loot Load**: `LootTable.load()` reads `loot_table.json`.
3. **Validation & Splitting**:
   - For each item:
     - Check if `item_id` exists in `propertytypes`.
     - Retrieve `stack_max`.
     - If `quantity > stack_max`, split into multiple stacks (e.g., 100 qty / 10 stack_max = 10 slots).
     - Trim total stacks to 20 per chest.
4. **Storage**: Prepared stacks are stored in `self._tables` indexed by `element_id`.

### 4.2 Spawning Logic
In `Game._spawn_interactive()`:
- If entity is a `chest`:
  - `entity.contents = loot_table.get_contents(entity.element_id)`
  - If no entry exists, `contents` defaults to an empty list `[]`.

---

## 5. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load loot table per map | Load once at game startup | Performance and data consistency |
| Crash on unknown item_id | Log warning and skip item | Engine stability during development |
| Ignore `stack_max` | Split into multiple stacks | Consistent with inventory mechanics |
| Exceed chest capacity | Trim excess stacks and log warning | Prevents UI overflow and memory issues |
| Hardcode loot in Python | Use JSON configuration | Allows designers to modify loot without code changes |

---

## 6. Test Case Specifications

### Unit Tests — `tests/test_loot_table.py`
- **TC-LT-01**: Load valid JSON → results in populated table.
- **TC-LT-02**: Unknown `item_id` → logged as warning, item skipped.
- **TC-LT-03**: Quantity > `stack_max` → correctly split into multiple stacks.
- **TC-LT-04**: Total slots > 20 → excess slots trimmed.
- **TC-LT-05**: Missing file → empty table, no crash.
- **TC-LT-06**: Malformed JSON → empty table, no crash.

---

## 7. Deep Links
- **LootTable Module**: [loot_table.py](../src/engine/loot_table.py)
- **Game Initialization**: [game.py L98](../src/engine/game.py#L98)
- **Interactive Spawning**: [game.py L715](../src/engine/game.py#L715)
