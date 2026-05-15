---
title: Autotile and Directional Movement Research
status: VALIDATED
---

# Research Results: Autotile and Directional Movement

## Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | `collidable` to `walkable` migration | Identify all impacted engine systems | Codebase search, `tmj_parser`, `manager.py`, `collision_checker.py` |
| 2 | `23-direction` property parsing | Understand how Tiled exports `valuesAsFlags` enum | Tiled documentation, `game.tiled-project` |
| 3 | Directional movement constraint logic | Define the exact algorithm for restricting movement | Codebase `base.py`, `player.py` |
| 4 | Autotile integration (`00-grass-1`, `01-water`) | Ensure asset pipeline supports simple and animated Wangsets | Existing python scripts (`scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py`) |

## Source Evaluation
| Source | Type | Date | Credibility | Key Findings | Conflicts? |
|--------|------|------|-------------|-------------|------------|
| `src/map/tmj_parser.py` | Code | Current | High | `collidable` is parsed as a boolean from Tiled `properties`. Must be inverted to `walkable`. | No |
| `src/map/manager.py` | Code | Current | High | `is_collidable(x, y)` checks `getattr(self.tiles[tile_id], "collidable", False)`. Needs to change to `is_walkable`. | No |
| `src/engine/collision_checker.py` | Code | Current | High | Calls `map_manager.is_collidable`. Logic will cleanly shift to `is_walkable`. | No |
| `src/entities/base.py` | Code | Current | High | `start_move()` calculates `target_pos` and calls `collision_func`. We must add logic to check the **current** tile's `direction` property before allowing `self.direction` vector to apply. | No |
| Tiled Enum Flags Docs | Docs | Current | High | Enum with `valuesAsFlags=true` exports as a comma-separated string (e.g. `"up,right"` or `"any"`). | No |

## Conflict Analysis
| Sources | Claim A | Claim B | Reason for Discrepancy | Resolution |
|---------|---------|---------|----------------------|------------|
| `base.py` movement | Checks target tile validity. | User wants "next direction depends on direction property" of current tile. | The current implementation only checks if the destination is valid. | Update `start_move` to first validate `self.direction` against the current tile's `direction` flags before checking destination `walkable`. |

## Gaps Identified
| Gap | Why It Matters | What Research Would Fill It |
|-----|---------------|---------------------------|
| Animated Autotile Pipeline | We need to generate `01-water` (animated). | Existing `scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py` handles blob autotiles. Needs to verify if it supports animated RPG Maker XP frames (which use 4 frames per tile). |

## Recommendation
- **Chosen approach:** Adapt existing map parsing to use `walkable` (default `True`), and augment `start_move()` in `BaseEntity` to restrict movement based on the current tile's `direction` string.
- **Justification:** Centralizing the logic in `BaseEntity.start_move()` prevents duplication across all entities and cleanly intercepts movement before destination collision checks.
- **Impact on spec:** The `engine-core.md` or `map-parser-spec.md` specs must be updated to reflect `walkable` and `direction` parsing. `game-flow-spec.md` or similar must mention the movement constraint.

## Discovered Patterns
- **Property parsing:** Tiled flags export as comma-separated strings. We will split by `,` and strip whitespace. If `"any"` is present or the list is empty/missing, all directions are allowed.
- **Vector mapping:** We must map `self.direction` (Vector2) to string values (`up`, `down`, `left`, `right`) to intersect with the tile's allowed directions.
  - `(0, -1)` -> `up`
  - `(0, 1)` -> `down`
  - `(-1, 0)` -> `left`
  - `(1, 0)` -> `right`
- **Inverted Default:** `collidable` defaulted to `False`. `walkable` will default to `True`.
