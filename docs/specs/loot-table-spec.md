# Technical Spec — Loot Table Initialization [Implementation]

> Document Type: Implementation


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
- **`LootTable` class**: [loot_table.py L15](../../src/engine/loot_table.py#L15)
- **`LootTable.load`**: [loot_table.py L27](../../src/engine/loot_table.py#L27)
- **`LootTable.get_contents`**: [loot_table.py L49](../../src/engine/loot_table.py#L49)
- **Game Initialization**: [game.py L98](../../src/engine/game.py#L98)
- **Interactive Spawning**: [game.py L715](../../src/engine/game.py#L715)
- **Unit tests**: [test_loot_table.py L1](../../tests/engine/test_loot_table.py#L1)

## 6. Test Case Specifications (Linked to Test Suite)

### Unit Tests — `tests/engine/test_loot_table.py`

| Test ID | Test Function | Component | Expected Output |
|---------|---------------|-----------|-----------------|
| TC-LT-01 | `test_load_valid_json` | `LootTable.load` | Table populated with valid items |
| TC-LT-02 | `test_load_unknown_item_id_skipped_and_warned` | `LootTable._validate_entries` | Item skipped + `WARNING` logged |
| TC-LT-03 | `test_load_missing_file` | `LootTable._read_json` | Empty table, no crash |
| TC-LT-04 | `test_load_malformed_json` | `LootTable._read_json` | Empty table, no crash |
| TC-LT-05 | `test_quantity_within_stack_max` | `LootTable._split_stacks` | Single stack created |
| TC-LT-06 | `test_quantity_exceeds_stack_max` | `LootTable._split_stacks` | Multiple stacks created |
| TC-LT-07 | `test_overflow_trimmed_with_warning` | `LootTable._trim_overflow` | Stacks trimmed to 20 + `WARNING` logged |
| TC-LT-08 | `test_known_element_id` | `LootTable.get_contents` | Returns correct item list |
| TC-LT-09 | `test_unknown_element_id` | `LootTable.get_contents` | Returns `[]` |
| TC-LT-10 | `test_get_contents_before_load` | `LootTable.get_contents` | Returns `[]` safely |

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-LT-01 | `test_load_valid_json` | `../../tests/engine/test_loot_table.py:L56` |
| TC-LT-02 | `test_load_unknown_item_id_skipped_and_warned` | `../../tests/engine/test_loot_table.py:L70` |
| TC-LT-03 | `test_load_missing_file` | `../../tests/engine/test_loot_table.py:L91` |
| TC-LT-04 | `test_load_malformed_json` | `../../tests/engine/test_loot_table.py:L99` |
| TC-LT-05 | `test_quantity_within_stack_max` | `../../tests/engine/test_loot_table.py:L198` |
| TC-LT-06 | `test_quantity_exceeds_stack_max` | `../../tests/engine/test_loot_table.py:L209` |
| TC-LT-07 | `test_overflow_trimmed_with_warning` | `../../tests/engine/test_loot_table.py:L235` |
| TC-LT-08 | `test_known_element_id` | `../../tests/engine/test_loot_table.py:L168` |
| TC-LT-09 | `test_unknown_element_id` | `../../tests/engine/test_loot_table.py:L178` |
| TC-LT-10 | `test_get_contents_before_load` | `../../tests/engine/test_loot_table.py:L186` |
