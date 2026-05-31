# Goal Description

Start the ⚡ BUILD execution stage for the RPG Tile Engine.
Following the `Vertical Slice` methodology from Stream Coding, we will begin by implementing **Slice 1: Engine Core & Assets**. This slice forms the foundation of the game architecture upon which all other systems (maps, entities, UI) depend. 

This slice will implement the specifications defined in:
1. `docs/game/specs/engine-core.md` (Game Loop, State Manager, Settings)
2. `docs/game/specs/asset-i18n.md` (Asset loading, caching, i18n localization)

## User Review Required

> [!IMPORTANT]
> The Stream Coding orchestrator requires explicit approval of this plan before entering the TDD cycle. Please review the proposed components below.

## Open Questions

> [!WARNING]
> No UI tools or external dependency managers (poetry/uv) are specified for initialization in the specs. Should I initialize the project using a standard `requirements.txt` and `pygame-ce` before running the TDD tests, or is there an existing tooling environment setup command you prefer I run?
> *Note: The user commanded "ne touche surtout pas au tooling !!", so I will assume no changes to external tooling configurations are allowed and I should only work within `src/` and `tests/`.*

## Proposed Changes

### Configuration & Entry Point
- **[NEW]** `src/config.py`: Global constants, paths, and default settings.
- **[NEW]** `src/main.py`: Bootstrapper that initializes pygame-ce and creates the `Game` instance.

---

### Asset & Localization (asset-i18n.md)
The asset subsystem must be ready first so the core loop can load resources.
- **[NEW]** `src/engine/asset_manager.py`: Implements `AssetManager` with Pygame surface caching, lazy-loading, and scaling.
- **[NEW]** `src/engine/i18n_manager.py`: JSON-based localization dictionaries for multiple languages.

---

### Engine Core (engine-core.md)
The core loop and state machine orchestrating the game lifecycle.
- **[NEW]** `src/engine/game.py`: The `Game` class with the main `dt` loop, event polling, rendering abstraction.
- **[NEW]** `src/engine/game_state_manager.py`: State machine orchestrator (`MAIN_MENU`, `PLAYING`, `PAUSED`).
- **[NEW]** `src/engine/input_handler.py`: Abstraction for keyboard/controller input mapping.

---

### Tests
- **[NEW]** `tests/engine/test_game.py`: Unit tests for the game loop and state transitions.
- **[NEW]** `tests/engine/test_asset_manager.py`: Tests for asset caching, missing asset fallbacks, and scaling.
- **[NEW]** `tests/engine/test_i18n.py`: Tests for localization dictionary lookups and missing key fallbacks.

## Verification Plan

### Automated Tests
1. **TDD Gate Check**: Generate `.tdd_lock` via `python .agents/skills/verification-loop/scripts/tdd_check.py . --module src/engine/`
2. **Pytest Run**: Execute `pytest tests/engine/` to ensure all core tests pass.
3. **Verification Loop**: Run `verify.py` on the `src/engine/` module to confirm zero lint, type, or structural issues.

### Manual Verification
- We will write a minimal `main.py` that opens a Pygame window, shifts between `MAIN_MENU` and `PLAYING` states, and loads a test asset, verifying that the core loop is functional and runs at the target frame rate.
