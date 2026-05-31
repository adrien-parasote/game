# Research & Discovery: Documentation Audit, Urbanization & Simplification

> **Document Type:** Research Reference  
> **Date:** 2026-05-27  
> **Status:** Completed (Discover Gate Passed)

This research document analyzes the current state of documentation in the RPG Tile Engine project, evaluating the urbanization structure, identification of gaps, potential for simplification without loss of technical assets, and alignment of the learnings registry.

---

## 1. Existing Documentation Inventory & Analysis

A complete scan of the project workspace reveals the following documentation footprint:

### 1.1 Folder Structure
- `docs/specs/`: 21 Markdown files detailing the consolidated technical specifications.
- `docs/ADRs/`: 8 Architectural Decision Records (ADRs) explaining major structural choices.
- `docs/strategic/`: 6 Strategic plans, blueprints, and vision documents.
- `docs/codemaps/`: 3 High-density architecture and data maps generated for fast agent onboarding.
- `docs/traceability.md` & `traceability_report.md`: Auto-generated matrices linking specs to test functions.
- `.agents/`: Internal agent metadata, active stage configs, and session observations.
- `.agents/learnings/`: 6 Domain-specific learnings registries.
- `.agents/learnings.md`: Central learnings index.

---

## 2. Key Urbanization & Consistency Gaps Identified

### Gap 1: Unregistered Specifications in `00_MASTER.md`
The master technical specification index (`00_MASTER.md`) lists only 15 consolidated core technical specifications. However, there are 21 files present in `docs/specs/`. The following 4 files are completely unregistered and orphan from the index:
1. `code-quality-constants-i18n.md` — Pass for translating French logs/docstrings and extracting magic color tuples.
2. `remediation_01_dt_text_cache.md` — Spec for DT Clamping and component-level pre-rendered text caching.
3. `remediation_02_saves_assets_pyright.md` — Spec for pyright type corrections and save pref-paths.
4. `remediation_03_modernization.md` — Spec for `pathlib.Path` migration and standardizations.

*Recommendation:* Do NOT delete these files as they contain historical context, implementation decisions, and test cases that future AI agents need to understand why these modifications were done. Instead, list them under a new dedicated **"Remediation & Hardening Specifications"** section in `00_MASTER.md`.

### Gap 2: Unregistered ADR in `00_MASTER.md`
The master index registers `ADR-001` through `ADR-007`. However, `ADR-008-frect-migration.md` exists on disk but is absent from the global registry table.

*Recommendation:* List `ADR-008` (FRect Non-Migration Decision) under Section 5 of `00_MASTER.md` with its correct relative path and summary.

### Gap 3: Missing Constraint Tiers & Cross-Spec Contracts in Remediation Specs
While core specs like `intra-map-teleport.md` contain strict Constraint Tiers and Cross-Spec tables, some historic specs and remediation plans lack these tables or have partial stubs.

*Recommendation:* Enhance remediation files by adding correct `## Constraints` tables.

### Gap 4: Learnings Index Synchronization
The central index `.agents/learnings.md` must be checked to ensure all domain summaries, counts, and descriptions perfectly match the 6 files inside `.agents/learnings/`.

---

## 3. Simplification & Retention Strategy (AI-Safety Gate)

> [!IMPORTANT]
> The user explicitly warned: **"ATTENTION JE NE VEUX PAS DE DELETE INUTILE, il faut que les futures agent IA puisse avoir l'ensemble des éléments nécessaires."**
> In AI documentation-driven coding, deleting technical descriptions or test-case definitions under the guise of "simplification" causes future agents to lose context, hallucinate interfaces, and introduce regressions.

### Simplification Guidelines:
1. **Keep all:** Test Cases, Error Handling Matrices, Constraints, and detailed File Trees.
2. **Remove:** Aspirational/future prose, duplicate paragraphs that repeat existing spec statements, and empty placeholder stubs.
3. **Consolidate:** Merge redundant architectural descriptions into `docs/codemaps/` or their respective core specs.
4. **Fix Links:** Ensure all Markdown links inside specs are relative (`../../` or `./`) and use anchors to avoid broken references.

---

## 4. Adopt, Adapt, or Build Decision

- **Adopt:** Standardize the document structure exactly as defined in `GEMINI.md` and `.agents/rules/spec-writing.md`.
- **Adapt:** Update `00_MASTER.md` and `.agents/learnings.md` as active living indexes that link everything together.
- **Build:** Implement a thorough audit, urbanization, and synchronization cycle. Update the index, structure the orphan specs, verify links, and audit the learnings.
