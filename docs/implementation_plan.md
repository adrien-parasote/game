# Plan: 2D Diagonal Wall Tile Transformation Utility

> **Document Type:** Implementation Plan  
> **Date:** 2026-05-28  
> **Status:** SPEC Gate Pending (User Approval Required)  
> **Covers:** F1 (CLI Tool), F2 (Vertical Shear PIL Engine), F3 (Automatic Grid Slicing), F4 (Batch Processing), F5 (Gitignore Safety)

---

## User Review Required

> [!IMPORTANT]
> **Git Tracking Strategy:** To satisfy your requirement, a `.gitignore` has been successfully created at `scripts/input/.gitignore` which excludes all files (e.g. `asset1.png`, `asset2.png`, `asset3.png`) except the `.gitignore` itself. This guarantees that your input directory is committed and tracked, while the heavy binary assets are safely ignored.

---

## Open Questions

Zero open questions remain. All choices regarding geometric algorithms, grid alignment, CLI signature, and output structures have been successfully resolved during the **DISCOVER** and **STRATEGY** phases.

---

## Proposed Changes

### Component: Developer Utility Scripts

#### [NEW] [flat_wall_to_diagonal.py](file:///Users/adrien.parasote/Documents/perso/game/scripts/assets/flat_wall_to_diagonal.py)
* **Main Script:** Implement a pure Python CLI utility that parses arguments (`--input-dir`, `--output-dir`, `--direction`).
* **PIL Shear Algorithm:** Loop through columns, slice $1$-pixel vertical strips, and translate them vertically to generate perfect, crisp $45^\circ$ diagonal tilesets (NW-SE and NE-SW slopes) without sub-pixel blur.
* **Batch Execution:** Scan `scripts/input/` for PNG files, process `asset1.png` ($32\times96$), `asset2.png` ($96\times192$), and `asset3.png` ($128\times224$), and output the results.
* **Auto-Directory Creation:** Ensure any missing output folders are created automatically.

### Component: Game Assets

#### [NEW] [asset1_nw_se.png](file:///Users/adrien.parasote/Documents/perso/game/assets/images/tilesets/asset1_nw_se.png)
#### [NEW] [asset1_ne_sw.png](file:///Users/adrien.parasote/Documents/perso/game/assets/images/tilesets/asset1_ne_sw.png)
#### [NEW] [asset2_nw_se.png](file:///Users/adrien.parasote/Documents/perso/game/assets/images/tilesets/asset2_nw_se.png)
#### [NEW] [asset2_ne_sw.png](file:///Users/adrien.parasote/Documents/perso/game/assets/images/tilesets/asset2_ne_sw.png)
#### [NEW] [asset3_nw_se.png](file:///Users/adrien.parasote/Documents/perso/game/assets/images/tilesets/asset3_nw_se.png)
#### [NEW] [asset3_ne_sw.png](file:///Users/adrien.parasote/Documents/perso/game/assets/images/tilesets/asset3_ne_sw.png)

---

## Verification Plan

### Automated Tests
1. **Spec Pre-check Validation:** Run `/spec-gate` validation to guarantee the spec remains at $100\%$ compliance.
2. **Deterministic Script Execution:** Run the newly created utility in both directions to verify output compilation.
3. **Automated Unit & Integration Tests:** Add detailed test cases in a new test file `tests/scripts/test_flat_wall_to_diagonal.py` covering:
   * CLI argument resolution and defaults.
   * Graceful path error handling.
   * Column-by-column vertical translation coordinate offsets.
   * Output dimensions checks ($W \times (H + W)$).
   * Execution of batch processing on test fixtures.
   * Run the test suite: `venv/bin/pytest tests/scripts/test_flat_wall_to_diagonal.py`

### Manual Verification
- Visual inspection of the generated diagonal assets (`asset3_nw_se.png` ($128\times352$) and `asset3_ne_sw.png` ($128\times352$)) in the scratch or output directories to confirm perfect geometric rendering, sharp pixel edges, and seamless continuity.
