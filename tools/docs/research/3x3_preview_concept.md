# Concept: 3x3 Seamless Preview (Target Resolution)

## The Goal
The user wants to visualize the seamlessness of the procedurally generated tiles. While the current 256x256 scaled-up single tile ("gros plan") is useful for seeing pixel details, a 3x3 tiled grid at the *target resolution* (1x scale, so 96x96 pixels total) is necessary to immediately verify if the edges loop perfectly without visual seams.

## Proposed Approach (DISCOVER)

1. **Keep the current "gros plan"**: The 256x256 scaled single-tile preview remains as the primary inspection tool.
2. **Add a secondary preview**: A 3x3 grid of the 32x32 tile.
3. **Pillow Tiling**: 
   - Create a new blank `PIL.Image` of size `(96, 96)` (since `32 * 3 = 96`).
   - Paste the generated 32x32 image into the 9 grid positions `(x*32, y*32)` where `x` and `y` range from 0 to 2.
4. **UI Integration**:
   - `CustomTkinter` (`CTkImage`) can display this 96x96 image.
   - We can add a second `CTkLabel` within the `preview_frame` or next to it to display this 3x3 grid.
   - Since 96x96 is relatively small, it fits perfectly underneath or alongside the main 256x256 preview without requiring a window resize.

## Trade-offs & Considerations
- **UI Space**: The window is currently 600x500. The right frame has a 300x300 space. The 256x256 image fits. Adding a 96x96 image below it might require a slight increase in window height (e.g., 600x600) or placing it cleverly (e.g., in the control frame if space permits, or under the main preview).
- **Performance**: Creating a 96x96 image and pasting a 32x32 image 9 times in Pillow takes less than 1ms. Negligible performance impact.

## Next Steps
This concept is ready. We can transition to the STRATEGY stage to define exactly where this goes in the UI layout (e.g., modifying the blueprint) and then SPEC/BUILD.
