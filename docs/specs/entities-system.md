# Technical Specification — Entities & Objects System [Implementation]

> **Document Type:** Implementation
> **Source Files:** `src/entities/interactive.py`, `src/entities/pickup.py`, `src/entities/emote.py`, `src/entities/emote_sprite.py`, `src/engine/interaction.py`

This document consolidates all engine-level interactive entities, ground items, and emote visual indicators into a single, high-fidelity implementation specification.

---

## 1. Component & Visuality Model

| Entity Type | Base Class | Primary Responsibility | Collidable |
|-------------|------------|------------------------|------------|
| **InteractiveEntity** | `BaseEntity` | Doors, levers, chests, dynamic barriers | Conditional |
| **PickupItem** | `BaseEntity` | Ground items, currency, potions, materials | No |
| **EmoteSprite** | `pygame.sprite.Sprite` | Animated visual feedback bubbles | No |

---

## 2. Interactive Objects Specification

### 2.1 Tiled Data Schema
Every interactive object is configured in Tiled with custom properties:

| Property | Type | Default | Description |
|---|---|---|---|
| `sub_type` | string | — | Decides logic type (`door`, `bridge`, `chest`, `lever`, `sign`, `animated_decor`) |
| `is_passable` | bool | `false` | True if the player can cross this object's boundaries when ON/open |
| `is_animated` | bool | `false` | True if ON state plays a continuous loop (e.g. fire/torch) |
| `is_on` | bool | `false` | Initial state of the object |
| `trigger_only` | bool | `false` | If True, player direct input is blocked; state toggles only via remote triggers |
| `off_position` | int | `-1` | Column index for the OFF state sheet strip (for multi-col animation sheets) |
| `target_id` | string | `""` | ID of the target interactive entity to trigger on interaction |
| `contents` | list | `[]` | Loot items inside a container (`chest`) |
| `halo_size` | int | `0` | Radial light mask overlay size in pixels |
| `particles` | bool | `false` | True if object spawns particles when ON |

### 2.2 Animation & Slicing Invariant
- **Frame Height Rule**: To prevent tall sprites (e.g., 43px iron chests or 64px levers) from clipping or shifting off-center, **the spritesheet is the authoritative source for frame height**, not the Tiled grid dimensions. Frame height is dynamically calculated as:
  ```python
  frame_h = sheet_h // (end_row + 1)
  ```
  This is applied to set `self.sprite_height` and construct logical hitboxes.
- **`off_position` Toggle**: For `animated_decor` with `off_position >= 0`, toggling `is_on` switches `col_index` between `on_position` (col 0) and `off_position`.

---

## 3. Subtype Dynamics: Doors vs. Bridges

The engine handles doors (blocking barriers) and bridges (walkable path overrides) with two distinct collision contracts:

### 3.1 Collision & Passability Lifecycle

| State | `sub_type: door` | `sub_type: bridge` |
|---|---|---|
| **Spawn (Closed/OFF)** | Solid — added to `obstacles_group`. | Passable — never in `obstacles_group`. Water tiles block at map layer. |
| **Lowered/Open (ON)** | Passable (removed from obstacles) if `is_passable: true`. | Lowered — registered in `walkable_override_entities` to permit water crossing. |
| **Transitioning (Animating)** | Solid. | Blocked — marked untraversable during active frame movement. |

### 3.2 Walkable Override Zones (Bridges)
Bridges bypass map-level collision boundaries using `Game.walkable_override_entities`:
- **Enrollment**: Only entities with `is_passable=True` and `is_on=True` register their bounding rect into this set.
- **Evaluation**: `CollisionChecker.check` queries `walkable_override_entities` as **step 0**. If the coordinates intersect, movement is permitted immediately, skipping water tile checks.
- **Entrapment Protection**: Inside `InteractionManager.toggle_entity_by_id`, remote commands are blocked if they would raise a bridge while the player's bounding rect overlaps it.

---

## 4. Trigger-Only Mechanism

For automated traps, switches, or remote doors:
- **`trigger_only = true`**: Directly suppresses the proximity emote `(!)` and ignores direct player interact inputs (E).
- **Automation**: State changes can only trigger programmatically via `toggle_entity_by_id()` chaining.

---

## 5. Ground Item Pickup System

`PickupItem` represents collectible items lying on the map.

### 5.1 Proximity & Orthogonal Checking
- **Detection Distance**: Within 48px.
- **Interaction Constraints**: Player must be orthogonally aligned (`abs(dx) < 20` or `abs(dy) < 20`) and facing the item.
- **On Top Exception**: If the player is standing directly on the item (distance < 16px), interaction is allowed regardless of orientation.

### 5.2 Collection & Inventory Stacking
1. Checks `player.inventory.can_add(item_id, quantity)` to see if there's enough space.
2. If full, triggers `frustration` emote on the player; item remains on the ground.
3. If partial space exists, splits quantity: saves `world_state.set(key, {"quantity": remaining})` and updates the ground sprite.
4. If successfully collected: persists state `world_state.set(key, {"collected": True})` and calls `pickup.kill()`.

---

## 6. Animated Emote System

Emote bubbles appear above the player's head for visual feedback.

### 6.1 Column Mapping & Indexing
Asset: `assets/images/sprites/04-emotes.png` (5 columns × 8 rows).

| Emote Name | Col | Trigger Condition |
|------------|-----|-------------------|
| `love` | 0 | NPC affinity (future) |
| `bored` | 1 | NPC idle (future) |
| `interact` | 2 | Player within 48px of a standard interactive object/NPC |
| `question` | 3 | Failed interaction (no target or wrong side) |
| `frustration` | 4 | Attempting to pick up an item with a full inventory |

### 6.2 Lifespan & Path Interpolation
- **Duration**: 0.6 seconds.
- **Follow Logic**: Pinned to the parent's horizontal coordinate (`self._entity.rect.centerx`).
- **Rise Offset**: Interpolates upward linearly by 15px over its 0.6s lifetime.
- **Cooldown**: Proximity emotes (`interact`) have a **1.5s rate-limit** to prevent spam. Failed (`question`) and full-inventory (`frustration`) emotes have no cooldown for instant feedback.
- **Single-Emote Invariant**: Triggering a new emote immediately empties the parent's emote group.

---

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Add `bridge` to `obstacles_group` | Let water tiles handle raised blocking | Bounding rect is larger than water zone; would over-block |
| Guard `trigger_only` in `interact()` | Guard in `_is_object_interactable()` | Bypasses programmatic chaining in `toggle_entity_by_id()` |
| Hardcode item attributes in `PickupItem` | Load from `propertytypes.json` | Breaks single source of truth for balancing |
| Trigger proximity emotes in `ON` state | Suppress emotes for open doors/containers | Prevents visual clutter |
| Stack emotes | Empty the rendering group first | Visual clutter and memory leak |
| Slice sheets by hardcoded heights | Read sheet height dynamically | Fits tall assets cleanly into centering logic |

---

## 8. Error Handling Matrix

| Error Case | Detection | Mitigation | Fallback |
|------------|-----------|------------|----------|
| Non-Divisible Sheet | `sheet_h % (end_row + 1) != 0` | Truncate division | Use integer frames |
| Missing Icon Asset | `FileNotFoundError` | Log warning | Render magenta color block |
| Stale Walkable Overrides | Map transition | Clear override set | Avoids ghost zones |
| Old Save Slot | AttributeError in `trigger_only` | Fallback to `False` | Backward compatibility |

---

## 9. Test Case Specifications

### 9.1 Unit Tests
- **UT-INT-01**: `is_on` toggle on an interactive door updates collision block state.
- **UT-INT-02**: Bridge spawning never registers in `obstacles_group` regardless of `is_on` state.
- **UT-INT-03**: Walkable bridgeLowered adds entity rect to `walkable_override_entities`.
- **UT-INT-04**: EmoteSprite `update` linear Y-offset interpolation rises by exactly 15px over 0.6s.
- **UT-INT-05**: Frame height computed dynamically matches sheet height for iron chests.
- **UT-INT-06**: `trigger_only` entity blocks direct E-key inputs.

---

## 10. Deep Links
- **Interactive Objects logic**: [interactive.py L1](../../src/entities/interactive.py#L1)
- **Ground pickups logic**: [pickup.py L1](../../src/entities/pickup.py#L1)
- **Emote manager & sprites**: [emote.py L1](../../src/entities/emote.py#L1)
- **Walkable override set updates**: [game.py L119](../../src/engine/game.py#L119)
