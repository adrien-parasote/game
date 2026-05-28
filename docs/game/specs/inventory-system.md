# Technical Specification — Inventory & Loot Systems [Implementation]

> **Document Type:** Implementation
> **Source Files:** `src/engine/inventory_system.py`, `src/ui/inventory.py`, `src/engine/loot_table.py`, `src/ui/inventory_constants.py`

This specification consolidates the Item Data Model, Equipment Slot system, drag-and-drop Inventory HUD interface, and data-driven Loot Table loaders.

---

## 1. System Architecture & Components

```
                ┌───────────────────────────────────┐
                │    propertytypes.json             │ (Technical Data)
                └─────────────────┬─────────────────┘
                                  │ (resolves)
┌──────────────────┐    ┌─────────▼────────┐    ┌──────────────────┐
│   I18nManager    ├───►│  create_item()   │◄───┤   loot_table.json│
│ (Localized Data) │    └─────────┬────────┘    └──────────────────┘
└──────────────────┘              │
                                  ▼
                        ┌──────────────────┐
                        │   Item Stack     │ (Dataclass)
                        └─────────┬────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │   Inventory      │ (Logic Layer)
                        └─────────┬────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │   InventoryUI    │ (Presentation Layer)
                        └──────────────────┘
```

---

## 2. Item & Inventory Logic Model

### 2.1 Item Dataclass
Represents a single slot stack of a specific item type.
- **Attributes**:
  - `id` (str): Unique identifier (e.g. `"pot_red"`).
  - `name` (str): Localized display name.
  - `description` (str): Localized descriptive text.
  - `icon` (str): Filename of the item image.
  - `quantity` (int): Number of items in this stack.
  - `stack_max` (int): Maximum quantity allowed per stack.
- **Technical & Localized Resolution**: Merges `propertytypes.json` (`stack_max`, `icon`, `equip_slot`) with `I18nManager` (`name`, `description`).

### 2.2 Inventory Manager
Defines player storage (capacity of 28 grid slots, 7 columns × 4 rows) and 8 fixed equipment slots:

| Slot Name | Equipment Position | Canonical Restriction |
|-----------|--------------------|-----------------------|
| `HEAD` | Top Center | Helmets / Caps |
| `BAG` | Left Upper | Utility items |
| `BELT` | Left Lower | Tool Belts |
| `LEFT_HAND` | Bottom Left | Offhand / Shields |
| `UPPER_BODY`| Center Upper | Torso Armor |
| `LOWER_BODY`| Center Lower | Leg Armor |
| `RIGHT_HAND`| Bottom Right | Mainhand Weapons |
| `SHOES` | Bottom Center | Boots |

- **`add_item(item_id, quantity)`**: Executes a two-pass algorithm:
  1. **Stack Pass**: Scans active slots with matching `id` and `quantity < stack_max` to fill existing stacks.
  2. **Empty Slot Pass**: Spills remaining quantities into empty slots up to `stack_max`. Returns any remaining overflow that doesn't fit.
- **`equip_item(slot_name, item)`**: Validates `item.id` against `propertytypes.json`. Returns the item untouched if `equip_slot` does not match the target slot. If valid, swaps with existing slot contents and returns the previously equipped item.

---

## 3. Inventory UI Visual Layout

Coordinates are scaled for a 1280×720 viewport (base asset 1344×704 scaled by `~0.89x` into 1200px width). All offsets relative to `bg_rect.topleft`.

### 3.1 Layout Coordinates (Centers / Positions)
- **Grid Slots**: 28 total. Horizontally and vertically spaced at 72px. Starts at `(713, 219)`.
- **Equipment Centers**:
  - `HEAD`: `(354, 160)` | `BAG`: `(212, 290)` | `BELT`: `(211, 405)` | `LEFT_HAND`: `(242, 529)`
  - `UPPER_BODY`: `(499, 291)` | `LOWER_BODY`: `(498, 406)` | `RIGHT_HAND`: `(469, 529)` | `SHOES`: `(354, 549)`
- **Info Bar**: Bottom-right green zone centered at `(929, 551)` displaying LVL, HP, and GOLD.
- **Character Preview**: Animates in place at `(358, 311)`. Pressing directional keys rotates the sprite.

### 3.2 Drag-and-Drop Interaction Matrix
- **Select**: Mouse-down on occupied slot hides slot icon and assigns `_dragging_item`.
- **Drag**: Cursor movement draws `_dragging_item` centered at `_drag_pos`. The system pointer swaps to `06-pointer_select.png`.
- **Drop**: Mouse-up drops item on target slot. If valid, swaps existing occupant or slides item to target.
- **Slot Hovers**: Renders `04-inventory_slot_hover.png` on grid slots, or draws a rounded gold border around equipment slots.

---

## 4. Loot Table System (Map Chests Populator)

Reads `loot_table.json` once at startup to prepare and distribute item drops to chest containers on map transitions.

### 4.1 Stacks Allocation & Capacity Trimming
- **Tiled Binding**: Primary chest key matches Tiled `element_id`.
- **Capacity constraint**: Chests are restricted to 20 slots (`Settings.CHEST_MAX_SLOTS`).
- **Deep Copy Invariant**: `LootTable.get_contents(element_id)` MUST return deep copies of the stored Item models:
  ```python
  return [item.copy() for item in self._tables[element_id]]
  ```
  Sharing raw dict references causes state corruption, emptying subsequent chests when items are moved to inventory.

> [!IMPORTANT]
> The loot table uses `element_id` (manual Tiled property) for chest content binding.
> WorldState persistence uses the native Tiled `id` (auto-generated, guaranteed unique) via key format `{map_basename}_{tiled_id}`.
> These are intentionally different: `element_id` enables designer-readable loot assignments,
> while native `id` ensures collision-free state keys. See [map-world-system.md §7.1](./map-world-system.md).

---

## 5. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Mutate `slots` list directly from UI | Use `add_item()` or `remove_item()` | Violates state and stacking invariants |
| Expose bare technical keys in UI | Retrieve values through i18n manager | Prevents localized text leaks |
| Draw `03-inventory_slot.png` on equipment | Rely on transparent backdrop | Visual framing consistency |
| Render character preview scaled | Render at native resolution | Visual pixel distortion |
| Open inventory while Chest is active | Ignore input if `ChestUI.is_open` | Intersecting inputs cause dialogue lockout crashes |
| Return shallow copies from LootTable | Return deep copies (`item.copy()`) | Modifying container items corrupts master table |

---

## 6. Test Case Specifications

### 6.1 Linked Test Functions
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-INV-001 | `test_inventory_add_item_stacks_in_existing_slot` | `../../tests/ui/test_inventory.py` |
| TC-INV-002 | `test_inventory_add_item_returns_overflow` | `../../tests/ui/test_inventory.py` |
| TC-INV-003 | `test_inventory_is_full_true` | `../../tests/ui/test_inventory.py` |
| TC-LT-01 | `test_load_valid_json` | `../../tests/engine/test_loot_table.py` |
| TC-LT-02 | `test_load_unknown_item_id_skipped_and_warned` | `../../tests/engine/test_loot_table.py` |
| TC-LT-03 | `test_load_missing_file` | `../../tests/engine/test_loot_table.py` |
| TC-LT-04 | `test_load_malformed_json` | `../../tests/engine/test_loot_table.py` |
| TC-LT-05 | `test_quantity_within_stack_max` | `../../tests/engine/test_loot_table.py` |
| TC-LT-06 | `test_quantity_exceeds_stack_max` | `../../tests/engine/test_loot_table.py` |
| TC-LT-07 | `test_overflow_trimmed_with_warning` | `../../tests/engine/test_loot_table.py` |
| TC-LT-08 | `test_known_element_id` | `../../tests/engine/test_loot_table.py` |
| TC-LT-09 | `test_unknown_element_id` | `../../tests/engine/test_loot_table.py` |
| TC-LT-10 | `test_get_contents_before_load` | `../../tests/engine/test_loot_table.py` |
| TC-LT-11 | `test_load_missing_file` | `../../tests/engine/test_loot_table.py` |

---

## 7. Deep Links
- **Item Data logic**: [inventory_system.py L9](../../src/engine/inventory_system.py#L9)
- **Inventory UI engine**: [inventory.py L1](../../src/ui/inventory.py#L1)
- **Loot Table distribution**: [loot_table.py L15](../../src/engine/loot_table.py#L15)
