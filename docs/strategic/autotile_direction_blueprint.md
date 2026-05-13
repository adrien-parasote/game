---
status: PROPOSED
date: 2026-05-13
---

# Blueprint: Directional Movement and Autotiles

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
   - Asset pipeline: Ensure `rpgmaker_blob_autotile_to_tiled.py` handles the new autotiles.

7. **What are you NOT building?**
   We are not building complex A* pathfinding modifications for NPCs yet; NPCs will simply fail to move if constrained. We are not implementing z-axis jumping over constrained tiles.

## Gap Discovery

| # | Gap | Impact if unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | **Movement Constraint Semantics**: Does `direction=up` restrict *entering* the tile, *exiting* the tile, or both? (Assume exiting based on prompt, but need confirmation). | Movement behavior (one-way walls vs conveyor belts) will be implemented incorrectly. | User |
| 2 | **Autotile Pipeline Support**: Do the current scripts fully support animated 4-frame RPG Maker XP water autotiles, or do we need to expand the script logic? | `01-water` will not convert correctly, delaying asset integration. | User |
| 3 | **Backwards Compatibility**: Do we need to migrate existing maps from `collidable` to `walkable`, or handle `collidable` gracefully as a fallback? | Older maps will crash or have completely broken collision (defaulting to walkable). | User |
