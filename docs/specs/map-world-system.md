# Technical Specification — Map, World & Interaction System [Implementation]

> **Document Type:** Implementation
> **Sources:** `src/map/tmj_parser.py` (264 LOC), `src/map/project_schema.py` (91 LOC), `src/map/manager.py` (192 LOC), `src/map/layout.py` (35 LOC), `src/engine/game.py`, `src/engine/map_loader.py`

This document specifies the AS-IS technical implementation of the map parsing pipeline, orthogonal layout, spatial query engine, intentional proximity interaction model, teleportation triggers, and session-level state persistence.

---

## 1. Goal Description

Parse Tiled-exported map files (`.tmj` JSON + `.tsx` XML tilesets), resolve custom class properties using the Tiled Project schema, maintain a unified layer/tile depth system, manage player interaction constraints, handle seamless map transitions (teleports), and guarantee persistent state across map swaps for interactive entities and pickup items.

---

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `TmjParser` | `src/map/tmj_parser.py` | 264 | TMJ/TSX parsing, entity extraction, occlusion pre-cache |
| `TiledProject` | `src/map/project_schema.py` | 91 | Custom property class resolution and deep-merge |
| `MapManager` | `src/map/manager.py` | 192 | Layer management, depth ordering, terrain lookup, collision checking |
| `OrthogonalLayout` | `src/map/layout.py` | 35 | Coordinate transformation strategy |
| `MapLoader` | `src/engine/map_loader.py` | — | Map switching pipeline and state snapshots |
| `WorldState` | `src/engine/world_state.py` | — | Global persistence registry for the game session |

---

## 3. TmjParser — TMJ/TSX Parsing Pipeline

### 3.1 Data Flow
```
.tmj (JSON) ──→ TmjParser.load()
                  ├─ _parse_tsx() for each tileset (XML)
                  ├─ _process_layers() recursive group support
                  └─ Returns: dict{width, height, layers, tiles, entities, spawn_player, properties}
```

### 3.2 TMJ Parsing (`load`)
Input: Path to `.tmj` file. Output is a dictionary containing:
- `width`, `height`, `tile_width`, `tile_height` in pixels (typically 32).
- `layers`: Processed tile/object layers.
- `tiles`: `dict[int, TileMapData]` mapping GIDs to tile properties.
- `entities`: Extracted entity objects for spawning.
- `spawn_player`: `{x, y}` center coordinates of player spawn.
- `properties`: Map-level custom properties (e.g., `bgm`, `map_display_name`).

*Coordinate Conversion*: Tiled objects use top-left origin. The parser adds `TILE_SIZE / 2` offset to convert to center-based coordinates used by the engine.

### 3.3 TSX Parsing (`_parse_tsx`)
XML parsing of `.tsx` files. Populates GID properties to `TileMapData` instances.

**`TileMapData` dataclass**:
- `image`: Pre-loaded pygame surface.
- `depth`: Render depth (0=background, 1+=foreground).
- `walkable`: Boolean (replaces legacy `collidable`).
- `direction_flags`: Allowed exit directions (`set[str]` defaulting to `{"any"}`).
- `frames`: List of animation frames `{tileid, duration}`.
- `occluded_image`: Cached semi-transparent copy of foreground tiles (alpha `160/255`) to eliminate per-frame overhead.
- `properties`: Raw Tiled custom properties dictionary.

### 3.4 Custom Property Schema Resolution (`TiledProject`)
Loads `assets/tiled/game.tiled-project` to resolve custom property class inheritance:
1. Object-level properties override class defaults.
2. Nested class references are resolved recursively.
3. Class definitions with `useAs` automatically inject defaults into matching object types.

---

## 4. MapManager — Layer & Tile Management

### 4.1 Two-Axis Depth System
The rendering system uses two independent depth axes that must never be conflated:
1. **Layer Z Bucket**: `layer_depths[layer_id] = order` derived from the Tiled layer `order` custom property (do NOT sort by alphabetical prefixes).
2. **Tile Occlusion Depth**: `tile.depth` from the TSX tile property (0=under player, 1=same level, 2=above player).

**Rendering Passes** (with player depth = 1):
1. **Pass 1 (Background)**: Layers with `order <= 1` rendering tiles where `tile.depth <= 1`.
2. **Pass 2 (Sprites Under)**: Entities with `depth <= 1`.
3. **Pass 3 (Foreground)**: Layers with `order > 1` (all tiles) + Layers with `order <= 1` rendering tiles where `tile.depth > 1`.
4. **Pass 4 (Sprites Over)**: Entities with `depth > 1` (always drawn after all tiles).

### 4.2 Core Interfaces

#### `is_walkable(x: int, y: int) -> bool`
Checks if player can occupy grid tile `(x, y)` (out-of-bounds yields `False`).
- **Ground-Only Constraint**: Scan layers from highest to lowest `order`. The topmost tile with **`tile.depth == 0`** determines walkability. Tiles with `depth >= 1` (ceiling decorators/overhanging elements) must NOT block player movement even if marked collidable.

#### `get_direction_flags(x: int, y: int) -> set[str]`
Returns the exit constraints intersection:
- `{"any"}` behaves as a neutral joker (ignored in accumulation).
- Restrictive constraints from active layers are intersected. If all layers are neutral, returns `{"any"}`.

#### `get_terrain_material_at(pixel_x: int, pixel_y: int) -> str | None`
Top-down layer scan at a given pixel position. Skip tiles with `tile.depth > 1` (floats and roofs ignored). Returns the `material` property of the topmost tile with `depth <= 1`.

---

## 5. Interaction Model

### 5.1 Standard Proximity Interaction
Triggered by the interact key when:
- Distance between player center and object footprint center is `< 45px`.
- Player is facing the object (symmetric orientation check).

### 5.2 Dynamic `activate_from_anywhere`
Even if `activate_from_anywhere = True`, **Directional Adjacency** is required:
- **Distance**: `< 48px`.
- **Facing**: Player must look directly towards the object's relative angle:
  - If horizontal distance > vertical distance: Player must face `right` if `dx > 0`, else `left`.
  - Otherwise: Player must face `down` if `dy > 0`, else `up`.

### 5.3 Visual Proximity Indicators (Emotes)
Automatic proximity reaction:
- Triggers an `interact` (`!`) emote when distance is `< 48px` to an interactive object or NPC.
- Gated to play only if no other emote is currently active on the player.

---

## 6. Teleportation System

### 6.1 Detection & Configuration
Teleporters are objects from Tiled maps identified by the custom property `type=teleport`.

### 6.2 Trigger Mechanics
1. **Arrival Trigger (Default)**: Fires exactly when a movement step ends (`was_moving=True`, `is_moving=False`) while the player's collision box overlaps the teleport zone.
   - If `required_direction` is NOT `"any"`, the player's final facing direction must match the portal's `required_direction`.
2. **Intent Trigger (Responsive)**: Fires if the player is idle inside the teleport rectangle and pushes a movement key matching `required_direction`.
   - **Safety Exception**: Portals with `required_direction="any"` **ignore Intent triggers** to prevent infinite loop traps when trying to walk away from spawn points.

---

## 7. WorldState Persistence

Interactive entities and pickups are persisted across map loads using a global session-level dictionary:

### 7.1 Persistence Key
Constructed using `{map_basename}_{tiled_id}`:
- **Example**: The chest with ID 12 in `01-castel.tmj` resolves to `01-castel_12`.

### 7.2 Interactive Objects
- **Spawn Registration**: When instantiating `InteractiveEntity`, the engine queries WorldState with the key. If stored state (e.g. `{"is_on": True}`) is found, the state is overridden and the visual frame is snapped immediately.
- **State Mutation**: When an interaction or trigger toggles `is_on`, the updated state (and optional `light_control` setting) is written to WorldState.

### 7.3 Pickup Items
Pickups use the same `{map_basename}_{tiled_id}` keys.
- **Full Pickup**: When remaining count reaches 0, writes `{"collected": True}`. The item is skipped and **never spawned** in subsequent map loads.
- **Partial Pickup**: Storing `{"quantity": remaining}` preserves item counts if inventory was full.

---

## 8. Map Loading Pipeline (`MapLoader.load()`)

When transition triggers a teleport, the following strict sequence occurs:
1. **State Snapshot**: Call `_save_npc_states()` and `_save_interactive_states()` to persist current states to WorldState. **This must occur BEFORE clearing groups**, otherwise entity data is lost.
2. **Entity Clearance**: Clear all sprite groups, excluding the persistent `Player` entity.
3. **Map Parsing**: `TmjParser` loads the new `.tmj` file and resolves schemas.
4. **State Queries**: Read persisted data from `WorldState` to adjust spawning properties.
5. **Player Spawn**: Move player to the matching target spawn point.
6. **Finalization**: Trigger transition SFX and clear screen fades.

---

## 9. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Parse TSX as JSON | Parse TSX as XML (`xml.etree.ElementTree`) | TSX files are XML |
| Calculate occlusion alpha per frame | Pre-cache `occluded_image` at load | Eliminates per-frame overhead |
| Sort layers by name prefix | Sort by Tiled `order` property | Layer name is decorative; `order` is authoritative |
| Conflate layer Z-order with tile depth | Keep `layer_depths` and `tile.depth` strictly separate | Conflation causes invisible tiles and artifacts |
| Use AND of all layers for `is_walkable` | topmost depth=0 tile wins | Mixed-depth layers with decorations block lower ground floors |
| Target `element_id` as persistence key | Target native Tiled `id` | `element_id` is manual and can be missing; native IDs are guaranteed unique |
| Call `_clear_groups()` before saving state | Always save interactive states BEFORE clearing groups | Clearing first erases the active instances, causing loss of states on transition |

---

## 10. Error Handling Matrix

| Error Type | Detection | Mitigation | Result |
|------------|-----------|------------|--------|
| Missing TMJ | FileNotFoundError | Log Critical | Abort map loading |
| Malformed TMJ JSON | `json.JSONDecodeError` | Log Error | Return empty dict |
| Malformed TSX XML | `ElementTree.ParseError` | Log Error | Skip tileset |
| Missing Spawn Point | Spawn ID missing | Log Warning | safe-spawn player at map center |
| Missing Teleport Map | Transition target missing | Log Error | Cancel transition; player remains |

---

## 11. Test Case Specifications

### 11.1 Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| MAP-U-01 | TmjParser.load | Valid `.tmj` file | Dictionary with parsed structures |
| MAP-U-02 | _parse_tsx | Valid `.tsx` XML | Correct TileProperty GID mapping |
| MAP-U-03 | TiledProject.resolve | Class with defaults | Overrides applied correctly |
| MAP-U-04 | MapManager.get_terrain_at | Pixel on grass tile | `"grass"` |
| WS-001 | make_key | `"00-spawn.tmj"`, `58` | `"00-spawn_58"` |
| WS-002 | State Persistence | `set` then `get` | Value properly stored and retrieved |
| WS-007 | Facing Adjacency | `activate_from_anywhere=True`, facing away | Proximity interaction fails |
| WS-008 | Teleport Guard | `required_direction="down"`, player facing up | Transition rejected |

---

## 12. Deep Links
- **`TmjParser`**: [tmj_parser.py L1](../../src/map/tmj_parser.py#L1)
- **`MapManager`**: [manager.py L1](../../src/map/manager.py#L1)
- **Spawning & Interactions**: [game.py L168](../../src/engine/game.py#L168)
- **WorldState Keys**: [world_state.py L1](../../src/engine/world_state.py#L1)
