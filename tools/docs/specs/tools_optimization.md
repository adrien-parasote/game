# Specification: Tools Directory Optimization

> Document type: Implementation

**Covers:** F1, F2, F3, F4

This document defines the technical specification for code refactoring, translation of developer comments from French to English, removal of dead code and unused constants, and replacing stdout print statements with proper logging inside the `tools/` directory.

---

## File Tree

The following files within the `tools/` directory are within the scope of this specification:

```
tools/
└── src/
    ├── asset_convertor/
    │   ├── core/
    │   │   ├── constants.py
    │   │   └── converter_xp.py
    │   └── gui/
    │       └── app.py
    └── calibration/
        └── calibrate_halos.py
```

> `assets/flat_wall_to_diagonal.py` was assessed during DISCOVER and confirmed out of scope (no dead code, no French comments, no print statements found).

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run the pytest suite `venv/bin/pytest tools/` before and after changes. |
| **Always do** | Maintain Tkinter GUI layout and widget dimensions exactly. |
| **Always do** | Keep all logging and user-facing terminal prints in French as per user instructions. |
| **Ask first** | Adding new external libraries/packages to `pyproject.toml` or `requirements.txt`. |
| **Never do** | Translate UI-visible text (buttons, labels, dialog titles) to English. |
| **Never do** | Modify files outside the `tools/` directory. |

---

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|------------|------|-------------|------------|
| 1 | Logging text translation is excluded; only developer comments and docstrings are translated to English. | Low | TELL (user instruction) | Spot check comments in translated files. |
| 2 | Python's standard `logging` library is the preferred logging framework for `calibrate_halos.py`. | Low | TELL (design choice) | Run tests to verify script loads and runs successfully. |
| 3 | Unused constants in `constants.py` can be safely removed without breaking untested components. | Medium | SHOW (verified via grep) | Run full pytest suite across `tools/tests/` to verify zero imports fail. |
| 4 | The Tkinter GUI `app.py` boots successfully without import regressions on the active python version. | Low | SHOW (verified via pytest) | Execute `venv/bin/pytest tools/tests/asset_convertor/gui/test_app.py`. |

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|--------------|-----------|------------------|
| 1 | Hardcoding magic dimensions | Redefining grid sizes like 16 or 32 locally inside `converter_xp.py` or `gui/app.py`. | Import `TILE_SIZE` and `SUBTILE_SIZE` from `constants.py`. |
| 2 | UI Text Localization | Translating GUI buttons, labels, and text fields to English. | Only translate developer comments and docstrings. GUI elements remain in French. |
| 3 | Direct stdout print usage | Using print() statements in Pygame/Tkinter files. | Use Python logging framework to log messages. |
| 4 | Non-anchored file links | Linking to files without line numbers or top-level anchors. | Always use `#L1` as the file-level anchor for external file links. |
| 5 | Over-pruning Shared Variables | Deleting constants that are imported dynamically or used by `generator.py` in the same directory. | Perform a workspace grep search to confirm a constant is unused before removing it. |

---

## Test Case Specifications

### Unit Tests

| Test ID | Component | Objective | Verification Method |
|---------|-----------|-----------|---------------------|
| **TC-001** | `constants.py` | Verify unused constants are successfully removed. | Assert that loading `constants.py` does not contain the pruned variables, while all remaining variables (`TILE_SIZE`, `SUBTILE_SIZE`, `BLOB_BITMASKS`, `TUFT_*`) are loaded correctly. |
| **TC-002** | `converter_xp.py` | Autotile Converter Constant Resolution. | Execute `convert_xp` with mock image data and assert that it correctly handles tile splitting using centralized constants. |
| **TC-003** | `calibrate_halos.py` | Calibration Prints to Logs. | Perform static search on `calibrate_halos.py` for print statements or intercept stdout during execution to check that logs are routed via `logging`. |
| **TC-004** | `converter_xp.py` & `app.py` | Translation Check. | Run a regex check for French developer comment vocabulary in `converter_xp.py` and `app.py`. Note: UI-visible labels remain in French per spec constraint. |

### Integration Tests

| Test ID | Component | Objective | Verification Method |
|---------|-----------|-----------|---------------------|
| **IT-001** | `converter_xp.py` | Autotile Converter Integration pipeline. | Run `test_pipeline.py` to convert a source XP image and assert that it produces exactly 47 tiles matching the expected hashes. |
| **IT-002** | `app.py` | GUI App Boot Verification. | Run `test_app.py` unit tests that mock the Tkinter environment and check frame initialization. |
| **IT-003** | `calibrate_halos.py` | Halo Calibration Integration. | Run `test_calibrate_halos.py` to trigger save calls against a tmp directory and verify output formatting. |

---

## Error Handling Matrix

| Error | Response | Fallback | Logging |
|-------|----------|----------|---------|
| Image dimensions are not 96x128 | Raise `standard ValueError` with clear size specifications. | Raised as error alert in GUI. | Logged via Tkinter alert dialog. |
| Background image file not found at path | Catch `pygame.error` or `standard FileNotFoundError`, log error in French. | Terminate process with exit code 1. | Logged as ERROR level output in French. |
| Selected conversion file is corrupted or not a PNG | Catch `standard OSError` or `PIL.UnidentifiedImageError` and update status bar in French. | Displays warning status text: "Impossible de lire l'image. Vérifiez que le fichier est un PNG valide." | Logged to terminal journal textbox. |
| Target output directory write permission denied | Catch `standard PermissionError` and output error log to stderr in French. | Return exit code 1. | Logged to stderr in French. |

---

## Deep Links

- Source file: [constants.py](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/core/constants.py#L1)
- Source file: [converter_xp.py](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/core/converter_xp.py#L1)
- Source file: [app.py](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/gui/app.py#L1)
- Source file: [calibrate_halos.py](file:///Users/adrien.parasote/Documents/perso/game/tools/src/calibration/calibrate_halos.py#L1)
- Test suite: [tools/tests/](file:///Users/adrien.parasote/Documents/perso/game/tools/tests/#L1)
