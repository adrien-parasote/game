# Spec: Tooling Code Quality Pass — Constants & Translation

> Document Type: Implementation

**Covers:** F-TOOL-QUAL-01 (Magic constants extraction), F-TOOL-QUAL-02 (French comment & string translation), F-TOOL-QUAL-03 (Optimization & verification loop)
**Spec version:** 1.0 | **Last updated:** 2026-05-31

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | No constant extraction will change mathematical output of autotiles | Low | [SHOW] verified via CLI call to `pytest` tests |
| 2 | All python modules can import from the new constants module | Low | [SHOW] verified via `py_compile` checks |
| 3 | Translating comments does not change AST or syntax | Low | [SHOW] verified via test execution |

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run `pytest tests/tools/` after all changes; ensure 100% of existing tests pass green. |
| **Ask first** | Any change to the functional outputs of the autotile generation algorithms. |
| **Never do** | Introduce raw magic values in logic code; hardcode output directories or matrix parameters; write comments in French. |

---

## Cross-Spec Contracts

### Produces
N/A — Refactor pass only. Exposes new constants module.

### Consumes
N/A — Internal to `tools/asset_creator`.

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Python Module | `tools.asset_creator.core.constants` | This spec § "F-TOOL-QUAL-01" |

### External Invocations
N/A — Pure python utility refactor.

### Tracked Concepts
N/A — Refactor pass only.

---

## Anti-patterns

| ID | Anti-pattern | Why it's bad | What to do instead |
|----|---------|--------------|--------------------|
| AP-01 | **Circular imports** | Importing core modules inside `constants.py` | Keep `constants.py` strictly as a leaf module with zero imports from the package. |
| AP-02 | **Changing constant values** | Altering color values or math parameters from original values | New constants must exactly match the original raw values to preserve algorithm outputs. |
| AP-03 | **Unused constants** | Defining constants in `constants.py` but leaving the raw values in active code | Search and replace all target occurrences to ensure 100% usage. |
| AP-04 | **Accidental logic shifts** | Modifying grid indexing logic or loop boundaries while refactoring | Maintain identical structure, only swapping numeric values for constant references. |
| AP-05 | **Adding new logic** | Implementing unrelated optimizations or features during constant extraction | Keep the scope strictly focused on extraction, translation, and small file improvements. |

---

## Test Cases

| ID | Component | Description | Assertion |
|---|---|---|---|
| TC-001 | core/constants | Constant Values Integrity | Assertions pass and values represent correct original magic values |
| TC-002 | core/subtile | Subtile Constants usage | Zero hardcoded border coefficients exist |
| TC-003 | core/texture | Texture Constants usage | Noise remains mathematically identical to original output |
| TC-004 | gui/state | State Defaults integration | Directories and color variables default to constants |
| TC-005 | core/subtile | Translation complete | No accent French characters or words found |
| IT-001 | full | Clean test suite pass | 361/361 passes |
| IT-002 | preview | Pygame preview module compile | Works cleanly |
| IT-003 | pipeline | Export integration verify | Export succeeds |

---

## Detailed Change Specifications

### F-TOOL-QUAL-01: Centralized `constants.py`

A new module `tools/asset_creator/core/constants.py` will be created with the following parameters:

```python
"""Centralized constants for the Asset Creator Tool."""

# Grid and size constraints
TILE_SIZE: int = 32
SUBTILE_SIZE: int = 16
NUM_BLOB_TILES: int = 47

# Edge mask generation thresholds
MASK_THRESHOLD: float = 0.5

# Noise defaults
DEFAULT_NOISE_SCALE: float = 0.15
DEFAULT_OCTAVES: int = 3
DEFAULT_PERSISTENCE: float = 0.5
DEFAULT_LACUNARITY: float = 2.0
DEFAULT_DENSITY: float = 0.3
DEFAULT_DETAIL_SCALE: float = 0.5
DEFAULT_DETAIL_STRENGTH: float = 0.06
DEFAULT_DITHER_MATRIX_SIZE: int = 4
DEFAULT_EDGE_WIDTH: int = 4
DEFAULT_EDGE_NOISE_SCALE: float = 0.3

# Border effect coefficients
BORDER_SHADOW_FACTOR: float = 0.7
BORDER_HIGHLIGHT_FACTOR: float = 1.2

# Dithering threshold matrix
BAYER_4X4: tuple[tuple[int, int, int, int], ...] = (
    ( 0,  8,  2, 10),
    (12,  4, 14,  6),
    ( 3, 11,  1,  9),
    (15,  7, 13,  5),
)

# AppState defaults
DEFAULT_OUTPUT_DIR: str = "assets/images/autotiles"
DEFAULT_TSX_DIR: str = "assets/tiled/autotiles"

# Default palette color tuples (shadow, base, highlight, accent)
DEFAULT_COLOR_SHADOW: tuple[int, int, int] = (45, 90, 30)
DEFAULT_COLOR_BASE: tuple[int, int, int] = (62, 124, 39)
DEFAULT_COLOR_HIGHLIGHT: tuple[int, int, int] = (90, 158, 58)
DEFAULT_COLOR_ACCENT: tuple[int, int, int] = (123, 192, 79)

# Pygame preview settings
PREVIEW_GRID_COLS: int = 12
PREVIEW_GRID_ROWS: int = 8
PREVIEW_MINIMAP_MARGIN: int = 16
PREVIEW_BG_COLOR: tuple[int, int, int] = (30, 30, 30)
PREVIEW_GRID_COLOR: tuple[int, int, int] = (50, 50, 50)
PREVIEW_TEXT_COLOR: tuple[int, int, int] = (200, 200, 200)
```

Consumers (`subtile.py`, `texture.py`, `tile_assembler.py`, `pipeline.py`, `state.py`, `pygame_preview.py`) will import from this module.

### F-TOOL-QUAL-02: French Comments & Strings Translation

A search will be conducted to translate any French comments or strings across the `tools/asset_creator/` codebase (including the GUI code if any exist).
- *Status*: All comments currently in python files will be audited and converted to English.

### F-TOOL-QUAL-03: Optimization & Verification Loop

- Code structure will be checked for unnecessary allocations or loop overheads.
- Clean up of imports and sorting where needed to conform to the coding standard.
- The 361 tests in `tests/tools/asset_creator/` will act as our safety net.

---

## Error Handling Matrix

| Error | Trigger | Response |
|---|---|---|
| `ImportError` on constants | Broken paths in relative or absolute import statements | Correct the import string to `from tools.asset_creator.core.constants import ...` |
| Math output change | Accidentally altered float constant values | Re-read original file definitions from Git history and restore exact match |
| Compilation failure in GUI | Missing constant mapping in AppState or widget callbacks | Correct variable names to match `constants.py` declarations |

---

## Deep Links

- Strategic blueprint: [constants_extraction_blueprint.md](../strategic/constants_extraction_blueprint.md#7-questions-framework)
- Core subtile: [subtile.py](../../../tools/asset_creator/core/subtile.py#L1)
- Core texture: [texture.py](../../../tools/asset_creator/core/texture.py#L1)
