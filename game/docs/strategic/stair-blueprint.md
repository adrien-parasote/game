# Blueprint: Stair Movement Mechanics

## Project Grade: Production

## Success Metrics
| Metric | Target | Timeline | How Measured |
|--------|--------|----------|-------------|
| Seamless Diagonal Movement | 0 extra inputs required | Launch | Player pressing purely "Right" successfully navigates a stair tile diagonally |
| Visual Footing Alignment | < 2px overlap with wall | Launch | Visual inspection of sprite feet vs step graphic during movement |

## Constraint Mapping
| Constraint | Impact | How We Handle It |
|-----------|--------|-----------------|
| Pygame Grid Movement | Characters move strictly from `(x, y)` to `(x±1, y±1)` | Intercept physical direction in `BaseEntity.start_move()` to convert horizontal input into diagonal target. |
| Mixed Graphic Tiles | Stair tiles contain both floor and wall components in the same 32x32 image | Apply a strict Y-offset solely in the rendering layer (`graphics/`) when standing on a stair tile (Option A). |

## Architecture Direction
| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Stair Metadata Storage | 1. Hardcoded coordinates<br>2. Tiled Object Layer<br>3. Tiled Tile Properties | **3. Tiled Tile Properties** | Extremely scalable. Mappers just place stairs, and `MapManager` reads the `direction` property automatically. |
| Visual Offset Implementation | 1. Offset `rect.center` (Option C)<br>2. Offset `image` blit (Option A) | **2. Offset `image` blit** | Option C (getting off the grid) requires "snapping" the player back to the grid at the end of the staircase, causing collision bugs or "jumps". By keeping the physics 100% aligned with the grid (physically moving in perfect diagonal `x+32, y-32`) and adding a purely visual offset (Option A), we maintain the engine's robustness while tricking the eye. |

## Exclusions & Boundaries
| Excluded | Why | Risk of Reversal |
|----------|-----|-----------------|
| Z-Axis Pathfinding | Too complex for a strictly 2D game. We just simulate Z via diagonal movement. | Introducing true Z-axis requires rewriting collision, depth sorting, and rendering pipelines. |
| Mid-stair Vertical Input | Pressing Up/Down while on a Left/Right stair breaks the sequence. | If allowed, the player will walk off the stairs into the void or walls. We must lock orthogonal input while traversing stairs. |

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| NPC Pathfinding Breaks | High | High | Ensure `BaseEntity.start_move()` interceptor applies to all entities (Player + NPCs). |
| Offset Snapping | Medium | Medium | If the Y-offset isn't lerped smoothly, the character might visually "jump" when entering/leaving stairs. |

## Gap Discovery
| # | Gap | Resolution | Owner |
|---|-----|---------------------|-------|
| 1 | Visual Y-offset value | To be calibrated experimentally during development (e.g., -8px or -12px) | Code |
| 2 | Stopping mid-staircase | Natural behavior preserved: the player ends on the current tile (step) and stops. | Code |
| 3 | Application to NPCs | Validated: the logic applies to the parent class `BaseEntity`. | Code |
