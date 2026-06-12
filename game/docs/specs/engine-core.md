# Technical Specification — Engine Core [Implementation]


> **Document Type:** Implementation
> **Source:** `src/engine/game.py`, `src/engine/game_state_manager.py`, `src/ui/title_screen.py`, `src/ui/pause_screen.py`, `src/ui/hud.py`, `src/config.py`, `src/engine/engine_constants.py`

This document specifies the core RPG Tile Engine lifecycle, GameStateManager orchestrations, rendering pipelines, grid-based movement systems, spatial interaction checks, Title Screen breathing lights animations, Pause Screen overlays, and UI priority guidelines.

---

## 1. Core Modules

| Module | Responsibility | Primary Classes |
|--------|----------------|-----------------|
| **Engine** | Lifecycle, Orchestration | `Game`, `MapLoader`, `EntityFactory`, `InputHandler`, `Settings` |
| **GameStateManager** | Screen State Machine | `GameStateManager`, `TitleScreen`, `PauseScreen`, `SaveManager` |
| **Map** | Data, Culling, Layout | `MapManager`, `AnimationMapManager`, `TmjParser`, `LayoutStrategy` |
| **Entity** | Sprites, Sorting, Movement | `BaseEntity`, `Player`, `CameraGroup`, `Teleport`, `EmoteBubble` |
| **Logic** | Gating, Proximity, Collision | `InteractionManager`, `CollisionChecker`, `spatial_utils` |

### 1.1 Engine Constants Inventory (`src/engine/engine_constants.py`)

This file is a **leaf module** (zero imports from `src/`). It provides:

| Constant | Value | Consumers |
|----------|-------|-----------|
| `COLOR_PLACEHOLDER_MAGENTA` | `(255, 0, 255)` | `asset_manager.py`, `teleport.py`, `pickup.py` |
| `COLOR_PLACEHOLDER_BLUE` | `(0, 0, 255)` | `spritesheet.py` |
| `SPRITESHEET_FALLBACK_SIZE` | `(32, 32)` | `spritesheet.py` — fallback surface dimensions when image load fails |
| `SPRITESHEET_FALLBACK_FRAME_COUNT` | `16` | `spritesheet.py` — fallback frame count when image load fails |
| `GRASS_MAX_DEPTH` | `1` | `map/manager.py` — layer depth threshold for grass-eligible tiles |
| `TILED_PROJECT_PATH` | `"assets/tiled/game.tiled-project"` | `map/tmj_parser.py` — Tiled project file path |

> See also: [code-quality-constants-i18n.md §F-QUAL-02-A](./code-quality-constants-i18n.md#L203) — original spec + BUILD Addendum §F for anti-divergence record.

## 2. GameStateManager & Screen State Machine

`GameStateManager` orchestrates the active screen context, high-level game state transitions, and event processing.

### 2.1 State Transitions
```
[MAIN_MENU]  ◄──────────────────────────────┐ (GameEvent.MAIN_MENU)
     │                                      │
     ├──(GameEvent.NEW_GAME)                │
     │      ▼                               │
     │   [PLAYING] ──────────────────────┐  │
     │       ▲  │                        │  │
     │       │  └──(K_ESCAPE)            │  │
     │       │      ▼                    │  │
     │       │   [PAUSED] ───────────────┼──┘
     │       │       │                   │
     │       │       └──(GameEvent.QUIT)─┼──┐
     │       │                           │  │
     └──(GameEvent.LOAD_GAME)            │  │
             ▼                           │  │
         Loads slot                      │  │
             │                           ▼  ▼
             └───────────────────────► [EXIT] (pygame.quit)
```

- **MainMenu State**: Instantiates and renders `TitleScreen`. Launches `NEW_GAME` or loads an existing slot via `LOAD_GAME`.
- **Playing State**: Holds active `Game` orchestration loop (updates logic, inputs, and custom rendering passes).
- **Paused State**: Overlays a semi-transparent gray surface `(0, 0, 0, 150)` with `PauseScreen` options.

> [!NOTE]
> During `PLAYING`, the `_intra_walk_target` flag creates a modal sub-state where player input is blocked and a scripted walk executes. See [intra-map-teleport.md §4.2](./intra-map-teleport.md#L1).

---

## 3. Title Screen & Pause Screen Interfaces

### 3.1 Title Screen Menu & Ambient Lights
Calibrated logical coordinate space: `1280×720`.
- **Title Text**: Font `assets/fonts/cormorant-garamond-regular.ttf` at size 90pt. Light cyan `(150, 255, 220)` with intense cyan glow `(0, 180, 150)`.
- **Fire/Lantern Halos (`BACKGROUND_LIGHTS`)**: 33 coordinates simulating fire scintillation:
  ```python
  scintillation = sin(t*0.4 + i*1.1) * 0.06 + sin(t*0.9 + i*2.3) * 0.04  # base 0.92
  ```
- **Bioluminescent Mushroom Halos (`MUSHROOM_LIGHTS`)**: 25 coordinates breathing slowly:
  ```python
  breathing = sin(t*0.15 + i*1.3) * 0.10 + sin(t*0.37 + i*2.1) * 0.06  # base 0.84
  ```

### 3.2 Pause Screen Overlay
Renders the panel asset scaled to `500×600` centered at `(390, 60)` with a dark overlay and provides navigation buttons.

---

## 4. Grid-Based Movement & Alignment

All mobile entities move in discrete steps of `TILE_SIZE` (32px):
1. **Targeting**: Target center is calculated as `current_pos + direction * TILE_SIZE`.
2. **Alignment Offset**: Entities must remain aligned to tile centers: `(col * TILE_SIZE + 16, row * TILE_SIZE + 16)`.
3. **Interpolation**: Linear interpolation between grid tiles governed by `Settings.PLAYER_SPEED`.
4. **Visuality**: Hitboxes remain strictly `32x32`. If the sprite is taller (e.g. `32x48`), the visual bottom-right aligns with the physical hitbox bottom-right, allowing correct Y-sorting.

---

## 5. Collision Checker & Obstacle Constraints

### 5.1 Authoritative Check Sequence (`CollisionChecker.check`)
Checks block status for grid coordinate `(px, py)` requested by `requester`:
1. **Walkable Override Priority**: If the target matches an entity in `game.walkable_override_entities` (e.g., an `EXTENDED` Drawbridge), skip tile constraints and return `False` immediately (player is permitted traversal).
2. **Map Tiles**: Query `MapManager.is_walkable(col, row)`. Return `True` (blocked) if the tile is not walkable.
3. **Obstacles**: Check for collidepoints inside `obstacles_group`.
4. **NPCs**: Check for collidepoints inside `npcs` group.
5. **Player**: Check for collidepoints on the player hitbox if the requester is not the player.

---

## 6. Rendering Pipeline & Viewport Culling

### 6.1 Viewport Frustum Culling
To prevent performance degradation on large maps, rendering loops iterate over O(1) tile bounds determined by the viewport position:
- `start_col = max(0, viewport.left // tile_size)`
- `end_col = min(map_width, ceil(viewport.right / tile_size))`

### 6.2 Camera Clamping
Viewport limits are strictly clamped inside map bounds:
```python
offset_x = clamp(player_center_x - screen_w // 2, 0, map_w_px - screen_w)
```
If screen width exceeds map width, coordinates are centered: `offset_x = (screen_w - map_w_px) // 2`.

### 6.3 Game Update Loop (`_update_core_state`)

The canonical per-frame update method is `Game._update_core_state(dt)`, called from the main loop during `PLAYING` state. Its structure:

1. **Intra-map walk intercept**: If `_intra_walk_target` is set, delegate to `_tick_intra_walk(dt)` and return early (blocks all other update logic). See [intra-map-teleport.md §4.5](./intra-map-teleport.md#L1).
2. **Player input**: `player.input()` (keyboard polling).
3. **Entity updates**: `player.update(dt)`, NPC updates (visibility-gated), interactive entity updates.
4. **Interaction checks**: `interaction_manager.update(dt)`, `interaction_manager.check_teleporters(was_moving)`.
5. **Audio flush**: `audio_manager.flush_ambient()`.
6. **Camera sync**: Update viewport offset.

---

## 7. Spatial Interaction & Dialogue HUD

### 7.1 Interaction Mechanics
- Triggered by `Settings.INTERACT_KEY` (E) with a **0.5s cooldown**.
- Open doors (`is_on=True`) relax the facing checks to let players close them from either side.

#### 7.1.1 Distance Thresholds

| Range | Constant | Applied To |
|-------|----------|------------|
| `< 45px` | `_RANGE_SQ_45` | Standard object interaction, chest auto-close |
| `< 48px` | `_RANGE_SQ_48` | Pickup items, `activate_from_anywhere` objects, proximity emotes |
| `< 16px` | `_RANGE_SQ_16` | On-top exception (passable objects, pickup facing bypass) |

> [!NOTE]
> These thresholds are distinct by design. Standard objects use 45px; pickups and `activate_from_anywhere` objects use the wider 48px range. The on-top exception at 16px allows interaction regardless of facing direction.

### 7.2 Dialogue Typewriter Box
- **Typewriter Rendering**: Reveals characters sequentially at `Settings.TEXT_SPEED` (cps).
- **Pagination Logic**: Line length and count wrap dynamically within `dialogue_box` margins (140px). Text blocks auto-paginate (3 lines max with a Title, 5 lines max without).
- **Control**: Pressing the interact key during typing fills the current page instantly. Pressing it when typing is done advances pages or dismisses dialogue.

### 7.3 Playtime Tracking
- `Game._playtime_seconds: float` — accumulated via `+= dt` every frame during `PLAYING` state only (paused time excluded).
- `SaveManager.save()` reads `game._playtime_seconds` and stores it in the JSON root as `playtime_seconds`.
- `SaveManager.load()` restores it into `game._playtime_seconds`.

---

## 8. UI Hierarchy & Input Blocking

Strict UI priority layers prevent overlapping menus and input conflicts:

| Layer | Priority | Inputs Blocked |
|-------|----------|----------------|
| **Dialogue** | 1 (Highest) | Blocks Inventory menu, Chest screens, and player movement. |
| **Inventory** | 2 | Blocks Player movement. Interaction keys are suppressed (returns early). |
| **Chest UI** | 3 | Blocks Inventory toggles. Allows limited player movement (auto-closes if distance exceeds range). |

---

## 9. Night Cycles & Halos

> **Note:** The authoritative brightness/darkness calculation is in [lighting-system.md](./lighting-system.md#L1). The formula below is a simplified overview for reference.

- **Sine Brightness**: Sinusoidal factor: `0.5 + 0.5 * sin(2π * hour/24 - π/2)`.
- **Night Shader**: A full-screen black overlay `(0, 0, 0)` with alpha reflecting darkness (max 180 alpha at midnight).
- **Breathing Glows**: Halos scale cyclically between `97%` and `103%` size to simulate glowing breathing effects.

---

## 10. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load assets inside `draw()` | Use pre-cached assets | Performance drops and disk I/O in main loop |
| Clamp `rect` directly | Clamp `pos` (float) | Sub-pixel jitter and rounding errors |
| Use `image.get_rect()` for physical hitboxes | Use explicit `Rect(0, 0, 32, 32)` | Tall sprites offset layout physical alignments |
| Call `.fill()` on a shared screen Surface | Use separate target layers | Modifies screen frames persistently, breaking overlays |
| Load slots fully for slot listing | Read slots lazily for metadata in `list_slots()` | Optimizes load menu speed |

---

## 11. Error Handling Matrix

| Error Type | Detection | Mitigation | Fallback |
|------------|-----------|------------|----------|
| Config Corrupt | JSONDecodeError | Log warning | Load internal fallback defaults |
| Map Missing | FileNotFoundError | Log critical | Terminate loop safely |
| Surface None | TypeError in blit | Log warning | Skip rendering step (prevents unit crashes) |
| Audio Init Fail | `pygame.error` in mixer | Log warning | Disable audio system, set `is_enabled=False` |
| Deep Chain Recursion | Chaining depth > 1 | Log warning | Break chain resolution to prevent crash |

---

## 12. Test Case Specifications

### 12.1 Core Lifecycle, Loops & Game Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| CORE-C-01 | `test_game_initialization` | `../../tests/engine/test_game.py` |
| CORE-H-01 | `test_update_dialogue_branch` | `../../tests/engine/test_game.py` |
| CORE-H-02 | `test_handle_events_dialogue_advance` | `../../tests/engine/test_game.py` |
| CORE-R-01 | `test_game_draw_loop` | `../../tests/engine/test_game.py` |
| CORE-R-02 | `test_game_draw_loop` | `../../tests/engine/test_game.py` |
| CORE-R-03 | `test_game_draw_loop` | `../../tests/engine/test_game.py` |
| DBG-CONF | `test_settings_load` | `../../tests/engine/test_game.py` |
| DBG-MAP | `test_game_actual_load_map` | `../../tests/engine/test_game.py` |
| DBG-SPAWN | `test_spawn_entities_initial_spawn_skipped` | `../../tests/engine/test_game.py` |
| GF-012 | `test_game_ui_toggles` | `../../tests/engine/test_game.py` |
| GF-013 | `test_game_update_loop` | `../../tests/engine/test_game.py` |
| GF-014 | `test_update_dialogue_branch` | `../../tests/engine/test_game.py` |
| GF-015 | `test_update_inventory_branch` | `../../tests/engine/test_game.py` |
| GF-016 | `test_update_chest_branch` | `../../tests/engine/test_game.py` |
| GF-017 | `test_handle_events_dialogue_advance` | `../../tests/engine/test_game.py` |
| GF-018 | `test_game_transition_map_fade` | `../../tests/engine/test_game.py` |
| WS-006 | `test_game_entity_spawning` | `../../tests/engine/test_game.py` |
| TC-FONT-01 | `test_settings_load` | `../../tests/engine/test_game.py` |
| TC-FONT-02 | `test_font_tiers_exist` | `../../tests/engine/test_game.py` |
| TC-FONT-03 | `test_font_tiers_exist` | `../../tests/engine/test_game.py` |

### 12.2 Game State Manager Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| GF-019 | `test_initial_state` | `../../tests/engine/test_game_state_manager.py` |
| GF-020 | `test_handle_title_new_game` | `../../tests/engine/test_game_state_manager.py` |
| GF-021 | `test_handle_title_load_game` | `../../tests/engine/test_game_state_manager.py` |
| GF-022 | `test_handle_title_quit` | `../../tests/engine/test_game_state_manager.py` |
| GF-023 | `test_handle_playing_pause_requested` | `../../tests/engine/test_game_state_manager.py` |
| GF-024 | `test_handle_paused_resume` | `../../tests/engine/test_game_state_manager.py` |
| GF-025 | `test_handle_paused_save_requested` | `../../tests/engine/test_game_state_manager.py` |
| GF-026 | `test_handle_paused_goto_title` | `../../tests/engine/test_game_state_manager.py` |
| GF-027 | `test_save_to_first_free_slot` | `../../tests/engine/test_game_state_manager.py` |
| GF-028 | `test_save_to_first_free_slot_all_full` | `../../tests/engine/test_game_state_manager.py` |
| GF-029 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py` |
| GF-030 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py` |
| GF-031 | `test_load_game_time_restored` | `../../tests/engine/test_game_state_manager.py` |
| GF-032 | `test_handle_events_filtering` | `../../tests/engine/test_game_state_manager.py` |
| GF-033 | `test_transition_to_title_resets_inventory_and_chest_ui` | `../../tests/engine/test_game_state_manager.py` |

### 12.3 Collision Checker Constraints Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-CC-01 | `test_tile_not_walkable_returns_true` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-02 | `test_obstacle_blocks` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-03 | `test_obstacle_skipped_if_requester` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-04 | `test_npc_blocks` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-05 | `test_npc_skipped_if_requester` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-06 | `test_player_blocks_npc` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-07 | `test_nothing_blocks_returns_false` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-08 | `test_open_bridge_overrides_non_walkable_tile` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-09 | `test_no_override_non_walkable_tile_still_blocks` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-10 | `test_override_rect_miss_still_blocks` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-11 | `test_animating_override_does_not_override_tile` | `../../tests/engine/test_collision_checker.py` |
| TC-CC-12 | `test_override_tile_still_checks_obstacles_and_npcs` | `../../tests/engine/test_collision_checker.py` |
| IT-CC-01 | `test_is_walkable_delegates_to_collision_checker` | `../../tests/engine/test_collision_checker.py` |

### 12.4 Spatial Utilities Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-SU-01 | `test_get_facing_vector_down` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-02 | `test_get_facing_vector_up` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-03 | `test_get_facing_vector_left` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-04 | `test_get_facing_vector_right` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-05 | `test_get_facing_vector_unknown_state` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-06 | `test_facing_toward_right_horizontal` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-07 | `test_facing_toward_left_horizontal` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-08 | `test_facing_toward_down_vertical` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-09 | `test_facing_toward_wrong_direction` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-10 | `test_verify_orientation_standard_up_down` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-11 | `test_verify_orientation_not_aligned` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-12 | `test_verify_orientation_door_relaxation` | `../../tests/engine/test_spatial_utils.py` |
| TC-SU-13 | `test_verify_orientation_default_false` | `../../tests/engine/test_spatial_utils.py` |

### 12.5 Game Orchestration (Phase 1.5 / Setup) Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-EF-01 | `test_get_property_root_level` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-02 | `test_get_property_nested` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-03 | `test_get_property_absent_returns_default` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-04 | `test_spawn_interactive_adds_to_groups` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-05 | `test_spawn_teleport_adds_to_teleports_group` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-06 | `test_spawn_npc_adds_to_visible_and_npcs` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-07 | `test_spawn_pickup_adds_to_pickups` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-08 | `test_spawn_entities_unknown_type_no_exception` | `../../tests/engine/test_phase15_game.py` |
| TC-EF-09 | `test_spawn_interactive_restores_world_state` | `../../tests/engine/test_phase15_game.py` |
| TC-GS-01 | `test_load_property_types_valid_file` | `../../tests/engine/test_phase15_game.py` |
| TC-GS-02 | `test_load_property_types_missing_file` | `../../tests/engine/test_phase15_game.py` |
| TC-GS-03 | `test_load_property_types_invalid_json` | `../../tests/engine/test_phase15_game.py` |
| TC-GS-04 | `test_setup_logging_adds_handlers` | `../../tests/engine/test_phase15_game.py` |
| TC-GS-05 | `test_load_property_types_missing_key` | `../../tests/engine/test_phase15_game.py` |
| TC-IH-01 | `test_quit_event_calls_sys_exit` | `../../tests/engine/test_phase15_game.py` |
| TC-IH-02 | `test_interact_key_no_dialogue_calls_handle_interactions` | `../../tests/engine/test_phase15_game.py` |
| TC-IH-03 | `test_interact_key_with_dialogue_advances_dialogue` | `../../tests/engine/test_phase15_game.py` |
| TC-IH-04 | `test_inventory_key_chest_closed_toggles_inventory` | `../../tests/engine/test_phase15_game.py` |
| TC-IH-05 | `test_inventory_key_chest_open_does_not_toggle` | `../../tests/engine/test_phase15_game.py` |
| TC-IH-06 | `test_interact_key_inventory_open_does_not_trigger_interaction` | `../../tests/engine/test_phase15_game.py` |
| IT-EF-01 | `test_game_has_entity_factory_map_loader_input_handler` | `../../tests/engine/test_phase15_game.py` |
| IT-GS-01 | `test_game_setup_logging_importable` | `../../tests/engine/test_phase15_game.py` |
| IT-IH-01 | `test_game_handle_events_delegates_to_input_handler` | `../../tests/engine/test_phase15_game.py` |

### 12.6 Title Screen Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| GF-034 | `test_title_screen_draw_main_menu` | `../../tests/ui/test_title_screen.py` |
| GF-035 | `test_title_screen_load_menu_back_button` | `../../tests/ui/test_title_screen.py` |
| GF-036 | `test_title_screen_options_state_transitions` | `../../tests/ui/test_title_screen.py` |

---

## 13. Deep Links
- **Spawning & Interactions**: [game.py L168](../../src/engine/game.py#L168)
- **Dialogue Paging Logic**: [dialogue.py - _paginate](../../src/ui/dialogue.py#L74)
- **State Switcher**: [game_state_manager.py L1](../../src/engine/game_state_manager.py#L1)
- **Glow & Lights**: [title_screen.py L1](../../src/ui/title_screen.py#L1)


