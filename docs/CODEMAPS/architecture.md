<!-- Generated: 2026-04-28 | Files scanned: ~30 | Token estimate: ~300 -->

# Game Engine Architecture

## System Flow
main.py → Game.run() (Game Loop)
Game.update() → Input → InteractionManager → Entity.update()
Game.draw() → _draw_background() → VisibleSprites.custom_draw() → _draw_foreground() → _draw_hud()

## Core Components
- **Game (src/engine/game.py)**: Central orchestrator, manages state transitions and loop.
- **MapManager (src/map/manager.py)**: Handles layer surfaces, tile mapping, and collision queries.
- **InteractionManager (src/engine/interaction.py)**: Proximity logic for emotes and triggers.
- **VisibleSprites (src/entities/groups.py)**: Y-sorted rendering group with camera offset support.
- **I18nManager (src/engine/i18n.py)**: Singleton for translation lookups (fr/en).

## Key Files
- `src/config.py`: Centralized Settings (JSON + defaults).
- `src/entities/interactive.py`: Logic for doors, chests, levers, signs.
- `src/ui/inventory.py`: Grid-based UI for item management.
- `src/map/tmj_parser.py`: Tiled JSON format importer.

## Tech Stack
- **Engine**: Pygame-CE
- **Data**: Tiled (TMJ/TSX), JSON (settings/lang)
- **Architecture**: Singleton managers + Component-based entities
