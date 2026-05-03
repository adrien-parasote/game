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
- **TDD:** `tests/test_inventory.py` covers logic states.
- **Transfer tests:** `tests/test_inventory_removal.py` covers `remove_item` edge cases.
- **Coords:** Verified via `detect_clusters_fuzzy.py` on the legacy asset.

**Last updated:** 2026-05-01

## Test Case Specifications

### Unit Tests Required
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-001 | [Component] | [Input] | [Expected Output] | [Edge Cases] |

### Integration Tests Required
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-001 | [Flow] | [Setup] | [Verification] | [Teardown] |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| [Error] | [Detection] | [Response] | [Fallback] | [Logging] | [Alert] |

## Deep Links
- [Link description](file:///path/to/file#anchor)