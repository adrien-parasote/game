# ⚔️ RPG Tile Engine

[![Python Version](https://img.shields.io/badge/python-3.12+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/built%20with-pygame--ce-orange?style=flat-square&logo=pygame)](https://pyga.me/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square&logo=python&logoColor=white)](https://github.com/astral-sh/ruff)
[![Type Checker: Pyright](https://img.shields.io/badge/types-pyright-yellow?style=flat-square&logo=python&logoColor=white)](https://github.com/microsoft/pyright)

Welcome to the **RPG Tile Engine** monorepository. This repository houses a professional-grade 2D RPG engine and its associated procedural asset creation tooling.

## 🏗️ Repository Architecture

The project has been transitioned to a multi-domain monorepo architecture to cleanly separate the game engine from development tooling, ensuring isolation, simplified onboarding, and independent evolution.

- **[`game/`](./game)**: The core RPG engine built with Pygame-CE. Contains the game source code, entity systems, rendering, tests, and its specific documentation (`game/docs/`).
- **[`tools/`](./tools)**: Procedural generation and development tools, such as the `asset_creator` (Dear PyGui), along with its specific documentation (`tools/docs/`).
- **[`assets/`](./assets)**: Shared global assets (images, audio, language files) used by both the game and the tools.
- **[`scripts/`](./scripts)**: Build pipelines, release management, and development scripts.

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Make** (optional, but recommended)

### Quick Start
To work on a specific domain, navigate to its directory:
```bash
# For the game engine:
cd game
make setup  # Initialize venv and install dependencies
make run    # Start the game engine

# For the asset tools:
cd tools
make setup  # Initialize venv and install dependencies
make run    # Start the asset creator tool
```

### Manual Setup
If you prefer not to use Make:
1. `cd game` (or `cd tools`)
2. `python -m venv venv`
3. Activate: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
4. `pip install -r requirements.txt`

## 🛠️ Domains

### [The Game Engine](./game)
A data-driven, tile-based 2D engine featuring:
- Smart camera with Y-sorted rendering
- Animated autotiles from TMX/TSX maps
- Interactive lighting and spatial audio
- Component-based entities (NPCs, Player, Inventory)

See the [Game README](./game/README.md) for details.

### [Asset Tools](./tools)
Standalone development tools featuring:
- A Dear PyGui procedural tileset generator
- Wang blob autotile transformations
- Color ramp generation

See the [Tools README](./tools/README.md) for details.

## 🧪 Quality & Verification

We enforce strict quality gates across the monorepo:
- **Testing**: Run tests with `make test` in the root, or directly in `game/` and `tools/`.
- **Linting & Formatting**: `ruff check .`
- **Type Checking**: `pyright`
- **Traceability**: `python scripts/dev/tc_report.py` validates spec coverage.

## 📜 License
MIT
