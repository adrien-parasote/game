# Technical Spec: Item Interaction and Pickup System

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

- [Pickup Interaction Logic](file:///Users/adrien.parasote/Documents/perso/game/src/engine/interaction.py#L166)
- [Proximity Emote Check](file:///Users/adrien.parasote/Documents/perso/game/src/engine/interaction.py#L56)
- [Inventory UI](file:///Users/adrien.parasote/Documents/perso/game/src/ui/inventory.py#L1)
- [Inventory System](file:///Users/adrien.parasote/Documents/perso/game/src/engine/inventory_system.py#L17)
- [Player Entity](file:///Users/adrien.parasote/Documents/perso/game/src/entities/player.py#L1)
- [Asset Path Config](file:///Users/adrien.parasote/Documents/perso/game/src/config.py)

## 5. Implementation Details

### Detection Logic
- Range: 48 pixels (same as NPCs/Chests).
- Emote: 'question' (as per `player.playerEmote('question')`).

### Pickup Logic
1. Get `object_id` from Tiled properties.
2. Lookup in `propertytypes.json`.
3. Try to add to `player.inventory`.
4. If successful, remove entity from `all_sprites` and `interactives`.
5. Depth Handling: Use shrunken hitbox (`20x10`) for pickups to ensure Y-sorting places player "in front".
6. Full Inventory: If `can_add` returns remaining > 0, trigger the `frustration` emote on the player instead of a dialogue.

### UI Logic
- Icons: `assets/images/icons/{item_id}.png`.
- Tooltip: Rendered in the green bar at bottom right of `InventoryUI`.
- Quantity: Small text at bottom-right of slot if > 1.
