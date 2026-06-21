# Concept: Dynamic Stair Clipping

> One-sentence problem statement: The Player and NPCs need their sprites partially clipped when walking on descending stair tiles because it visually simulates descending behind the staircase/floor structure while keeping physical movement horizontal.

## Problem
In a 2.5D top-down perspective, descending stairs should look like the character is sinking into the staircase. If we simply shift the sprite downwards, the bottom of the sprite (feet) overlaps the floor below the stairs, breaking the depth illusion. We need the sprite to be clipped dynamically from the bottom to represent the character being occluded by the stair steps.

## Direction
Adopt **Skeleton A (Direct Sprite Cropping)**:
- We will dynamically crop the bottom portion of the entity sprite during `blit` in `CameraGroup.custom_draw` using Pygame-CE's `area` parameter.
- The amount of clipping will be driven by a new attribute `current_stair_clip` on `BaseEntity`, which smoothly interpolates alongside `current_stair_offset` during transitions.
- The maximum clip amount for a tile is retrieved as the absolute value of the tile's `visual_y_offset` property.

## Target User
The Player and any PNJ (NPC) entities traversing descending stair tiles.

## Success Looks Like
- When standing on a stair tile with `clip = true` and `visual_y_offset = 24`, the sprite's bottom 24 pixels are cropped, and the top of the sprite is shifted down by 24 pixels.
- The visual bottom of the sprite remains aligned with the bottom of the tile.
- When moving between a clipped and a non-clipped tile, the transition is completely smooth with no visual jumping or popping.
- Performance is unchanged with zero dynamic memory allocation.

## Scope Boundaries
What's IN:
- Clipping for any tile in the TMJ map where the Tiled property `clip = true` is set.
- Smooth interpolation of the clip amount during movement.
- Clamping of the clip amount between 0 and the sprite's height.
- Fallback of clip amount to 8 pixels if `visual_y_offset` is empty or not specified on a clipped tile.

What's NOT (and why):
- Masking with arbitrary shapes (non-rectangular) — because simple rectangular cropping is sufficient for 26.5° stairs and is much more performant.
- Changing logical/physical coordinates on the Y-axis — because physical movement remains purely horizontal to preserve simple grid collision physics.

## Key Assumptions
Assumptions surfaced and confirmed during /frame and /clarify:
- **Tiled Property Trigger:** The clipping effect is triggered solely by the presence of `clip = true` on the map tiles, regardless of their ID. — Status: Confirmed.
- **Physical Y Movement:** No physical Y movement is executed on these stairs. — Status: Confirmed.
- **Clip calculation:** The clip amount uses the absolute value of `visual_y_offset` (defaulting to 8 if missing, clamped to sprite height). — Status: Confirmed.
- **PNJ Support:** NPCs moving on these tiles are clipped in the exact same manner. — Status: Confirmed.
- **Transition fluidity:** The clip amount is interpolated during movement progress. — Status: Confirmed.

## Open Questions for Strategy
- Should the clipping coordinate calculation take into account other sprite-altering effects such as grass wading? (Grass wading redraws the bottom 8px of the sprite using a grass texture; if clipped, how do they interact?)
