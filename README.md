# RPG Tile Engine

A modular, scalable tile-based RPG engine skeleton built with Python and Pygame-CE.

## 🚀 Portability & Setup

This project is designed to be easily shared. Follow these steps to set up the environment on a new machine.

### Prerequisites
- **Python 3.9+** installed on your system.

### Quick Start (Linux / macOS)
If you have `make` installed:
```bash
make setup
make run
```

### Manual Setup (All Systems)
If you don't have `make` or want to do it manually:

1. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   ```
2. **Activate the environment:**
   - Linux/macOS: `source venv/bin/bin/activate`
   - Windows: `venv\Scripts\activate`
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the game:**
   ```bash
   python src/main.py
   ```

## 🧪 Testing
To run the automated test suite:
```bash
make test
# OR
pytest tests/
```

## 📂 Architecture
- `src/engine/`: Main game loop and system management.
- `src/map/`: Tile data and coordinate layouts (Orthogonal).
- `src/entities/`: Base classes, player logic, and Y-sorted rendering.
- `docs/specs/`: Strategic and technical documentation.

## 📜 License
MIT
