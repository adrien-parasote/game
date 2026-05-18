# Strategic Blueprint: Documentation Language Urbanization

> **Document Type:** Strategic
> **Status:** APPROVED — 2026-05-18
> **Methodology Stage:** STRATEGY Gate Validation

This document defines the strategic approach, translation decisions, feature prioritization, and exclusions for the language urbanization of the RPG game's documentation.

---

## 1. The 7 Questions Framework

### Q1: What exact problem are you solving?
We are resolving language fragmentation in the repository's documentation directory (`docs/`). Currently, critical architectural decisions (ADRs), core game flow vision, and implementation specs are written partially or entirely in French. This causes cognitive friction during developer onboarding, inconsistent specification standards, and semantic misunderstanding for AI coding agents. We are urbanizing the entire documentation corpus to be 100% English.

### Q2: What are your success metrics?
- **100% English Coverage**: A complete absence of French stop words/phrases across all markdown (`.md`) files in `docs/` (excluding historical tombstone logs if any).
- **Zero Broken Links**: All markdown relative hyperlinks (`../../src/...`, `./...`, etc.) and exact line anchors (`#L10`) must remain perfectly valid.
- **Traceability Integrity**: All Test Case IDs (e.g. `SAVE-U-001`, `IT-003`) and technical mappings remain fully intact, maintaining 100% compliance with automated verification tools.

### Q3: Why will you win?
We are combining professional, precise, and cozy-RPG idiomatic English translations with strict automated verification. We preserve exact variable names, class names, method signatures, file names, and directories in backticks to guarantee zero divergence between the newly-translated specifications and the actual python codebase.

### Q4: What's the core architecture decision?
We will execute a 1:1 structural and semantic translation. We will maintain the exact layouts, markdown formatting, tables, alert boxes, and deep links of the original files. We are not modifying any architectural decisions or technical requirements; we are strictly translating their descriptions and rationales.

### Q5: What's the tech stack rationale?
Standard Markdown (`.md`) files conforming to standard GitHub Flavored Markdown (GFM).

### Q6: What are the features?
The urbanization feature list is ordered by document priority and dependency:
1. **Phase 1: Strategic Documents**
   - [game_vision.md](../strategic/game_vision.md)
   - [MASTER_ROADMAP.md](../strategic/MASTER_ROADMAP.md)
   - [autotile_direction_blueprint.md](../strategic/autotile_direction_blueprint.md)
2. **Phase 2: Architectural Decision Records**
   - [ADR-001-gamestate-architecture.md](../ADRs/ADR-001-gamestate-architecture.md)
   - [ADR-002-save-format.md](../ADRs/ADR-002-save-format.md)
   - [ADR-003-key-mapping.md](../ADRs/ADR-003-key-mapping.md)
   - [ADR-004-refactoring-context-injection.md](../ADRs/ADR-004-refactoring-context-injection.md)
   - [ADR-005-singleton-new.md](../ADRs/ADR-005-singleton-new.md)
   - [ADR-006-perf-constants-pre-render-cache.md](../ADRs/ADR-006-perf-constants-pre-render-cache.md)
3. **Phase 3: High-Priority Specifications**
   - [save-system.md](../specs/save-system.md)
   - [bridge-sfx-spec.md](../specs/bridge-sfx-spec.md)
   - [game-flow-spec.md](../specs/game-flow-spec.md)
   - [npc-system.md](../specs/npc-system.md)
   - [00_MASTER.md](../specs/00_MASTER.md)
   - [engine-core.md](../specs/engine-core.md)
   - [performance-optimization-spec.md](../specs/performance-optimization-spec.md)
   - [quality-gates.md](../specs/quality-gates.md)

### Q7: What are you NOT building?
- We are **NOT** modifying any Python code under `src/` or `tests/`.
- We are **NOT** altering the physical Tiled maps or projects (`assets/tiled/`).
- We are **NOT** altering the actual JSON save structure or keys (e.g. slot files in `saves/`).
- We are **NOT** renaming any actual files (which would break git history and external links).

---

## 2. Strategic Exclusions and Rules

1. **Do Not Touch Code Identifiers**: Do not translate code symbols in backticks unless they are descriptive placeholders (e.g. `` `self.is_on` `` remains `` `self.is_on` ``).
2. **Do Not Alter Test Case Specifications Tables**: The Test ID and verification flows are strictly bound to automated tests. They must match exactly.
3. **Preserve Path Layouts**: Keep all relative paths (e.g. `../../src/...`) clean and intact.
