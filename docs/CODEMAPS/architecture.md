<!-- Generated: 2026-05-01 | Files scanned: 32 | Token estimate: ~300 -->

# Game Engine Architecture

## System Flow
`main.py` → `Game.run()` (Main Loop)
`Game.update()` → Input → `InteractionManager` → `Entity.update()`
`Game.draw()` → `_draw_background()` → `VisibleSprites.custom_draw()` (Y-sorted) → `_draw_foreground()` → `_draw_hud()` → UIs

## Core Components
- **Game** (`src/engine/game.py`): Central orchestrator, manages state transitions, entity spawning, loop.
- **MapManager** (`src/map/manager.py`): Handles layer surfaces, TMJ map state, collision queries.
- **InteractionManager** (`src/engine/interaction.py`): Proximity logic for objects, chests, NPCs, pickups, and emotes.
- **VisibleSprites** (`src/entities/groups.py`): Y-sorted rendering group with camera offset support.
- **AssetManager** (`src/engine/asset_manager.py`): Singleton for image/font caching.
- **I18nManager** (`src/engine/i18n.py`): Singleton for translation lookups.

## Key Subsystems
- **Inventory/Chest UI** (`src/ui/inventory.py`, `src/ui/chest.py`): Grid-based, absolute slot index D&D overlay UI.
- **Dialogue/Speech** (`src/ui/dialogue.py`, `src/ui/speech_bubble.py`): Typewriter and Paginated 9-patch bubbles.
- **Entities** (`src/entities/interactive.py`, `npc.py`, `pickup.py`): Base `Entity` subclasses with interaction and logic loops.

## Tech Stack
- **Engine**: Python 3.13+, Pygame-CE (Community Edition)
- **Data Format**: Tiled (TMJ/TSX), JSON (settings, i18n, loot)
- **Architecture Pattern**: Component-based entities, Singleton managers, Centralized Game Loop
