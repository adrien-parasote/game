> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Inventory Data Model [Implementation]

> Document Type: Implementation
> Source: `src/engine/inventory_system.py` (143 LOC)

This document specifies the AS-IS implementation of the `Inventory` and `Item` data model, covering stacking, capacity, equipment slots, and item data resolution.

## 1. Goal Description

Provide the core data layer for player inventory management: slot-based storage with stacking, equipment slots with validation, and item creation from technical + localized data sources.

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `Item` | `src/engine/inventory_system.py:9` | 7 | Dataclass representing a single item stack |
| `Inventory` | `src/engine/inventory_system.py:19` | 124 | Slot management, stacking, equipment |

### Dependencies
- `src.engine.i18n.I18nManager` — localized item names/descriptions
- `assets/data/propertytypes.json` — technical item data (stack_max, icon, equip_slot)

## 3. Item Dataclass

```python
@dataclass
class Item:
    id: str                        # Unique item identifier (e.g., "iron_sword")
    name: str                      # Localized display name
    description: str               # Localized description text
    icon: str | None = None        # Icon filename (e.g., "iron_sword.png")
    quantity: int = 1              # Current stack count
    stack_max: int = 1             # Maximum stack size for this item type
```

**Source**: [inventory_system.py:9-17](../../src/engine/inventory_system.py#L9)

### Data Resolution

Item creation merges two data sources:
1. **Technical data** (`propertytypes.json`): `stack_max`, `icon`, `equip_slot`
2. **Localized data** (`I18nManager.get_item(id)`): `name`, `description`

```python
def create_item(self, item_id: str, quantity: int) -> Item:
    tech_data = self.item_data.get(item_id, {})
    lang_data = self.i18n.get_item(item_id)
    return Item(
        id=item_id,
        name=lang_data["name"],
        description=lang_data["description"],
        icon=tech_data.get("icon", f"{item_id}.png"),
        quantity=quantity,
        stack_max=tech_data.get("stack_max", 1),
    )
```

**Fallback behavior**:
| Field | Missing Data Fallback |
|-------|----------------------|
| `name` | `item_id.replace("_", " ").capitalize()` |
| `description` | `"No description available."` |
| `icon` | `f"{item_id}.png"` |
| `stack_max` | `1` (non-stackable) |

## 4. Inventory Class

### 4.1. Initialization

```python
def __init__(self, capacity: int = 28) -> None
```

**State**:
| Attribute | Type | Initial Value |
|-----------|------|---------------|
| `capacity` | `int` | `28` |
| `slots` | `list[Item \| None]` | `[None] * capacity` |
| `equipment` | `dict[str, Item \| None]` | 8 slots, all `None` |
| `item_data` | `dict[str, dict]` | Loaded from `propertytypes.json` |
| `i18n` | `I18nManager` | Singleton instance |

### 4.2. Equipment Slots

Fixed 8-slot equipment layout:

| Slot Name | Position |
|-----------|----------|
| `HEAD` | Top center |
| `BAG` | Left upper |
| `BELT` | Left lower |
| `LEFT_HAND` | Bottom left |
| `UPPER_BODY` | Center upper |
| `LOWER_BODY` | Center lower |
| `RIGHT_HAND` | Bottom right |
| `SHOES` | Bottom center |

### 4.3. Interfaces

#### `add_item(item_id: str, quantity: int = 1) -> int`

**Returns**: Remaining quantity that couldn't be added (0 = all added).

**Algorithm** (two-pass):
1. **Stack pass**: Scan all slots for existing items with same `id` and `quantity < stack_max`. Add as much as possible to each.
2. **Empty slot pass**: Fill empty slots with new `Item` objects, up to `stack_max` per slot.

**Source**: [inventory_system.py:67-95](../../src/engine/inventory_system.py#L67)

#### `get_item_at(index: int) -> Item | None`

Returns the item at `index`, or `None` if empty or out of bounds.

#### `remove_item(index: int) -> Item | None`

Removes and returns the item at `index`. Sets slot to `None`.

#### `is_full() -> bool`

Returns `True` if all slots are occupied (no `None` entries).

#### `equip_item(slot_name: str, item: Item) -> Item | None`

**Validation**: Checks `item.id` against `propertytypes.json` → `equip_slot` field.
- If `equip_slot != slot_name` → returns the item untouched (equip rejected)
- If valid → swaps into `equipment[slot_name]`, returns previously equipped item (or `None`)

**Source**: [inventory_system.py:114-132](../../src/engine/inventory_system.py#L114)

#### `unequip_item(slot_name: str) -> Item | None`

Removes and returns the equipped item. Sets equipment slot to `None`.

## 5. Data Source: `propertytypes.json`

**Path**: `assets/data/propertytypes.json`

**Schema** (per item):
```json
{
  "iron_sword": {
    "icon": "iron_sword.png",
    "stack_max": 1,
    "equip_slot": "RIGHT_HAND"
  },
  "health_potion": {
    "icon": "health_potion.png",
    "stack_max": 10
  }
}
```

**Error handling**: If file missing or JSON invalid → `item_data = {}`, all items use defaults. Logged at ERROR level.

## 6. Wiring

| Caller | Usage |
|--------|-------|
| `Player.__init__()` | Creates `Inventory(capacity=28)` |
| `InventoryUI` | Reads `player.inventory.slots`, `equipment`, `get_item_at()` |
| `ChestUI` / `ChestTransferMixin` | Calls `add_item()`, `create_item()`, reads `slots` directly |
| `LootTable` | Calls `add_item()` for chest initialization |
| `SaveManager` | Serializes/deserializes `slots` and `equipment` |
| `InteractionManager` | Calls `add_item()` for pickup items |

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Create `Item` directly with hardcoded values | Use `inventory.create_item(id, qty)` | Ensures tech + lang data resolution |
| Mutate `slots` list directly from UI code | Use `add_item()`, `remove_item()`, `get_item_at()` | Preserves stacking invariants |
| Assume all items are stackable | Check `stack_max` from `propertytypes.json` | Default is 1 (non-stackable) |
| Skip equip validation | Always call `equip_item()` which checks `equip_slot` | Prevents weapon in HEAD slot |
| Access `item_data` outside Inventory class | Use `create_item()` which merges tech + i18n | Ensures consistent data resolution |

## 8. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| UT-INV-01 | `add_item` | 5 potions (stack_max=10) to empty | Slot 0 has qty=5, returns 0 |
| UT-INV-02 | `add_item` | 15 potions (stack_max=10) to empty | Slot 0 qty=10, slot 1 qty=5, returns 0 |
| UT-INV-03 | `add_item` | Item when full | Returns full quantity |
| UT-INV-04 | `add_item` | Stack onto existing partial stack | Existing stack fills first |
| UT-INV-05 | `equip_item` | Valid slot match | Returns `None`, item equipped |
| UT-INV-06 | `equip_item` | Wrong slot | Returns item untouched |
| UT-INV-07 | `equip_item` | Slot already occupied | Returns swapped item |
| UT-INV-08 | `unequip_item` | Occupied slot | Returns item, slot is None |
| UT-INV-09 | `unequip_item` | Empty slot | Returns None |
| UT-INV-10 | `create_item` | Unknown item_id | Uses fallback name/icon |
| UT-INV-11 | `is_full` | 28/28 slots occupied | Returns True |
| UT-INV-12 | `remove_item` | Valid index with item | Returns item, slot is None |

### Integration Tests
| Test ID | Flow | Verification |
|---------|------|--------------|
| IT-INV-01 | Pickup → add_item → UI display | Item appears in correct slot with icon |
| IT-INV-02 | Equip → save → load → verify | Equipment persists across save/load |
| IT-INV-03 | Chest transfer → inventory | Stacking respects stack_max across containers |

## 9. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing `propertytypes.json` | `os.path.exists()` | Log ERROR | `item_data = {}` |
| Invalid JSON in propertytypes | `json.JSONDecodeError` | Log ERROR | `item_data = {}` |
| Unknown `item_id` in `create_item` | `item_data.get(id, {})` | No error | Default stack_max=1, icon=`{id}.png` |
| Invalid equipment slot name | `slot_name not in equipment` | Return item | No mutation |
| Index out of bounds in `get_item_at` | Range check | Return `None` | No error |

## 10. Deep Links
- **Item dataclass**: [inventory_system.py:9-17](../../src/engine/inventory_system.py#L9)
- **Inventory class**: [inventory_system.py:19-143](../../src/engine/inventory_system.py#L19)
- **InventoryUI consumer**: [inventory.py](../../src/ui/inventory.py#L1)
- **ChestUI consumer**: [chest_transfer.py](../../src/ui/chest_transfer.py#L1)
- **SaveManager serialization**: [save_manager.py](../../src/engine/save_manager.py#L1)

## 11. Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| 1 | 28 is the permanent inventory capacity | Low | Config could evolve |
| 2 | Equipment slots are fixed at 8 | Low | No dynamic slot system planned |
| 3 | `propertytypes.json` is the single source of item tech data | Medium | Verify no duplicate definitions |
| 4 | All items have unique string IDs | Low | Enforced by JSON key uniqueness |
| 5 | `equip_slot` in propertytypes is the canonical validation | Medium | UI must also respect this |
