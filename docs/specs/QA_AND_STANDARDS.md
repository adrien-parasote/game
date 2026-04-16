# QA and Testing Standards

This document defines the quality gates and standards for the RPG Tile Engine.

## 1. Quality Gates

| Gate | Target | Tool |
|------|--------|------|
| **Unit Test Coverage** | >= 80% | `pytest-cov` |
| **Linting** | Zero Errors | `ruff` / `flake8` |
| **Static Analysis** | Zero High Risk | `bandit` |

## 2. Logging Level Strategy

| Level | Description | Example Events |
|-------|-------------|----------------|
| **DEBUG** | Mathematical results | Camera offset calc, raw input bits |
| **INFO** | Core lifecycle | Engine init, map load, settings load |
| **WARNING** | Performance dip | FPS < 30, fallback to defaults |
| **ERROR** | Asset failure | Missing entity texture, non-fatal asset load |
| **CRITICAL** | System failure | Pygame init fail, missing core map file |

## 3. Portability & Maintenance

- **Config**: Always use `Settings` class; never access `settings.json` directly from logic.
- **Dependencies**: Keep `requirements.txt` updated with pinned versions.
- **Paths**: Use `os.path` for cross-platform compatibility (Windows/Linux/Mac).
- **Automation**: Standard developer workflows handled via `Makefile` or similar.

## 4. Deep Links
- [STRATEGY.md](STRATEGY.md)
- [ENGINE_CORE.md](ENGINE_CORE.md)
