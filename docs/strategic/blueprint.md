# Strategic Blueprint: Interaction & Teleportation Refinement

## 1. What exact problem are you solving?
Current interaction and teleportation logic is too permissive and relies on legacy Tiled metadata. This leads to accidental map transitions and unrealistic object interactions (activating items while looking away).

## 2. What are your success metrics?
- **Zero accidental teleports**: Teleporters only trigger if the player's movement direction matches the `required_direction`.
- **Realistic Interactions**: `activate_from_anywhere` objects now require the player to be facing them from an adjacent tile.
- **Strict Data Model**: Objects are identified by explicit `type` properties rather than legacy class IDs.
- **Test Integrity**: All 133+ tests pass, including new edge cases for direction-aware logic.

## 3. Why will you win?
By enforcing "Intentionality" in controls, we improve the player's sense of agency. The game feels more polished when the transition between maps reflects a deliberate action (pushed a direction to enter a room) rather than a collision mishap.

## 4. What's the core architecture decision?
Implementing a **Directional Guard** at the engine level (`Game` loop). We leverage existing `player.current_state` (facing) and `player.direction` (intent) to validate interactions before they fire.

## 5. What's the tech stack rationale?
Python/Pygame with Tiled integration. The specific use of `_get_property` allows us easy access to custom metadata without hardcoding object indices.

## 6. What are the MVP features?
- Support for `any` as a `required_direction` for teleporters.
- Strict mapping of `type=teleport` in `_spawn_entities`.
- Facing-aware validation for all interactive triggers.

## 7. What are you NOT building?
- Automatic pathfinding to objects.
- Multi-tile trigger regions (beyond standard Tiled object rects).
- Visual UI for selecting directions.
