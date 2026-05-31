> Document type: Implementation

# Implementation Plan: Repository Restructuring

## Covers: Blueprint F1, F2, F3, F4, F5

## 1. Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Use `git mv` instead of `mv` to preserve file history. Run tests after moving files to verify paths. |
| **Ask first** | Deleting any file or folder not explicitly mentioned in this spec. |
| **Never do** | Modify the internal logic of the game or tooling code. We are only fixing imports/paths. |

## 2. Assumptions

| Assumption | Risk | Validation Strategy | Source Type | Status |
|------------|------|---------------------|-------------|--------|
| `src/` contains only game code | HIGH | Confirmed by user | SHOW (verified via user) | VERIFIED |
| Tests are cleanly separated | MEDIUM | Exhaustive mapping defined in spec | SHOW (verified via `ls`) | VERIFIED |
| Assets are strictly in `/assets` | LOW | Verified via `du -sh *` | SHOW (verified via `du`) | VERIFIED |
| Python scripts in `scripts/` are tools | HIGH | Mapped to `/tools/` below based on content | SHOW (verified via `ls`) | VERIFIED |
| `gameplay.json` & `settings.json` belong to game | MEDIUM | Will move them to `/game/` | TELL | VERIFIED |
| No hardcoded absolute path strings in code | MEDIUM | Static scan of imports and file paths | SHOW (verified via grep) | VERIFIED |

## 3. Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|--------------|-----------|------------------|
| 1 | Moving without Git | Using standard `mv` or drag-and-drop instead of `git mv` breaks history | Always use `git mv` |
| 2 | Hardcoded Absolute Paths | Updating paths in code to absolute paths | Always use relative paths |
| 3 | Mixing Domains | Leaving a script that only builds the game in the `/tools` folder | Strictly isolate tools and game |
| 4 | Git LFS Activation | Trying to initialize Git LFS | The assets are currently 8.5MB, so this is explicitly excluded |
| 5 | Blind Path Updates | Doing a global find-and-replace for "src/" | Update paths individually and test |
| 6 | Stale Config Files | Leaving workspace configuration files (`pyproject.toml`, `pyrightconfig.json`) unchanged | Always update environment configurations to map the new domain layout |

## 4. Test Case Specifications

### Linked Test Functions
| TC ID | Spec Target | Target Component | Behavior |
|-------|-------------|------------------|----------|
| TC-001 | § "Proposed Changes" | Game Tests | Game core module logic tests pass |
| TC-002 | § "Proposed Changes" | Game Tests | Game rendering logic tests pass |
| TC-003 | § "Proposed Changes" | Tools Tests | Map editor logic tests pass |
| TC-004 | § "Proposed Changes" | Tools Tests | Importer logic tests pass |
| TC-005 | § "Proposed Changes" | Tools Tests | Exporter logic tests pass |
| IT-001 | § "Proposed Changes" | Docs | Verify `/game/docs/` and `/tools/docs/` exist and contain files |
| IT-002 | § "Proposed Changes" | Assets | Verify `/assets/` remains intact |
| IT-003 | § "Proposed Changes" | Build | Build script completes without file not found errors |
| IT-004 | § "Proposed Changes" | Workspace | Pyright static analysis passes with zero new import failures |
| IT-005 | § "Proposed Changes" | Tests Discovery | Pytest successfully discovers and executes both game and tools test suites |

## 5. Error Handling Matrix

| Scenario | Error State / Behavior | Mitigation / Resolution |
|----------|------------------------|-------------------------|
| `git mv` fails on a locked file | Git error `fatal: rename failed` | Ensure the file is not open in an editor or locked by a process, then retry. |
| Tests fail after move | `ModuleNotFoundError` or similar | Identify the broken relative import, calculate the new relative path based on the new domain isolation, and update the code or adjust pythonpath. |
| Build script cannot find assets | Missing asset exception at runtime | Update the asset base path constant in the game configuration to point to `../assets/` instead of `./assets/`. |
| Pytest cannot find tests | `ValueError: PytestConfigWarning` or zero tests run | Ensure root `pyproject.toml` lists the plural `"game/tests"` and `"tools/tests"` directories under `testpaths`. |

## 6. Deep Links
- [Strategic Blueprint](./STRATEGIC_BLUEPRINT.md#L1)
- [ADR 0001: Architecture](./adr/0001-repository-architecture.md#L1)

## Proposed Changes

### 1. Sequential Move Commands (Must run exactly in this order)
To avoid directory nesting issues (e.g. creating `tools/src/tools` instead of renaming `tools`):
```bash
# 1. Create domain wrapper structures
mkdir -p game tools/src

# 2. Move source modules
git mv src game/src
git mv tools/asset_creator tools/src/asset_creator
git mv tools/__init__.py tools/src/__init__.py

# 3. Move other folders
git mv tests game/tests
git mv docs game/docs
git mv gameplay.json game/gameplay.json
git mv settings.json game/settings.json
```

### 2. Workspace & Tooling Configuration Updates

#### [MODIFY] [pyproject.toml](file:///Users/adrien.parasote/Documents/perso/game/pyproject.toml)
Modify Pytest settings to target the domain test suites and locate domain source roots:
```toml
[tool.pytest.ini_options]
testpaths = ["game/tests", "tools/tests"]
pythonpath = ["game", "tools/src"]
```

#### [MODIFY] [pyrightconfig.json](file:///Users/adrien.parasote/Documents/perso/game/pyrightconfig.json)
Map Pyright lookup paths to the restructured directories to preserve type safety:
```json
{
  "pythonVersion": "3.12",
  "pythonPlatform": "Darwin",
  "extraPaths": ["game", "tools/src"],
  "exclude": [
    "**/__pycache__",
    ".venv",
    "venv",
    "**/tests",
    ".agents",
    "scripts",
    "build",
    "dist"
  ],
  "typeCheckingMode": "basic",
  "reportMissingModuleSource": "none",
  "reportMissingImports": "warning",
  "reportAttributeAccessIssue": "none"
}
```

### 3. Build & Developer Utility Script Fixes

#### [MODIFY] [scripts/build/release.py](file:///Users/adrien.parasote/Documents/perso/game/scripts/build/release.py)
Point paths and Git commands to `/game/settings.json`:
- Line 51: Update check to `"M game/settings.json"`
- Line 71: Update Git stage command to `git add game/settings.json`
- Line 92: Update settings path resolution to `os.path.join(root_dir, "game", "settings.json")`

#### [MODIFY] [scripts/dev/tc_report.py](file:///Users/adrien.parasote/Documents/perso/game/scripts/dev/tc_report.py)
- Line 19: `SPECS_DIR = "game/game/docs/specs"` (after docs migration)
- Line 20: `TRACEABILITY_OUTPUT = "game/docs/traceability.md"`
- Line 45: Scan both domain test directories:
  ```python
  test_dirs = ["game/tests", "tools/tests"]
  ```

#### [MODIFY] [scripts/dev/profile_game.py](file:///Users/adrien.parasote/Documents/perso/game/scripts/dev/profile_game.py)
- Line 9: Update `sys.path` append target to resolve `/game/` package directory:
  ```python
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "game")))
  ```

#### [MODIFY] [scripts/dev/check_lengths.py](file:///Users/adrien.parasote/Documents/perso/game/scripts/dev/check_lengths.py)
- Line 22: Update function target directory:
  ```python
  check_functions("game/src")
  ```

### 4. Documentation & READMEs

#### [MODIFY] [README.md](file:///Users/adrien.parasote/Documents/perso/game/README.md)
Refactor global Monorepo entrypoint to detail the domain separation.

#### [NEW] [game/README.md](file:///Users/adrien.parasote/Documents/perso/game/game/README.md)
Instructions on how to build, run, and test the game.

#### [NEW] [tools/README.md](file:///Users/adrien.parasote/Documents/perso/game/tools/README.md)
Pipeline, asset creation, and autotiling workflow documentation.

### 5. Cleanups & Deletions
- `[DELETE]` `src/` at root
- `[DELETE]` `tests/` at root
- `[DELETE]` `tools/asset_creator/` and `tools/__init__.py` at root
- `[DELETE]` `docs/` at root
- `[DELETE]` `gameplay.json` at root
- `[DELETE]` `settings.json` at root

## Verification Plan
1. Use `git status` to ensure all moves are tracked as "Renamed" to preserve historical identity.
2. Run static analysis `pyright` to ensure zero unresolved imports.
3. Run `pytest` at the root and verify that tests in both `/game/tests` and `/tools/tests` are executed.
4. Execute `python scripts/dev/tc_report.py --markdown` to verify spec↔test traceability matrix generation remains fully intact.
5. Dry-run `python scripts/build/release.py 0.6.2 --dry-run` to verify bump logic.
