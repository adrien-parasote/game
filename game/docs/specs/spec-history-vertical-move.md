# Spec History — Vertical Move Refactoring

> Archive of adversarial review rounds and corrections.
> Main spec: `vertical-move.md`

## Revision History

| Version | Date | Event |
|---------|------|-------|
| v10 | 2026-06-17 | Initial audited spec |
| v11 | 2026-06-17 | Round 0 (self) — 2 CRITICAL + 8 HIGH found: A1 sign convention, A6 field init, A2 ladder unspec'd, A3 execution order, A4 stale _vertical_move, A5 intercepted_dir undefined |
| v12 | 2026-06-17 | Round 0 fixes applied — all CRITICAL/HIGH resolved |
| v13 | 2026-06-17 | Round 1 (cross-model) — 4 new: B1-B4. All resolved. |
| v14 | 2026-06-17 | Round 2 (cross-model) — 1 CRITICAL + 2 HIGH: C1 move_map mismatch, C2 stair_phase→stair_half, C3 sign convention ground truth, C4-C6 medium. All resolved. |
| v15 | 2026-06-17 | Round 3 (cross-model, Claude Opus 4.6) — 1 CRITICAL + 3 HIGH: D1 §4.2 property resolution, D2 clip deletion checklist, D3 arrival re-fetch contradiction, D4 §4.3/§4.0 order contradiction. All resolved. Consolidated after 3 rounds. |

## Key User Decisions

| Decision | Date | Rationale |
|----------|------|-----------|
| C3: Sign convention — code is correct (signed offset, ADD to Y) | 2026-06-17 | Level designer sets sign in Tiled: negative=up, positive=down |
| C5: Delete `stair_clip` per blueprint | 2026-06-17 | Separate feature may reintroduce later |
| D1: Keep `direction`+comma heuristic (Option A) | 2026-06-17 | Avoids Tiled map updates; spec updated to match |
| D3: No re-fetch on arrival (Option A) | 2026-06-17 | Cleaner; `_vertical_move` already holds target props from `start_move()` |

## Consolidation Notes (2026-06-17)

**Contradiction sweep:** 3 contradictions found (AP#1, AP#5, Error row 1) — all stemming from §4.2's `direction`+comma heuristic not being reflected in anti-patterns and error handling. Fixed.

**Correction Log:** No correction log section existed — nothing to archive.

**Anti-pattern dedup:** AP#1 and AP#5 rewritten to be consistent with §4.2. No duplicates found.

**Test case audit:** All test cases remain relevant. IT-003 (NPC) noted as aspirational/deferred.
