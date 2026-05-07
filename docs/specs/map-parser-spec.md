# Technical Specification - Map Parser & Manager [Implementation]

> Document Type: Implementation

This document specifies the AS-IS technical implementation of the map parsing pipeline, covering TMJ/TSX data extraction, Tiled Project schema resolution, map layer management, and coordinate layout strategies.

## 1. Goal Description

Parse Tiled-exported map files (`.tmj` JSON + `.tsx` XML tilesets) into internal engine data structures, resolve custom class properties via the Tiled Project schema, and provide a unified layer/tile management interface for rendering and spatial queries.

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `TmjParser` | `src/map/tmj_parser.py` | 264 | TMJ/TSX parsing, entity extraction, occlusion pre-cache |
| `TiledProject` | `src/map/project_schema.py` | 91 | Custom property class resolution and deep-merge |
| `MapManager` | `src/map/manager.py` | 192 | Layer management, depth ordering, terrain lookup |
| `OrthogonalLayout` | `src/map/layout.py` | 35 | Coordinate transformation strategy |

## 3. TmjParser — TMJ/TSX Parsing Pipeline

### 3.1. Data Flow

```
.tmj (JSON) ──→ TmjParser.load()
                  ├─ _parse_tsx() for each tileset (XML)
                  ├─ _process_layers() recursive group support
                  └─ Returns: dict{width, height, layers, tiles, entities, spawn_player, properties}
```

### 3.2. TMJ Parsing (`load`)

**Input**: Path to `.tmj` file (Tiled JSON export).

**Output**: Dictionary containing:
| Key | Type | Description |
|-----|------|-------------|
| `width` | int | Map width in tiles |
| `height` | int | Map height in tiles |
| `tile_width` | int | Tile width in pixels (typically 32) |
| `tile_height` | int | Tile height in pixels (typically 32) |
| `layers` | list[dict] | Processed tile/object layers |
| `tiles` | dict[int, TileProperty] | GID → tile properties mapping |
| `entities` | list[dict] | Extracted entity objects for spawning |
| `spawn_player` | dict | `{x, y}` center coordinates of player spawn |
| `properties` | dict | Map-level custom properties (e.g., `bgm`, `map_display_name`) |

**Coordinate Conversion**: Tiled objects use top-left origin. The parser adds `TILE_SIZE / 2` offset to convert to center-based coordinates used by the engine.

### 3.3. TSX Parsing (`_parse_tsx`)

**Input**: Path to `.tsx` file (XML tileset), `firstgid` from TMJ.

**Output**: Populates `tile_dict` mapping GIDs to `TileProperty` named tuples.

**TileProperty fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `collidable` | bool | `False` | Blocks movement |
| `depth` | int | `0` | Render depth (0=background, 1+=foreground) |
| `material` | str | `""` | Footstep sound material identifier |
| `is_window` | bool | `False` | Light source for lighting system |
| `image` | Surface | — | Pre-loaded pygame surface |
| `occluded_surface` | Surface\|None | `None` | Pre-alpha'd surface for high-depth tiles |

**Occlusion Pre-Cache**: For tiles with `depth > 0`, a copy of the tile surface is created with alpha set to `160/255` (semi-transparent). This is cached as `occluded_surface` to avoid per-frame alpha computation during foreground rendering.

### 3.4. Recursive Layer Processing (`_process_layers`)

Supports nested Tiled group layers via recursive descent:
- **Tile layers**: Extracted as grid data with GID references
- **Object layers**: Entities extracted with property resolution
- **Group layers**: Children processed recursively, inheriting parent visibility

Layer names follow the convention `{depth_prefix}-{name}` (e.g., `00-ground`, `01-objects`, `18-light`).

### 3.5. Entity Extraction

Objects from object layers are converted to entity dictionaries:
| Field | Source | Description |
|-------|--------|-------------|
| `type` | Tiled `type` or resolved `entity_type` | Engine dispatch key |
| `x`, `y` | Tiled position + TILE_SIZE/2 offset | Center coordinates |
| `width`, `height` | Tiled dimensions | Physical bounds |
| `properties` | Deep-merged via TiledProject | All custom properties |
| `gid` | Tiled GID (if tile object) | Spritesheet reference |
| `id` | Tiled object ID | Unique identifier within map |

## 4. TiledProject — Custom Property Schema Resolution

### 4.1. Purpose

Tiled 1.10+ stores custom class properties in a nested hierarchy. The `TiledProject` class loads the `.tiled-project` file and resolves property inheritance.

### 4.2. Resolution Algorithm

```python
# Pseudocode
def resolve(object_props, class_name):
    defaults = project_schema.get_class_defaults(class_name)
    return deep_merge(defaults, object_props)  # object overrides win
```

**Deep Merge Rules**:
1. Load class definition from `.tiled-project` → `propertyTypes` array
2. If the class has a `useAs` member matching the object type → apply defaults
3. Object-level properties override class defaults
4. Nested class references are resolved recursively

### 4.3. Data Source

File: `assets/tiled/game.tiled-project` (JSON)

**Example**: A `torch` object defined as class `12-light_source` in Tiled automatically receives `particles: true`, `halo_size: 50`, etc., even if not explicitly set in the `.tmj` file.

## 5. MapManager — Layer & Tile Management

### 5.1. Layer Management

- **Sorting**: Layers sorted by name prefix (e.g., `00-`, `01-`, `18-`) for render order
- **Depth extraction**: Parsed from layer name prefix (`int(name.split('-')[0])`)
- **Pre-rendered surfaces**: Background layers (`depth=0`) are pre-rendered to full-size cached surfaces via `get_layer_surface()`

### 5.2. Depth System

| Depth | Meaning | Rendering Pass |
|-------|---------|----------------|
| 0 | Background (ground, floors) | Pass 1: below entities |
| 1+ | Foreground (roofs, treetops) | Pass 3: above entities (with occlusion alpha) |

### 5.3. Window Detection

Priority-based window position extraction for the lighting system:
1. **Priority 1**: Rectangle objects in `18-light` layer → direct position extraction
2. **Priority 2**: Tile properties with `is_window=True` → fallback scanning

Returns: `list[tuple[int, int]]` of window pixel coordinates.

### 5.4. Terrain Material Lookup (`get_terrain_at`)

Top-down layer scan at a given `(x, y)` pixel position:
- Iterates layers from highest to lowest
- Returns the `material` property of the first non-empty tile found
- Used by `Player` for footstep SFX selection

## 6. OrthogonalLayout — Coordinate Strategy

### 6.1. Pattern

Strategy pattern with `LayoutStrategy` ABC:
```python
class LayoutStrategy(ABC):
    @abstractmethod
    def tile_to_pixel(self, col, row, tile_w, tile_h) -> tuple[int, int]: ...
    @abstractmethod
    def pixel_to_tile(self, x, y, tile_w, tile_h) -> tuple[int, int]: ...
```

### 6.2. OrthogonalLayout (Current Implementation)

- `tile_to_pixel`: `(col * tile_w, row * tile_h)`
- `pixel_to_tile`: `(x // tile_w, y // tile_h)`

> Isometric layout is architecturally supported but not yet implemented.

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Parse TSX as JSON | Parse TSX as XML (`xml.etree.ElementTree`) | TSX files are XML, not JSON |
| Hardcode tile properties | Read from TSX `<property>` elements | Supports Tiled editor customization |
| Flatten group layers | Process recursively | Preserves Tiled layer organization |
| Calculate occlusion alpha per frame | Pre-cache `occluded_surface` at load | Eliminates per-frame Surface.copy() + set_alpha() |
| Assume single tileset per map | Iterate all tilesets with `firstgid` offset | Multi-tileset maps are standard |
| Access properties directly from TMJ | Resolve via `TiledProject` schema first | Missing defaults cause KeyError |

## 8. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| MAP-U-01 | TmjParser.load | Valid `.tmj` file | Dict with all required keys | Missing spawn point |
| MAP-U-02 | _parse_tsx | Valid `.tsx` XML | Correct TileProperty mapping | Tile with no properties |
| MAP-U-03 | TiledProject.resolve | Class `torch` + empty overrides | Returns class defaults | Unknown class name |
| MAP-U-04 | MapManager.get_terrain_at | Pixel on grass tile | `"grass"` | Pixel outside map bounds |
| MAP-U-05 | OrthogonalLayout.tile_to_pixel | `(2, 3)` with tile_size=32 | `(64, 96)` | `(0, 0)` |

### Integration Tests
| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| MAP-I-01 | Full map load | Load test `.tmj` with entities | All entity dicts contain resolved properties |
| MAP-I-02 | Multi-tileset | Map with 3 tilesets | GIDs correctly offset by firstgid |

## 9. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing .tmj | `FileNotFoundError` | Log critical | Abort map load |
| Malformed JSON | `json.JSONDecodeError` | Log error | Return empty dict |
| Missing .tsx | `FileNotFoundError` | Log warning | Skip tileset, continue |
| Invalid XML | `xml.etree.ElementTree.ParseError` | Log error | Skip tileset |
| Missing .tiled-project | `FileNotFoundError` | Log warning | Use empty schema (no defaults) |
| GID out of range | KeyError in tile_dict | Log debug | Return default TileProperty |

## 10. Deep Links
- **`TmjParser`**: [tmj_parser.py L1](../../src/map/tmj_parser.py#L1)
- **`TiledProject`**: [project_schema.py L1](../../src/map/project_schema.py#L1)
- **`MapManager`**: [manager.py L1](../../src/map/manager.py#L1)
- **`OrthogonalLayout`**: [layout.py L1](../../src/map/layout.py#L1)
- **Unit tests**: [test_parser.py L1](../../tests/map/test_parser.py#L1)
- **Integration tests**: [test_map.py L1](../../tests/map/test_map.py#L1)


## Assumptions
| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | System performs adequately | Low | Playtest |
| 2 | Inputs are sanitized | Low | Code review |
| 3 | Components interact seamlessly | Low | Integration tests |

## Test Case Specifications
| ID | Description | Type |
|---|---|---|
| TC-001 | Validate initialization | Unit |
| TC-002 | Validate state transition | Unit |
| TC-003 | Validate edge case handling | Unit |
| TC-004 | Validate error raising | Unit |
| TC-005 | Validate boundary conditions | Unit |
| IT-001 | Validate module integration | Integration |
| IT-002 | Validate state persistence | Integration |
| IT-003 | Validate system flow | Integration |
