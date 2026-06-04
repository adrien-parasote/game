# Blueprint: Grass Rendering Improvements

## Project Grade: Production

## Success Metrics
| Metric | Target | Timeline | How Measured |
|--------|--------|----------|-------------|
| Visual fidelity | Match or exceed reference mask structure (Crescent/V-shapes) | V3.1 | Visual comparison of outputs vs references |
| Palette diversity | ≥ 8 distinct palettes from references (Crimson, Teal, Snow, etc.) | V3.1 | Count of palettes available in `constants.py` / YAML |
| Detail inclusion | Optional floral/detail layer integrated without breaking core generation | V3.1 | Toggle in GUI or parameter in CLI |
| Performance | Generation time remains < 50ms per tile despite larger matrices | V3.1 | Profiling `generate_texture()` |

## Constraint Mapping
| Constraint | Impact | How We Handle It |
|-----------|--------|-----------------|
| **Tile Resolution** | References use 48x48, our game engine uses 32x32 tiles. | We must design the new tuft matrices to look good and readable within a 32x32 grid, rather than blindly copying the 48x48 pixel counts. We will adapt the *shapes* (crescents/V's) but keep them small enough (e.g. 5x5 or 6x6) to tile well in 32x32. |
| **Existing Kitbash Engine** | We want to avoid rewriting the core Y-sorted kitbash engine. | We will only change the *data* (the matrices in `constants.py`) and add a small detail-pass step at the end of `generate_texture`. |

## Architecture Direction
| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| **Tuft Definitions** | 1. Hardcoded arrays in Python (current)<br>2. Load from PNG files | **1. Hardcoded arrays** | Keeps dependencies low, extremely fast to parse. The matrices are small enough (5x5) that Python 2D lists are manageable. |
| **Detail Pass (Flowers)** | 1. Built into tuft matrices<br>2. Procedurally scattered post-tufts | **2. Procedurally scattered** | Allows independent control over flower density, and prevents repetitive flower patterns inside identical tufts. |

## Exclusions & Boundaries
| Excluded | Why | Risk of Reversal |
|----------|-----|-----------------|
| **Dynamic 48x48 Export** | The game engine uses 32x32. Supporting arbitrary tile sizes would require a massive overhaul of the UI, minimap, and autotiling logic. | High risk of breaking the entire tool if we try to make base tile resolution dynamic just for one texture. |
| **Animated Grass** | The reference images are static. Adding animation (wind) requires sprite sheet generation, which is a completely different scope. | Infinite scope creep. Asset Creator is for static autotiles. |

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Density Clutter** | High | Medium | Larger tufts might turn the 32x32 tile into noise. We must carefully tune `DEFAULT_DENSITY` for the new matrices. |
| **Performance hit** | Low | Low | Larger tufts mean slightly more iteration, but numpy operations on 32x32 grids are extremely fast. |

## Gap Discovery
| # | Gap | Impact if Unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | **Scale Adaptation** | If we use 48x48 tuft sizes on 32x32 tiles, the grass will look massive and break the scale of the game's characters. What exact dimensions (e.g., 5x5 vs 8x8) should the new matrices be to look right at 32x32? | Adopter/User |
| 2 | **Detail Integration UI** | If we add a "flowers/details" pass, how is it exposed in the UI? Does it reuse the existing `DetailConfig` or do we need new sliders specifically for "Floral Density"? | Adopter/User |
| 3 | **Palette Structure** | Our current `DEFAULT_PALETTES` uses 4 tuples (Shadow, Base, Highlight, Accent). The new references have very specific lighting. Are 4 colors enough, or do we need 5 (Deep Shadow, Shadow, Base, Highlight, Tip Highlight)? | Adopter/User |
