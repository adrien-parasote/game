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
| Visual Offset Implementation | 1. Offset `rect.center` (Option C)<br>2. Offset `image` blit (Option A) | **2. Offset `image` blit** | Option C (sortir du grid) oblige à "raccrocher" le joueur à la grille à la fin de l'escalier, causant des bugs de collision ou des "sauts". En gardant la physique 100% alignée sur la grille (en se déplaçant physiquement en diagonale parfaite `x+32, y-32`) et en ajoutant un offset purement visuel (Option A), on garde la robustesse du moteur tout en trompant l'œil. |

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
| 1 | Valeur de l'offset Y visuel | À calibrer expérimentalement lors du dev (ex: -8px ou -12px) | Code |
| 2 | Arrêt au milieu de l'escalier | Comportement naturel conservé : le joueur termine sur la tuile courante (marche) et s'arrête. | Code |
| 3 | Application aux NPCs | Validé : la logique s'applique à la classe mère `BaseEntity`. | Code |
