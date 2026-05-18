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
- `depth=1` entities (99% of all interactive objects) are unaffected — the reassignment is a no-op.
- Regression tests: `TC-INT-DEPTH-01`, `TC-INT-DEPTH-02`, `TC-INT-DEPTH-03`.

## Lessons Learned

When a class uses private setup helpers that call `super().__init__()` internally, any state set before that call is at risk of being reset by the parent. Document the initialization order explicitly and re-apply configuration values after the parent call.

---

## Addendum — BUG-BRIDGE-RENDER-001: Y-sort occulsion after depth fix

**Date**: 2026-05-18  
**Related bug**: After the depth-fix above, setting the bridge to `depth=1` placed it in the same `custom_draw` pass as the player. The bridge's tall sprite (224px) had a `rect.bottom` further south than the player's `rect.bottom`, causing the bridge to render **after** the player in the Y-sort — hiding the player when walking on the bridge.

**Fix**: For `sub_type=="bridge"`, `InteractiveEntity.__init__` now sets `self.sort_y = self.rect.top`. `CameraGroup.get_sorted_sprites()` uses `getattr(s, "sort_y", s.rect.bottom)` as the sort key. This makes the bridge sort by its **top edge**, so any sprite with `rect.bottom > bridge.rect.top` (standing on or south of the bridge) renders in front.

**Tests**: `TC-BRIDGE-SORT-01` through `TC-BRIDGE-SORT-04` in `tests/entities/test_interactive.py` and `tests/entities/test_groups.py`.
