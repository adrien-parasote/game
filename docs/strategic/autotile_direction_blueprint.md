---
status: PROMOTED_TO_SPEC
date: 2026-05-13
promoted: 2026-05-15
---

# Blueprint: Directional Movement and Autotiles

> **Implementation Spec:** [`docs/specs/map-parser-spec.md`](../specs/map-parser-spec.md) (sections `walkable`, `direction_flags`, `TileMapData`)  
> ~~Phase 1.6 spec consolidated into map-parser-spec.md on 2026-05-15~~ — see also [`engine-core.md`](../specs/engine-core.md)  
> This blueprint was promoted to spec on 2026-05-15. The gaps below have been resolved.

## 7 Questions Strategy

1. **What exact problem are you solving?**
   We are shifting from a binary collision model (`collidable`) to a richer traversal model (`walkable` + `direction`). This allows one-way tiles, ledges, or constrained paths. Concurrently, we are adding simple (`00-grass-1`) and animated (`01-water`) autotiles to improve map aesthetics without tedious manual placement.

2. **What are your success metrics?**
   - The engine correctly interprets `walkable` and blocks movement when `False`.
   - The engine intercepts movement requests and cancels them if the *current* tile's `direction` flags do not include the intended movement vector.
   - Autotiles render seamlessly in-game.

3. **Why will you win?**
   By leveraging Tiled's native `valuesAsFlags` enum, we can easily represent allowed directions as a comma-separated string. Centralizing the constraint check in `BaseEntity.start_move()` cleanly intercepts all entity movements without modifying individual AI or player input scripts.

4. **What's the core architecture decision?**
   The directional constraint is applied to the **departure** tile, not the arrival tile. Before an entity begins moving to `target_pos`, it asks the map: "Does the tile I am currently standing on allow me to exit in `self.direction`?".

5. **What's the tech stack rationale?**
   Python, Pygame, and Tiled (JSON/TMJ). The existing `tmj_parser` and `map_manager` will simply extract new properties.

6. **What are the features?**
   - Parser update: Extract `walkable` (default `True`) and `direction` (default `"any"`).
   - Engine update: `MapManager.is_walkable(x, y)` and `MapManager.get_allowed_directions(x, y)`.
   - Physics update: `BaseEntity.start_move()` validation.
   - Asset pipeline: Ensure `scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py` handles the new autotiles.

7. **What are you NOT building?**
   We are not building complex A* pathfinding modifications for NPCs yet; NPCs will simply fail to move if constrained. We are not implementing z-axis jumping over constrained tiles.

## Gap Discovery

> All gaps have been resolved prior to specification promotion (2026-05-15).

| # | Gap | Resolution |
|---|-----|------------|
| 1 | **Movement Constraint Semantics**: Does `direction=up` restrict *entering* or *exiting* the tile? | **Resolved:** Exiting. The constraint is evaluated at the **departure** tile — see `map-parser-spec.md` § direction_flags. |
| 2 | **Autotile Pipeline Support**: Support for 4-frame RPG Maker XP water autotiles? | **Resolved:** Yes, `scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py` supports animated frames — see research `autotile_directional_movement_research.md`. |
| 3 | **Backwards Compatibility**: Migration from `collidable` to `walkable`? | **Resolved:** `collidable` is parsed as a fallback (`walkable = not collidable` if `walkable` is absent) — see `map-parser-spec.md` § TileMapData Assumptions. |
