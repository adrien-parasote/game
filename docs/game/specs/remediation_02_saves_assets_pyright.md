# Spec — Steps 5 to 7: Save Path + AssetManager UI + Pyright

> Document Type: Implementation
> **Covers:** Save-Path, AssetManager-UI, Pyright-basic
> **Blueprint Reference:** [`best_practices_remediation_blueprint.md`](../strategic/best_practices_remediation_blueprint.md#implementation-plan--10-steps)
> **Best Practices Guide:** [`pygame_ce_python_312_best_practices.md`](./pygame_ce_python_312_best_practices.md#section-3-save-system)
> **Status:** SPEC — ready for BUILD

---

## Context

Three medium-severity violations:

1. **Relative save path**: `SAVES_DIR = "saves"` in `save_manager.py` — fragile in distribution (macOS .app bundle, Windows UAC). Must use `pygame.system.get_pref_path()`.
2. **UI images loaded outside `AssetManager`**: 8 UI files use `pygame.image.load(path).convert_alpha()` directly, bypassing the shared cache.
3. **Pyright virtually disabled**: `pyrightconfig.json` suppresses 7 categories of errors, of which 5 hide nothing and 2 suppress 14 real, fixable errors.

---

## Constraints

| Tier | Examples |
|---|---|
| **Always do** | Initialize `pygame.system` before calling `get_pref_path`. Create the directory if absent. Use `AssetManager.get_image()` for any `pygame.image.load` in `src/ui/`. |
| **Ask first** | Modify the public signature of `SaveManager.__init__`. Change `SAVES_DIR` globally (impacts existing saves). |
| **Never do** | Remove `reportAttributeAccessIssue: none` (unresolvable without pygame-ce type stubs). Modify `AssetManager` itself. Touch `src/engine/save_manager.py` beyond `SAVES_DIR`. |

---

## Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema | Consumers |
|---|---|---|---|
| Saves directory | Filesystem, path `str` | `save-system.md § "Save Format"` | `SaveManager.list_slots()`, `SaveManager.load()`, `SaveManager.save()` |

### Consumes
| Identifier | Format | Defined in | Producer |
|---|---|---|---|
| `AssetManager.get_image(path)` | `pygame.Surface` (convert_alpha'd) | `engine-core.md § "AssetManager"` | `AssetManager` singleton |
| `pygame.system.get_pref_path(org, app)` | `str` (OS-specific absolute path) | pygame-ce docs | pygame-ce stdlib |

### Public Interface
N/A — no public API changes. `SaveManager.__init__(saves_dir)` keeps the same signature (overridable via optional parameter).

### External Invocations
| Type | Invoked | Defined in |
|---|---|---|
| `pygame.system.get_pref_path("adrien", "game")` | Returns OS preference directory | pygame-ce API — returns `str` |

### Tracked Concepts
| Concept | Status | Mentioned in |
|---|---|---|
| `SAVES_DIR` | Migrated to `get_pref_path` at init | `save-system.md § "Directory"` |
| `AssetManager` singleton | Consumed, not modified | `engine-core.md § "AssetManager"` |

---

## Step 5 — `pygame.system.get_pref_path` for Saves

### Modified File: `src/engine/save_manager.py`

**Before (L12):**
```python
SAVES_DIR = "saves"
```

**After:**
```python
import pygame.system
import os
import shutil

def _get_saves_dir() -> str:
    """Return the OS-appropriate saves directory path.

    Uses pygame.system.get_pref_path() for cross-OS compatibility:
    - macOS: ~/Library/Application Support/adrien/game/
    - Windows: %APPDATA%/adrien/game/
    - Linux: ~/.local/share/adrien/game/

    Falls back to "./saves" if pygame not initialized (e.g. test context).
    
    Migration logic: If legacy "./saves" exists and the new directory is empty,
    moves all saves to the new directory and renames "./saves" to "./saves_migrated".
    """
    try:
        path = pygame.system.get_pref_path("adrien", "game")
        
        # MIGRATION: Preserve user data from legacy paths
        legacy_path = "./saves"
        if os.path.exists(legacy_path) and os.path.isdir(legacy_path):
            # Check if new path is empty
            if not os.path.exists(path) or not os.listdir(path):
                os.makedirs(path, exist_ok=True)
                for item in os.listdir(legacy_path):
                    s = os.path.join(legacy_path, item)
                    d = os.path.join(path, item)
                    if os.path.isdir(s): shutil.copytree(s, d)
                    else: shutil.copy2(s, d)
                # Safe rename to avoid crashing if destination already exists
                migrated_path = legacy_path + "_migrated"
                if not os.path.exists(migrated_path):
                    os.rename(legacy_path, migrated_path)
                else:
                    counter = 1
                    while os.path.exists(f"{migrated_path}_{counter}"):
                        counter += 1
                    os.rename(legacy_path, f"{migrated_path}_{counter}")
                
        return path
    except Exception:
        return "saves"  # fallback for headless tests
 
SAVES_DIR = _get_saves_dir()
```

**Rule:** `pygame.init()` must be called before `_get_saves_dir()`. In the current initialization order (`game.py:__init__` → `pygame.init()` → `SaveManager()`), this is guaranteed.

**Existing Tests:** `SaveManager` accepts `saves_dir` in its parameters (`__init__(self, saves_dir: str = SAVES_DIR)`). Tests pass their own temporary directory, meaning they are not impacted by this change.

### Post-Implementation Verification

```bash
python3 -c "
import pygame
pygame.init()
import pygame.system
print(pygame.system.get_pref_path('adrien', 'game'))
"
# → must display an absolute path in ~/Library/Application Support/ (macOS)
```

---

## Step 6 — Centralize Image Loading in `AssetManager`

### Complete Inventory of Violations

| File | Lines | Loaded Image |
|---|---|---|
| `src/ui/inventory.py` | 144, 210 | Inventory images (backgrounds, slots) |
| `src/ui/chest_draw.py` | 216, 227, 238, 246, 258, 277 | Chest images |
| `src/ui/chest_layout.py` | 96 | Slot hover image |
| `src/ui/hud.py` | 46 | HUD images (clock, season icons) |
| `src/ui/title_screen.py` | 83, 94 | Title screen backgrounds |
| `src/ui/pause_screen.py` | 76, 87 | Pause screen backgrounds |
| `src/ui/dialogue.py` | 66, 75 | Dialogue bubbles |
| `src/ui/speech_bubble.py` | Variable | Speech bubble assets |
| `src/ui/save_slot.py` | Variable | Save slot icons |
| `src/ui/save_menu.py` | Variable | Save menu background |

### Migration Pattern

**Before:**
```python
# In __init__ of a UI module
img = pygame.image.load(path).convert_alpha()
```

**After:**
```python
from src.engine.asset_manager import AssetManager

# In __init__
am = AssetManager()
img = am.get_image(path)
```

**Rule:** `AssetManager` is a singleton — calling `AssetManager()` always returns the same instance. `.get_image(path)` calls `.convert_alpha()` internally (verified in `asset_manager.py:44`). No double conversion.

**⚠️ Precaution:** Before each migration, verify that the path passed to `pygame.image.load(path)` is identical to the path that `am.get_image(path)` would receive. `AssetManager.get_image` may use a different path format (relative vs absolute). Verify `asset_manager.py` before migrating.

### Modified Files

Each of the 10 files listed above — **only the `pygame.image.load` lines**. No other changes.

---

## Step 7 — Pyright `basic` Mode + Removal of Ghost Suppressions

### Measured Data

| Config | Errors |
|---|---|
| Current config (7 suppressions) | 0 errors (Pyright silent) |
| `basic` mode without any suppression | 158 errors |
| `basic` mode + `reportAttributeAccessIssue: none` only | **14 errors** |

### Target Config: `pyrightconfig.json`

```json
{
  "pythonVersion": "3.12",
  "pythonPlatform": "Darwin",
  "extraPaths": ["."],
  "exclude": [
    "**/__pycache__",
    ".venv",
    "venv",
    "tests",
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

**Removed Suppressions (were ghost suppressions — 0 extra errors):**
- `reportGeneralTypeIssues` (was `"none"`)

> **Note:** `reportGeneralTypeIssues` has been deprecated in modern Pyright versions and split into specific rules. This suppression may already be absent or generate a deprecation warning.
- `reportOptionalSubscript` (was `"none"`)
- `reportOptionalCall` (was `"none"`)
- `reportOptionalIterable` (was `"none"`)

**Retained Suppression (unresolvable without pygame-ce type stubs):**
- `reportAttributeAccessIssue: none` — 144 type errors for `.blit`, `.pos`, `.rect` on pygame objects

**Additional Correction:** `"pythonVersion": "3.13"` → `"3.12"` (the project runs on 3.12)

### 14 Real Errors to Fix

| File | Qty | Type | Fix |
|---|---|---|---|
| `src/engine/lighting.py` | 4 | `reportOptionalOperand` — `/`, `*`, `+`, `-` operations on potentially `None` value | Add guard `if value is None: return` or assertion |
| `src/map/tmj_parser.py` | 2 | `str | None` type passed to `int()` | `int(value)` → `int(value) if value is not None else default` |
| `src/ui/dialogue.py` | 3 | `reportOptionalMemberAccess` — `.render()` and `.get_linesize()` on `font: Font | None` | Guard `if self._font is None: return` at the start of the method |
| `src/ui/save_menu.py` | 3 | `reportOptionalMemberAccess` — attrs on `SaveData | None` | Guard `if slot_data is None: return` |
| `src/ui/speech_bubble.py` | 1 | `reportOptionalMemberAccess` — `.render()` on `None` font | Guard `if self._font is None: return` |

**Typical Correction:**
```python
# BEFORE — lighting.py:150
result = value / divisor  # value can be None

# AFTER
if value is None:
    logging.warning("lighting: expected float, got None")
    return
result = value / divisor
```

### Post-Step 7 Verification

```bash
source venv/bin/activate && pyright src/
# → 0 errors, N warnings (informational)
```

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | `pygame.image.load().convert_alpha()` inline in UI `__init__` | `img = pygame.image.load(path).convert_alpha()` in 8 UI modules | `am = AssetManager(); img = am.get_image(path)` — conforms to [`engine-core.md`](./engine-core.md#assetmanager) |
| 2 | Suppressing all Pyright rules without measuring | 7 active suppressions, 5 hid nothing | Remove only suppressions verified as ghost suppressions. Retain `reportAttributeAccessIssue: none` |
| 3 | Removing `reportAttributeAccessIssue` | Suppresses 144 unresolvable pygame-ce errors | NEVER remove this suppression without pygame-ce stubs |
| 4 | `get_pref_path` before `pygame.init()` | `SaveManager()` instantiated before the first `pygame.init()` | Always initialize pygame before `SaveManager`. Verify ordering in [`engine-core.md`](./engine-core.md#init-sequence) |
| 5 | Hardcoded absolute paths for saves | `SAVES_DIR = "/Users/user/game/saves"` | Only use `pygame.system.get_pref_path(org, app)` as the path source |
| 6 | Modifying `AssetManager.get_image()` to adapt UI paths | Change path format in `AssetManager` to accommodate UI modules | Adapt path at the UI call site, not in `AssetManager` |
| 7 | `"pythonVersion": "3.13"` in pyrightconfig.json | 3.13 false positives on a 3.12 project | Always align `pythonVersion` with the actual venv version |

---

## Test Case Specifications

### Unit Tests — Save Path

**TC-SAVE-001**: `SaveManager()` initialized with active `pygame.init()` → `self._saves_dir` is an absolute path (does not start with `"saves"`)
```python
# Arrange: pygame.init() called (conftest.py)
# Act: sm = SaveManager()
# Assert: os.path.isabs(sm._saves_dir) == True
```

**TC-SAVE-002**: `SaveManager()` initialized without pygame → `self._saves_dir == "saves"` (fallback)
```python
# Arrange: patch pygame.system.get_pref_path → raise Exception
# Act: sm = SaveManager()
# Assert: sm._saves_dir == "saves"
```

**TC-SAVE-003**: Existing tests pass without modification — the `saves_dir` parameter override remains functional
```python
# Arrange: SaveManager(saves_dir="/tmp/test_saves")
# Assert: sm._saves_dir == "/tmp/test_saves"
```

**TC-SAVE-004**: `_get_saves_dir()` returns a `str` (not `bytes`) on pygame-ce
```python
# Assert: isinstance(result, str)
```

### Unit Tests — AssetManager UI

**TC-ASSET-001**: After migration, no file in `src/ui/` contains `pygame.image.load`
```python
# Static check:
# grep -rn "pygame.image.load" src/ui/ → 0 results
```

**TC-ASSET-002**: `AssetManager.get_image(path)` called 3× with the same path → `pygame.image.load` called 1× (cache hit)
```python
# Arrange: mock pygame.image.load
# Act: am.get_image(path) × 3
# Assert: load.call_count == 1
```

**TC-ASSET-003**: UI module tests (chest, inventory, pause_screen) pass after migration — no regression on surfaces

### Unit Tests — Pyright

**TC-PYRIGHT-001**: `pyright src/` with the new config → 0 errors
```bash
pyright src/ | grep "0 errors"
```

**TC-PYRIGHT-002**: `lighting.py` — operation on `None` value → logging warning raised, no crash
```python
# Arrange: put None value in lighting context
# Assert: logging.warning called, no exception
```

**TC-PYRIGHT-003**: `dialogue.py` — `_font is None` → `draw()` returns without blit
```python
# Arrange: dialogue._font = None
# Act: dialogue.draw(screen)
# Assert: screen.blit not called, no AttributeError
```

**TC-PYRIGHT-004**: `save_menu.py` — `slot_data is None` → render empty slot without crash
```python
# Arrange: slot_data = None
# Assert: no AttributeError on None.map_display_name
```

### Integration Tests

**TC-IT-SAVE-001**: save → quit → load cycle on `get_pref_path` path → identical data before/after

**TC-IT-ASSET-001**: Full game startup, open inventory + chest + title screen → no `pygame.error` on missing image

---

## Error Handling Matrix

| Error | Cause | Behavior |
|---|---|---|
| `pygame.system.get_pref_path` raises exception | pygame not initialized | Fallback to `"saves"` + log warning |
| `get_pref_path` directory not writable (permissions) | Restricted OS permissions | `OSError` bubbled up by `SaveManager.save()` — user-friendly message "Unable to save" |
| `AssetManager.get_image(path)` — missing file | Asset deleted/renamed | `AssetManager` returns fallback surface + logs error (existing unmodified behavior) |
| UI path incompatible with `AssetManager` | Different path format | `FileNotFoundError` visible during migration — fix path at call site |
| `lighting.py` — `None` in arithmetic operation | Uninitialized value | Guard + `logging.warning` + `return` |
| `dialogue.py` — `None` font | Failed font load | Guard `if self._font is None: return` |

---

## Bundling & Native-Module Audit

- **BM1:** N/A — pure Python project
- **BM2:** N/A
- **BM3:** N/A — no native module introduced
- **BM4:** N/A — no constants renamed. Verify `SAVES_DIR` is not imported directly elsewhere: `grep -rn "from src.engine.save_manager import SAVES_DIR" src/`

---

## File Tree

```
src/
├── engine/
│   └── save_manager.py              [MODIFY] — SAVES_DIR via _get_saves_dir()
└── ui/
    ├── inventory.py                 [MODIFY] — pygame.image.load → AssetManager
    ├── chest_draw.py                [MODIFY] — pygame.image.load → AssetManager
    ├── chest_layout.py              [MODIFY] — pygame.image.load → AssetManager
    ├── hud.py                       [MODIFY] — pygame.image.load → AssetManager
    ├── title_screen.py              [MODIFY] — pygame.image.load → AssetManager
    ├── pause_screen.py              [MODIFY] — pygame.image.load → AssetManager
    ├── dialogue.py                  [MODIFY] — pygame.image.load → AssetManager + font None guard
    ├── speech_bubble.py             [MODIFY] — pygame.image.load → AssetManager + font None guard
    ├── save_slot.py                 [MODIFY] — pygame.image.load → AssetManager
    └── save_menu.py                 [MODIFY] — pygame.image.load → AssetManager + SlotInfo None guard

pyrightconfig.json                   [MODIFY] — typeCheckingMode basic, python 3.12, 5 suppressions removed
```

---

## Assumptions

| Assumption | Risk | Validation |
|---|---|---|
| `AssetManager.get_image()` accepts the same paths as `pygame.image.load()` in UI modules | Medium — paths may be relative vs absolute | Verify `asset_manager.py:get_image()` for expected format before migrating each file |
| `pygame.system.get_pref_path` is available in pygame-ce 2.x | Low — API stable since pygame 2.0 | `import pygame.system; hasattr(pygame.system, 'get_pref_path')` |
| The 14 Pyright errors are all fixable by an `is None` guard | Low — all categorized as `reportOptionalMemberAccess` / `reportOptionalOperand` | Data measured on actual codebase |
| Existing saves in ./saves/ will be inaccessible after migrating to `get_pref_path` | High — **breaking change for ongoing games** | **MIGRATION REQUIRED** implemented in `_get_saves_dir`. The legacy directory is copied to pref_path and then renamed to `saves_migrated`. |
