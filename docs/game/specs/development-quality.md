# Technical Specification — Development Quality, Automation & Verification [Reference]

> **Document Type:** Implementation
> **Source Files:** `scripts/build/release.py`, `src/config.py`, `src/engine/game.py`, `src/entities/groups.py`, `tests/conftest.py`

This reference specification consolidates the development quality gates, domain-driven test suite architectures, version release pipelines, internal debugging configurations, and multilingual translation dictionaries.

---

## 1. Development Quality Gates & Verification

All code changes are governed by three progressive gating checks to guarantee codebase health:

### 1.1 Spec Gate (AI-Readiness)
Before writing code, the implementation specification must achieve a perfect **10/10 Understandability Score** checked by automated static pre-checks.
- **Mandatory Sections**: Every spec must contain:
  1. Anti-patterns (Explicit "DO NOT" practices).
  2. Test Case Specifications (TDD definitions).
  3. Error Handling Matrix (Precise exception behaviors).
  4. Deep Links (Direct file and line number mapping).

### 1.2 TDD Gate (Test-First Verification)
No production or business logic code may be modified or created without a corresponding, pre-existing failing (RED) unit or integration test. This prevents confirmation bias and enforces proper coverage interfaces.

### 1.3 Verify Gate (Pre-Commit / Pre-PR)
Runs comprehensive system verification prior to merge:
- **Linting & Formatting**: Zero syntax errors, zero unused imports, strict compliance.
- **Static Security Analysis**: Mandatory scan using `bandit -r src/` with zero high-risk findings.
- **Test Pass Rate**: 100% pass rate in the complete test suite.
- **Coverage Minimums**: Global coverage must exceed **90%** of all lines, with **100%** coverage enforced on the following critical modules:
  - `inventory_system.py`, `npc.py`, `audio.py`, `map/manager.py`, `spritesheet.py`, `emote_sprite.py`, `teleport.py`.

> **Project-specific override:** This project targets 90% global coverage (stricter than the Stream Coding default of 80%) due to the critical nature of game engine code. Critical modules (player movement, save/load, collision) target 100%.

---

## 2. Technical & Architectural Standards

### 2.1 Multi-Tier Logging Strategy
The engine utilizes a standardized logging hierarchy across all modules:

| Level | Description | Example Event |
|-------|-------------|---------------|
| **DEBUG** | Mathematical and coordinate sweeps | Viewport offset calculations, raw input scans |
| **INFO** | Core system lifecycle updates | Pygame init, map loadings, settings changes |
| **WARNING** | Performance anomalies | FPS drops < 30, fallback assets used |
| **ERROR** | Recoverable operational failures | Missing character textures, single asset load failure |
| **CRITICAL** | Fatal runtime exceptions | SDL initialization crash, map file corruption |

### 2.2 Core Development Principles
- **Settings Portability**: All values and constants must be mapped to the `Settings` class. Raw file paths, screen sizes, or UI variables must never be accessed directly in logic.
- **Framerate Physics Stability**: Game loops must clamp update tick sizes using `MAX_DT_CLAMP = 10.0` inside `update()` to prevent collision and physics breakdowns after debugging breaks.
- **Cross-Platform Compatibility**: All file access, directory routing, and asset loads must be constructed using `os.path` operations, preventing Windows/macOS path failures.

---

## 3. Domain-Driven Test Suite Architecture

The test suite is structured around clean domain layers to match engine modules:

```
tests/
├── conftest.py                       # Global: dummy video drivers, pygame.init(), spritesheet mocks
├── engine/
│   ├── conftest.py                   # mock_game fixture (Game() with _load_map patched)
│   ├── test_game.py                  # Game loops, event handling, teleport, settings
│   ├── test_audio.py                 # AudioManager controls and volumes
│   ├── test_lighting.py              # LightingManager overlays and slants
│   └── test_loot_table.py            # Loot table parser and stack split validations
├── entities/
│   ├── test_entities.py              # NPCs, emotes, items lifecycle
│   └── test_interactive.py           # On/Off state switches and column restorations
├── map/
│   ├── test_map.py                   # MapManager chunk rendering and layout grids
│   └── test_parser.py                # TMJ parser and Tiled compatibility checks
├── ui/
│   ├── conftest.py                   # UI mock inventories and chests
│   ├── test_inventory.py             # Inventory UI grid and drag-and-drop state machines
│   └── test_chest.py                 # Chest UI draw loops and page increments
└── graphics/
    └── test_graphics.py              # Spritesheet loaders and fallback dummy grids
```

- **Global conftest**: Initializes Pygame in a headless mode (`dummy` video driver) to allow execution inside GUI-less CI environments.
- **Isolation Rule**: Standard settings mutated in a test must be restored inside a try/finally block or context manager to prevent test suite state pollution.

---

## 4. SemVer Release Automation

Version updates are automated via the `scripts/build/release.py` workflow:
1. **Pre-checks**:
   - Verification that the working directory is clean (using git status --porcelain).
   - Semantic Versioning check of requested tag.
   - Local and remote validation that the target tag does not already exist.
2. **Version Bump**:
   - Modifies the `"version"` attribute inside `settings.json` with a 2-space indentation format.
3. **Git Integration**:
   - Commits the updated `settings.json` under `chore: bump version to <version>`.
   - Creates a local Git tag corresponding to the version.
   - Pushes both the active branch and the new tag safely to the remote origin.
   - **Rule**: Force pushing (`--force`) is strictly forbidden.

---

## 5. Game Debug Features

The engine contains comprehensive features for testing and coordinate layout verification:

### 5.1 Debug Room & Spawns
- **Activation**: When `Settings.DEBUG == True` is set via `settings.json`, the engine overrides the default map loading, opening `99-debug_room.tmj` instead of normal spawn zones.
- **Spawn Rules**: Searches for objects with `is_initial_spawn: True` (or fallback `is_initial_pawn: True`) to position the player character instantly.

### 5.2 Hitbox Draw Overlays
- **Hitbox Drawing**: Hitboxes are drawn as transparent, colored outline rectangles over player, NPC, and interactive entity borders.
- **Draw Location**: Hitboxes must only be drawn within `CameraGroup.custom_draw` (never in `Game._draw_scene`), ensuring proper sorting and alignment with camera view offsets.
- **Performance Guard**: Drawing only occurs when `DEBUG` is active, completely eliminating graphics pipelines overhead in production builds.

---

## 6. Documentation Urbanization & Translation

To support clean maintenance, all documents under `docs/` must follow strict translation, vocabulary, and file link rules:

### 6.1 Translation Dictionary
All technical features and in-game names must be mapped uniformly:

| French Original | English Urbanized | Technical Context / Rationale |
|-----------------|-------------------|--------------------------------|
| `Castel` | `Castel` | Named in-game castle/hub (keep capitalized). |
| `Majordome` | `Butler` | Player's mechanical companion (`02-butler.png`). |
| `Sauvegarde` | `Save` / `Save System` | Mapped to `SaveManager` and slot persistence. |
| `Miniature` | `Thumbnail` | Square 120x120px screen crop for save slots. |
| `Menu de pause` | `Pause Screen` | Mapped to `PauseScreen` UI class. |
| `Bouton retour` | `Back Button` | Renders with I18n translation `menu.back`. |
| `Pont-levis` / `Pont` | `Drawbridge` / `Bridge` | Mapped to the `bridge` interactive entity subtype. |
| `Éther` / `Éthéré` | `Ether` / `Ethereal` | Magical energy currency used in character scaling. |
| `Sphérier` | `Sphere Grid` | Node-based character progression system. |

### 6.2 Reference Integrity Constraints
- **Absolute Paths Forbidden**: All internal spec links must be relative paths (`./filename.md`). Machine-specific directory prefixes (e.g. `file:///Users/...`) are rejected.
- **Code Purity**: Python class names, property metrics (e.g. `is_on`), and test case IDs (e.g. `UT-ILT-01`) must not be translated.

---

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Skip the TDD Gate | Write failing RED tests first | Prevents false-positive passes |
| Draw hitboxes in the draw_scene loop | Draw inside custom_draw | Hitboxes drift from Y-sorting and camera offsets |
| Use machine-specific absolute file links | Use relative Markdown links | Absolute links break between machines and CI |
| Force push tags on release | Verify existing remote tags | Force pushing destroys remote Git history |
| Modify settings globally during tests | Use context managers to restore | Pollution cascades failures to subsequent tests |

---

## 8. Test Case Specifications

### 8.1 Release Automation Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-REL-01 | `test_validate_version` | `../../tests/scripts/build/test_release.py` |
| TC-REL-02 | `test_update_version` | `../../tests/scripts/build/test_release.py` |
| TC-REL-03 | `test_run_git_commands` | `../../tests/scripts/build/test_release.py` |

---

## 9. Deep Links
- **Release script**: [release.py L1](../../scripts/build/release.py#L1)
- **Config / Settings**: [config.py L1](../../src/config.py#L1)
- **Game loop**: [game.py L1](../../src/engine/game.py#L1)
- **Test conftest (global)**: [conftest.py L1](../../tests/conftest.py#L1)
- **Release tests**: [test_release.py L1](../../tests/scripts/build/test_release.py#L1)
