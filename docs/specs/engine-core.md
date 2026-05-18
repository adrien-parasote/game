# Technical Specification — Engine Core [Implementation]

> **Document Type:** Implementation
> **Source:** `src/engine/game.py`, `src/engine/game_state_manager.py`, `src/ui/title_screen.py`, `src/ui/pause_screen.py`, `src/ui/hud.py`, `src/config.py`

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

---

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

---

## 7. Spatial Interaction & Dialogue HUD

### 7.1 Interaction Mechanics
- Triggered by `Settings.INTERACT_KEY` (E) with a **0.5s cooldown**.
- Valid within a `< 45px` range when facing the target.
- Open doors (`is_on=True`) relax the facing checks to let players close them from either side.

### 7.2 Dialogue Typewriter Box
- **Typewriter Rendering**: Reveals characters sequentially at `Settings.TEXT_SPEED` (cps).
- **Pagination Logic**: Line length and count wrap dynamically within `dialogue_box` margins (140px). Text blocks auto-paginate (3 lines max with a Title, 5 lines max without).
- **Control**: Pressing the interact key during typing fills the current page instantly. Pressing it when typing is done advances pages or dismisses dialogue.

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

### 12.1 Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| UT-GSM-01 | GameStateManager | Transition `NEW_GAME` | Instantiates `Game`, state set to `PLAYING` |
| UT-GSM-02 | GameStateManager | Transition `LOAD_GAME(1)` | Restores state via slot 1, starts game |
| UT-GSM-03 | GameStateManager | Event `K_ESCAPE` in play | Switches state to `PAUSED` |
| UT-TS-01 | TitleScreen | Click "Options" button | Sets state to `OPTIONS` |
| UT-TS-02 | TitleScreen | Input hover | Updates `_hovered_item` |
| CORE-R-01 | Y-Sorting | [Y=100, Y=50] elements | Rendered in order [50, 100] |
| CORE-R-02 | Culling | Viewport at `(0, 0)` | Skips rendering tiles outside culling limits |
| CORE-H-01 | Dialogue Update | Dialogue started | Sequential typewriter rendering advances |
| TC-CC-08 | Collision Check | Walkable bridge overlap | Return `False` (traversal permitted) |

---

## 13. Deep Links
- **Spawning & Interactions**: [game.py L168](../../src/engine/game.py#L168)
- **Dialogue Paging Logic**: [dialogue.py - _paginate](../../src/ui/dialogue.py#L74)
- **State Switcher**: [game_state_manager.py L1](../../src/engine/game_state_manager.py#L1)
- **Glow & Lights**: [title_screen.py L1](../../src/ui/title_screen.py#L1)
