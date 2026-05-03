# Technical Spec: Item Interaction and Pickup System

> Document Type: Implementation


## 1. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Hardcode item properties in `PickupItem` | Use `propertytypes.json` as central source | Easier balance changes and consistency |
| Remove item from map before inventory check | Check `inventory.can_add()` first | Prevents losing items if pickup fails |
| Use `pygame.display.flip()` in entity code | Manage rendering in `Game` or `UI` classes | Separation of concerns and performance |
| Directly modify `Player` attributes from UI | Use `Inventory` methods (encapsulation) | Safer state management |
| Use absolute paths for assets | Use `os.path.join` and relative paths | Portability across OS |
| Assume `item_id` == `icon_filename` | Allow explicit `icon` property in metadata | Decouples IDs from asset filenames |
| Use full visual rect for pickup sorting | Use thin/shrunken hitbox for ground items | Ensures player always appears in front |
| Allow diagonal interactions for pickups | Require orthogonal alignment and facing | Keeps interaction consistent with other objects (`activate_from_anywhere`) |
| Call `pickup.kill()` without persisting state | Always call `world_state.set(key, {collected: True})` before `kill()` | Without persistence, item respawns on map reload |

## 2. Test Case Specifications

### Unit Tests Required
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-INV-001 | Inventory | Potion (max 10), qty 5 | Stacked, total 5 | New slot used if empty |
| TC-INV-002 | Inventory | Potion (max 10), qty 8 + 5 | One stack of 10, one of 3 | Partial stacking |
| TC-INV-003 | Inventory | Full grid | `can_add` returns False | No slot left |
| TC-PROP-001 | PropertyLoader | "ether_potion" | Returns {name, desc, stack_max} | Missing key returns default |

### Integration Tests Required
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-PICK-001 | Pickup Flow | Player near Item | Emote '?' visible, Press E -> Item moved to Inv | Remove item from group |
| IT-PICK-002 | Pickup Flow | Inventory Full | Emote 'frustration' visible, Item stays | Partial or no pickup |
| IT-UI-001 | UI Hover | Mouse over slot | Tooltip displays correct name/desc | Move mouse away |

## 3. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| Missing JSON | `FileNotFoundError` | Load empty dict | Default item props | ERROR | Toast "Config Error" |
| Missing Icon | `pygame.error` | Use magenta placeholder | No icon displayed | WARNING | None |
| Invalid Sprite | `NoneType` in draw | Skip draw call | Invisible item | ERROR | None |

## 4. Deep Links

- **Pickup Interaction Logic**: [interaction.py L166](../../src/engine/interaction.py#L166)
- **Proximity Emote Check**: [interaction.py L56](../../src/engine/interaction.py#L56)
- **`PickupItem` entity**: [pickup.py L1](../../src/entities/pickup.py#L1)
- **Inventory System**: [inventory_system.py L17](../../src/engine/inventory_system.py#L17)
- **Spawn logic**: [game.py L1](../../src/engine/game.py#L1)
- **Integration tests**: [test_interaction.py L119](../../tests/engine/test_interaction.py#L119)

### Linked Test Functions

| Spec ID | Test Function | File |
|---------|---------------|------|
| TC-INV-001 | `test_inventory_add_item_stacks_in_existing_slot` | `tests/ui/test_inventory.py:L37` |
| TC-INV-002 | `test_inventory_add_item_returns_overflow` | `tests/ui/test_inventory.py:L55` |
| TC-INV-003 | `test_inventory_is_full_true` | `tests/ui/test_inventory.py:L73` |
| IT-PICK-001 | `test_handle_interaction_pickup` | `tests/engine/test_interaction.py:L119` |
| IT-PICK-002 | `test_handle_interaction_pickup_partial` | `tests/engine/test_interaction.py:L141` |


## 5. Implementation Details

### Detection Logic
- Range: 48 pixels (same as NPCs/Chests).
- Emote: 'question' (as per `player.playerEmote('question')`).
- Alignment: Player must be orthogonally aligned (`abs(dx) < 20` or `abs(dy) < 20`) and facing the item.
- Exception (On Top): If the player is standing on top of a traversable item (distance < 16px), interaction is permitted regardless of alignment or facing. Diagonal interactions remain prohibited for distant items.

### Pickup Logic
1. Get `object_id` from Tiled properties.
2. Lookup in `propertytypes.json`.
3. Try to add to `player.inventory`.
4. If successful, persist collection state and remove entity from groups.
5. Depth Handling: Use shrunken hitbox (`20x10`) for pickups to ensure Y-sorting places player "in front".
6. Full Inventory: If `can_add` returns remaining > 0, trigger the `frustration` emote on the player instead of a dialogue.

### Session Persistence (WorldState)
Pickup items use the same `{map_basename}_{tiled_id}` key as interactive objects.

**On collection:**
- Full pickup → `world_state.set(key, {"collected": True})` → `pickup.kill()`
- Partial pickup (inventory full) → `world_state.set(key, {"quantity": remaining})`

**On map spawn (`_spawn_pickup`):**
- `world_state.get(key)["collected"] is True` → skip spawn entirely
- `world_state.get(key)["quantity"]` exists → spawn with restored quantity
- No saved state → spawn with original Tiled quantity

**Key source:** Native Tiled `obj["id"]` (always present, no manual config required).

### UI Logic
- Icons: `assets/images/icons/{item_id}.png`.
- Tooltip: Rendered in the green bar at bottom right of `InventoryUI`.
- Quantity: Small text at bottom-right of slot if > 1.