<!-- Generated: 2026-04-24 | Files scanned: 25 | Token estimate: ~400 -->

# Game Engine Architecture

## System Overview
`src/main.py` → `Game.run()` (Main Loop) → `Event Handling` + `Logic Update` + `Render Sequence`

## Core Coordination (src/engine/)
- `game.py`: Main Orchestrator. Coordinates managers and main sprite groups.
- `interaction.py`: `InteractionManager`. Handles spatial triggers and orientation math.
- `time_system.py`: `TimeSystem`. Drives game clock, seasons, and lighting alpha.
- `world_state.py`: `WorldState`. Session-persistent dictionary for interactive states.
- `audio.py`: `AudioManager`. Centralized BGM and SFX controller.
- `inventory.py`: `InventoryUI`. Manages inventory display, tabs, and custom cursor.

## Data Flow
`assets/*.tmj` → `TmjParser` (Resolves Tiled Project Schema) → `MapManager` (Frustum Culling) → `Game` (Rendering Pass)

## Rendering Pipeline
`Game._draw_scene`
1. Background Layers (depth=0)
2. Sorted Entities (Y-Sort via `CameraGroup`)
3. Night Overlay (Alpha blending)
4. Light Halos & Particles (Additive blending)
5. Foreground Layers (depth=1)
6. HUD & Dialogue Overlay
7. Player Emotes
8. Custom Cursor (Absolute Top)

## Key Sprite Groups
- `visible_sprites`: `CameraGroup` with custom Y-Sort drawing.
- `interactives`: `InteractiveEntity` (Chests, doors, levers).
- `npcs`: `NPC` (Wandering AI entities).
- `teleports_group`: `Teleport` (Logical trigger volumes).
- `obstacles_group`: Solid hitboxes for collision detection.
