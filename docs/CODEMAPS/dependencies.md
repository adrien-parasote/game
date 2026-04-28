<!-- Generated: 2026-04-24 | Files scanned: 25 | Token estimate: ~250 -->

# Dependencies & Assets

## Core Stack
- **Python 3.13+**
- **Pygame-ce** (Community Edition): Core engine, input, rendering.
- **Tiled** (1.10+): Map and object property design.

## Asset Directory Map
- `assets/images/sprites/`: Spritesheets for Player, NPCs, and Objects.
- `assets/images/hud/`: UI elements (textbox, cursor, clock).
- `assets/images/ui/`: Inventory background, slots, tabs, and custom pointers (`05-pointer.png`).
- `assets/audio/bgm/`: Background music (.ogg).
- `assets/audio/sfx/`: Interaction sounds (.ogg).
- `assets/tiled/maps/`: `.tmj` map files.
- `assets/tiled/tilesets/`: `.tsx` tilesets.
- `assets/tiled/game.tiled-project`: Central property resolver.

## Critical Third-Party Integrations
- **JSON**: Map data and configuration.
- **OS/Sys**: Path resolution and lifecycle management.
- **Logging**: Rotating file logs in `logs/game.log`.
