# Master Specification Index [Strategic]


> **Document Type:** Strategic

This document serves as the Master Index and Architectural Registry for the 25 consolidated technical specifications of the RPG Tile Engine. It lists all active specification maps, global singletons, shared constant definitions, and general architectural standards.

---

## 1. Active Specification Index

### 1.1 Core Engine Systems
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Engine Core** | [engine-core.md](./engine-core.md#L1) | `Game` core loop, `GameStateManager`, `InputHandler` |
| **Save System** | [save-system.md](./save-system.md#L1) | `SaveManager` serialization, screenshot thumbnail pipelines |
| **Audio System** | [audio-system.md](./audio-system.md#L1) | `AudioManager` channels, spatial volume calculations, ambient fades |
| **Asset & I18n** | [asset-i18n.md](./asset-i18n.md#L1) | `AssetManager` loaders, `I18nManager` JSON dictionaries |

### 1.2 Map, World & Navigation
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Map & World** | [map-world-system.md](./map-world-system.md#L1) | `TmjParser`, `MapManager` chunks, coordinate conversions, teleport triggers |
| **Intra-Map Teleport** | [intra-map-teleport.md](./intra-map-teleport.md#L1) | `game.intra_map_teleport()`, `MapLoader.resolve_spawn_by_id()`, walk transition |
| **NPC System** | [npc-system.md](./npc-system.md#L1) | `NPC` base, navigation pathways, patrol patterns, collision avoidance |

### 1.3 Entities & Lighting
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Entities System** | [entities-system.md](./entities-system.md#L1) | `BaseEntity`, `PickupItem` drops, emote bubble loops, bridge gates |
| **Lighting System** | [lighting-system.md](./lighting-system.md#L1) | Subtractive dark overlays, window beam projection, flicker mixins |

### 1.4 User Interface (UI)
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Inventory System** | [inventory-system.md](./inventory-system.md#L1) | `Inventory` data, slot drag-and-drop, character equipment sheets |
| **Chest UI** | [chest-ui.md](./chest-ui.md#L1) | `ChestUI` layout cards, transaction mixers, scroll panels |
| **Dialogue System** | [dialogue-system.md](./dialogue-system.md#L1) | `DialogueManager` typewriters, pagination, overhead speech bubbles |

### 1.5 Quality, Optimization & Diagnostics
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Camera & Rendering** | [camera-rendering.md](./camera-rendering.md#L1) | Camera viewport coordinates tracking, `RenderManager` batching, grass wading pass |
| **Performance System** | [performance-system.md](./performance-system.md#L1) | Y-sorting dirty cache flags, inlined tuples, distance-squared math |
| **Development & Quality** | [development-quality.md](./development-quality.md#L1) | Automated quality gates, test layouts, release scripts, debug room |
| **Best Practices** | [pygame_ce_python_312_best_practices.md](./pygame_ce_python_312_best_practices.md#L1) | Modern Python 3.12 and Pygame-CE best practices and optimizations |
---

### 1.6 Historical Remediation & Hardening
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Code Quality Pass** | [code-quality-constants-i18n.md](./code-quality-constants-i18n.md#L1) | French→EN translation, magic color constants, pre-existing constant usage bugs |
| **DT Clamp & Text Cache** | [remediation_01_dt_text_cache.md](./remediation_01_dt_text_cache.md#L1) | DT Clamping and pre-rendered text cache (HUD, Inventory, Chest) |
| **Saves & Pyright** | [remediation_02_saves_assets_pyright.md](./remediation_02_saves_assets_pyright.md#L1) | Pyright type checking and `pygame.system.get_pref_path` save paths |
| **Modernization** | [remediation_03_modernization.md](./remediation_03_modernization.md#L1) | `pathlib.Path` migration and standardizations |

---

### 1.7 Navigation Extensions
| Spec | File | Modules Covered |
|------|------|-----------------|  
| **Stair Movement** | [stair-movement.md](./stair-movement.md#L1) | `BaseEntity._apply_stair_interception`, `MapManager.get_vertical_move_props`, diagonal stair climbing |

---

### 1.8 Rendering Optimization
| Spec | File | Modules Covered |
|------|------|-----------------|  
| **Foreground Rendering P-001** | [p001-foreground-rendering.md](./p001-foreground-rendering.md#L1) | `RenderManager` WorldSurface blit, spatial culling, foreground pre-render cache |
| **Render Pipeline Optimization** | [render-pipeline-optimization.md](./render-pipeline-optimization.md#L1) | Spatial index, rect pooling, animated tile layer map |
| **Pixel-Perfect Occlusion** | [pixel-perfect-occlusion.md](./pixel-perfect-occlusion.md#L1) | `OcclusionRenderer` composite-based partial occlusion |

---

## 2. Global Subsystem Registry

| Singleton / Global | Instantiation | Access Pattern |
|--------------------|---------------|----------------|
| `Game` | `GameStateManager.run()` | Passed as context parameter `game: Any` |
| `AssetManager` | `__new__` singleton | Class invocation `AssetManager()` |
| `I18nManager` | `__new__` singleton | Class invocation `I18nManager()` |
| `InteractionManager` | `Game.__init__()` | Engine context mapping `game.interaction_manager` |
| `AudioManager` | `Game.__init__()` | Engine context mapping `game.audio` |
| `DialogueManager` | `Game.__init__()` | Engine context mapping `game.dialogue` |
| `MapManager` | Managed per map load | Engine context mapping `game.map_manager` |
| `Settings` | Module-level class constants | `from src.config import Settings` |

---

## 3. Shared Architectural Constants

| Constant | Source | Value | Applied Subsystems |
|----------|--------|-------|--------------------|
| `TILE_SIZE` | `config.py` | `32` | Chunks, boundaries, entity collisions |
| `WINDOW_WIDTH` | `config.py` | `1280` | Viewport dimensions, UI overlays |
| `WINDOW_HEIGHT` | `config.py` | `720` | Viewport dimensions, UI overlays |
| `DT_MAX` | `config.py` | `0.1` | Physics framerate delta clamping (caps dt for physics/rendering) |
| `MAX_DT_CLAMP` | `time_system.py` | `10.0` | In-game time acceleration clamping (NOT physics — limits simulated time skip per frame) |
| `PAGE_COMPLETE` | `ui/dialogue.py` | `1` | Dialogue pagination status |
| `SHADOW_COLOR` | `config.py` | `(0, 0, 0)` | Text shadow color |
| `SHADOW_OFFSET` | `config.py` | `1` | Text shadow offset (scalar `int`, applied to both X and Y) |
| `STATIC_LABELS` | `config.py` | `{}` | Pre-rendered static UI text labels |
| `TEXT_COLOR` | `config.py` | `(255, 255, 255)` | Default UI text color |

---

## 4. General Development Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load assets directly in game updates | Queue assets at boot using `AssetManager` | Mid-game disk I/O causes severe stuttering |
| Capture generic `except:` without logs | Specify exception types and log warnings | Silencing exceptions creates invisible, untraceable bugs |
| Concatenate filesystem path chunks | Standardize routing with `pathlib.Path` | Platform-specific slash directions break portability (codebase migrated to pathlib — see [remediation_03](./remediation_03_modernization.md#L1)) |
| Bypass the TDD fail-first gate | Create a RED test before the logic fix | Bypassing TDD increases regression rates on release |

---

## 5. Architectural Decision Records (ADRs)

| ADR | Summary | Rationale |
|-----|---------|-----------|
| [ADR-001](../ADRs/ADR-001-gamestate-architecture.md#L1) | External State Management | Deconstructs `game.py` loops into an independent state controller |
| [ADR-002](../ADRs/ADR-002-save-format.md#L1) | Persistent JSON Schema | Standardizes a 3-slot JSON save structure containing thumbnails |
| [ADR-003](../ADRs/ADR-003-key-mapping.md#L1) | Escape UI Interceptor | Map ESC key triggers to the Pause overlay instead of exit |
| [ADR-004](../ADRs/ADR-004-refactoring-context-injection.md#L1) | Loose coupling context injection | Uses duck-typed `game` parameters to eliminate circular module imports |
| [ADR-005](../ADRs/ADR-005-singleton-new.md#L1) | Singleton loaders | Applies `__new__` singleton patterns to core asset & language managers |
| [ADR-006](../ADRs/ADR-006-perf-constants-pre-render-cache.md#L1) | Composite graphics caching | Pre-renders button and font assets to eliminate drawing allocations |
| [ADR-007](../ADRs/ADR-007-partial-occlusion-surface-composite.md#L1) | Partial Occlusion Surface Composite | Documents the composite-based approach to partial sprite occlusion behind foreground tiles |
| [ADR-008](../ADRs/ADR-008-frect-migration.md#L1) | pygame.FRect migration decision | Non-migration decision deferred to avoid regression risk on collision math |
| [ADR-009](../ADRs/ADR-009-side-by-side-wiki-workspace.md#L1) | Wiki/Repo Documentation Split | Separates game-wiki (gameplay) from game/docs (technical specs) |
| [ADR-010](../ADRs/ADR-010-urbanisation-makefiles.md#L1) | Urbanization & Makefiles | Standardizes Makefile dev tooling and project environment layout |
| [ADR-011](../ADRs/ADR-011-spatial-index-and-rect-pooling.md#L1) | Spatial Index + Rect Pooling | Pre-allocated rect pool and spatial grid for render performance |
| [ADR-012](../ADRs/ADR-012-grass-material-grid.md#L1) | Grass Material Grid | Pre-computed 2D grass grid for O(1) wading lookups |
| [ADR-013](../ADRs/ADR-013-stair-climbing-alignment.md#L1) | Stair Climbing Alignment | Descent direction asymmetry fix — `not stair_half` for downward movement |

---

## 6. Project Structure Reference

For a complete, up-to-date project structure reference, see the architecture codemaps:
- [Architecture Overview](../codemaps/architecture.md) — modules, classes, key methods
- [Logic Flow](../codemaps/logic.md) — event flow, state transitions
- [Data Flow](../codemaps/data.md) — data models, persistence schema

