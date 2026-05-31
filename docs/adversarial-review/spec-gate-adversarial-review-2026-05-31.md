# Spec Gate + Adversarial Review — 2026-05-31

> **Scope:** All 22 specs in `docs/game/specs/`
> **Method:** Deterministic pre-check (`spec_precheck.py`) → LLM adversarial review (2 parallel reviewers) → cross-doc consistency audit → execution simulation

---

## 1. Deterministic Pre-Check Results

**Score: 117 PASS / 29 PARTIAL / 21 FAIL** across 167 check-points (22 specs × 7–8 checks each)

### Per-Spec Scoring

| Spec | Doc Type | Anti-Patterns | Test Cases | Error Handling | Deep Links | Cross-Spec | Constraints | Score |
|------|----------|---------------|------------|----------------|------------|------------|-------------|-------|
| `00_MASTER.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7/7 |
| `engine-core.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7/7 |
| `map-world-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `camera-rendering.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7/7 |
| `entities-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `npc-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `intra-map-teleport.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `lighting-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7/7 |
| `save-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | 6/7 |
| `asset-i18n.md` | ❌ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 5.5/7 |
| `audio-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `inventory-system.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `chest-ui.md` | ✅ | ✅ | 🟡 | ✅ | ✅ | ❌ | ✅ | 5.5/7 |
| `dialogue-system.md` | ✅ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | 6/7 |
| `performance-system.md` | ❌ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 5.5/7 |
| `development-quality.md` | ❌ | 🟡 | ✅ | ✅ | ❌ | 🟡 | ✅ | 4/7 |
| `pixel-perfect-occlusion.md` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7/7 |
| `code-quality-constants-i18n.md` | ✅ | ✅ | 🟡 | ✅ | ❌ | 🟡 | ✅ | 5/7 |
| `remediation_01_dt_text_cache.md` | ✅ | ✅ | ❌ | ✅ | ✅ | 🟡 | ✅ | 5.5/7 |
| `remediation_02_saves_assets_pyright.md` | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 6.5/7 |
| `remediation_03_modernization.md` | ✅ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | 6/7 |
| `pygame_ce_python_312_best_practices.md` | ❌ | ❌ | ❌ | ✅ | ❌ | 🟡 | ✅ | 3/7 |

**Legend:** ✅ PASS · 🟡 PARTIAL · ❌ FAIL

---

## 2. Adversarial Review — Findings by Severity

### 🔴 CRITICAL (3 findings)

#### CRIT-01 — Contradictory `_apply_partial_occlusion` walk guard (camera-rendering.md ↔ intra-map-teleport.md)
- **Location:** `camera-rendering.md` §4.3.2 L205-212 vs `intra-map-teleport.md` §4.6 L275-284
- **Problem:** camera-rendering.md says `_apply_partial_occlusion` is ALWAYS called, with the walk guard skipping only the player sprite internally. intra-map-teleport.md says `draw_scene()` skips `_apply_partial_occlusion()` **entirely** during walk. camera-rendering.md §anti-patterns (L519) explicitly warns against the global guard that intra-map-teleport.md specifies.
- **Impact:** During scripted walk, ALL NPCs lose occlusion — visual regression.
- **Fix:** Update `intra-map-teleport.md` §4.6 L275-284 to always call `_apply_partial_occlusion`, matching camera-rendering.md's internal guard pattern.

#### CRIT-02 — `SHADOW_OFFSET` type mismatch: tuple (MASTER) vs int (code)
- **Location:** `00_MASTER.md` §3 L82 vs `hud_constants.py:16` vs `remediation_01_dt_text_cache.md` §Step 2 L158
- **Problem:** MASTER spec defines `SHADOW_OFFSET = (1, 1)` as tuple. Actual code: `SHADOW_OFFSET: int = 1`. remediation_01 uses it as scalar: `center[0] + SHADOW_OFFSET`. An AI coder reading MASTER would use tuple indexing → `TypeError: 'int' object is not subscriptable`.
- **Fix:** Update MASTER spec: `SHADOW_OFFSET | hud_constants.py | 1 | Text shadow offset (int, applied to both X and Y)`.

#### CRIT-03 — Contradictory chest slot grid: 14 vs 20 within chest-ui.md
- **Location:** `chest-ui.md` §2 A-04 (L33) vs §4.3 (L79)
- **Problem:** Assumption A-04 says "7×2 = 14 slots" but is resolved to "10×2 = 20 slots" in §4.3. Both values coexist in the same document. Code confirms `_SLOT_COLS = 10`.
- **Fix:** Update A-04 text: "The slot grid for the chest is **10 columns × 2 rows (20 slots)** — validated (resolved)."

---

### 🟠 HIGH (10 findings)

#### HIGH-01 — `MAX_DT_CLAMP = 10.0` conflated with physics DT clamping
- **Location:** `00_MASTER.md` L79 vs `config.py:105` (`DT_MAX = 0.1`)
- **Problem:** MASTER says `MAX_DT_CLAMP = 10.0` (actually for in-game time in `time_system.py`), not physics. An AI coder would use 10.0 for physics clamping — 100× too large.
- **Fix:** List both: `DT_MAX | config.py | 0.1 | Physics delta clamp` and `MAX_DT_CLAMP | time_system.py | 10.0 | In-game time acceleration clamp`.

#### HIGH-02 — `footstep_material` vs `material` property name mismatch
- **Location:** `audio-system.md` §6.1 L178 vs `map-world-system.md` §4.2 L94-95
- **Problem:** Audio spec queries tile property `footstep_material`, map spec returns `material`. Different names → every tile query returns `None`.
- **Fix:** Standardize to `material` in audio-system.md §6.1.

#### HIGH-03 — Chest title text: "coffre" (chest-ui.md) vs "Chest" (code)
- **Location:** `chest-ui.md` §4.4 L87 vs `chest_constants.py:54`
- **Problem:** Spec says hardcoded `"coffre"` (French). Code uses `"Chest"`.
- **Fix:** Update chest-ui.md §4.4: use `CHEST_TITLE_TEXT` constant (value: `"Chest"`).

#### HIGH-04 — `Settings.CHEST_MAX_SLOTS` doesn't exist
- **Location:** `inventory-system.md` §4.1 L99
- **Problem:** Spec references `Settings.CHEST_MAX_SLOTS` but constant lives in `loot_table.py` as module-level `CHEST_MAX_SLOTS`, not on `Settings`.
- **Fix:** Change to `CHEST_MAX_SLOTS` from `src.engine.loot_table`.

#### HIGH-05 — `OccludingRect` type alias: 2-element (remediation_03) vs 3-element (pixel-perfect-occlusion)
- **Location:** `remediation_03_modernization.md` §Step 9 L107 vs `pixel-perfect-occlusion.md` §3.2 L107
- **Problem:** remediation_03 defines 2-element tuple. pixel-perfect-occlusion extends to 3-element. Code confirms 3-element.
- **Fix:** Update remediation_03 §Step 9: `type OccludingRect = list[tuple[pygame.Rect, int, pygame.Surface | None]]`.

#### HIGH-06 — Static NPC animation condition needs pseudocode
- **Location:** `npc-system.md` §3.2 L119
- **Problem:** Dense boolean condition for animation loop is error-prone: "MUST explicitly increment `frame_index` if `sub_type == 'static_npc'` and `state != 'interact'`, or if `is_moving`". Two developers would implement this differently.
- **Fix:** Add pseudocode block:
  ```python
  should_animate = self.is_moving or (self.sub_type == 'static_npc' and self.state != 'interact')
  should_reset_frame = not self.is_moving and self._was_moving and self.sub_type != 'static_npc'
  ```

#### HIGH-07 — Night brightness formula inconsistency (engine-core vs lighting-system)
- **Location:** `engine-core.md` §9 L167 vs `lighting-system.md` §2-3
- **Problem:** engine-core uses `0.5 + 0.5 * sin(2π*hour/24 - π/2)`, lighting-system uses `sun_angle = 2π*(hour-6)/24`. Different phase origins → different time-of-day curves.
- **Fix:** engine-core.md §9 should defer to lighting-system.md for the authoritative brightness formula.

#### HIGH-08 — Coverage threshold: 90% (development-quality) vs 80% (coding-standards.md)
- **Location:** `development-quality.md` §1.3 L30 vs `.agents/rules/coding-standards.md`
- **Problem:** Project spec says 90% global, 100% critical. Agent rules say 80% minimum.
- **Fix:** Reconcile — either project overrides to 90% (with explicit note) or align to 80%.

#### HIGH-09 — Duplicate test case IDs in code-quality-constants-i18n.md
- **Location:** `code-quality-constants-i18n.md` L485-537 and L539-600
- **Problem:** TC-002 through TC-008 defined twice with slightly different content.
- **Fix:** Remove duplicate block (L539-600).

#### HIGH-10 — Nine-patch tail asset filename confusion (dialogue-system.md)
- **Location:** `dialogue-system.md` §3.1 L77 vs §3.2 L89
- **Problem:** Tile set table lists `21-bubble_bottom_right.png` as bottom-right corner. Algorithm step 6 references `21-bubble_queue.png` as tail. Same `21-` prefix, different assets. Confusing for an AI coder.
- **Fix:** Clarify that the `21-` prefix is a file naming convention, not a positional slot number. List both assets explicitly.

---

### 🟡 MEDIUM (23 findings)

| ID | Spec | Issue | Fix |
|----|------|-------|-----|
| MED-01 | `map-world-system.md` | `get_direction_flags` neutral joker accumulation logic underspecified — Python `set.intersection` with `{"any"}` produces `set()` | Add pseudocode: filter out `{"any"}` layers before intersecting |
| MED-02 | `camera-rendering.md` | `_apply_grass_wading_to_images` references undefined `walk_active` variable | Add `walk_active = getattr(self.game, "_intra_walk_target", None) is not None` |
| MED-03 | `camera-rendering.md` | Restoration order between occlusion and wading composites — missing constraint on `pre_occlusion_originals` | Add: "MUST always pass pre_occlusion_originals, even if empty" |
| MED-04 | `camera-rendering.md` | Simplified depth system in map-world-system.md vs detailed Y-sort pipeline | Add cross-reference note in map-world-system.md §4.1 |
| MED-05 | `entities-system.md` | Squared distance comparison not mentioned — coder might use `sqrt` | Reference engine-core.md §7.1.1 for `dist_sq` pattern |
| MED-06 | `entities-system.md` | Orthogonal alignment constant `20` not named | Decide if inline or named constant |
| MED-07 | `npc-system.md` | Guard sprite per-direction loading mechanism undocumented | Clarify Tiled `image` property → spritesheet file selection |
| MED-08 | `intra-map-teleport.md` | `_start_intra_walk` doesn't specify how `player.direction` is set | Document that `move(dt)` uses `target_pos` directly |
| MED-09 | `lighting-system.md` | Window beam cache key quantization not specified | Specify cache key: `(round(slant_offset, 1), width)` |
| MED-10 | `save-system.md` | Atomic write temp file location not specified | Specify: same directory, `os.replace()` |
| MED-11 | `save-system.md` | Thumbnail 120×120 vs slot size — scale or 1:1 not specified | Specify blit position and scaling behavior |
| MED-12 | `save-system.md` | Missing Cross-Spec Contracts section | Add Produces/Consumes/Interface |
| MED-13 | `asset-i18n.md` | Missing Document Type label | Add `> **Document Type:** Implementation` |
| MED-14 | `asset-i18n.md` | Font sizes 22/20 may not be native multiples of m5x7 pixel font | Confirm or correct to native multiples |
| MED-15 | `audio-system.md` | Three different footstep fallback behaviors | Standardize to `04-footstep` generic |
| MED-16 | `audio-system.md` | Spatial volume formula (linear vs logarithmic) not specified | Specify exact formula |
| MED-17 | `chest-ui.md` | Arrow buttons: `up_rect`=DOWN arrow, `down_rect`=UP arrow — confusing | Rename to semantic names or add mapping table |
| MED-18 | `chest-ui.md` | Auto-close distance threshold unspecified (45px vs 48px) | Specify `_RANGE_SQ_45` |
| MED-19 | `chest-ui.md` | Duplicate test IDs CHEST-U-06/07 map to same functions as 04/05 | Deduplicate or explain |
| MED-20 | `inventory-system.md` | Returned unequipped item destination when inventory full | Specify swap behavior |
| MED-21 | `development-quality.md` | `os.path.join` recommended but codebase migrated to `pathlib` | Update to `pathlib.Path` |
| MED-22 | `pixel-perfect-occlusion.md` | `tile_a > 0` treats alpha=1 as "opaque" — inconsistent with §2 text | Clarify: "any non-zero alpha" or threshold `>= 128` |
| MED-23 | `pygame_ce_python_312_best_practices.md` | Recommends `FRect` but ADR-008 deferred migration | Add project override note |

---

### 🔵 LOW (8 findings)

| ID | Spec | Issue |
|----|------|-------|
| LOW-01 | `engine-core.md` | Duplicate Test IDs CORE-R-01/R-02/R-03 |
| LOW-02 | `dialogue-system.md` | Misplaced test TC-DLG-01 (spec-documented tech debt) |
| LOW-03 | `performance-system.md` | Missing document type label |
| LOW-04 | `code-quality-constants-i18n.md` | Deep links use absolute `file://` paths |
| LOW-05 | `remediation_02` | Pyright `reportGeneralTypeIssues` deprecated in modern versions |
| LOW-06 | `remediation_03` | Only 2/3 minimum integration tests |
| LOW-07 | `pixel-perfect-occlusion.md` | Anti-pattern says "set_alpha(None)" but implementation doesn't do it |
| LOW-08 | `pygame_ce_python_312_best_practices.md` | Missing document type label, anti-patterns, deep links |

---

## 3. Cross-Document Consistency Audit

### 3.1 Verified Consistent ✅
| Topic | Specs | Status |
|-------|-------|--------|
| Interaction distance `<45px` standard, `<48px` NPC/pickup | engine-core, map-world-system, npc-system | ✅ Consistent |
| `TILE_SIZE = 32` | All specs | ✅ Consistent |
| Player depth = 1 | camera-rendering, map-world-system, entities-system | ✅ Consistent |
| Y-sort rendering order | camera-rendering, npc-system | ✅ Consistent |
| WorldState key format `{map_basename}_{tiled_id}` | map-world-system, save-system | ✅ Consistent |

### 3.2 Contradictions Found ❌
| Topic | Specs | Nature | Severity |
|-------|-------|--------|----------|
| `_apply_partial_occlusion` walk guard | camera-rendering ↔ intra-map-teleport | Global skip vs internal guard | CRITICAL |
| `SHADOW_OFFSET` type | 00_MASTER (tuple) ↔ code (int) | Type mismatch | CRITICAL |
| `OccludingRect` arity | remediation_03 (2-elem) ↔ pixel-perfect-occlusion (3-elem) | Stale typedef | HIGH |
| `material` vs `footstep_material` | map-world-system ↔ audio-system | Property name mismatch | HIGH |
| Night brightness formula | engine-core ↔ lighting-system | Phase origin mismatch | HIGH |
| Chest title text | chest-ui ("coffre") ↔ code ("Chest") | Stale French text | HIGH |
| DT clamp constant | 00_MASTER (10.0) ↔ config.py (0.1) | Wrong constant scope | HIGH |
| `os.path.join` vs `pathlib` | development-quality, 00_MASTER ↔ remediation_03 | Migration not reflected | MEDIUM |

---

## 4. Execution Simulations

### 4.1 "Player Opens Chest" (inventory + chest-ui + performance)

| Step | Action | Result |
|------|--------|--------|
| 1 | Player presses E near chest | ✅ InteractionManager triggers correctly |
| 2 | `game.chest_ui.open(obj, player)` | ✅ |
| 3 | `_compute_layout()` with `_SLOT_COLS` | ✅ Code uses 10 (spec A-04 says 7 — **CRIT-03**) |
| 4 | `_draw_title()` | ❌ Spec says "coffre", code says "Chest" (**HIGH-03**) |
| 5 | Capacity check `Settings.CHEST_MAX_SLOTS` | ❌ Would crash — constant is in `loot_table.py` (**HIGH-04**) |
| 6 | Player walks away, auto-close | ⚠️ Which threshold? 45px or 48px (**MED-18**) |

### 4.2 "NPC Walk Behind Partial Tile During Scripted Walk" (camera + intra-teleport + occlusion)

| Step | Action | Result |
|------|--------|--------|
| 1 | Scripted walk active (`_intra_walk_target` set) | ✅ |
| 2 | `draw_scene()` called | ✅ |
| 3 | Per intra-map-teleport.md: skip `_apply_partial_occlusion` entirely | ❌ NPC behind tile loses occlusion (**CRIT-01**) |
| 4 | Per camera-rendering.md: call it, skip only player | ✅ NPC correctly occluded |

### 4.3 "HUD Renders Shadow Text" (remediation_01 + MASTER)

| Step | Action | Result |
|------|--------|--------|
| 1 | `_render_text_cached()` called | ✅ |
| 2 | Shadow offset: `center[0] + SHADOW_OFFSET` | ✅ Code uses int |
| 3 | AI coder reads MASTER spec → `SHADOW_OFFSET = (1,1)` | ❌ Would use tuple indexing → crash (**CRIT-02**) |

---

## 5. Pre-Commitment Prediction Validation

| # | Prediction | Validated? |
|---|-----------|------------|
| 1 | Walk state ownership ambiguity (engine-core ↔ intra-map-teleport) | ✅ Found as CRIT-01 — even worse than predicted |
| 2 | Depth system interaction (map-world ↔ camera-rendering) | ✅ Found as MED-04 — lower severity than predicted |
| 3 | Static NPC animation loop ambiguity (npc-system) | ✅ Found as HIGH-06 |
| 4 | Chest drag-and-drop edge cases (chest-ui ↔ inventory) | ✅ Found as MED-20 |
| 5 | Speech bubble width consistency (dialogue ↔ npc-system) | ✅ Consistent — no issue found |

---

## 6. Overall Assessment

### Score: 7.5 / 10

The spec suite is **mature and generally well-structured**. The majority of specs (13/22) score ≥ 6.5/7 on the deterministic pre-check. Deep links, anti-patterns, and test case specifications are consistently present.

### Strengths
- Excellent anti-pattern documentation across core engine specs
- Linked test functions with file references in most specs
- Assumptions table with risk and validation columns
- Error handling matrices present in all core specs

### Critical Gaps
1. **3 cross-spec contradictions** that would produce runtime crashes or visual regressions
2. **MASTER spec accuracy drift** — `SHADOW_OFFSET` type, `DT_MAX` scope, `os.path.join` recommendation
3. **Stale references** in `chest-ui.md` (French text, wrong constant path) and `remediation_03` (old `OccludingRect` alias)
4. **Reference guide (`pygame_ce_python_312_best_practices.md`)** recommends patterns explicitly rejected by ADRs

### Recommended Priority Actions

| Priority | Action | Specs Affected |
|----------|--------|----------------|
| P0 | Fix CRIT-01: occlusion walk guard contradiction | intra-map-teleport.md |
| P0 | Fix CRIT-02: SHADOW_OFFSET type in MASTER | 00_MASTER.md |
| P0 | Fix CRIT-03: chest slot grid 14→20 | chest-ui.md |
| P1 | Fix HIGH-01: DT_MAX vs MAX_DT_CLAMP | 00_MASTER.md |
| P1 | Fix HIGH-02: material property name | audio-system.md |
| P1 | Fix HIGH-03: chest title "coffre"→"Chest" | chest-ui.md |
| P1 | Fix HIGH-04: CHEST_MAX_SLOTS location | inventory-system.md |
| P1 | Fix HIGH-05: OccludingRect arity | remediation_03_modernization.md |
| P1 | Fix HIGH-06: static NPC animation pseudocode | npc-system.md |
| P2 | Fix all MEDIUM findings | Multiple |
| P3 | Fix LOW findings + add missing doc type labels | 4 specs |
