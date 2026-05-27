# Plan: Documentation Audit, Urbanization & Simplification

> **Document Type:** Implementation Plan  
> **Covers:** F-DOC-01 (Documentation Check & Urbanization), F-DOC-02 (Learnings Index Synchronization)  
> **Status:** SPEC Gate Pending (User Approval Required)  
> **Last Updated:** 2026-05-27

---

## 1. User Review Required

> [!IMPORTANT]
> **AI Context Retention Guard:** As requested by the user, **no technical specifications, test cases, or historical remediation spec files will be deleted**. They represent high-value training context for future AI agents to avoid regressions. They will be organized, indexed, and simplified by removing only boilerplate prose and dead links.

---

## 2. Open Questions & 7 Questions Framework

### Q1. What exact problem are you solving?
We are resolving documentation fragmentation. The project has 21 specs, but only 15 are registered. Active remediation plans and architectural records (`ADR-008`) are unregistered, making them invisible to newly onboarded AI agents. Furthermore, the learnings index (`.agents/learnings.md`) needs a complete audit to ensure it matches the actual contents of `.agents/learnings/`.

### Q2. What are your success metrics?
- **100% Indexing Coverage:** All 21 spec files and 8 ADR files registered in `00_MASTER.md`.
- **0 Broken Links:** All relative links verified and aligned.
- **Perfect Learning Registry:** `.agents/learnings.md` index matches `.agents/learnings/*.md` files exactly.
- **Zero Logic Regressions:** 1094 tests pass cleanly.

### Q3. Why will you win?
By systematically organizing technical documentation inside the project workspace using a single source of truth, rather than letting unstructured documents accumulate or deleting historic context.

### Q4. What's the core architecture decision?
- **Urbanization:** Keep `00_MASTER.md` as the unified entry-point.
- **Categorization:** Create a new **"Remediation & Hardening Specifications"** section in `00_MASTER.md` to house the 4 historical refactoring specs.
- **Leaf-Linking:** Every spec file will have a relative link to `.agents/learnings.md` to ensure future agents read learnings before building.

### Q5. What's the tech stack rationale?
Plain Markdown documents with deep linking and standard relative paths, allowing maximum compatibility with LLMs.

### Q6. What are the features?
1. **Feature 1 (Master Index Urbanization):** Add the 4 unregistered specs and `ADR-008` to `docs/specs/00_MASTER.md`.
2. **Feature 2 (Orphan Specs Hardening):** Add Constraint Tiers and Cross-Spec tables to `code-quality-constants-i18n.md` and the 3 remediation specs.
3. **Feature 3 (Learnings Audit):** Audit `.agents/learnings.md` and the 6 domain files under `.agents/learnings/` to ensure absolute consistency.
4. **Feature 4 (Verification & Compilation):** Run link checking scripts and execute the test suite to ensure no structural regression.

### Q7. What are you NOT building/deleting?
- **NO DELETIONS of technical files:** We will not delete any spec or ADR.
- **NO Logic modifications:** No production code will be changed.

---

## 3. Assumptions I'm Making

- **Assumption A-01:** The existing `tc_report.py` and `spec_precheck.py` scripts are functional and can be used to verify consistency. (Risk: Low | Validation: Run them before/after edits).
- **Assumption A-02:** All 4 historical remediation specs (`remediation_01` through `remediation_03` and `code-quality-constants-i18n.md`) are currently fully implemented in the code. (Risk: Low | Validation: Verified via test pass rate).

---

## 4. Proposed Changes

### Component: Technical Specifications Index

#### [MODIFY] [00_MASTER.md](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/00_MASTER.md)
- Register `ADR-008-frect-migration.md` in the ADR Registry table.
- Create a new section **"1.6 Historical Remediation & Hardening"** and register:
  - `code-quality-constants-i18n.md`
  - `remediation_01_dt_text_cache.md`
  - `remediation_02_saves_assets_pyright.md`
  - `remediation_03_modernization.md`

### Component: Historical Remediation Specifications

#### [MODIFY] [code-quality-constants-i18n.md](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/code-quality-constants-i18n.md)
- Add standard Constraint Tiers table.
- Ensure all relative links are verified.

#### [MODIFY] [remediation_01_dt_text_cache.md](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/remediation_01_dt_text_cache.md)
- Add standard Constraint Tiers table.
- Ensure all relative links are verified.

#### [MODIFY] [remediation_02_saves_assets_pyright.md](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/remediation_02_saves_assets_pyright.md)
- Add standard Constraint Tiers table.
- Ensure all relative links are verified.

#### [MODIFY] [remediation_03_modernization.md](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/remediation_03_modernization.md)
- Add standard Constraint Tiers table.
- Ensure all relative links are verified.

### Component: Learnings Registry

#### [MODIFY] [learnings.md](file:///Users/adrien.parasote/Documents/perso/game/.agents/learnings.md)
- Audit the registered entry count for each domain and verify it matches the actual files under `.agents/learnings/`.
- Ensure naming conventions are strictly documented and correct.

---

## 5. Verification Plan

### Automated Tests
1. **Traceability Matrix Regeneration:** Run `python3 scripts/tc_report.py --markdown` to ensure 100% alignment.
2. **Deterministic Spec Precheck:** Run `python3 /Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/spec-gate/scripts/spec_precheck.py --dir docs/specs` to ensure all check gates pass.
3. **Full Pytest Suite:** Run `venv/bin/python3 -m pytest tests/` to confirm 1094 tests pass.

### Manual Verification
- Verify that `00_MASTER.md` renders beautifully in the markdown viewer and all links resolve perfectly.
