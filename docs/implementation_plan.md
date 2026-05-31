# Spec Gate Remediation Plan

The `spec_precheck.py` tool found 18 FAIL and 34 PARTIAL issues across the `docs/game/specs/` directory. These issues block the LLM scoring step and the `/adversarial-review` process.

## Proposed Changes

We need to fix the structural gaps in the following specification files to make them fully AI-ready and compliant with the Stream Coding methodology.

### `00_MASTER.md`
- [MODIFY] Add `> Document Type: Strategic` label at the top. Since it's a master/strategic doc, this should resolve the missing anti-patterns check if appropriately typed, or we add an anti-patterns section if it's meant to be an Implementation doc.

### Documents Missing Type Labels
- [MODIFY] Add `> Document Type: Implementation` to the following files:
  - `asset-i18n.md`
  - `audio-system.md`
  - `development-quality.md`
  - `dialogue-system.md`
  - `engine-core.md`
  - `entities-system.md`
  - `inventory-system.md`
  - `lighting-system.md`
  - `map-world-system.md`
  - `performance-system.md`
  - `pygame_ce_python_312_best_practices.md`

### Documents Missing `Cross-Spec Contracts`
- [MODIFY] Add `## Cross-Spec Contracts` with `### Produces`, `### Consumes`, and `### Public Interface` to:
  - `chest-ui.md`
  - `npc-system.md`
  - `pixel-perfect-occlusion.md`
  - `code-quality-constants-i18n.md`
  - `camera-rendering.md` (add missing strict subsections)

### Documents with Missing Anti-patterns or Test Cases Formatting
- [MODIFY] `dialogue-system.md`: Add 1 more anti-pattern to reach the 5-entry minimum.
- [MODIFY] `pygame_ce_python_312_best_practices.md`: Add missing Anti-patterns section.
- [MODIFY] `chest-ui.md`: Fix non-standard test IDs (e.g. `IT-CA-01` -> `IT-001`, `TC-CA-01` -> `TC-001`).

### Deep Links without Anchors
- [MODIFY] Fix links in `00_MASTER.md`, `chest-ui.md`, `code-quality-constants-i18n.md`, `dialogue-system.md`, and `engine-core.md` by appending section anchors (e.g., `#L1`).

## User Review Required

> [!WARNING]
> Please review whether `00_MASTER.md` should be considered an `Implementation` document or a `Strategic` document. If it's Strategic, I will label it as such, which bypasses the anti-patterns check.

> [!IMPORTANT]
> The automated spec checks enforce rigorous formatting (e.g. strict test ID formats, mandatory headers). Should I proceed with executing these structural fixes across the specifications?

## Verification Plan
1. Re-run `python3 .agents/skills/spec-gate/scripts/spec_precheck.py --dir ./docs/game/specs/` to verify that there are zero `FAIL` or `PARTIAL` results.
2. Proceed with the LLM-based Spec Gate AI Scoring (16-item checklist).
3. If scoring is 10/10, proceed with the `/adversarial-review` epistemic pre-scan and cross-model run.
