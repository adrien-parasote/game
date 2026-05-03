# SPEC: Map Rendering Fix (00-layer)

> Document Type: Implementation


## Goal
Ensure that the `00-layer` (typically the base background) is always visible and rendered first, regardless of its internal Tiled ID.

## Proposed Changes

### [MODIFY] [tmj_parser.py](file:///Users/adrien.parasote/Documents/perso/game/src/map/tmj_parser.py)
- Update `_parse_tilelayer` to store the layer name in addition to the data.
- The `layers_dict` should mapping `layer_id` to a dictionary or object containing both name and data.

### [MODIFY] [manager.py](file:///Users/adrien.parasote/Documents/perso/game/src/map/manager.py)
- Update `MapManager` to handle the new layer data structure.
- Store a mapping of names to IDs.

### [MODIFY] [game.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- In `_draw_background`, prioritize layers named `00-layer` or similar patterns.
- Ensure the rendering order follows the layer sequence defined in the map file or explicit name-based ordering.

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Sort layers solely by ID | Sort by order in file or name | ID order may not match intended rendering order |
| Hardcode "00-layer" logic only | Use a regex or configurable list | Flexibility for different naming conventions |
| Skip layers with zero depth | Always render background layers | Some maps may use depth 0 for important background data |
| Filter layers in the parser | Parse all and filter at render time | Parser should be agnostic to rendering logic |
| Use layer index as depth | Use explicit depth properties | Tiled IDs and indices are not reliable depth indicators |

## Test Case Specifications

| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-MAP-01 | MapManager | Map with "00-layer" | "00-layer" is identified as background |
| TC-MAP-02 | Game Render | Map with multiple layers | "00-layer" is drawn first (bottom-most) |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Layer | `00-layer` not found | Log warning | Draw existing layers in ID order |

## Deep Links
- **`TmjParser`**: [tmj_parser.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/map/tmj_parser.py#L1)
- **`MapManager`**: [manager.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/map/manager.py#L1)
- **`Game._draw_background`**: [game.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py#L1)
- **Map tests**: [test_map.py L1](file:///Users/adrien.parasote/Documents/perso/game/tests/map/test_map.py#L1)
- **Parser tests**: [test_parser.py L1](file:///Users/adrien.parasote/Documents/perso/game/tests/map/test_parser.py#L1)