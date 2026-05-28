# Research: RPG Maker XP Autotile to Tiled Wang Set (Edge-based)

## Context
The objective is to successfully map and convert RPG Maker XP (96x128px) autotiles into a functional Wang-terrain tileset for Tiled, switching from a 47-tile mixed-mode blob pattern to a simpler 16-tile edge-based matching.

## Findings

### Tiled Wang ID Format
Tiled's Wang IDs consist of a comma-separated list of 8 indices representing the colors applied to the 8 directions of the tile, starting from the top edge and going clockwise.
The sequence is:
1. Top Edge
2. Top-Right Corner
3. Right Edge
4. Bottom-Right Corner
5. Bottom Edge
6. Bottom-Left Corner
7. Left Edge
8. Top-Left Corner

### Current Script Issue
In `scripts/autotiles/rpgmaker_autotile_to_tiled.py`, the `_wang_id` function outputs:
`0,{t},0,{r},0,{b},0,{l}`
This assigns the Wang colors to the **corners** (indices 1, 3, 5, 7) instead of the **edges** (indices 0, 2, 4, 6), which completely breaks the `type="edge"` matching logic in Tiled. 

### Geometric Coordinate Mapping Issue
Some user-supplied autotiles (like `grass.png`) leave the standard RPG Maker XP "Tile B" (convex corners at top right) completely transparent. Relying on Tile B produces transparent "square" borders in Tiled.
To solve this reliably for all 96x128px autotiles, the script extracts features directly from the guaranteed **96x96 main block** (starting at row 2):
- **Convex Corners (`cvx_*`)**: extracted directly from the 4 absolute outer corners of the 96x96 block: `(0,2)`, `(5,2)`, `(0,7)`, `(5,7)`.
- **Straight Edges (`top_*`, `bot_*`, `lft_*`, `rgt_*`)**: extracted directly from the outer straight lines of the 96x96 block.
- **Center (`inn_*`)**: extracted directly from the inner 64x64 core of the 96x96 block.
- **Isolated (`out_*`)**: extracted from the isolated 32x32 block (Tile A) at `(0,0)`.

The correct Wang ID mapping for an edge-based Wang set should be:
`{t},0,{r},0,{b},0,{l},0`

### Autotile Sub-tile Mapping (Quarter-tiles)
RPG Maker XP autotiles are 96x128px (3 columns, 4 rows of 32x32px tiles). They can be divided into a 6x8 grid of 16x16px half-tiles.
To construct the 16 combinations for an edge-based matching set, we iterate from mask 0 to 15, taking bits:
- bit 0: Top edge (connects up)
- bit 1: Right edge (connects right)
- bit 2: Bottom edge (connects down)
- bit 3: Left edge (connects left)

The script already implements a `_build_tile` function that uses a 4-bit mask to assemble the 16 tiles by picking the correct 16x16px quarters. By fixing the `_wang_id` output, the generated TSX will correctly label these 16 tiles as edge Wang tiles.

## Decision: Adopt / Adapt / Build
**Adapt:** We will modify the existing `scripts/autotiles/rpgmaker_autotile_to_tiled.py` script to correct the `_wang_id` return value. By shifting the values to the edge indices, Tiled will correctly recognize the terrain edges and allow seamless auto-painting.
