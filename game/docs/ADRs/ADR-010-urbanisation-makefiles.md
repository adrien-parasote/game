# ADR-010: Urbanization Plan — Makefiles & Environments

## Status: ✅ Accepted

## Context

The project had grown to a point where each sub-project (`game/`, `tools/`) maintained its own `requirements.txt`, its own `Makefile`, and its own virtual environment. This duplication created unnecessary maintenance overhead, inconsistent dependency versions across sub-projects, and friction when running the full test suite or switching between development contexts.

The core sub-projects (`game/` for the game engine, `tools/` for the asset converter) share many dependencies (`pytest`, `pygame-ce`, `ruff`, `pyright`) and should be tested from a single root venv.

## Decision

Simplify the project infrastructure to have **only one virtual environment** and **only one Makefile** at the workspace root.

### 1. Centralization of Dependencies

Instead of `game/requirements.txt` and `tools/requirements.txt`, a single `requirements.txt` is maintained at the root. This removes obsolete dependencies from the old `asset_convertor` (`dearpygui`, `opensimplex`) and adds `customtkinter`.

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

Files removed: `game/requirements.txt`, `tools/requirements.txt`.

### 2. Single Makefile at the Root

A single `Makefile` orchestrates everything. It creates a single `venv` at the root and uses the global configurations in `pyproject.toml`.

| Target | Description |
|--------|-------------|
| `make setup` | Creates the root venv and installs the global `requirements.txt` |
| `make run-game` | Launches the game |
| `make run-tools` | Launches the procedural generator |
| `make test` | Runs `pytest` (covers both `game/` and `tools/`) |
| `make lint` / `make typecheck` | Utility commands for `ruff` and `pyright` |
| `make clean` | Cleans caches and the `venv` |

Files removed: `game/Makefile`, `tools/Makefile`.

## Consequences

- **Single venv**: All developers and CI use one environment — no drift between sub-project dependency versions.
- **Simplified onboarding**: `make setup && make test` is the full setup ritual.
- **Cross-project tests**: `pytest` covers both `game/tests/` and `tools/tests/` from the root in one command.
- **Migration cost**: Path references in existing scripts and CI configs must be updated to use root-relative paths.
