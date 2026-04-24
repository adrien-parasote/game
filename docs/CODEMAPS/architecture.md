<!-- Generated: 2026-04-24 | Files scanned: 25 | Token estimate: ~400 -->

# RPG Engine Architecture

## Core Flow
main.py → Game.run() → Game.update() → Game.draw()
Game.update() → TimeSystem.update() → Entities.update() → Interaction Check
Game.draw() → Map.render() → Y-Sorted Entities → UIManager.draw()

## Key Modules
- **Engine**: `src/engine/game.py` (Main loop, event bus, state)
- **Data**: `src/map/tmj_parser.py` (Tiled TMJ/TSX resolving), `src/engine/world_state.py` (Persistence)
- **Entities**: `src/entities/base.py` (Grid movement), `src/entities/npc.py` (AI), `src/entities/interactive.py` (Triggers)
- **UI**: `src/ui/hud.py` (Clock), `src/ui/dialogue.py` (Paginated UI)
- **Graphics**: `src/graphics/spritesheet.py` (Asset management)

## Tech Stack
- **Runtime**: Python 3.13+
- **Framework**: Pygame-ce (Rendering, Input, Audio)
- **Map Format**: Tiled 1.10+ (TMJ/TSX + .world)
