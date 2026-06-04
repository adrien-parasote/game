# ADR-005: Animated Autotile Tileset Layout & Cycle Rules

## Context
We need to support animated autotiles (water/floor and waterfalls) in the autotile converter. Tiled's TSX format supports animations by referencing a sequence of frame tile IDs. We need a deterministic way to arrange the frames in the output PNG sheet and define the animation loops in the TSX metadata.

## Options Considered

### Option A: Vertical Stacking (8 columns, 6 × N rows)
Stack the 47-tile sheets for each frame vertically.
- Row 0-5: Frame 0 (tiles 0-47, where 47 is padding)
- Row 6-11: Frame 1 (tiles 48-95, where 95 is padding)
- Row 12-17: Frame 2 (tiles 96-143, where 143 is padding)
- Row 18-23: Frame 3 (tiles 144-191, where 191 is padding)

*Pros:*
- Clean, standard 8-column layout maintained.
- Simple math to compute tile ID offsets: `tile_index + frame_index * 48`.
- Complete compatibility with Tiled's Terrain/Wangset paint brush on the first frame.
- Unused/padded 48th slot per frame is kept transparent.

*Cons:*
- Height increases with the number of frames (256x576 px for 3-frame 32px tiles), which is negligible.

### Option B: Horizontal Stacking (8 × N columns, 6 rows)
Align the frames side-by-side horizontally.

*Pros:*
- None.

*Cons:*
- Changes the tileset width dynamically, breaking Tiled's column-based index parsing.

---

## Chosen Solution: Option A

We will adopt vertical stacking. The generated PNG will always have 8 columns, and the row count will be `6 × N`, where `N` is the number of animation frames.

### Cycle Rules

1. **Water / Floor (3-frame Horizontal):**
   - RPG Maker engine cycles: `0 → 1 → 2 → 1` (ping-pong, 4 steps).
   - Tiled animation mapping:
     - Frame 0: `tileid = i`
     - Frame 1: `tileid = i + 48`
     - Frame 2: `tileid = i + 96`
     - Frame 3: `tileid = i + 48`
2. **Waterfall (3-frame Vertical):**
   - RPG Maker engine cycles: `0 → 1 → 2` (linear loop, 3 steps).
   - Tiled animation mapping:
     - Frame 0: `tileid = i`
     - Frame 1: `tileid = i + 48`
     - Frame 2: `tileid = i + 96`
3. **4-Frame Animation:**
   - Linear loop: `0 → 1 → 2 → 3` (4 steps).
   - Tiled animation mapping:
     - Frame 0: `tileid = i`
     - Frame 1: `tileid = i + 48`
     - Frame 2: `tileid = i + 96`
     - Frame 3: `tileid = i + 144`
