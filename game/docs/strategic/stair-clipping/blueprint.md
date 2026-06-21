# Blueprint: Stair Clipping

## Project Grade: Prototype

## Success Metrics
| Metric | Target | Timeline | How Measured |
|--------|--------|----------|-------------|
| Sprite bottom cropping | 100% of the player's legs are cropped up to the absolute value of `visual_y_offset` | Immediate on standing | Visual inspection + Unit tests verifying `current_stair_clip` value. |
| Smooth transition | Transition from unclipped to clipped state has zero visual jump | During movement | Unit tests verifying smooth interpolation of `current_stair_clip` based on movement progress. |
| Performance | FPS remains at target (e.g. 60 FPS) with 0 additional memory allocations per frame | Continuous | Pygame performance profiler showing 0 new Surface creations during movement on stairs. |

## Constraint Mapping
| Constraint | Impact | How We Handle It |
|-----------|--------|-----------------|
| Performance (Zero Allocation) | Cannot instantiate surfaces or generate dynamic subsurfaces in the drawing loop. | Perform clipping dynamically during blit in `CameraGroup.custom_draw` using Pygame-CE's `area` parameter with a pre-calculated tuple/rect. |
| Asset-Driven Properties | Map files and Tiled properties must be the sole source of truth for the clipping feature. | Read `clip` and `visual_y_offset` properties dynamically via `MapManager.get_vertical_move_props()`. |
| Separation of Concerns | Physical movement logic must not be contaminated by visual clipping concerns. | Keep logical/physical movement horizontal (no Y coordinate changes). |

## Architecture Direction
| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| State Storage and Update | A: In `BaseEntity` (reusing vertical movement interpolation code)<br>B: On the fly in `custom_draw()` (fetching map properties every frame)<br>C: At the `RenderManager` level | **A: In `BaseEntity`** | Reuses the existing robust interpolation architecture of `current_stair_offset` inside `update_stair_offset()`, ensuring perfect synchronization with movement progress and clean separation of concerns. |

## Exclusions & Boundaries
| Excluded | Why | Risk of Reversal |
|----------|-----|-----------------|
| Non-rectangular Masking | A simple rectangular crop from the bottom provides an excellent 2.5D visual illusion for 26.5° stairs and is much more performant. | Low |
| Physical Y-axis Changes | Physical movement on these stairs is kept purely horizontal to preserve simple grid collision physics and prevent diagonal mapping complexities. | Low |

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Interaction with grass wading | Low | Medium | If `current_stair_clip > 0`, grass wading (which draws grass over the bottom 8px of the sprite) is bypassed to prevent grass rendering in the air. |
| Layer collision property leakage | Low | High | Ensure decorative foreground layers (like banisters on layer `02-layer`) never contain movement-related properties, letting the parser correctly fall back to physical floor tiles. |

## Gap Discovery
| # | Gap | Impact if Unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | Fallback for missing `visual_y_offset` on clipped tiles | If `clip = true` is set but `visual_y_offset` is missing or empty, the engine wouldn't know how much to clip, causing no effect. Resolved: default to 8. | Agent |
| 2 | Value bounds for `visual_y_offset` | A value larger than the sprite height would crop the entire sprite, making the player invisible. Resolved: clamp to sprite height. | Agent |
| 3 | Interaction with grass wading | Grass rendering on clipped tiles could appear floating in the air. Resolved: skip grass wading when clipping is active. | Agent |
