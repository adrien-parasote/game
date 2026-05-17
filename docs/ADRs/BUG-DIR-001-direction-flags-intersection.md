# BUG-DIR-001 — `get_direction_flags` Multi-Layer Semantics: Intersection vs Last-Write-Wins

**Date**: 2026-05-17  
**Status**: Resolved  
**Type**: Bug Fix + Architectural Decision  

---

## Context

`MapManager.get_direction_flags(x, y)` was returning the direction flags of the **last non-empty layer** (last-write-wins). This caused a silent bug when stacking tiles across layers:

```
Layer 0: {"any"}               ← no constraint
Layer 1: {"down","left","right"} ← restricts movement
Layer 2: {"any"}               ← no constraint, but OVERWROTE Layer 1
```

Result (buggy): `{"any"}` — player could move in all directions including `up`.  
Expected result: `{"down","left","right"}` — `up` must be blocked.

## Decision

**`get_direction_flags` computes the INTERSECTION of all constrained layers.**

Rules:
1. A tile with `{"any"}` is a **neutral joker** — it imposes no constraint and is ignored.
2. A tile with specific directions (e.g. `{"down","left"}`) is a **constraint** — it is collected.
3. The result is the intersection of all collected constraints.
4. If no layer has a specific constraint → return `{"any"}`.

## Why intersection and not union?

- **Union** would mean "any direction allowed by ANY layer" → too permissive.
- **Intersection** means "only directions allowed by ALL constrained layers" → correct restrictive semantics.
- A layer with `{"any"}` should NOT override a restrictive layer below it — it simply has no opinion.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Last-write-wins (top layer) | Silently erases constraints from lower layers depending on stacking order |
| Union of all layers | Too permissive — `any` in one layer would always expand to `any` overall |
| Only check highest constrained layer | Still order-dependent; misses intersection constraints between two specific layers |

## Impact

- `src/map/manager.py`: `get_direction_flags()` rewritten
- `docs/specs/map-parser-spec.md`: Updated description + new anti-pattern BUG-DIR-001
- `tests/map/test_map.py`: 3 new regression tests added

## Test Coverage

| Test | Purpose |
|---|---|
| `test_direction_flags_multilayer_any_does_not_override_constraint` | Exact reproduction of BUG-DIR-001 |
| `test_direction_flags_multilayer_intersection` | Two constrained layers → intersection returned |
| `test_direction_flags_all_any_returns_any` | All-`any` layers → `{"any"}` returned |
