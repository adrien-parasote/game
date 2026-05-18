# Research & Discovery: Documentation Language Urbanization

> **Document Type:** Research
> **Status:** APPROVED — 2026-05-18
> **Methodology Stage:** DISCOVER Gate Validation

This document establishes the strategic research, scope, and validation checklist for urbanizing all project documentation. The goal is to enforce a 100% English standard across all `.md` files in the repository.

---

## 1. Context and Problem Statement

A comprehensive review of the project's documentation reveals a mixed language profile:
- Several **Strategic Blueprints** and **Vision** documents are written entirely in French.
- The **Architectural Decision Records (ADRs)** are written entirely in French, which hinders onboarding and AI understanding.
- Multiple **Technical Specifications (specs)** contain mixed French annotations, comments, anti-patterns, or test cases.

To ensure consistency, readability, and maximize compatibility with modern LLM coding agents (conforming to `user_global` rules), we are urbanizing the entire documentation directory (`docs/`) to be fully English.

---

## 2. Scope of Target Documents

Based on a global grep-scan for French stop words and structural annotations, we have cataloged the following target files:

### 2.1 100% French Documents
These documents require a complete translation of all headings, tables, body text, and annotations:
1. `docs/strategic/game_vision.md` (Vision of the Cozy RPG loop, mechanics, weather, and guilds)
2. `docs/strategic/MASTER_ROADMAP.md` (Detailed versioning, phases 1-9, asset audits, and dependencies)
3. `docs/ADRs/ADR-001-gamestate-architecture.md` (Decoupled GameStateManager from Game object)
4. `docs/ADRs/ADR-002-save-format.md` (JSON serialization schemas and slot thumb logic)
5. `docs/ADRs/ADR-003-key-mapping.md` (ESC/K_ESCAPE pause key bind and standard OS window quit handling)
6. `docs/ADRs/ADR-004-refactoring-context-injection.md` (Duck-typing `game: Any` patterns to avoid import cycles)
7. `docs/ADRs/ADR-005-singleton-new.md` (Using `__new__` singleton patterns for stateless managers)
8. `docs/ADRs/ADR-006-perf-constants-pre-render-cache.md` (Text Surface pre-rendering caches to save frame budgets)

### 2.2 Mostly/Partially French Specifications
These documents are written mostly in English but contain mixed French comments, section stubs, tables, or annotations:
9. `docs/specs/save-system.md` (~80% French: slots dimensions, gem hover effects, back button, test case descriptions)
10. `docs/specs/bridge-sfx-spec.md` (~90% French: state sound triggers, footstep materials prioritizations, test scenarios)
11. `docs/specs/game-flow-spec.md` (~40% French: background halo positions, SaveMenu overlays, calibration loops)
12. `docs/specs/npc-system.md` (Residual French: AI wanderer constraints, update frozen margin tables)
13. `docs/specs/00_MASTER.md` (Residual French: minor index descriptions and phase 1.6/1.7 titles)
14. `docs/specs/engine-core.md` (Residual French: minor collision loop notes, physics assumptions)
15. `docs/specs/performance-optimization-spec.md` (Residual French: minor timing loops notes)
16. `docs/specs/quality-gates.md` (Residual French: minor traceability reference stubs)

---

## 3. Preservations and Constraints (Golden Rules)

During translations, we must preserve the following elements exactly to prevent system breakages:
1. **Deep Links**: Relative line range links like `[inventory.py L21](../../src/engine/inventory_system.py#L21)` must be preserved exactly as they are.
2. **Anchors**: Headings anchors used in internal referencing must be either preserved or updated with perfect traceability (e.g. `[design-tokens.md]`).
3. **Test Case IDs**: Unique identifiers like `SAVE-U-001` or `UT-001` in the tables must not be modified or translated. They map directly to test suite validations.
4. **Code References**: Precise variable names, class names, method signatures, file names, and directories in backticks must remain untouched.

---

## 4. Translation Strategy

We will adopt a systematic, phased translation strategy:
- **Phase 1: Strategic Documents** (`game_vision.md`, `MASTER_ROADMAP.md`).
- **Phase 2: Architectural Decision Records** (`ADR-001` through `ADR-006`).
- **Phase 3: Technical Specifications** (`save-system.md`, `bridge-sfx-spec.md`, `game-flow-spec.md`, `npc-system.md`, `00_MASTER.md`, etc.).

Each translated document will be carefully audited to ensure that it has zero French characters left, while maintaining beautiful formatting and exact technical details.
