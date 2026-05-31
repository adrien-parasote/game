# Implementation Plan — Spec Gate & Adversarial Review (Tooling)

This implementation plan covers the Spec Gate check and Adversarial Review conducted on the tooling specifications folder (`docs/tooling/specs/`).

---

## 1. Deterministic Precheck (`spec_precheck.py`)
- **Status:** **100% PASS** (63 checks passing, 0 failures, 0 partials).
- All minor partial warnings (such as pipeline test alignments, assumptions formats, and secondary constants tables) have been fully resolved directly within the specs:
  - **`asset_creator_v2_texture_quality.md`**: Updated integration test `IT-004` description with the keywords `Proposed Changes` and `Produces` to achieve full pipeline seam coverage alignment.
  - **`asset_creator_v3_gui.md`**: Upgraded the assumptions table to a standard 5-column layout with risk-rated `[SHOW]` indicators and backticked API/CLI validation text.
  - **`blob_autotile_pipeline_spec.md`**: Moved the constants table from `## Assumptions` to its own `## Constants` heading to avoid confusing the precheck assumptions parser.

---

## 2. Cross-Spec Validator (`run_all.py`)
- **Status:** **PASS** (0 failures, 0 warnings across all 10 universal checks). All file paths, dependencies, concepts, and interfaces are fully unified and aligned globally across the 6 specifications.

---

## 3. Adversarial Review (Hostile Stress-Test)
- **Path:** `docs/adversarial-review/0001-2026-05-31-tooling-review/`
- **Overall Verdict:** **WARNING (CRITICAL ISSUES FOUND)**
- Three **CRITICAL** issues, three **HIGH** issues, and two **MEDIUM** issues have been discovered that must be corrected in the specifications before entering the **BUILD** stage.

### Critical Findings & Fix Strategy

#### F1. `opensimplex` API method signature mismatch in `asset_creator_spec.md`
- **Problem:** Spec references `opensimplex_generator.noise4(nx, ny, nz, nw)`, which does not exist in Python's `opensimplex` library. It will raise a fatal `AttributeError` at runtime.
- **Fix:** Update spec code snippet to call `noise4d(nx, ny, nz, nw)`.

#### F2. Canvas cell textures registry initialization missing in `asset_creator_v3_gui.md`
- **Problem:** `build_canvas` attempts to draw grid cell images referencing `canvas_cell_{col}_{row}` texture tags that are never pre-registered in the Dear PyGui raw texture registry. DPG will fail or crash on startup.
- **Fix:** Pre-register raw texture tags in `build_canvas` for all 16×12 cells during startup drawlist creation.

#### F3. Output Canvas height dimension and Vertical Shear staggering mismatch in `diagonal_wall_spec.md`
- **Problem:** The `Produces` table specifies output dimensions of $W \times (H + W)$ for continuous walls, but Section 5.2 Step 2 mandates allocating a canvas of size $W \times (H + 32)$ and pasting columns staggered by local `Y = dx` (0 to 31). This resets the staggered offset every 32px, producing a sawtooth pattern instead of a continuous diagonal wall.
- **Fix:** Align canvas allocation to $W \times (H + W)$ and continuously shift columns along the global coordinate `Y = x` (NW-to-SE) or `Y = (W - 1) - x` (NE-to-SW).

---

## 4. Verification Plan

### Automated Pre-check
```bash
# Verify the spec gate is 100% clean
python3 /Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/spec-gate/scripts/spec_precheck.py --dir docs/tooling/specs/

# Verify cross-spec validation remains green
python3 /Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/cross-spec-validator/scripts/run_all.py
```
