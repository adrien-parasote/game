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
N/A — Internal to `tools/asset_convertor`.

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Python Module | `tools.asset_convertor.core.constants` | This spec § "F-TOOL-QUAL-01" |

### External Invocations
N/A — Pure python utility refactor.

### Tracked Concepts
N/A — Refactor pass only.

---

## Project File Tree

The following files are managed by this specification:
```
tools/
  asset_convertor/
    core/
      constants.py                    # [DEV-TOOL] Centralized magic constants
tests/
  tools/
    asset_convertor/                    # [DEV-TOOL] Tooling tests directory
```

---

## Anti-patterns

| ID | Anti-pattern | Why it's bad | What to do instead |
|----|---------|--------------|--------------------|
| AP-01 | **Circular imports** | Importing core modules inside `tools/asset_convertor/core/constants.py` | Keep `tools/asset_convertor/core/constants.py` strictly as a leaf module with zero imports from the package. |
| AP-02 | **Changing constant values** | Altering color values or math parameters from original values | New constants must exactly match the original raw values to preserve algorithm outputs. |
| AP-03 | **Unused constants** | Defining constants in `tools/asset_convertor/core/constants.py` but leaving the raw values in active code | Search and replace all target occurrences to ensure 100% usage. |
| AP-04 | **Accidental logic shifts** | Modifying grid indexing logic or loop boundaries while refactoring | Maintain identical structure, only swapping numeric values for constant references. |
| AP-05 | **Adding new logic** | Implementing unrelated optimizations or features during constant extraction | Keep the scope strictly focused on extraction, translation, and small file improvements. |

---

## Test Cases

| ID | Component | Description | Assertion |
|---|---|---|---|
| TC-001 | core/constants | Constant Values Integrity | Assertions pass and values represent correct original magic values |
| TC-002 | core/subtile | Subtile Constants usage | Zero hardcoded border coefficients exist |
| TC-003 | core/texture | Texture Constants usage | Noise remains **bit-for-bit** identical to original output (verified with `numpy.array_equal`, not `allclose`) |
| TC-004 | gui/state | State Defaults integration | Directories and color variables default to constants |
| TC-005 | core/subtile | Translation complete | No French comments in `tools/asset_convertor/core/`. Note: user-facing labels in `gui/app.py` are excluded (French mandatory per GUI spec). |
| TC-006 | core/constants | Float Precision | For each float constant, `ast.literal_eval(repr(constant)) == original_value` using Python `==` (no tolerance) |
| TC-007 | core/constants | Leaf module (no package imports) | Parsing `tools/asset_convertor/core/constants.py` with `ast` reveals zero `ImportFrom` nodes referencing `tools.asset_convertor` package |
| IT-001 | full | Clean test suite pass | All existing tests pass green. Count ≥ 361 (exact number grows as new feature specs add tests). |
| IT-002 | preview | Pygame preview module compile | Works cleanly |
| IT-003 | pipeline | Export integration verify | Export succeeds |

---

## Detailed Change Specifications

### F-TOOL-QUAL-01: Centralized `tools/asset_convertor/core/constants.py`

Extraction of magic values into `tools/asset_convertor/core/constants.py`.
Constants include: grid constraints, noise defaults, border effects, dithering thresholds, default application settings, default UI colors, and preview settings.

**Float constant precision rule:** All floating-point constants must be extracted as their **exact source code string representation** — do not round or truncate. Verify by parsing the original file with `ast.parse`, extracting each `ast.Constant` node's `.value`, and asserting `original_value == new_constant` using Python `==` (bitwise identical, no tolerance). TC-003 must use `numpy.array_equal` (not `numpy.allclose`) to confirm generated textures are bit-for-bit identical before and after extraction.

### F-TOOL-QUAL-02: French Comments Translation

Translate French **code comments** (`# ...`) to English across `tools/asset_convertor/core/` and `tools/asset_convertor/gui/` modules.

**⛔ EXCEPTION — `gui/app.py` user-facing labels:** Per [asset_convertor_spec.md](./asset_convertor_spec.md#L1) § "UI Language Constraint", all user-visible widget labels in `gui/app.py` MUST remain in French. Do NOT translate them.

Scope:
- ✅ Code comments in any `.py` file under `tools/asset_convertor/` (except gui/app.py UI strings)
- ✅ Log strings not shown directly to the user
- ❌ User-facing widget labels in `gui/app.py` — French is mandatory per the GUI spec

### F-TOOL-QUAL-03: Optimization & Verification Loop

- Code structure will be checked for unnecessary allocations or loop overheads.
- Clean up of imports and sorting where needed to conform to the coding standard.
- The tests in `tests/tools/asset_convertor/` will act as our safety net (≥ 361 tests — count grows as new specs add tests).

---

## Error Handling Matrix

| Error | Trigger | Response |
|---|---|---|
| `ImportError` on constants | Broken paths in relative or absolute import statements | Correct the import string to `from tools.asset_convertor.core.constants import ...` |
| Math output change | Accidentally altered float constant values | Re-read original file definitions from Git history and restore exact match |
| Compilation failure in GUI | Missing constant mapping in AppState or widget callbacks | Correct variable names to match `tools/asset_convertor/core/constants.py` declarations |

---

## Deep Links

- Strategic blueprint: [constants_extraction_blueprint.md](../strategic/constants_extraction_blueprint.md#7-questions-framework)
- Core subtile: [subtile.py](../../../tools/asset_convertor/core/subtile.py#L1)
- Core texture: [texture.py](../../../tools/asset_convertor/core/texture.py#L1)
