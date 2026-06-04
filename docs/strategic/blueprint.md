# Blueprint: Tools Directory Optimization

## Project Grade: Internal

This blueprint outlines the strategic alignment, boundaries, and validation requirements for refactoring, translating comments, and eliminating dead code in the `tools/` directory.

## Success Metrics

| Metric | Target | Timeline | How Measured |
|--------|--------|----------|-------------|
| **Functional Integrity** | 100% test pass rate | Immediate (post-BUILD) | Execution of `venv/bin/pytest tools/` |
| **Localization Standardization** | 0 French comments/docstrings | Immediate (post-BUILD) | `rg "#.*[a-zA-ZÀ-ÿ]" tools/src/` search for French comments |
| **Dead Code Elimination** | 100% of identified unused constants removed | Immediate (post-BUILD) | Static verification of `constants.py` imports |
| **Constant Centralization** | All magic numbers / local configurations moved to constants modules | Immediate (post-BUILD) | Code review conformance check |

## Constraint Mapping

| Constraint | Impact | How We Handle It |
|-----------|--------|-----------------|
| **Python Runtime Compatibility** | Refactored code must remain compatible with Python 3.13.7. | Verify syntax and run tests using the active virtual environment python interpreter. |
| **GUI Core Layout** | Constant extraction for GUI widgets must not alter the layout flow or window dimensions. | Test the interactive GUI tool manually or via automated screenshot/tests. |
| **Bitwise Autotile Mapping** | `BLOB_BITMASKS` and related layout matrices in `converter_xp.py` are mathematically critical. | Keep bitwise configurations structurally identical; do not modify the logic itself during extraction. |

## Architecture Direction

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| **Constants Centralization Scope** | (A) Single global constants file for the whole `tools/` directory.<br>(B) Submodule-specific constants (e.g. `asset_convertor/core/constants.py` and `calibration/constants.py`). | **Chosen: Option (B)** | Modular cohesion. `asset_convertor` and `calibration` are independent utilities; sharing a single file would create unnecessary coupling. |
| **Developer Comments vs. UI strings** | (A) Translate comments and UI strings (buttons, labels).<br>(B) Translate only developer comments and docstrings. | **Chosen: Option (B)** | Preserves the localized runtime experience for users running the GUI, whilst aligning all developer-facing documentation to English. |

## Exclusions & Boundaries

| Excluded | Why | Risk of Reversal |
|----------|-----|-----------------|
| **UI Design Alterations** | The task is strictly a backend/comment refactor. Visual enhancements are out of scope. | Low. Any UI visual changes will be rejected. |
| **Main Game Codebase (`game/`)** | Refactoring is strictly isolated to the `tools/` folder. | None. Files outside `tools/` must not be touched. |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Breaking External Imports** | Low | Medium | Run a workspace-wide grep search for imports from `tools/src/asset_convertor/core/constants.py` before pruning any constant. |
| **Breaking Autotile Bitmask Calculations** | Medium | High | Rely on the 100% coverage of autotile conversion unit tests (`test_converter_xp.py` and `test_converter_mv.py`). |
| **Tkinter GUI Import Regressions** | Low | High | Run GUI verification tests (`test_app.py`) and perform manual boot check of Tkinter interface if needed. |

## Gap Discovery

| # | Gap | Impact if Unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | **Pruning Accuracy**: Which specific variables in `constants.py` are actually dead vs. imported dynamically? | We might delete a constant that is used, causing a runtime crash. | Agent (to verify via workspace-wide grep) |
| 2 | **External Tool Dependencies**: Do external config files or wiki tools depend on `tools/` modules? | A changed package import path could break external scripts. | Agent (to scan import usage in workspace) |
| 3 | **French Log/Print Messages**: Should we translate `print()` or `logger.info()` strings that print French text to the terminal? | Inconsistent log languages across CLI tools. | User (Assumed: Developer comments only; prints/logs remain unchanged) |
