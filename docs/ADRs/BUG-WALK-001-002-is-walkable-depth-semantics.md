# BUG-WALK-001 / BUG-WALK-002 — `is_walkable` Multi-Layer Depth Semantics

**Date**: 2026-05-17  
**Status**: Resolved  
**Type**: Bug Fix + Architectural Decision

---

## Context

Two related bugs were discovered in `MapManager.is_walkable` when testing multi-layer tile stacking.

### BUG-WALK-001 — Topmost tile wins (original fix attempt)

`is_walkable` used AND logic across all layers: any `walkable=False` tile in any layer blocked movement.

**Symptom**: A bridge (`walkable=True`) stacked on a ravine (`walkable=False`) → player blocked.

**Attempted fix**: "topmost tile wins" — return walkable of the highest-order non-empty tile.

### BUG-WALK-002 — Foreground decorations blocking ground (real-world failure)

After the BUG-WALK-001 fix, the bridge in the debug room still blocked the player.

**Root cause**: The bridge is built with two layer types:
- Layer 0 (order=0): stone floor, `walkable=True, depth=0`  
- Layer 1 (order=1): visual edges, `walkable=False, depth=2`

The "topmost wins" logic returned the edge tile (`walkable=False`) since it was on the higher layer — still blocking the player.

---

## Decision

**`is_walkable` only considers `depth=0` tiles (ground/floor tiles).**

Rules:
1. Scan layers from highest to lowest order.
2. Skip any tile with `depth≥1` (visual decorations, foreground walls).
3. Return the `walkable` property of the first non-empty `depth=0` tile found.
4. If no `depth=0` tile exists at position → return `False`.

## Why depth=0 only?

The `depth` axis in the engine has a specific semantic meaning:
- `depth=0` → ground/floor tile — defines the terrain the player stands on
- `depth≥1` → visual layer rendered above the player — decorations, wall tops, bridge edges

A `depth=2` tile is by definition NOT the ground. It's a visual element. Its `walkable` property should only affect rendering decisions, not movement collision.

## Architecture: Two complementary functions

| Function | Tiles considered | Question answered |
|---|---|---|
| `is_walkable(x, y)` | depth=0 only | Can I stand here? |
| `get_direction_flags(x, y)` | ALL depths | Which exits are allowed? |

A `depth=2` tile with `direction={up,left,right}` CAN constrain movement exits via `get_direction_flags` — this is the intended use case for guardrails, bridge barriers, etc.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| AND of all layers | Foreground decorations with walkable=False block walkable floors |
| Topmost tile wins (any depth) | Same problem — foreground layer overwrites ground layer |
| Ignore all depth≥1 for walkable AND direction | Too restrictive — depth≥1 tiles with direction constraints are valid |

## Test Coverage

| Test | Purpose |
|---|---|
| `test_is_walkable_bridge_over_ravine` | depth=0 bridge over depth=0 ravine → True |
| `test_is_walkable_ravine_without_bridge` | Lone non-walkable depth=0 → False |
| `test_is_walkable_depth0_ground_blocks_when_not_walkable` | Non-walkable depth=0 → False |
| `test_is_walkable_decor_depth2_does_not_block_walkable_ground` | BUG-WALK-002 exact repro → True |
| `test_is_walkable_non_walkable_depth0_on_top_blocks` | Non-walkable depth=0 on top → False |
| `test_depth1_tile_contributes_direction_but_not_walkability` | depth=2 guardrail constrains direction, not walkable |
| `test_decor_depth2_walkable_false_no_direction_does_not_constrain` | Bridge edge: no effect on either |
