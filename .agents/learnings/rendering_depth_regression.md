# Learning: Rendering Depth Regression & Multi-Pass Pipeline Fix

## Context
A regression was introduced in `RenderManager.draw_scene()` where interactive objects (chests, levers, NPCs) with `depth=1` were becoming invisible or being occluded by foreground tiles with `depth=2`.

## Root Cause
The rendering pipeline was split into two entity drawing passes (Pass 2 and Pass 3b) with the `draw_foreground()` (Pass 3) in between.
The original split point was `player.depth` (1):
- **Pass 2**: `max_depth=1` -> Drew everything at `depth <= 1` (including chests, player, NPCs).
- **Pass 3**: `draw_foreground()` -> Drew walls/tiles at `depth=2`.
- **Pass 3b**: `min_depth=2` -> Drew torches/higher objects at `depth=2`.

Because `depth=1` entities were drawn in Pass 2, they were completely covered by the `depth=2` tiles drawn in Pass 3.

## Solution
Shifted the pivot point to `player.depth - 1` (0) to ensure only strictly background elements (floor-level pickable items, etc.) are drawn before the foreground tiles.
- **Pass 2**: `max_depth=player.depth - 1` (0) -> Only ground-level sprites.
- **Pass 3**: `draw_foreground()` -> Draws walls/foreground tiles (`depth=2`).
- **Pass 3b**: `min_depth=player.depth` (1) -> Draws player, NPCs, chests, levers, and torches.

This ensures all interactive entities are rendered **after** the world geometry they might overlap, maintaining their visibility.

## Verification
- **TC-04** in `tests/engine/test_bug_depth2_sprite_invisible.py` was updated to enforce this specific pass filtering.
- Visual verification in `99-debug_room.tmj` confirmed chests and levers are now visible against walls.

## Anti-Pattern to Avoid
Don't draw interactable entities (chests, NPCs) in the background pass if they share the same or lower depth than the walls they sit against. The "interactable layer" should almost always be rendered after the "static geometry layer" to ensure visibility.
