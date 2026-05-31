# RPG Tile Engine - Game Core

This directory contains the core source code and test suite for the RPG Tile Engine.

## 📂 Structure

- `src/`: The game engine source code. This domain is strictly reserved for the game engine and its runtime systems. Tools and asset pipelines have been moved to the root `/tools/` directory.
- `tests/`: Unit and integration tests for the game engine.
- `assets/`: Symbolic or actual references to the root `assets/` directory where game data is stored.
- `settings.json` / `gameplay.json`: Runtime configuration files for the engine.

## 🚀 Running the Game

If you have set up the virtual environment from the workspace root:

```bash
# Set up virtual environment and install dependencies
make setup

# Run the game
make run

# Run tests
make test
```

## 🛠️ Systems

- **Engine Core**: Main game loop, time systems, and system orchestration.
- **Rendering**: Custom `RenderManager` supporting partial occlusion, Y-sorting, and composite surfaces.
- **Map System**: Custom parsers for Tiled (TMX/TSX) maps, including animated autotiles.
- **Entities**: Player, NPCs, interactive objects, and pick-ups.
- **UI**: Inventory, HUD, dialogs, and chest interaction screens.

For architectural blueprints and specifications, refer to the `docs/` folder in this directory.
