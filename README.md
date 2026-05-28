# ⚔️ RPG Tile Engine

[![Python Version](https://img.shields.io/badge/python-3.12+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/built%20with-pygame--ce-orange?style=flat-square&logo=pygame)](https://pyga.me/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square&logo=python&logoColor=white)](https://github.com/astral-sh/ruff)
[![Type Checker: Pyright](https://img.shields.io/badge/types-pyright-yellow?style=flat-square&logo=python&logoColor=white)](https://github.com/microsoft/pyright)
[![Methodology: Stream Coding v6.0](https://img.shields.io/badge/methodology-Stream%20Coding%20v6.0-brightgreen?style=flat-square)](./GEMINI.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

A professional-grade, modular RPG engine built with **Python 3.12** and **Pygame-CE**. This project prioritizes technical excellence, architectural health, and AI-ready documentation via the **Stream Coding v6.0** methodology.

## 🌟 Highlights

- **Technical Excellence**: 10/10 AI-readiness score across 30+ technical specifications.
- **Robust Architecture**: Layered design with structural governance via **Sentrux**.
- **High Performance**: Optimized with frame-level caching, dirty-flag render batching, and surface pooling for flawless 60 FPS performance.
- **Data-Driven**: Full **Tiled (TMX/TSX)** integration with support for custom properties and animated autotiles.
- **Traceability**: Every feature is backed by specs, and every test is linked to its specification via `tc(id)` markers.

## 🛠️ Core Systems

- **🎥 Camera & Rendering**: Smart camera with Y-sorted rendering, efficient tile batching, partial sprite occlusion, and transparent grass-wading effects.
- **✨ Animated Autotiles**: Native support for frame-based animations parsed directly from Tiled assets.
- **💡 Interactive Lighting**: Real-time lighting system with halo calibration, window beam overlays, and flicker mixins.
- **🗺️ World & Navigation**: Seamless map loading, interactive chest UIs, and intra-map teleports with smooth walk transitions.
- **🔊 Spatial Audio**: Adaptive sound manager with multi-channel fading and distance-based spatial panning.
- **💬 Dialogue & NPCs**: Advanced NPC logic with speech bubbles, branching dialogue choices, and pathway patrol patterns.
- **📦 Inventory & Save State**: Data-driven inventory systems, loot drops, and persistent slot saves with PNG screenshot thumbnails.

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
- **Traceability Report**: `python scripts/dev/tc_report.py` (Verify spec coverage)
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
