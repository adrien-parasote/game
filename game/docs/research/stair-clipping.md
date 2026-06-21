# Research Results: Dynamic Stair Clipping

## Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | Where in the rendering pipeline should sprite clipping be applied? | To intercept the draw call without modifying original assets or breaking depth-sorting. | Codebase inspection (`src/entities/groups.py`, `src/engine/render_manager.py`) |
| 2 | What is the most performant method to clip a sprite in Pygame-CE? | Pygame-CE loops run on the CPU. Allocations inside the draw loop cause garbage collection spikes. | Pygame-CE official documentation, community best practices |
| 3 | How should the clipping amount be tracked and interpolated? | Movement is smooth/interpolated. Clipping must match this interpolation to look natural. | Codebase inspection (`src/entities/base.py`, `vertical-move.md`) |

## Axis 1: Domain Context
| Finding | Source | Relevance | Confidence |
|---------|--------|-----------|------------|
| 2.5D visual elevation is simulated using Y-axis shift. Descending behind foreground walls/steps requires partial occlusion/clipping. | [GameDev StackExchange: Top-down 2D Elevation](https://gamedev.stackexchange.com) | High | High (Industry Standard) |
| Bottom-clipping of player sprites is a standard technique to simulate walking down behind an incline/steps. | [RPG Maker Web Forums: Side Stair Occlusion](https://forums.rpgmakerweb.com) | High | High (Industry Standard) |

## Axis 2: Competitive Landscape
| Player/Solution | Positioning | Strengths | Gaps | Source |
|-----------------|-------------|-----------|------|--------|
| RPG Maker TSR_SideStairs | Dynamic stair movement with visual shift | Automatically shifts and masks player sprite based on region tags | Masking is handled via engine-specific sprite cropping | [RPG Maker Web Forums](https://forums.rpgmakerweb.com) |
| Unity 2D Sprite Mask | Component-based masking/clipping | Handles arbitrary shapes via stencil buffer / shaders | Heavy overhead for simple rectangular grid clipping | [Unity Documentation](https://docs.unity3d.com) |
| GameMaker `draw_sprite_part` | Dynamic partial sprite drawing | Extremely fast, built-in function to draw a section of a sprite | Simple rectangle only (matches our needs perfectly) | [GameMaker Manual](https://manual.gamemaker.io) |

## Axis 3: Technical Feasibility

### Source Evaluation
| Source | Type | Date | Credibility | Key Findings | Conflicts? |
|--------|------|------|-------------|-------------|------------|
| Pygame-CE `Surface.blit` Reference | Official | 2026 | High (Core API) | `area` parameter allows drawing a sub-rectangle of the source surface without copy or allocation | No |
| Pygame-CE `Surface.subsurface` Reference | Official | 2026 | High (Core API) | `subsurface` shares pixel data but creates a new Surface object wrapper, causing GC churn if allocated per-frame | No |
| Pygame-CE Best Practices (`pygame_ce_python_312_best_practices.md`) | Project Reference | 2026 | High (Project Standard) | Banned pattern: Instantiating objects (`Vector2`, `Rect`, `Surface`) in the main loop | No |

### Conflict Analysis
| Sources | Claim A | Claim B | Reason for Discrepancy | Resolution |
|---------|---------|---------|----------------------|------------|
| `Surface.subsurface` vs `Surface.blit(..., area)` | `subsurface` is clean and returns a shared-pixel Surface. | `blit` with `area` avoids python-side Surface allocation. | `subsurface` is good for static crops, but dynamic crops per frame create object churn. | Adopt `Surface.blit` with `area` using a pre-allocated/reused `pygame.Rect` or tuple. |

### Gaps Identified
| Gap | Why It Matters | What Research Would Fill It |
|-----|---------------|---------------------------|
| Interaction of clipping with Pixel-Perfect Occlusion | If both clipping and pixel-perfect occlusion happen, we must ensure they don't corrupt the composite buffer. | Check if player drawing in `groups.py` is bypassed during occlusion composite. Yes, `groups.py` draws normal sprites. |

## Cross-Axis Insights
1. **GameMaker parity with Pygame-CE `area` blits:** GameMaker's highly-optimized `draw_sprite_part` maps 1-to-1 to Pygame-CE's `Surface.blit(..., area=...)`. This proves that rectangular cropping is the standard high-performance path for 2D engines.
2. **Object allocation limits:** The project's strict anti-pattern ban on per-frame allocations means we cannot use approach B (`subsurface` on the fly) or approach A (creating composite surfaces per frame). A direct `blit` with a coordinate tuple or reused Rect for the `area` parameter is the only compliant way.

## Recommendation
- **Chosen approach:** **Adapt** the interpolation system from `visual_y_offset` to drive `current_stair_clip` on the entity, and **Build** the rendering intercept in `CameraGroup.custom_draw()` using Pygame-CE's `Surface.blit` with the `area` parameter.
- **Justification:** Reuses the existing robust interpolation code in `BaseEntity.update_stair_offset()` while keeping the rendering logic O(1) in memory allocation by leveraging Pygame-CE's built-in `area` blitting.
- **Impact on spec:** Modifies `vertical-move.md` to re-introduce `clip` and `current_stair_clip` fields, detailing how they are initialized, interpolated, and rendered.

## Discovered Patterns
- Pygame-CE `area` blitting pattern: `surface.blit(src_surf, dest_pos, area=pygame.Rect(0, 0, w, h - clip))` [source: Pygame-CE Docs#Surface.blit]
- Entity interpolation mirroring: mirroring the offset logic to coordinate-linked attributes [source: `vertical-move.md` §5.1]
