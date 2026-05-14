# ⚔️ RPG Tile Engine

A professional-grade, modular RPG engine built with **Python 3.12** and **Pygame-CE**. This project prioritizes technical excellence, architectural health, and AI-ready documentation via the **Stream Coding v6.0** methodology.

## 🌟 Highlights

- **Technical Excellence**: 10/10 AI-readiness score across 30+ technical specifications.
- **Robust Architecture**: Layered design with structural governance via **Sentrux**.
- **Data-Driven**: Full **Tiled (TMX/TSX)** integration with support for custom properties and animated autotiles.
- **Traceability**: Every feature is backed by specs, and every test is linked to its specification via `tc(id)` markers.

## 🛠️ Core Systems

- **🎥 Camera & Rendering**: Smart camera with Y-sorted rendering and efficient tile batching.
- **✨ Animated Autotiles**: Native support for frame-based animations parsed directly from Tiled assets.
- **💡 Interactive Lighting**: Real-time lighting system with halo calibration and environmental blending.
- **💬 Dialogue & NPCs**: Advanced NPC logic with speech bubbles and branching interaction states.
- **📦 Inventory & Loot**: Data-driven inventory system with loot table support and persistent save states.
- **🗺️ World System**: Seamless map transitions and interactive object handling.

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Make** (optional, but recommended)

### Quick Start
```bash
make setup  # Initialize venv and install dependencies
make run    # Start the engine
```

### Manual Setup
1. `python -m venv venv`
2. Activate: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
3. `pip install -r requirements.txt`
4. `python src/main.py`

## 🧪 Quality & Verification

We maintain an **80%+ test coverage** and enforce strict quality gates.

- **Run Tests**: `make test` or `pytest tests/`
- **Traceability Report**: `python scripts/tc_report.py` (Verify spec coverage)
- **Linting**: `ruff check .`
- **Static Analysis**: `pyright`

## 📂 Architecture Overview

- `src/engine/`: Core loop, event management, and system orchestration.
- `src/map/`: Tiled parser, tile animations, and coordinate systems.
- `src/entities/`: Component-based entity system (Player, NPCs, Interactives).
- `src/systems/`: Specialized logic (Lighting, Audio, Dialogue, UI).
- `docs/specs/`: **Source of Truth**. Technical and strategic documentation.
- `.agents/`: Stream Coding methodology, skills, and architectural rules.

## 📜 Methodology: Stream Coding v6.0

This project follows a strict documentation-first approach. No code is implemented without a validated specification.
- **Discover Gate**: Mandatory research before strategy.
- **Spec Gate**: 10/10 AI-readiness check.
- **TDD Gate**: Implementation follows test case definitions.
- **Verify Gate**: Deterministic verification of all quality metrics.

## 📜 License
MIT
