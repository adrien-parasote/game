# Technical Spec - RPG Inventory Interface (v1.1)

> Document Type: Implementation


## 📋 System Architecture

### 1. Asset Mapping
| Component | Path | Description |
|-----------|------|-------------|
| Background | `assets/images/ui/01-inventory.png` | Main 1344x704 parchment background |
| Slot Frame | `assets/images/ui/03-inventory_slot.png` | Used for grid slots only (55x58) |
| Active Tab | `assets/images/ui/02-active_tab.png` | Highlight overlay (143x67) |
| Slot Hover | `assets/images/ui/04-inventory_slot_hover.png`| Superposed on hovered grid slot |
| Pointer | `assets/images/ui/05-pointer.png` | Default cursor (pointing) |
| Pointer Select| `assets/images/ui/06-pointer_select.png` | Click/hold cursor (closed) |

### 2. Layout & Positioning (Scaled for 1280x720)
*Urbanization Note: All original 1344x704 coordinates are multiplied by a scale factor of ~0.89x (Target Width 1200px) to fit the screen.*

#### Custom Cursor Scaling
- **Default Height:** 48px (configurable via `Settings.CURSOR_SIZE`).
- **Aspect Ratio:** Preserved (original 309x535 -> ~27x48).
- **Layering:** Absolute top-level (drawn after stats and HUD).

#### Character Preview (Center Left)
- **Position:** (358, 311)
- **Behavior:** No scaling (base sprite size).
- **Controls:** Animates in place. Direction can be changed using `MOVE_UP/DOWN/LEFT/RIGHT` keys while inventory is open.

#### Equipment Zones (Interaction Only)
- **Rendering:** No slot frames drawn (transparent zones).
- **Hit Area:** Scaled size of 78x78px to match background visual frames exactly.
- **Coordinates (Centers):**
    - HEAD: (354, 160) | BAG: (212, 290) | BELT: (211, 405) | LEFT_HAND: (242, 529)
    - UPPER_BODY: (499, 291) | LOWER_BODY: (498, 406) | RIGHT_HAND: (469, 529) | SHOES: (354, 549)

#### Inventory Grid (Right Tab)
- **Dimensions:** 7 Columns x 4 Rows (28 total slots).
- **Spacing:** Equalized at 72px (horizontal & vertical).
- **Start Pos:** (713, 219)

#### Tab System
- **Quantity:** 4 Tabs.
- **Positions (Centers):** X: [733, 863, 992, 1121] | Y: 130
- **Logic:** `02-active_tab.png` is rendered only on the currently selected tab.

#### Info Bar (Bottom Right)
- **Green Zone:** Center (929, 551).
- **Content:** LVL (Left), HP (Center), GOLD (Right) aligned in the bar.

### 3. Interaction Matrix

| Action | Input | Result |
|--------|-------|--------|
| Toggle | Key 'I' | Toggles `is_open`, pauses `TimeSystem`, manages `mouse_visible`. **Blocked if `ChestUI.is_open` is True.** |
| Rotate Preview | Dir Keys | Updates `preview_state` ('up', 'down', 'left', 'right'). |
| Select Tab | Left Click | Updates `active_tab` index. |
| Click Slot | Mouse Down | Sets `_dragging_item` if clicking an occupied grid or equipment slot. |
| Drag Item | Mouse Move | Updates `_drag_pos` for the item icon to follow the cursor. |
| Drop Item | Mouse Up | Transfers the item to the new slot (grid or equipment). Swaps if target is occupied. |
| Hover Grid | Mouse Move | Renders `04-inventory_slot_hover.png` over grid slots. |
| Hover Equip | Mouse Move | Renders a rounded gold border (78x78) around the equipment slot. |
| Custom Cursor| Always | Replaces system cursor. Switches to 'select' image on left-click. Size controlled by `Settings.CURSOR_SIZE`. |

## ❌ Anti-Patterns (DO NOT)
1.  **Do NOT scale** the character preview sprite; use native resolution.
2.  **Do NOT draw** `03-inventory_slot.png` over equipment zones.
3.  **Do NOT process** movement while inventory is open (pause logic).
4.  **Do NOT hardcode** offsets; always relate to `bg_rect.topleft`.
5.  **Do NOT scale** cursors without preserving aspect ratio.
6.  **Do NOT draw** the cursor before any other UI element (must be absolute last).
7.  **Do NOT draw** the dragged item's icon in its original slot while dragging.

## ✅ Patterns to Reproduce
1.  **Preserved Aspect Ratio Scaling:** Calculate target dimensions based on a configurable height (Settings) and the asset's native ratio.
2.  **Absolute Top-Level Layering:** Place the custom cursor at the very end of the main `draw` cycle to overlay HUD, stats, and emotes.
3.  **Conditional Emote Suppression:** Provide user settings to toggle visual feedback for failed actions ("?") to avoid UX annoyance.
4.  **Measurement-First UI Alignment:** Always measure dark/interactive zones in background assets pixel-perfectly before defining collision rects or selection frames.

## 🔧 `Inventory` API — `src/engine/inventory_system.py`

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `create_item` | `(item_id: str, quantity: int) -> Item` | `Item` | Creates a new Item populated with lang/tech data. **Added v1.2** |
| `add_item` | `(item_id: str, quantity: int) -> int` | Remaining quantity | Adds items, merges stacks. Returns 0 if all added. |
| `get_item_at` | `(index: int) -> Optional[Item]` | `Item \| None` | Returns item at slot index without removing it. |
| `remove_item` | `(index: int) -> Optional[Item]` | `Item \| None` | Removes and returns item at slot index, sets slot to `None`. Returns `None` if out of bounds or empty. **Added v1.1** |
| `equip_item` | `(slot_name: str, item: Item) -> Optional[Item]` | `Item \| None` | Equips item in `slot_name` if `propertytypes.json` allows it. Returns swapped item if occupied, else `None`. |
| `unequip_item` | `(slot_name: str) -> Optional[Item]` | `Item \| None` | Removes and returns the equipped item from `slot_name`. |

**Boundary invariants:**
- `remove_item` on an empty slot returns `None` without raising.
- `remove_item` with `index < 0` or `index >= capacity` returns `None`.
- `equip_item` enforces `equip_slot` from `propertytypes.json` matching `slot_name`. Returns the passed item untouched if invalid.

## 🔍 Verification
- **TDD:** `../../tests/test_inventory.py` covers logic states.
- **Transfer tests:** `../../tests/test_inventory_removal.py` covers `remove_item` edge cases.
- **Coords:** Verified via `detect_clusters_fuzzy.py` on the legacy asset.

**Last updated:** 2026-05-01

## Test Case Specifications

### Unit Tests — `Inventory` Logic (`../../tests/ui/test_inventory.py`, `../../tests/ui/test_inventory_removal.py`, `../../tests/ui/test_inventory_equipment.py`)

| Test ID | Test Function | Component | Expected Output |
|---------|---------------|-----------|-----------------|
| INV-001 | `test_inventory_localization` | `Inventory.create_item` | Item name localized from i18n |
| INV-002 | `test_inventory_load_item_data_file_not_found` | `Inventory._load_item_data` | Empty dict, no crash |
| INV-003 | `test_inventory_load_item_data_json_error` | `Inventory._load_item_data` | Empty dict, no crash |
| INV-004 | `test_inventory_add_item_stacks_in_existing_slot` | `Inventory.add_item` | Merges into existing stack |
| INV-005 | `test_inventory_add_item_returns_overflow` | `Inventory.add_item` | Returns remaining quantity |
| INV-006 | `test_inventory_is_full_false` | `Inventory.is_full` | `False` when slots available |
| INV-007 | `test_inventory_is_full_true` | `Inventory.is_full` | `True` when all slots occupied |
| INV-008 | `test_inventory_get_item_at_out_of_bounds` | `Inventory.get_item_at` | Returns `None` |
| INV-009 | `test_inventory_remove_item` | `Inventory.remove_item` | Item removed, slot is `None` |
| INV-010 | `test_inventory_remove_item_invalid_index` | `Inventory.remove_item` | Returns `None` (no crash) |
| INV-011 | `test_inventory_remove_item_empty_slot` | `Inventory.remove_item` | Returns `None` |
| INV-012 | `test_equip_item_valid` | `Inventory.equip_item` | Item placed in equipment slot |
| INV-013 | `test_equip_item_invalid_slot` | `Inventory.equip_item` | Item returned, no equip |
| INV-014 | `test_equip_item_swap` | `Inventory.equip_item` | Old item returned, new item equipped |
| INV-015 | `test_unequip_item` | `Inventory.unequip_item` | Item removed from slot, returned |

### Unit Tests — `InventoryUI` (`../../tests/ui/test_inventory_coverage.py`)

| Test ID | Test Function | Component | Expected Output |
|---------|---------------|-----------|-----------------|
| INVUI-001 | `test_drag_from_equipment_slot` | `InventoryUI.handle_input` | `_dragging_item` set from equip slot |
| INVUI-002 | `test_drag_from_grid_slot` | `InventoryUI.handle_input` | `_dragging_item` set from grid slot |
| INVUI-003 | `test_drop_on_equipment_slot` | `InventoryUI.handle_input` | Item moved to equipment slot |
| INVUI-004 | `test_drop_on_grid_slot` | `InventoryUI.handle_input` | Item moved to grid slot |
| INVUI-005 | `test_grid_to_grid_swap` | `InventoryUI._handle_drop` | Items swapped between grid slots |

### Integration Tests (`../../tests/ui/test_inventory_chest_interaction.py`)

| Test ID | Test Function | Flow | Verification |
|---------|---------------|------|--------------|
| IT-INV-001 | `test_inventory_wont_open_when_chest_is_open` | Chest open → press 'I' | `is_open` remains `False` |
| IT-INV-002 | `test_inventory_toggles_normally_when_no_chest` | No chest → press 'I' | `is_open` becomes `True` |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging |
|------------|-----------|----------|----------|---------|
| `propertytypes.json` missing | `FileNotFoundError` in `_load_item_data` | Return `{}` | Item has no equip restriction | `WARNING` |
| `propertytypes.json` malformed | `json.JSONDecodeError` | Return `{}` | Item has no equip restriction | `WARNING` |
| Asset image missing (slot, cursor) | `pygame.error` | Catch silently | Fallback 32×32 magenta surface | `WARNING` |
| `get_item_at` out-of-bounds | Index `< 0` or `>= capacity` | Return `None` | — | — |
| `equip_item` invalid slot | `slot_name` not in `propertytypes` | Return item unchanged | Item stays in grid | — |

## Deep Links

- **`Inventory` class**: [inventory_system.py L21](../../src/engine/inventory_system.py#L21)
- **`Inventory.add_item`**: [inventory_system.py L58](../../src/engine/inventory_system.py#L58)
- **`Inventory.remove_item`**: [inventory_system.py L97](../../src/engine/inventory_system.py#L97)
- **`Inventory.equip_item`**: [inventory_system.py L105](../../src/engine/inventory_system.py#L105)
- **`InventoryUI` class**: [inventory.py L1](../../src/ui/inventory.py#L1)
- **Layout constants**: [inventory_constants.py L1](../../src/ui/inventory_constants.py#L1)
- **Unit tests (logic)**: [test_inventory.py L1](../../tests/ui/test_inventory.py#L1)
- **Unit tests (equipment)**: [test_inventory_equipment.py L1](../../tests/ui/test_inventory_equipment.py#L1)
- **Unit tests (drag-drop coverage)**: [test_inventory_coverage.py L1](../../tests/ui/test_inventory_coverage.py#L1)
- **Integration tests (chest)**: [test_inventory_chest_interaction.py L1](../../tests/ui/test_inventory_chest_interaction.py#L1)