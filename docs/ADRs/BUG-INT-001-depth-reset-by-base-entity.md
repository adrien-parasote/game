# BUG-INT-001 — InteractiveEntity depth reset by BaseEntity.__init__

**Status**: Fixed  
**Date**: 2026-05-17  
**Component**: `src/entities/interactive.py`

## Problem

`InteractiveEntity` objects with a Tiled `sprite.depth` value other than `1` (the default) were silently rendered at depth `1` at runtime, regardless of the configured value.

**Symptom**: A drawbridge configured with `depth=0` in Tiled appeared at the same Y-sort depth as the player, causing the player to disappear visually when walking over the bridge.

**Root cause**: Initialization order in `InteractiveEntity.__init__`:

```
_parse_properties()   → self.depth = 0  ✅  (from Tiled)
_load_assets()
_setup_physics()      → super().__init__()  → BaseEntity.__init__  → self.depth = 1  ❌ OVERWRITES
```

`BaseEntity.__init__` always initialises `self.depth = 1`. Because `_setup_physics` calls `super().__init__()` **after** `_parse_properties` had already set the correct value, the Tiled value was silently discarded on every spawn.

## Decision

Re-apply `self.depth = depth` immediately after `_setup_physics()` in `InteractiveEntity.__init__`. This is the minimal, non-invasive fix — no change to `BaseEntity` or the call order of sub-methods.

```python
self._setup_physics(pos, t_w, t_h, is_passable, obstacles_group, groups, element_id)

# Restore depth from Tiled: BaseEntity.__init__ (called inside _setup_physics via
# super().__init__) resets self.depth = 1. We must re-apply the Tiled value here.
self.depth = depth
```

## Consequences

- All interactive entities now correctly reflect their Tiled `sprite.depth` value at runtime.
- `depth=0` entities are rendered in the background pass (before the player), enabling floor-level bridge rendering.
- `depth=1` entities (99% of all interactive objects) are unaffected — the reassignment is a no-op.
- Regression tests: `TC-INT-DEPTH-01`, `TC-INT-DEPTH-02`, `TC-INT-DEPTH-03`.

## Lessons Learned

When a class uses private setup helpers that call `super().__init__()` internally, any state set before that call is at risk of being reset by the parent. Document the initialization order explicitly and re-apply configuration values after the parent call.
