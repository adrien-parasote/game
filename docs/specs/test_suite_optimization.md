# SPEC: Test Suite Optimization

## Goal
Consolidate and optimize the 23 test files into a smaller, more maintainable set to improve developer velocity and CI efficiency.

## Proposed Changes

### Consolidation Mapping
| Original Files | Target File | Rationale |
|----------------|-------------|-----------|
| `test_engine_core.py`, `test_game_logic.py`, `test_system_bootstrap.py`, `test_asset_manager.py` | `test_engine.py` | Core loop, bootstrap logic and Asset Manager |
| `test_entities_logic.py`, `test_entities_extended.py`, `test_emotes.py` | `test_entities.py` | Entity behaviors and emotes |
| `test_interactions.py`, `test_interactions_extended.py`, `test_audio_interaction.py` | `test_interaction.py` | Player-world interactions |
| `test_ui_and_pickups.py`, `test_ui_extended.py`, `test_ui_ux.py`, `test_inventory.py` | `test_ui.py` | HUD, Inventory, and UI/UX |
| `test_parser.py`, `test_parser_extended.py`, `test_world_infrastructure.py` | `test_parser.py`, `test_map.py`, `test_map_manager.py` | Map parsing, layout, and logic |
| `test_config.py`, `test_graphics.py`, `test_audio.py` | `test_config.py`, `test_graphics.py`, `test_audio.py` | Specialized isolated subsystem tests |

### Specific Focus Areas (Game Logic Deep Dive)
- **`src/engine/game.py` Coverage**: Mock `MapManager` and `Layout` more extensively to test main game loop branches (day/night transitions, scene loading).
- **Asset Manager Edge Cases**: Cover failure modes for missing assets and spritesheet out-of-bounds errors.
- **Refactor Mocks**: Consolidate redundant pygame mocks into a shared `conftest.py` to simplify future test expansion.

### [DELETE] 23 original files after consolidation.
### [NEW] 10 consolidated target files.

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Duplicate setup code | Use pytest fixtures in `conftest.py` | Cleaner tests and easier setup |
| Keep redundant tests | Keep only high-value coverage tests | Faster test runs and lower maintenance |
| Use `unittest` style classes | Use plain `pytest` functions | Less boilerplate and more idiomatic |
| Mock everything | Use integration tests for core systems | Verify actual behavior between components |
| Hardcode file paths in tests | Use `os.path.join` and relative paths | Portability across different environments |
| Leak state between tests (e.g. `Settings`) | Patch or reset global Singletons/Settings | Prevents cascading test failures based on execution order |

## Test Case Specifications
- All existing tests MUST pass after consolidation.
- Coverage must remain at or above **90%** overall (current: 90%, 2026-04-30). Core modules (`inventory_system.py`, `npc.py`, `audio.py`, `map/manager.py`) must maintain 100%.

## Error Handling Matrix
| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Test Failure | `pytest` non-zero exit | Re-run with `-vv` and fix | Revert to individual files if needed |
