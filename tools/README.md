# Asset Convertor Tools

This directory contains standalone tools and procedural generation pipelines used for the RPG Tile Engine.
These tools are decoupled from the game engine to prevent dependency pollution and ensure that the game runtime remains lightweight.

## 📂 Tools Available

### Asset Convertor (`src/asset_convertor/`)
A procedural tileset generator with both a CLI and a Dear PyGui (v2) graphical interface.
It transforms base autotile templates (like 47-tile Wang blobs) into styled game-ready TSX/PNG assets.
- Procedural noise and detail application
- OKLCh color palette generation
- Direct export to Tiled formats

### Asset Processors (`src/assets/`)
Scripts for handling legacy asset structures (e.g. `process_banners.py`, `flat_wall_to_diagonal.py`).

### Calibration (`src/calibration/`)
Visual calibration scripts for halo effects and light rendering (`calibrate_halos.py`).

## 🚀 Usage
Execute tools from the `tools/` directory using the dedicated Makefile:

```bash
# Initialize virtual environment and install dependencies
make setup

# Launch the Asset Convertor GUI
make run

# Alternatively, use the Python module directly if in the virtual environment:
# python -m tools.src.asset_convertor.cli generate grass --seed 42
```

## 📚 Documentation
For specifications, architecture decisions (ADRs), and research related to the tooling domain, see the local `docs/` folder.

## 🧪 Testing

```bash
# Run all tool-related tests
make test
```
