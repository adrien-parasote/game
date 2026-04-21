# Strategic Blueprint - RPG Tile Engine [Strategic]

## 🎯 The 7 Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | What exact problem are you solving? | We are building a modular, scalable 2D tile-based RPG engine in Python. The core focus is overcoming performance bottlenecks (Culling), ensuring visual consistency (Y-sorting, Camera Clamping), and securing entity movement (World Boundaries). We are expanding from single maps to an interconnected world architecture via smooth transitions. |
| 2 | What are your success metrics? | Maintain 60 FPS with huge maps (200x200+) via dynamic Frustum Culling. Zero "void" visible at map edges. Entities physically restricted to the world rectangle. High test coverage (>= 90%). Map transitions must execute seamlessly without crashing the game loop. |
| 3 | Why will you win? | Architecture-first approach with a robust coordinate system, math-driven optimization (O(1) culling), and a decoupled data schema using a Tiled Project Resolver. |
| 4 | What's the core architecture decision? | Manager Pattern with strict separation of concerns (Game, Map, Entities). CameraGroup for single-pass sorted rendering. Grid-based atomic movement. Logical teleporters. |
| 5 | What's the tech stack rationale? | Python 3 for high productivity and readability. Pygame-CE for a stable, high-performance 2D backend. JSON for configuration and map exchange. |
| 6 | What are the MVP features? | Frustum Culling, Map Edge Clamping, Grid Movement, Time/Season System, robust Interactive Object system, and map interconnection (teleporters/doors). |
| 7 | What are you NOT building? | Final game assets, combat logic, inventory (logic placeholders only), or network multiplayer. No Isometric rendering (architecture ready but inactive). |

## 🚀 Roadmap

### Milestone: Engine Foundation [COMPLETE]
- Main loop, Input handling, JSON Settings.
- Rotating log directory (`logs/`).

### Milestone: World & Entities [COMPLETE]
- Orthogonal tile rendering with Frustum Culling.
- Player movement with World Boundaries.
- Camera following player with Map Edge Clamping.
- Time & Seasonal System: Day/night cycles and seasonal labels.

### Milestone: Interactions & Interconnected World [IN PROGRESS]
- Dynamic FPS display and high-coverage test suite.
- NPC System with basic AI and spatial interactions.
- Fixed Interactive Objects (chests, switches) with unified interaction and collision.
- Interaction Chaining and Omni-directional trigger support implemented.
- **[WIP]** Logical Teleportation and Map Transitions (world.world parsing).

## 🛠️ Core Architecture Decisions (ADRs)

| Feature | Decision | Rationale |
|---------|----------|-----------|
| **Core** | Manager Pattern | Strict separation of concerns (Game, Map, Entities). |
| **Rendering** | CameraGroup (Y-Sorted) | Single-pass sorted rendering with offset displacement. |
| **Optimization**| Frustum Culling | Avoid rendering off-screen tiles/sprites to support large worlds. |
| **Camera** | Visual Clamping | Restrict viewport to map pixels; center view if map < screen. |
| **Movement** | Grid-Based (Atomic) | Entities move tile-by-tile; cardinal directions only. |
| **Time** | World Clock | Real-to-game time mapping; seasonal cycles & dynamic lighting. |
| **Interactions**| ID-Based Chaining | The Game engine resolves `target_id` -> `element_id` connections to keep entities decoupled. |
| **World** | Connected Maps | Teleporter components offload scenes. Time continues silently during transitions. |

## 🔗 Implementation Specs
- [Engine Core](specs/ENGINE_CORE.md)
- [Interactive Objects](specs/INTERACTIVE_OBJECTS.md)
- [NPC System](specs/NPC_SYSTEM.md)
- [Quality Gates](specs/QUALITY_GATES.md)
