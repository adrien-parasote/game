<!-- Generated: 2026-04-24 | Files scanned: 25 | Token estimate: ~300 -->

# Data & Persistence

## Configuration (src/config.py)
`Settings` loads from:
1. `settings.json` (Resolution, Fullscreen, Debug, Paths)
2. `gameplay.json` (Speed, Interaction keys, Time scale, Dialogue speed)

## World Persistence (src/engine/world_state.py)
- **Key Format**: `{map_base_name}_{element_id}` (e.g., `00-spawn_lever1`)
- **Storage**: Python dictionary `_state`.
- **Saved Properties**: `is_on` (bool) for chests, doors, switches.

## Map Schema (src/map/tmj_parser.py)
`load_map()` returns:
- `layers`: Dict of 2D matrices (Layer Name -> List of Lists)
- `entities`: List of dicts (Spawn properties)
- `spawn_player`: `{"x": int, "y": int}`
- `tile_dict`: GID to `TileProperty` mapping

## Localization (assets/langs/)
- `fr.json`: Dictionary of `dialogues` and environmental labels.
- Format: `{ "dialogues": { "map-id": "text" } }`
