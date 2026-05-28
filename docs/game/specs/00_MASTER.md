# Master Specification Index [Strategic]

> **Document Type:** Strategic

This document serves as the Master Index and Architectural Registry for the 15 consolidated technical specifications of the RPG Tile Engine. It lists all active specification maps, global singletons, shared constant definitions, and general architectural standards.

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
### 1.6 Historical Remediation & Hardening
| Spec | File | Modules Covered |
|------|------|-----------------|
| **Code Quality Pass** | [code-quality-constants-i18n.md](./code-quality-constants-i18n.md#L1) | French→EN translation, magic color constants, pre-existing constant usage bugs |
| **DT Clamp & Text Cache** | [remediation_01_dt_text_cache.md](./remediation_01_dt_text_cache.md#L1) | DT Clamping and pre-rendered text cache (HUD, Inventory, Chest) |
| **Saves & Pyright** | [remediation_02_saves_assets_pyright.md](./remediation_02_saves_assets_pyright.md#L1) | Pyright type checking and `pygame.system.get_pref_path` save paths |
| **Modernization** | [remediation_03_modernization.md](./remediation_03_modernization.md#L1) | `pathlib.Path` migration and standardizations |

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
| `MAX_DT_CLAMP` | `config.py` | `10.0` | Physics framerate delta clamping |
| `PAGE_COMPLETE` | `ui/dialogue.py` | `1` | Dialogue pagination status |
| `SHADOW_COLOR` | `config.py` | `(0, 0, 0)` | Text shadow color |
| `SHADOW_OFFSET` | `config.py` | `(1, 1)` | Text shadow offset |
| `STATIC_LABELS` | `config.py` | `{}` | Pre-rendered static UI text labels |
| `TEXT_COLOR` | `config.py` | `(255, 255, 255)` | Default UI text color |

---

## 4. General Development Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load assets directly in game updates | Queue assets at boot using `AssetManager` | Mid-game disk I/O causes severe stuttering |
| Capture generic `except:` without logs | Specify exception types and log warnings | Silencing exceptions creates invisible, untraceable bugs |
| Concatenate filesystem path chunks | Standardize routing with `os.path.join` | Platform-specific slash directions break portability |
| Bypass the TDD fail-first gate | Create a RED test before the logic fix | Bypassing TDD increases regression rates on release |

---

## 5. Architectural Decision Records (ADRs)

| ADR | Summary | Rationale |
|-----|---------|-----------|
| [ADR-001](../ADRs/ADR-001-gamestate-architecture.md) | External State Management | Deconstructs `game.py` loops into an independent state controller |
| [ADR-002](../ADRs/ADR-002-save-format.md) | Persistent JSON Schema | Standardizes a 3-slot JSON save structure containing thumbnails |
| [ADR-003](../ADRs/ADR-003-key-mapping.md) | Escape UI Interceptor | Map ESC key triggers to the Pause overlay instead of exit |
| [ADR-004](../ADRs/ADR-004-refactoring-context-injection.md) | Loose coupling context injection | Uses duck-typed `game` parameters to eliminate circular module imports |
| [ADR-005](../ADRs/ADR-005-singleton-new.md) | Singleton loaders | Applies `__new__` singleton patterns to core asset & language managers |
| [ADR-006](../ADRs/ADR-006-perf-constants-pre-render-cache.md) | Composite graphics caching | Pre-renders button and font assets to eliminate drawing allocations |
| [ADR-007](../ADRs/ADR-007-partial-occlusion-surface-composite.md) | Partial Occlusion Surface Composite | Documents the composite-based approach to partial sprite occlusion behind foreground tiles |
| [ADR-008](../ADRs/ADR-008-frect-migration.md) | pygame.FRect migration decision | Non-migration decision deferred to avoid regression risk on collision math |

---

## 6. Project Deliverables Tree

```text
    assets/
        data/
            loot_table.json
            propertytypes.json
        fonts/
            cormorant-garamond-regular.ttf
        images/
            characters/
            HUD/
                07-chest.png
            menu/
                01-menu_back_cursor.png
                03-save_slot.png
            sprites/
                04-emotes.png
            ui/
                03-inventory_slot.png
        tiled/
            game.tiled-project
    characters/
    data/
        loot_table.json
    saves/
        slot_1_thumb.png
        slot_X
    sprites/
    src/
        engine/
            asset_manager.py
            collision_checker.py
            lighting.py
            map_loader.py
        entities/
            emote_sprite.py
            interaction.py
            teleport.py
        graphics/
            spritesheet.py
        ui/
            chest.py
            chest_layout.py
            chest_transfer.py
            inventory_system.py
        config.py
    settings.json
    pyproject.toml
    docs/
        README.md
        game/
            specs/
                00_MASTER.md
                engine-core.md
                entities-system.md
                map-world-system.md
                camera-rendering.md
                pygame_ce_python_312_best_practices.md
                ...
            strategic/
                MASTER_ROADMAP.md
                game_vision.md
                best_practices_remediation_blueprint.md
                ...
            research/
            ADRs/
                ADR-001 .. ADR-008
        tooling/
            specs/
                autotile-pipeline-spec.md
                blob_autotile_pipeline_spec.md
                diagonal_wall_spec.md
            strategic/
                autotile-pipeline-strategy.md
                diagonal_wall_blueprint.md
            research/
                autotile_to_tiled.md
                diagonal_wall_transformation.md
        codemaps/
            architecture.md
            logic.md
            data.md
    tests/
        engine/
            test_game.py
            test_game_state_manager.py
            test_collision_checker.py
            test_spatial_utils.py
            test_phase15_game.py
            test_interaction.py
            test_loot_table.py
            test_lighting.py
            test_map_loader.py
            test_performance_optimizations.py
            test_save_manager.py
            test_bridge_sfx_interaction.py
        entities/
            test_interactive.py
            test_sprite_frame_loading.py
            test_entities.py
            test_npc.py
            test_bridge_sfx.py
            test_bridge_sfx_player.py
        ui/
            test_dialogue.py
            test_speech_bubble.py
            test_inventory.py
            test_title_screen.py
            test_save_menu.py
            test_pause_screen.py
        scripts/
            build/
                test_release.py
        test_chest_ui.py
        test_transfer_logic.py
        test_interaction.py
.agents/
    learnings/
        game_engine.md
        ui.md
engine-core.md
asset_manager.py
chest.py
chest_layout.py
chest_transfer.py
propertytypes.json
loot_table.json
best_practices_remediation_blueprint.md
pygame_ce_python_312_best_practices.md
camera-rendering.md
entities-system.md
collision_checker.py
test_dialogue.py
ADR-006-perf-constants-pre-render-cache.md
interaction.py
map_loader.py
map-world-system.md
inventory_system.py
spritesheet.py
emote_sprite.py
teleport.py
gameplay.json
game_engine.md
title_screen_draw.py
_constants.py
save_menu_constants.py
game_setup.py
spatial_utils.py
config.py
ui/dialogue.py
game.py
lighting.py
test_npc.py
saves/
```
