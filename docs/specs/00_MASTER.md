
# Master Specification Index [Strategic]

> Document Type: Strategic

This document is the master index for all technical specifications in the RPG engine project. It provides cross-references, a global registry, shared constants, and anti-patterns that apply across all modules.

## 1. Specification Index

### Engine Core
| Spec | File | Modules Covered |
|------|------|-----------------|
| Engine Core | [engine-core.md](./engine-core.md#L1) | `Game`, `GameStateManager`, `InputHandler` |
| Game Flow | [game-flow-spec.md](./game-flow-spec.md#L1) | State transitions, game loop |
| Save System | [save-system.md](./save-system.md#L1) | `SaveManager`, persistence |
| Audio System | [audio-system-spec.md](./audio-system-spec.md#L1) | `AudioManager` (BGM, SFX, ambient) |
| Asset & I18n | [asset-i18n-spec.md](./asset-i18n-spec.md#L1) | `AssetManager`, `I18nManager` |

### Map & World
| Spec | File | Modules Covered |
|------|------|-----------------|
| Map Parser | [map-parser-spec.md](./map-parser-spec.md#L1) | `TmjParser`, `TiledProject`, `MapManager`, `OrthogonalLayout` |
| World System | [world-system.md](./world-system.md#L1) | WorldManager, map transitions |
| Directional Autotiles | [phase-1.6-directional-autotiles.md](./phase-1.6-directional-autotiles.md#L1) | Walkability directionnelle, animated autotile pipeline |

### Entities
| Spec | File | Modules Covered |
|------|------|-----------------|
| Interactive Objects | [interactive-objects.md](./interactive-objects.md#L1) | `InteractiveEntity`, `BaseEntity` |
| Interactive Lighting | [interactive-lighting-spec.md](./interactive-lighting-spec.md#L1) | `InteractiveLightingMixin`, `InteractiveParticleMixin` |
| NPC System | [npc-system.md](./npc-system.md#L1) | `NPC`, patrol, dialogue triggers |
| Emotes | [emote-spec.md](./emote-spec.md#L1) | EmoteSystem |
| Item Pickup | [item_pickup_spec.md](./item_pickup_spec.md#L1) | `PickupItem`, ground drops |

### UI
| Spec | File | Modules Covered |
|------|------|-----------------|
| Inventory UI | [inventory-spec.md](./inventory-spec.md#L1) | `InventoryUI`, grid, equipment panel |
| Inventory Data | [inventory-data-spec.md](./inventory-data-spec.md#L1) | `Inventory`, `Item`, stacking |
| Chest UI | [chest-ui-spec.md](./chest-ui-spec.md#L1) | `ChestUI`, transfer mixins |
| Dialogue | [dialogue-spec.md](./dialogue-spec.md#L1) | `DialogueManager`, typewriter |
| Speech Bubbles | [speech-bubble-spec.md](./speech-bubble-spec.md#L1) | `SpeechBubble`, NPC overhead text |
| Loot Table | [loot-table-spec.md](./loot-table-spec.md#L1) | `LootTable`, chest initialization |
| Localization & Fonts | [localization_font_urbanization.md](./localization_font_urbanization.md#L1) | Font pipeline, i18n |

### Systems
| Spec | File | Modules Covered |
|------|------|-----------------|
| Lighting System | [lighting-system.md](./lighting-system.md#L1) | `LightingManager`, day/night, window beams |
| Camera & Rendering | [camera-rendering-spec.md](./camera-rendering-spec.md#L1) | Camera, `RenderManager` |
| Debug Features | [debug-features-spec.md](./debug-features-spec.md#L1) | Debug overlay, console |

### Performance & Quality
| Spec | File | Modules Covered |
|------|------|-----------------|
| Performance Optimization | [performance-optimization-spec.md](./performance-optimization-spec.md#L1) | Frame budget, profiling |
| Performance Constants | [perf-constants-spec.md](./perf-constants-spec.md#L1) | Tuned thresholds |
| Quality Gates | [quality-gates.md](./quality-gates.md#L1) | CI/test coverage |
| Test Suite Optimization | [test_suite_optimization.md](./test_suite_optimization.md#L1) | Test infrastructure |

### Refactoring Phases
| Spec | File | Modules Covered |
|------|------|-----------------|
| Phase 1.5 — Game Refactoring | [phase-1.5-game-refactoring.md](./phase-1.5-game-refactoring.md#L1) | Core extraction |
| Phase 1.5 — Interaction Refactoring | [phase-1.5-interaction-refactoring.md](./phase-1.5-interaction-refactoring.md#L1) | Interaction overhaul |
| Phase 1.5 — Chest Refactoring | [phase-1.5-chest-refactoring.md](./phase-1.5-chest-refactoring.md#L1) | Chest mixin extraction |
| Phase 1.6 — Plan exécution | [phase-1.6-plan.md](./phase-1.6-plan.md#L1) | Plan implémentation (détaille [phase-1.6-directional-autotiles.md](./phase-1.6-directional-autotiles.md#L1)) |

## 2. Global Registry

| Singleton / Global | Instantiation | Access Pattern |
|--------------------|---------------|----------------|
| `Game` | `GameStateManager.run()` | Passed as `self` to subsystems |
| `AssetManager` | `__new__` singleton | `AssetManager()` anywhere |
| `I18nManager` | `__new__` singleton | `I18nManager()` anywhere |
| `InteractionManager` | `Game.__init__()` | `game.interaction_manager` |
| `AudioManager` | `Game.__init__()` | `game.audio` |
| `DialogueManager` | `Game.__init__()` | `game.dialogue` |
| `MapManager` | Per map load | `game.map_manager` |
| `Settings` | Module-level constants | `from src.config import Settings` |

## 3. Shared Constants

| Constant | Source | Value | Used By |
|----------|--------|-------|---------|
| `TILE_SIZE` | `config.py` | `32` | Map, entities, collision |
| `WINDOW_WIDTH` | `config.py` | `1280` | All UI, camera |
| `WINDOW_HEIGHT` | `config.py` | `720` | All UI, camera |
| `BGM_VOLUME` | `config.py` | `0.5` | AudioManager |
| `SFX_VOLUME` | `config.py` | `0.7` | AudioManager |
| `TEXT_SPEED` | `config.py` | `0.05` | DialogueManager |

## 4. Anti-Patterns (DO NOT — Global)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Use `__import__()` to break circular deps | Constructor injection or lazy attribute | Fragile, hides dependencies |
| Bare `except Exception` without logging | Catch specific exceptions, log with context | Silent failures mask bugs |
| Hardcode constants in multiple files | Import from single source (config, constants module) | Configuration drift |
| Access game subsystems via `game.` without type hints | Use `TYPE_CHECKING` + type annotations | IDE support, documentation |
| Create pygame Surfaces in the game loop | Pre-cache at init time, use `set_alpha()` over `.copy()` | Frame budget (16ms @ 60fps) |
| Use `os.path.join()` with hardcoded segments | Define paths as constants in config | Path duplication across modules |

## 5. Architecture Decision Records

| ADR | Décision | Rationale |
|-----|----------|-----------|
| [ADR-001](../ADRs/ADR-001-gamestate-architecture.md) | `GameStateManager` externe orchestre `Game` | `game.py` à 854L — séparation état/logique sans regression sur les tests existants |
| [ADR-002](../ADRs/ADR-002-save-format.md) | Format JSON versioned pour les sauvegardes | 3 slots, `version: "0.4.0"`, thumbnails PNG |
| [ADR-003](../ADRs/ADR-003-key-mapping.md) | Bucket pre-cached pour les light masks (10 échelles) | Évite `rotozoom()` par frame dans le lighting des entités |
| [ADR-004](../ADRs/ADR-004-refactoring-context-injection.md) | Duck-typing `game: Any` pour l'injection de contexte | Couplage faible entre sous-systèmes, évite les imports circulaires |
| [ADR-005](../ADRs/ADR-005-singleton-new.md) | `__new__` singleton pour AssetManager/I18nManager | Accès zero-config depuis tout module sans import circulaire |
| [ADR-006](../ADRs/ADR-006-perf-constants-pre-render-cache.md) | Pre-render cache pour les surfaces UI statiques | Zéro allocation `Surface` dans les hot paths de draw |

> **Note :** ADR-005 a été créé le 2026-05-15. Si le lien est rouge, le fichier ADR est en cours de création.
