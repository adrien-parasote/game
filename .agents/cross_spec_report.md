# Cross-Spec Validation Report

**Project:** Master Specification Index [Strategic]
**Language:** mixed
**Specs validated:** 21 modules + 1 Master
**Date:** 2026-05-28

## Summary

| Check | Status | Issues |
|---|---|---|
| 1. Global Access Patterns | ⏭️ SKIP | 0 |
| 2. Constant Naming | ❌ FAIL | 6 |
| 3. Numeric Mapping Consistency | ✅ PASS | 0 |
| 4. Callback Safety Rules | ⏭️ SKIP | 0 |
| 5. Coverage Matrix | ⏭️ SKIP | 0 |
| 6. Dependency Acyclicity | ⏭️ SKIP | 0 |
| 7. Shared Artifact Schema | ✅ PASS | 0 |
| 8. Cross-Spec Invocation Contract | ⏭️ SKIP | 0 |
| 9. File Tree Completeness | ❌ FAIL | 8 |
| 10. Concept Coherence | ✅ PASS | 0 |

**Total: 14 issues, 14 critical**

## Detailed Issues

### ⏭️ 1. Global Access Patterns — SKIPPED

Reason: Check 'global_access_patterns' not activated by any preset. Active presets: python, universal

### ❌ 2. Constant Naming (6 issues)

**Issue C1** — Undeclared constant `BACK_BTN_LABEL_DEFAULT` used in 1 spec(s).
- Used in: code-quality-constants-i18n.md
- Suggested fix: Declare `BACK_BTN_LABEL_DEFAULT` in the canonical constants source or remove the reference.

**Issue C2** — Undeclared constant `FALLBACK_SURF_SIZE` used in 1 spec(s).
- Used in: code-quality-constants-i18n.md
- Suggested fix: Declare `FALLBACK_SURF_SIZE` in the canonical constants source or remove the reference.

**Issue C3** — Undeclared constant `IT_` used in 1 spec(s).
- Used in: pixel-perfect-occlusion.md
- Suggested fix: Declare `IT_` in the canonical constants source or remove the reference.

**Issue C4** — Undeclared constant `MASTER_ROADMAP` used in 1 spec(s).
- Used in: 00_MASTER.md
- Suggested fix: Declare `MASTER_ROADMAP` in the canonical constants source or remove the reference.

**Issue C5** — Possible typo: `PARTICLE_DEFAULT_COLOR` used but `HALO_DEFAULT_COLOR` declared (similarity: 73%).
- Used in: code-quality-constants-i18n.md
- Suggested fix: Rename `PARTICLE_DEFAULT_COLOR` to `HALO_DEFAULT_COLOR` or declare `PARTICLE_DEFAULT_COLOR` explicitly.

**Issue C6** — Undeclared constant `UT_` used in 1 spec(s).
- Used in: pixel-perfect-occlusion.md
- Suggested fix: Declare `UT_` in the canonical constants source or remove the reference.

### ✅ 3. Numeric Mapping Consistency — PASS

Found 3 numeric mapping tables across 22 specs.

### ⏭️ 4. Callback Safety Rules — SKIPPED

Reason: Check 'callback_safety_rules' not activated by any preset. Active presets: python, universal

### ⏭️ 5. Coverage Matrix — SKIPPED

Reason: No Coverage Matrix table found in Master Spec — check skipped. Expected a table with 'Feature ID' and 'Spec file' columns under a '## Coverage Matrix' heading.

### ⏭️ 6. Dependency Acyclicity — SKIPPED

Reason: No `Depends on:` / `Dépend de:` headers found in module specs — check skipped.

### ✅ 7. Shared Artifact Schema — PASS

Audited 0 cross-spec artifact paths across 22 specs.

### ⏭️ 8. Cross-Spec Invocation Contract — SKIPPED

Reason: No cross-spec invocations detected (no CLI calls, HTTP routes, or env var usage).

### ❌ 9. File Tree Completeness (8 issues)

**Issue F1** — Spec `code-quality-constants-i18n.md` references path `ui_colors.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `ui_colors.py` to the file tree of the spec that owns this deliverable, or (b) mark `ui_colors.py` as an external dependency if it's not produced by this project.

**Issue F2** — Spec `code-quality-constants-i18n.md` references path `engine_constants.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `engine_constants.py` to the file tree of the spec that owns this deliverable, or (b) mark `engine_constants.py` as an external dependency if it's not produced by this project.

**Issue F3** — Spec `code-quality-constants-i18n.md` references path `pickup.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `pickup.py` to the file tree of the spec that owns this deliverable, or (b) mark `pickup.py` as an external dependency if it's not produced by this project.

**Issue F4** — Spec `code-quality-constants-i18n.md` references path `game-flow-spec.md` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `game-flow-spec.md` to the file tree of the spec that owns this deliverable, or (b) mark `game-flow-spec.md` as an external dependency if it's not produced by this project.

**Issue F5** — Spec `intra-map-teleport.md` references path `../../tests/engine/test_intra_map_teleport.py` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `../../tests/engine/test_intra_map_teleport.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_intra_map_teleport.py` as an external dependency if it's not produced by this project.

**Issue F6** — Spec `intra-map-teleport.md` references path `../../tests/engine/test_render_order.py` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `../../tests/engine/test_render_order.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_render_order.py` as an external dependency if it's not produced by this project.

**Issue F7** — Spec `remediation_01_dt_text_cache.md` references path `../../tests/engine/test_dt_clamp.py` but no spec's file tree declares it.
- Used in: remediation_01_dt_text_cache.md
- Suggested fix: Either: (a) add `../../tests/engine/test_dt_clamp.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_dt_clamp.py` as an external dependency if it's not produced by this project.

**Issue F8** — Spec `remediation_01_dt_text_cache.md` references path `../../tests/ui/test_text_cache.py` but no spec's file tree declares it.
- Used in: remediation_01_dt_text_cache.md
- Suggested fix: Either: (a) add `../../tests/ui/test_text_cache.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_text_cache.py` as an external dependency if it's not produced by this project.

### ✅ 10. Concept Coherence — PASS

C1 tracked: 0 concepts. C3 advisory: 3 concepts mentioned in ≥ 3 specs.
