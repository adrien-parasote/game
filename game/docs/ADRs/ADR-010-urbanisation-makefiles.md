# Urbanization Plan: Makefiles & Environments

## Goal
Simplify the project infrastructure to have **only one virtual environment** and **only one Makefile**.

## Proposed Changes

### 1. Centralization of Dependencies
Instead of having `game/requirements.txt` and `tools/requirements.txt`, we will have a single `requirements.txt` at the root.
We will take this opportunity to clean up obsolete dependencies from the old `asset_convertor` (`dearpygui`, `opensimplex`) and add `customtkinter`.

#### [NEW] requirements.txt
```txt
# Core Dependencies
pygame-ce==2.5.7
numpy
Pillow
customtkinter==5.2.2
PyYAML

# Development & Testing
pytest==9.0.3
pytest-cov==6.1.0
ruff==0.9.9
pyright==1.1.396
pyobjc-framework-Cocoa; sys_platform == 'darwin'
```
#### [DELETE] game/requirements.txt
#### [DELETE] tools/requirements.txt

---

### 2. Single Makefile at the Root
A single `Makefile` to orchestrate everything. It will create a single `venv` at the root and use the global configurations already present in `pyproject.toml`.

#### [MODIFY] Makefile
The new Makefile will contain:
- `make setup`: Creates the root venv and installs the global `requirements.txt`.
- `make run-game`: Launches the game.
- `make run-tools`: Launches the procedural generator.
- `make test`: Runs `pytest` (which already covers both `game/` and `tools/`).
- `make lint` / `make typecheck`: Utility commands for `ruff` and `pyright`.
- `make clean`: Cleans caches and the `venv`.

#### [DELETE] game/Makefile
#### [DELETE] tools/Makefile
