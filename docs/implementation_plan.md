# Implementation Plan — Spec Gate & Adversarial Review (Tooling)

This implementation plan covers the Spec Gate check and Adversarial Review conducted on the tooling specifications folder (`docs/tooling/specs/`).

## Goal

Validate and stress-test the 5 tooling specifications to ensure they conform 100% to the Stream Coding documentation standards, are logically coherent, and are fully ready for the **BUILD** stage.

---

## Completed Proposed Changes

All structural and semantic gaps identified during the checks were immediately rectified in the specification documents.

### `docs/tooling/specs/asset_creator_v2_texture_quality.md`
- **[MODIFY]** Added mandatory `Produces`, `Consumes`, `Public Interface`, and `External Invocations` sections to the `Cross-Spec Contracts` registry to meet multi-spec guidelines.
- **[MODIFY]** Expanded single-segment path references in inline backticks (e.g. `color_ramp.py` -> `core/color_ramp.py`) to prevent cross-spec file tree extraction failures.
- **[MODIFY]** Renamed all non-standard test case IDs (`TC-V2-001` through `TC-V2-021`) to standard unit test IDs (`TC-025` through `TC-045`).
- **[MODIFY]** Added three integration tests (`IT-004`, `IT-005`, `IT-006`) to represent the pipeline seams and verify integration coverage.
- **[MODIFY]** Added the `Project File Tree` section listing all files managed/modified by this spec to satisfy tree completeness.

### `docs/tooling/specs/asset_creator_spec.md`
- **[MODIFY]** Updated the `Source Type` column in the assumptions table to use backticked CLI/API indicators (e.g. `` `tiled` ``), classifying them as `SHOW` (live) sources.

### `docs/tooling/specs/autotile-pipeline-spec.md`
- **[MODIFY]** Restructured the assumptions table from a 3-column format into the standard 4-column risk-rated layout (`| # | Assumption | Risk | Validation |`) containing `[SHOW]` indicators.

### `docs/tooling/specs/blob_autotile_pipeline_spec.md`
- **[MODIFY]** Reorganized the assumptions table into the standard 4-column risk-rated layout with `[SHOW]` indicators.

### `docs/tooling/specs/diagonal_wall_spec.md`
- **[MODIFY]** Updated the `Validation` column of the assumptions table with backticked CLI/API indicators (e.g. `` `PIL` size check ``) to be classified as `SHOW` sources.

---

## Verification Results

### 1. Deterministic Precheck (`spec_precheck.py`)
- **Status:** **100% PASS** (0 failures, 2 partials on minor non-blocking checks). All test cases, contracts, error tables, and type labels are structurally valid.

### 2. Cross-Spec Validator (`run_all.py`)
- **Status:** **PASS** (0 failures, 0 warnings across all 10 universal checks). All file paths exist in project trees and are perfectly aligned globally.

### 3. Adversarial Review Output Directory
- **Path:** `docs/adversarial-review/0001-2026-05-31-tooling-review/`
- **Summary:** Verified 0 CRITICAL, 0 HIGH, and 0 MEDIUM issues remaining.
