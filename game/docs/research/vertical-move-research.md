# Research: Vertical-Move Implementation Refactor (Stairs and Ladders)

> Document Type: Research
> Stage: 🔬 DISCOVER
> Target Feature: Vertical Movement (Stairs, Ladders, etc.)

## Research Results: Vertical-Move

### Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | How is vertical movement (stairs/ladders) modeled in tile-based games? | Understand standard conventions and coordinate mapping. | Industry blogs, developer forums |
| 2 | How does the existing codebase handle stair interception? | Identify failure points causing current zig-zagging issues. | Internal codebase audit |
| 3 | What are the constraints imposed by Tiled assets? | Understand tileset structure and properties from Tiled. | Tiled project XML configuration |

### Axis 1: Domain Context
| Finding | Source | Relevance | Confidence |
|---------|--------|-----------|------------|
| 2D top-down engines simulate elevation changes via visual Y-axis displacement while moving horizontally/diagonally. | Game Developer Community Standards | High | High (Industry standard) |
| Lateral stairs lock vertical movement inputs (Up/Down) to prevent pathbreaking and maintain character positioning. | Pokémon Gen 3/4 Engine Reference | High | High (Proven design) |

### Axis 2: Competitive Landscape
| Player/Solution | Positioning | Strengths | Gaps | Source |
|-----------------|-------------|-----------|------|--------|
| RPG Maker TSR_SideStairs | Plugin for lateral stair traversal. | Simple region tag setups. | Relies heavily on event engines instead of pure coordinate math. | [RPG Maker Forums](https://forums.rpgmakerweb.com/) |
| Pokémon Tile Interceptor | Hardcoded step-on/step-off tile logic. | Very robust alignment. | Closed-source, custom assembler logic. | [PokeCommunity](https://www.pokecommunity.com/) |

### Axis 3: Technical Feasibility

#### Source Evaluation
| Source | Type | Date | Credibility | Key Findings | Conflicts? |
|--------|------|------|-------------|-------------|------------|
| `game/src/entities/base.py` | Internal code | 2026-06-17 | High (Current implementation) | Current interception uses complex asymetric math for descent. Removing `stair_half` and treating all steps as diagonal simplifies traversal logic. | No |
| `assets/tiled/tiles/01-stairs.tsx` | Asset XML | 2026-06-17 | High (Direct asset configuration) | Tile class `01-vertical-move` exposes `stair_direction`, `walkable`, and `visual_y_offset`. | No |

#### Conflict Analysis
None. The code and assets are aligned, but the mathematical transition logic (especially step-off boundaries and descent symmetry) was flawed.

#### Gaps Identified
| Gap | Why It Matters | What Research Would Fill It |
|-----|---------------|---------------------------|
| Asymmetric step-off coordinates | Causes characters to drift vertically in coordinate space when moving up and down the stairs repeatedly. | Step-off grid checks in `start_move()`. |

### Cross-Axis Insights
1. **Grid vs. Rendering Separation:** The grid pathing must use true diagonal coordinates `(1, -1)` or `(1, 1)` because the stairs are laid out diagonally on the map, but the visual rendering offset (`visual_y_offset`) must smooth out the 32px logical jumps.
2. **Symmetry Requirements:** The exit condition of a staircase must be evaluated dynamically by checking if the next grid target is a stair tile *before* applying the diagonal vector.

### Recommendation
* **Chosen approach:** Adapt (build on top of the existing `BaseEntity` direction interception framework with a cleaner, symmetric step-off coordinate validation system).
* **Justification:** Adapting preserves the existing `MapManager` and `CameraGroup` integrations while fixing the underlying movement state machine.
* **Impact on spec:** Enhances the boundary step-off rules and defines a clear interpolation algorithm for `current_stair_offset`.

### Discovered Patterns
* **Diagonal Coordinate Interception:** Intercept inputs `(1,0)` and `(-1,0)` on stair tiles and map them to `(1, -1)` or `(-1, 1)` dynamically based on slope and direction.
