# Technical Specification — `trigger_only` Interactive Objects [Implementation]

> Document Type: Implementation
> Parent spec: [interactive-objects.md](./interactive-objects.md#L1)

---

## 1. Overview

Some interactive objects must **not be operable directly by the player** (no emote, no direct `E` key toggle). They can only change state when commanded by another entity via `toggle_entity_by_id()` (e.g. a lever or a button with a `target_id` pointing to them).

**Examples:**
- Drawbridge controlled exclusively by a lever
- Dungeon portcullis raised only by a distant pressure plate
- Timed mechanism activated by a button elsewhere in the room

This is expressed via a single boolean Tiled property: `trigger_only`.

---

## 2. Tiled Property

### 2.1. Property Definition

Added to the `11-interactive_object` class in `assets/tiled/game.tiled-project`:

| Property | Type | Default | Class |
|----------|------|---------|-------|
| `trigger_only` | `bool` | `false` | `11-interactive_object` |

**Semantic**: when `trigger_only = true`, the object:
1. Does **NOT** show a proximity emote (`!`) to the player
2. Does **NOT** respond to the player's `E` key (direct interaction)
3. **DOES** respond to `toggle_entity_by_id()` calls from any triggering entity

### 2.2. Default Behaviour

`trigger_only = false` (default) preserves the existing behaviour for all objects that do not declare this property. Zero breakage to existing maps.

### 2.3. Tiled Setup Example

```
Object: drawbridge_01
  Class: 11-interactive_object
  Properties:
    sub_type: bridge
    trigger_only: true       ← NEW
    is_passable: true
    is_on: true
    target_id: (empty)

Object: lever_01
  Class: 11-interactive_object
  Properties:
    sub_type: lever
    trigger_only: false      ← Player CAN interact
    target_id: drawbridge_01 ← Chains to the bridge
```

---

## 3. Engine Changes

### 3.1. `InteractiveEntity` — Store the attribute

**File**: [`src/entities/interactive.py`](../../src/entities/interactive.py#L218)

In `_parse_misc()`, add `trigger_only` parameter and store it:

```python
def _parse_misc(
    self, particles, particle_count, activate_from_anywhere,
    sfx, sfx_open, sfx_close, sfx_ambient, material, trigger_only,   # +1 param
):
    ...
    self.trigger_only = trigger_only   # bool — disables direct player interaction
```

In `__init__()`, add `trigger_only: bool = False` parameter and thread it through `_parse_properties()` → `_parse_misc()`.

**File**: `src/entities/interactive.py` inside `_parse_properties()` signature:
```python
    def _parse_properties(
        self, sub_type, start_row, end_row, is_on, is_animated, depth, position,
        off_position, halo_size, halo_color, halo_alpha, particles, particle_count,
        activate_from_anywhere, sprite_sheet, facing_direction, sfx, sfx_open,
        sfx_close, sfx_ambient, material, day_night_driven, trigger_only,   # +1 param
    ):
```

And thread it when calling `_parse_misc()` inside `_parse_properties()`:
```python
        self._parse_misc(
            particles, particle_count, activate_from_anywhere, sfx, sfx_open,
            sfx_close, sfx_ambient, material, trigger_only   # +1 param
        )
```

**No change to `interact()` itself.** The guard is at the caller level (interaction manager), not the entity. `interact()` must remain reachable by `toggle_entity_by_id()` without restriction.

### 3.2. `EntityFactory` — Parse from Tiled

**File**: [`src/engine/entity_factory.py`](../../src/engine/entity_factory.py#L119)

In `spawn_interactive()`, add one line in the `InteractiveEntity(...)` call:

```python
trigger_only=bool(_get_property(props, "trigger_only", False)),
```

`_get_property()` already handles nested class resolution via `interactive_object` → flat key lookup. No change needed to `_get_property()`.

### 3.3. `InteractionManager` — Block direct player interaction

**File**: [`src/engine/interaction.py`](../../src/engine/interaction.py#L98)

In `_is_object_interactable()`, add guard as **first check** (short-circuit before any distance/orientation logic):

```python
def _is_object_interactable(self, obj, p_pos, p_state) -> bool:
    if getattr(obj, "trigger_only", False):
        return False
    # ... existing logic unchanged
```

`toggle_entity_by_id()` is **NOT modified**: it calls `entity.interact()` directly, bypassing `_is_object_interactable()`. This is the correct and intended path.

### 3.4. `InteractionEmoteMixin` — Suppress proximity emote

**File**: [`src/engine/interaction_emote.py`](../../src/engine/interaction_emote.py#L23)

In `_check_interactive_emote()`, add guard inside the loop, before the valid_position check:

```python
for obj in self.game.interactives:
    sq_dist = p_pos.distance_squared_to(obj.pos)
    if sq_dist >= _RANGE_SQ_48:
        continue
    if getattr(obj, "trigger_only", False):   # +NEW GUARD
        continue
    # ... existing logic unchanged
```

**Why `getattr` with default**: defensive access in case the attribute is absent (e.g. test stubs without the property). Default `False` preserves existing behaviour.

---

## 4. Data Flow

```
Tiled map (trigger_only=true)
  → TmjParser._parse_objects() → props dict
  → TiledProject.resolve("11-interactive_object", props)
  → entity_factory.spawn_interactive()
      → InteractiveEntity(trigger_only=True)
          → _parse_misc() → self.trigger_only = True

Player presses E near trigger_only object:
  → InteractionManager._check_object_interactions()
  → _is_object_interactable(obj, ...) → False (guard hit)
  → interaction skipped — no state change, no SFX

Player enters proximity of trigger_only object:
  → InteractionEmoteMixin._check_interactive_emote()
  → getattr(obj, "trigger_only", False) == True → continue
  → emote NOT triggered

Lever with target_id pointing to trigger_only bridge:
  → player interacts with lever (trigger_only=False) ← allowed
  → _trigger_object_interaction(lever)
  → toggle_entity_by_id("drawbridge_01")
  → entity.interact(player)  ← direct call, bypasses _is_object_interactable()
  → bridge state toggles ← works correctly
```

---

## 5. Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Guard inside `InteractiveEntity.interact()` | Guard in `_is_object_interactable()` | `interact()` must stay reachable by `toggle_entity_by_id()`. Blocking at the entity level would break chaining. |
| Add a new method `can_player_interact()` | Use `_is_object_interactable()` guard | Single point of truth for player interaction eligibility. No new protocol needed. |
| Check `trigger_only` in `toggle_entity_by_id()` | Leave `toggle_entity_by_id()` unchanged | Triggered objects MUST be togglable by other entities — that is the entire purpose of the property. |
| Use `obj.trigger_only` without `getattr` | `getattr(obj, "trigger_only", False)` | Defensive: test stubs or future entity types may not have the attribute. |
| Set `trigger_only=true` AND `target_id` on the SAME object | `trigger_only` on the controlled target, `target_id` on the trigger | A trigger_only object with a target_id would chain on toggle but never be triggerable by the player — confusing and untestable. |
| Suppress emote only for specific sub_types | Use the `trigger_only` flag | Sub-type gating is hardcoded and brittle; the flag is explicit intent from the map designer. |

---

## 6. Test Case Specifications

### Unit Tests

| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-001 | `_is_object_interactable` | `trigger_only=True`, player in range + correct facing | Returns `False` | Guard is first check |
| TC-002 | `_is_object_interactable` | `trigger_only=False`, player in range + correct facing | Returns `True` (existing path) | No regression |
| TC-003 | `_check_interactive_emote` | `trigger_only=True`, player within 48px + facing | Emote NOT triggered, returns `False` | Cooldown=0 |
| TC-004 | `_check_interactive_emote` | `trigger_only=False`, player within 48px + facing | Emote triggered normally | No regression |
| TC-005 | `InteractiveEntity.__init__` | `trigger_only=True` passed | `entity.trigger_only == True` | Default `False` |
| TC-006 | `InteractiveEntity.__init__` | no `trigger_only` arg (default) | `entity.trigger_only == False` | Backward compat |
| TC-007 | `entity_factory.spawn_interactive` | Tiled props `{"trigger_only": True}` | Spawned entity has `trigger_only=True` | Props nested in `interactive_object` class |
| TC-008 | `entity_factory.spawn_interactive` | Tiled props without `trigger_only` | Spawned entity has `trigger_only=False` | Default resolution |

### Integration Tests

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-001 | Lever → Bridge toggle | Lever (`target_id=bridge_01`, `trigger_only=False`) + Bridge (`trigger_only=True`, initial `is_on=False`) | Player interacts with lever → bridge.is_on flips to True | Reset state |
| IT-002 | Direct block | Bridge (`trigger_only=True`) in range, correct facing | Player presses E → bridge.is_on unchanged, no emote | — |
| IT-003 | Emote suppression | Bridge (`trigger_only=True`) within 48px | `_check_interactive_emote()` returns False | emote_group empty |

---

## 7. Error Handling

| Error | Detection | Response | Fallback |
|-------|-----------|----------|----------|
| `trigger_only` missing on entity (old save / test stub) | `getattr(obj, "trigger_only", False)` | Treats as `False` — player interaction allowed | Silent; backward compat |
| `trigger_only` set on a `sign` sub_type | No conflict — `sign.interact()` returns `element_id` before any toggle | Dialogue fires normally; `trigger_only` guard in emote/interactable short-circuits before reaching `interact()` | Log `INFO` at factory spawn if desired |
| `trigger_only=True` object has no triggering entity | Object stays at its Tiled default `is_on` value | Object is static for this session | No action needed — valid design intent |
| `toggle_entity_by_id` depth guard (depth > 1) | Existing guard in `interaction.py#L311` | Chain broken, warning logged | Existing behaviour unchanged |

---

## 8. Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| 1 | `TiledProject.resolve()` correctly flattens `trigger_only` from the `11-interactive_object` class template into the flat props dict | Low | `TC-007` — spawn from Tiled props with nested class |
| 2 | `toggle_entity_by_id()` is the only code path that bypasses `_is_object_interactable()`; no other caller directly calls `entity.interact()` on objects without going through the interaction manager | Low | `grep "\.interact(" src/` shows only: `interaction.py` (`_trigger_object_interaction`, `toggle_entity_by_id`, `_close_chest`) and `tests/`. All caller paths are controlled. |
| 3 | `trigger_only=False` (default) means no map change is required for existing objects — only new objects set it to `true` | Low | Default in `_parse_misc()` + `_get_property(props, "trigger_only", False)` |

---

## 9. Deep Links

- **`InteractiveEntity._parse_misc`**: [interactive.py#L218](../../src/entities/interactive.py#L218)
- **`InteractiveEntity.__init__` signature**: [interactive.py#L37](../../src/entities/interactive.py#L37)
- **`EntityFactory.spawn_interactive`**: [entity_factory.py#L106](../../src/engine/entity_factory.py#L106)
- **`InteractionManager._is_object_interactable`**: [interaction.py#L98](../../src/engine/interaction.py#L98)
- **`InteractionManager.toggle_entity_by_id`**: [interaction.py#L306](../../src/engine/interaction.py#L306)
- **`InteractionEmoteMixin._check_interactive_emote`**: [interaction_emote.py#L23](../../src/engine/interaction_emote.py#L23)
- **`TiledProject.resolve`**: [project_schema.py#L33](../../src/map/project_schema.py#L33)
- **Parent spec (interactive objects)**: [interactive-objects.md#L57](./interactive-objects.md#L57)
- **Unit tests (interactive entity)**: [test_interactive.py#L1](../../tests/entities/test_interactive.py#L1)
- **Integration tests (interaction)**: [test_interaction.py#L1](../../tests/engine/test_interaction.py#L1)
