# SPEC: Test Suite Architecture [Reference]

> Document Type: Implementation


> **Status:** ✅ Completed 2026-05-01 — 436 tests, 92% coverage, 0 regressions.
> This document describes the **actual** domain-based structure. Update when adding new test domains.

## Final Structure

```
tests/
├── conftest.py                   # Global: SDL_VIDEODRIVER=dummy, pygame.init(), mock_spritesheet
├── engine/
│   ├── conftest.py               # mock_game fixture (Game() with _load_map patched)
│   ├── test_game.py              # Game init, event loop, draw, teleport, fullscreen, config/Settings
│   ├── test_game_coverage.py     # TestI18nCoverage (error branches, fallbacks)
│   ├── test_interaction.py       # Proximity, facing, diagonals, NPC/interactive/pickup interactions
│   ├── test_interaction_coverage.py  # InteractionManagerCoverage, TestPickupPersistence
│   ├── test_audio.py             # AudioManager init, play/stop, mute
│   ├── test_lighting.py          # LightingManager, DayNight cycle
│   └── test_loot_table.py        # LootTable parsing, stack splitting
├── entities/
│   ├── test_entities.py          # BaseEntity, NPC AI, Emote, Teleport, PickupItem lifecycle
│   ├── test_base.py              # TestBaseEntityCoverage, TestPlayerCoverage (branches)
│   ├── test_interactive.py       # TestInteractiveCoverage (off_position, col-switch, restore_state)
│   └── test_off_position.py      # TDD suite for animated_decor ON/OFF column switch
├── map/
│   ├── test_map.py               # MapManager, layout, chunk visibility, collision
│   └── test_parser.py            # TMJ parsing, Tiled project schema
├── ui/
│   ├── conftest.py               # ChestUI fixture (mock chest + inventory)
│   ├── test_inventory.py         # InventoryUI: grid, equipment slots, preview, dialogue manager
│   ├── test_inventory_coverage.py    # Drag-and-drop state machine, transfer, icon cache
│   ├── test_inventory_equipment.py   # Equipment equip/unequip/swap, slot validation
│   ├── test_inventory_removal.py     # remove_item(), index guards
│   ├── test_inventory_chest_interaction.py  # Inventory blocked when chest open
│   ├── test_chest.py             # ChestUI full suite: state, draw, D&D, page scroll, transfer
│   └── test_speech_bubble.py     # SpeechBubble render, pagination, font guard
└── graphics/
    └── test_graphics.py          # SpriteSheet loading, dummy fallbacks, grid slicing
```

## Fixture Strategy

| Scope | File | Key Fixtures |
|-------|------|--------------|
| **Global** | `../../tests/conftest.py` | `pygame.init()`, `SDL_VIDEODRIVER=dummy`, `mock_spritesheet` |
| **Engine** | `../../tests/engine/conftest.py` | `mock_game` — `Game()` with `_load_map` patched |
| **UI** | `../../tests/ui/conftest.py` | `chest_ui` — `ChestUI` with mocked `Inventory` + chest data |

## Coverage Expectations

| Module | Target | Notes |
|--------|--------|-------|
| `inventory_system.py` | 100% | Pure logic, easy to test |
| `npc.py`, `audio.py`, `teleport.py`, `emote.py` | 100% | No UI rendering dependencies |
| `map/manager.py`, `spritesheet.py` | 100% | No asset I/O in hot paths |
| `ui/inventory.py`, `ui/chest.py` | ~85-90% | Render-only branches require display; see A-TEST-006 |
| `engine/game.py` | ~90% | Complex init; some branches need real map files |
| **Global floor** | **92%** | Validated on 2026-05-01 |

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Scatter `pygame.init()` per file | Use global `conftest.py` | Drift, env failures |
| Test in a flat `../../tests/` root | Use domain subdirectories | Unfindable on large suites |
| `shutil.copy` + slice extraction in same script | Copy 1:1 separately, slice separately | Slice without `ast.parse()` → `IndentationError` |
| Add coverage tests to existing functional files | Create `test_*_coverage.py` per module | Stays removable and localized |
| Assert `surface.get_size()` after UI `__init__` | Assert `is not None` / `isinstance(Surface)` | `smoothscale` changes size at init |
| Modify `Settings` without restoring | `try/finally: Settings.X = original` | Singleton pollution cascades |

## Migration Notes (for future urbanizations)

When adding a new domain:
1. Create `../../tests/<domain>/` with `__init__.py`
2. Create `../../tests/<domain>/conftest.py` if domain-specific fixtures are needed
3. Run `pytest tests/ --co -q` to verify count before deleting old files
4. Use `shutil.copy()` for 1:1 migrations; Python script with `ast.parse()` validation for splits
5. Delete old files only after `pytest tests/ -q` shows zero regressions

