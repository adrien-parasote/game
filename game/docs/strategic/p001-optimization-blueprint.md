# Blueprint: P-001 Rendering Bottleneck Optimization

## Project Grade: Prototype / Internal Utility

## Success Metrics
| Metric | Target | Timeline | How Measured |
|--------|--------|----------|-------------|
| Iteration reduction | -95% iteration count for `_build_screen_occluding_rects` and `_blit_occluded_tiles_near_player` | Immediate | Profiler (`profile_game.py`) |
| Frame-rate improvement | ~2-3 ms saved per frame (measured on average frame time) | Immediate | Profiler average frame time report |
| Test compliance | 100% of existing tests pass | Immediate | `pytest` runner |

## Constraint Mapping
| Constraint | Impact | How We Handle It |
|-----------|--------|-----------------|
| Test Compatibility | Existing tests call private methods directly. | Fall back to full `_fg_occlusion_world` iteration if `self._frame_visible_fg_tiles` is not set. |
| Zero Visual Regression | Player occlusion and collision rects must function identically. | Keep identical viewport and depth checks in the list comprehension. |
| Memory Footprint | Avoid allocation spike during optimization. | Cache contains references to existing tuples in a list of size <50 (no new data allocated per frame). |

## Architecture Direction
| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Viewport pre-filter cache | (A) Run culling loop twice (original)<br>(B) Combine functions<br>(C) Frame-level pre-filtered cache | **(C) Frame-level pre-filtered cache** | Retains test compatibility for direct method calls while yielding single-pass performance in main loop. |

## Exclusions & Boundaries
| Excluded | Why | Risk of Reversal |
|----------|-----|-----------------|
| Animated Foreground Tiles | Out of scope for static rendering optimization. | Low. Animated tiles handle their own culling. |
| Global render pipeline restructuring | Unnecessary risk of regressions in background/entity layers. | Low. Keep refactoring strictly localized. |

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Unit tests mock private methods | High | Medium | Implement the fallback mechanism in both private methods. |

## Gap Discovery
| # | Gap | Impact if Unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | Does the list comprehension allocate new tuple objects? | No, it copies reference pointers. Checked via Python interpreter behavior. | Agent |
| 2 | Do tests assert viewport bound borders? | Yes, tests verify cull logic. Viewport checks in comprehension must be mathematically identical. | Agent |
| 3 | Is `walk_active` true inside tests? | Tests check walk_active behavior. We must preserve `not walk_active` guard. | Agent |
