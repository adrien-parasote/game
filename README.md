# ⚔️ RPG Tile Engine & The Heir's Awakening

[![Python Version](https://img.shields.io/badge/python-3.12+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/built%20with-pygame--ce-orange?style=flat-square&logo=pygame)](https://pyga.me/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square&logo=python&logoColor=white)](https://github.com/astral-sh/ruff)

Welcome to the **The Heir's Awakening** "Meta-Workspace". This root directory is the entry point for developers, centralizing the game engine, procedural generation tools, and our AI agent configurations (Stream Coding).

> 📖 **Players, Writers, and Game Designers:**  
> Everything regarding the story, mechanics (GDD), global vision, and roadmap of the game can be found on our **[Official GitHub Wiki](https://github.com/adrien-parasote/game/wiki)**.

---

## 🏗️ Project Architecture

The project adopts a strict separation between the technical engine and business documentation (Lore/GDD) to keep the code clean and prevent cognitive overload.

- **[`game/`](./game)**: The RPG engine built with Pygame-CE. Contains the source code, entities, rendering, tests, and *strictly technical* documentation (AI specifications, ADRs).
- **[`tools/`](./tools)**: Standalone development tools (Procedural tileset generator built with Dear PyGui).
- **[`assets/`](./assets)**: Shared assets (images, audio, data) used by both the game and the tools.
- **[`scripts/`](./scripts)**: Build pipelines, release management, and quality checks.
- **`game-wiki/`** *(Not versioned here)*: If you have cloned it, this "ghost" folder (ignored by Git) contains the local wiki allowing you to edit human-facing documentation side-by-side with the code.

---

## 🚀 Getting Started (Developers)

### Prerequisites
- **Python 3.12+**
- **Make** (optional, but recommended)

### Quick Start
To work on a specific area, navigate to its directory:
```bash
# For the game engine:
cd game
make setup  # Initializes the venv and installs dependencies
make run    # Runs the game

# For the procedural tools:
cd tools
make setup
make run
```

### Manual Installation (Without Make)
1. `cd game` (or `cd tools`)
2. `python -m venv venv`
3. Activation: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
4. `pip install -r requirements.txt`

---

## 🧪 Quality & AI (Stream Coding)

This project is actively developed with AI agents following a strict methodology (Stream Coding).

- **Testing**: Run `make test` at the root, or within `game/`.
- **Linting & Formatting**: `ruff check .`
- **AI Validation**: `verify.py` and `spec_conformance.py` ensure that generated code conforms 100% to the specifications (`game/docs/specs/`).
- **Git Sentinels**: Never bypass hooks without a valid reason. Commits are formatted semantically.

---

## 📜 License
MIT
