# Strategic Blueprint: Tooling Code Check, Optimization & Constants Extraction

Strategic blueprint for modularizing compile-time parameters and cleaning up code quality issues within the `tools/asset_convertor/` codebase.

## 🎯 7 Questions Framework

### 1. What exact problem are you solving?
We are refactoring the `tools/asset_convertor` package to:
- Eradicate hardcoded magic numbers/strings scattered in multiple modules (`subtile.py`, `texture.py`, `state.py`, `app.py`, `tile_assembler.py`).
- Consolidate all parameters into a unified, centralized `constants.py` module to follow the Single Source of Truth coding standard.
- Identify and translate any residual French comments or debug logs to English to ensure codebase internationalization standards.
- Maintain 100% regression-free behavior across all 361 unit and integration tests.

### 2. What are your success metrics?
- Clean execution of `./venv/bin/pytest tests/tools/` showing 361/361 passes.
- Zero raw magic numbers in core logic modules. All referenced from `constants.py`.
- Zero French comments in the `tools/asset_convertor/` directory.

### 3. Why will you win?
By utilizing a centralized `constants.py` architecture, the generation parameters, layout specs, and UI defaults are defined in one place. Future asset convertor updates will only require a single file change to modify engine-wide asset creation assumptions.

### 4. What's the core architecture decision?
Define `tools/asset_convertor/core/constants.py` which will house:
- Grid Layout specs (`TILE_SIZE`, `SUBTILE_SIZE`, `NUM_BLOB_TILES`)
- Math / Pattern specs (`BAYER_4X4`)
- Procedural parameters (`DEFAULT_PERSISTENCE`, `DEFAULT_LACUNARITY`, `MASK_THRESHOLD`, `BORDER_SHADOW_FACTOR`, `BORDER_HIGHLIGHT_FACTOR`)
- Path defaults (`DEFAULT_OUTPUT_DIR`, `DEFAULT_TSX_DIR`)
- Default color values for AppState

### 5. What's the tech stack rationale?
Python 3.13 + NumPy + PIL. Centralized module using clear uppercase naming convention is standard, fast, and pyright-compliant.

### 6. What are the features?
- Complete extraction of magic variables into `constants.py`.
- Safe import and mapping inside `subtile.py`, `texture.py`, `tile_assembler.py`, `state.py`, `app.py`, etc.
- Scan and translate French comments.
- Verify through full test coverage.

### 7. What are you NOT building?
- No changes to gameplay code outside the `tools/` and `tests/tools/` workspace.
- No new UI features or changes to generation algorithms; this is purely a code quality, optimization, and constant extraction pass.

---

## 🔒 Assumptions Audit

- **Setting constants won't break existing tests or change standard behaviors** — Risk: Low
  - *Evidence*: High-coverage test suite (361 tests) verifies exactly what each function produces. We will run it at every step.
- **A new file `tools/asset_convertor/core/constants.py` is the correct place to keep these constants** — Risk: Low
  - *Evidence*: Coheres with other engine modules (e.g. `engine_constants.py`, `chest_constants.py`).
- **Translating French comments won't affect functionality** — Risk: Low
  - *Evidence*: Standard python comment parsing treats `# ...` as no-op.
