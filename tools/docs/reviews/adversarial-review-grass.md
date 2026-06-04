# Adversarial Review: Grass Rendering Improvements

**Spec:** `tools/docs/specs/grass_rendering_spec.md`
**Reviewer source:** self (Round 1 — preflight)
**Date:** 2026-06-04

---

## Phase 0: Epistemic Pre-Scan

### Step 0.0: Cross-Spec Validator (multi-spec project — 8 specs in `docs/specs/`)

**CRITICAL CONFLICT FOUND — blocks review until fixed.**

`phase-1-simple-tiles.md`, TC-002, explicitly asserts:

> `generator.generate_texture("grass", seed=42, density=10, sub_type="wild")` returns a `(32, 32)` numpy array containing only values `0, 1, 2, 3`.

The grass spec changes the range to `0–4`. These two specs are now in direct conflict. Any test suite running `phase-1-simple-tiles.md`'s TC-002 after the grass spec is implemented **will fail**. The test must be updated — and that update must be recorded in `phase-1-simple-tiles.md`, not silently allowed to drift.

**Resolution required:** Either update TC-002 in `phase-1-simple-tiles.md` to accept values `0–4`, or add a version-gated annotation. This must be done before BUILD.

---

### Step 0.1: Cross-Document Data Consistency

| Check | Finding |
|-------|---------|
| `DEFAULT_PALETTES` schema | Grass spec says "5 colors per entry". Current `constants.py` has 4-color tuples. The grass spec claims this is a modification — OK. But `asset_convertor_spec.md` does **not** mention `DEFAULT_PALETTES` at all (confirmed via search: zero hits). The cross-spec contract in the grass spec claims the producer is `asset_convertor_spec.md`, but this is **phantom reference** — the contract is undocumented there. |
| `generate_texture` / `quantize_image` public interface | Grass spec declares these in its `## Public Interface` table pointing to `asset_convertor_spec.md`. Confirmed via search: `asset_convertor_spec.md` does not document these functions. Only `phase-1-simple-tiles.md` does, with the conflicting 4-value range. |
| `app.py` palette loading | `on_palette_write` callback in `app.py` (L78–83) **hard-codes 4 slots**: `custom_palette = [pal[0], pal[(L-1)//3], pal[2*(L-1)//3], pal[L-1]]`. This always picks exactly 4 colors from the palette, discarding the 5th. The spec says `IT-003` will verify the GUI doesn't crash — but crashing is not the risk. **Silently discarding the 5th color (the highlight) is the real risk**, and no test covers it. |
| `quantizer.py` 5-color branch | Current code at L20–26: if `L < 4` → pad to 4; else → `np.linspace(0, L-1, 4)` — always picks 4. After the spec change, a 5-color palette passed here will **still produce only 4 mapped colors** via linspace, unless the spec's instruction ("if L == 5, use all 5") is implemented. The spec is correct, but the existing behavior creates a subtle trap for the AI coder. |

---

### Step 0.2: Externally Verifiable Claims

None. All claims are internal (tuft matrices, numpy behavior, PIL behavior). No external APIs or services cited.

---

### Step 0.3: Hidden Assumptions

| # | Assumption (marked or unmarked) | Risk | Status |
|---|--------------------------------|------|--------|
| A1 | Marked: `val` inside tufts only goes up to 4 | Low | Handled — validation in `generate_texture`. ✅ |
| A2 | Marked: `apply_stamp` safely modulo-wraps negatives | Low | Handled — Python modulo arithmetic. ✅ |
| A3 | Marked: 5 colors per palette sufficient | Low | Reasonable. ✅ |
| A4 | **Unmarked:** The new tufts (`TUFT_CRESCENT`, `TUFT_SWEEP_LEFT`, etc.) will be defined in `constants.py` | HIGH | Spec §1.2 refers to `TUFT_CRESCENT`, `TUFT_SWEEP_LEFT` as if they will exist, but §1.1 only gives one example matrix (`TUFT_CRESCENT_1`). The complete set of new tufts — how many? what shapes? — is **never specified**. An AI coder will invent them. |
| A5 | **Unmarked:** The background noise initialization in `generate_texture` still only uses tones `1` and `2` post-migration | MEDIUM | Spec §1.2 says "ensure that the background noise initialization is adjusted for the 5-tone system (e.g., using tones 1 and 2, leaving 0 for deep shadow...)" — the `e.g.` makes this optional-sounding. An AI may choose different tones. |
| A6 | **Unmarked:** The 32x32 grid initialization `np.ones((32, 32))` (tone 1) is still correct for the 5-tone system | MEDIUM | Spec never explicitly says the grid initialization tone remains `1`. If tone semantics shift, this could be wrong. |
| A7 | **Unmarked:** `apply_composite_stamp` requires no changes beyond tone `4` support | LOW | The spec says "if necessary" for `apply_composite_stamp` — but the function already handles arbitrary integer values (just writes `val` to the grid). This assumption is valid, but should be stated. |

---

### Step 0.4: POC Gate — External API/CLI Fact Verification

All facts are internal to the codebase. No CLI flags, external API endpoints, or external JSON schemas cited.

| Claim | Classification | Risk |
|-------|---------------|------|
| Numpy modulo handles negative indices correctly | VERIFIED — Python/numpy behavior, tested via the existing toroidal wrapping | LOW |
| PIL `Image.fromarray(out, "RGB")` handles 5-color output | CITED — standard PIL behavior, no actual call captured in spec | LOW |

All LOW-risk claims are acceptable without POC.

---

### Step 0.5: Pre-Commitment Predictions

1. **The quantizer will still pick only 4 colors after the change** — the `np.linspace` branch and the `< 4` pad branch both cap at 4. The spec says "if L == 5, use all 5" but the existing code structure resists this addition.
2. **The GUI palette picker will silently drop the 5th color** — `on_palette_write` hard-codes exactly 4 slots. No test covers this path.
3. **The new tuft set is underspecified** — the spec names `TUFT_CRESCENT`, `TUFT_SWEEP_LEFT`, etc. but never defines their matrices, leaving the AI to improvise.
4. **The cross-spec conflict with `phase-1-simple-tiles.md` TC-002 will cause test failure** — the 4-value range assertion will break.
5. **The `generate_texture` sub-type → tuft list mapping is not updated in the spec** — the spec says "update the tuft lists" but doesn't say which existing sub-types (classic, short, curly, wild) get which new tufts, or whether new sub-types are added.

---

## Phase 1: Multi-Lens Analysis

### 🔒 Security

**Central question:** What attack surface or data integrity risk does this change introduce?

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | No security concerns | — | This is a local procedural texture generator with no network calls, auth, or user input beyond integers. | N/A |

**Clean areas:** No hardcoded secrets, no external calls, no user-controlled file paths.

---

### 💰 Cost

**Central question:** What scales linearly vs. exponentially with the change?

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | 5x5 tufts vs 4x4: pixel-loop cost increase | LOW | `apply_composite_stamp` iterates `n_rows × n_cols` per tuft. 5x5 = 25 ops vs 3x3 = 9 ops for classic tufts. With toroidal neighbor expansion (9x copies), cost is still O(density × 225) — negligible at 32x32 scale. | Accept. No action needed. |
| 2 | Background noise pass: `density * 3` random writes | LOW | Already present in current code. 5-tone system doesn't change this. | Accept. |

**Clean areas:** No new dependencies, no storage growth, no external calls.

---

### 🔧 Ops

**Central question:** What's observable? What fails silently?

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | Silent palette truncation in GUI | HIGH | `on_palette_write` (app.py L78–83) hard-codes 4 picks from the palette regardless of length. A 5-color palette produces a 4-color `custom_palette`. `quantize_image` then receives a 4-color list and maps values 0–3 correctly — but value `4` from the new tufts will be **clamped to `3`** by the old clamping logic. No error, no warning. | Spec must require fixing `on_palette_write` to pick 5 colors when palette has ≥5. Also fix the clamping. |
| 2 | `generate_thread` exception handler swallows details | LOW | `app.py` L258: `except Exception as e: ... f"Generation failed: {e}"`. This is pre-existing, not introduced by the spec. | Out of scope — pre-existing. |

**Clean areas:** No deployment concerns, no migration path needed (pure code change).

---

### 🚀 Perf

**Central question:** What's the critical path? What can be parallelized?

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | Pixel-loop in `quantize_image` is O(h×w) with Python loops | MEDIUM | Lines 31–39 in `quantizer.py` iterate every pixel in Python. At 32x32, this is 1024 iterations — acceptable. But if grid size ever changes, this becomes a bottleneck. The spec says "never resize to 48x48" — but no test enforces grid size. | Accept for now. Add anti-pattern explicitly: "Never vectorize prematurely — profile at scale first." |
| 2 | All-tufts expansion (9x copies for toroidal neighbors) | LOW | `generate_texture` L73–76 creates 9 copies of base_tufts. With density=100: 9 × (300+100) = 3600 tuft draws. Each 5x5 tuft = 25 ops → 90,000 write ops max. Still under 100µs. | Accept. |

**Clean areas:** Numpy array writes are O(1) per pixel. Seed-based RNG is deterministic and fast.

---

### 👤 User

**Central question:** Error messages, edge cases, first-time use, cognitive load.

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | GUI palette picker labels don't match 5-color semantics | HIGH | `app.py` L144: `labels = ["Shadow", "Midtone 1", "Midtone 2", "Highlight"]` — 4 labels for 4 buttons. If the GUI is updated to support 5 colors, a 5th label and button must be added. The spec doesn't mention this UI change at all. | Spec must explicitly state whether the GUI palette picker gains a 5th slot or not. |
| 2 | New sub-types not exposed in GUI | MEDIUM | The spec mentions `TUFT_CRESCENT`, `TUFT_SWEEP_LEFT`, etc. as replacements for existing tufts, but it's unclear if new sub-types (e.g., "Crescent") appear in the GUI dropdown. The spec §1.2 says "update the tuft lists" without clarifying sub-type routing. | Spec must state: are new tufts replacing existing sub-type pools, or added as new sub-types in the dropdown? |
| 3 | `custom_palette` default in `app.py` is still 4-color RGBA on init | MEDIUM | `app.py` L54: `self.custom_palette = [(0,0,0), (85,85,85), (170,170,170), (255,255,255)]` — 4 colors. If `quantize_image` is updated to use 5 colors and `custom_palette` is never updated, the fallback path silently uses 4 colors. | Spec must address initialization path for `custom_palette`. |

**Clean areas:** Export path unchanged. Seed and density UX unchanged.

---

### ♻️ Evol

**Central question:** What changes if we add a 6th color? A new sub-type? Swap the generator?

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | Tone count is hardcoded in multiple places | HIGH | `quantizer.py` will have `if L == 5` branch. `app.py` will have 4-slot palette picker. `constants.py` will have 5-color tuples. Adding a 6th tone requires changes in at least 4 files. | The spec should acknowledge this technical debt or add a `MAX_TONES` constant to centralize the constraint. |
| 2 | Sub-type → tuft mapping is undocumented | MEDIUM | The existing `generate_texture` maps `sub_type` strings to tuft lists inline. Adding new tufts without documenting the routing means the next developer (or AI) must reverse-engineer the intent from code. | Add a data structure (dict or table) in the spec defining sub_type → tuft list mapping. |

**Clean areas:** `apply_composite_stamp` is already tone-agnostic (writes `val` directly). This is a good extension point — the spec leverages it correctly.

---

### 🎯 Scope

**Central question:** Is there unrequested code? Over-abstraction? Future-proofing nobody asked for?

| # | Finding | Severity | Evidence | Recommendation |
|---|---------|----------|----------|----------------|
| 1 | Spec §1.1 says "add at least 6 new palettes" but only names 5 | MEDIUM | "e.g., 'Grass (Crimson)', 'Grass (Teal)', 'Grass (Snow)', 'Grass (Autumn)', 'Grass (Purple)'" — that's 5 examples for "at least 6". An AI coder will add exactly those 5. | Either list 6 explicitly, or say "add the following 5 palettes" and drop "at least 6." |
| 2 | "Replace or extend" tuft arrays (§1.1) is ambiguous | HIGH | "Replace or extend the small TUFT_* arrays with larger 5x5 and 6x6 matrices." An AI coder must choose: do old tufts (TUFT_CLASSIC_RIGHT etc.) survive? Get extended? Get deleted? The anti-pattern §2.5 says "preserve backward compatibility of naming" but this only applies to palettes. Tufts are unaddressed. | Spec must state explicitly: are the old 4-tone TUFT_* constants deleted, replaced, or kept alongside new ones? |
| 3 | 6x6 tuft size introduced without anti-pattern or validation | MEDIUM | §1.1 says "5x5 and 6x6 matrices." But anti-pattern §2.4 says "never resize the grid from 32x32 to 48x48." A 6x6 tuft fits within a 32x32 grid. However, toroidal wrapping uses `% 32` — a 6x6 tuft stamped at position (28, 28) would wrap correctly. But IT-002 only tests "6x6 tuft at edge" for crashes — it doesn't verify the wrapped pixels are correct. | Add explicit verification that 6x6 tufts produce correct toroidal wrapping, not just no crash. |

---

## Phase 2: Cross-Lens Synthesis

### Cross-Reference Matrix

| Finding A | Finding B | Signal Type | Description |
|-----------|-----------|-------------|-------------|
| 🔧 Ops #1 (GUI silent truncation) | 👤 User #1 (4-label palette picker) | 🎯 Convergence | Both flag the same gap: GUI palette handling not updated for 5 colors |
| 🔧 Ops #1 (clamping still at 3) | ♻️ Evol #1 (hardcoded tone count) | 🔁 Pattern | Hardcoded "4" appears in quantizer, GUI picker, and clamping — systemic magic number problem |
| 👤 User #2 (new sub-types in GUI?) | 🎯 Scope #2 ("replace or extend" ambiguity) | 🎯 Convergence | Both flag the same gap: sub-type → tuft routing is unspecified |
| ♻️ Evol #2 (sub-type mapping undocumented) | 👤 User #2 (new sub-types not exposed) | 🔁 Pattern | Routing and UX are both undefined — no single place defines what sub-types exist and how they map |
| 🎯 Scope #2 ("replace or extend" tufts) | 🎯 Scope #3 (6x6 tufts unvalidated) | 🔁 Pattern | Tuft definition scope is consistently under-specified throughout §1.1–1.2 |
| Cross-spec TC-002 conflict | 🔧 Ops #1 (silent clamping failure) | 🎯 Convergence | Both stem from the 4→5 tone upgrade touching more consumers than the spec acknowledges |

---

### Signals

#### 🎯 Convergence 1: GUI is not upgraded for 5 colors

**🔧 Ops found:** `on_palette_write` always produces 4 colors; value `4` will be clamped to `3` silently.
**👤 User found:** 4 palette labels, 4 buttons — no 5th slot exists in the UI.

**Why this matters:** Two independent perspectives flag the same gap. The spec treats `IT-003` ("GUI doesn't crash") as sufficient validation, but the real failure is silent visual corruption: highlights (tone 4) in tufts render as midtone 2 (tone 3) color because the 5th color is never passed to `quantize_image`.

**Action:** The spec must explicitly address GUI palette-picker update: add a 5th color slot, update `custom_palette` initialization, and update `on_palette_write` to extract 5 colors. Or explicitly state it is out of scope with a documented limitation.

---

#### 🎯 Convergence 2: Sub-type → tuft routing is entirely unspecified

**🎯 Scope found:** "Replace or extend" tuft arrays is ambiguous — old tufts survival unclear.
**👤 User found:** New tufts exist but no sub-type routing defined — GUI dropdown unaddressed.

**Why this matters:** An AI coder implementing §1.2 will read "update the tuft lists in `generate_texture` to use the new tufts (TUFT_CRESCENT, TUFT_SWEEP_LEFT, etc.)" and must invent: (a) tuft matrix contents, (b) which sub_type uses which tufts, (c) whether old tufts survive. This produces 100% improvised code for the most creative part of the feature.

**Action:** The spec must provide: (a) the complete matrix for each new tuft, and (b) the explicit sub_type → tuft list mapping table.

---

#### 🔁 Pattern: Hardcoded "4" (formerly the max tone) is not systematically replaced

**Instances:**
- `quantizer.py` L22: `(4 - L)` — pads to 4
- `quantizer.py` L25: `np.linspace(0, L-1, 4)` — picks 4
- `quantizer.py` L37: `if val > 3: val = 3` — caps at 3
- `app.py` L78–83: 4-slot custom_palette
- `app.py` L144: 4 labels
- Anti-pattern §2.1: correctly identifies the `val > 3` clamping issue

**Root cause:** The spec identifies one instance (clamping in `quantizer.py`) but not the systemic nature. All five locations contain the same hardcoded magic number that must change to 5. The spec only mentions §1.3 (quantizer update) and leaves the GUI changes completely unaddressed.

**Fix:** The spec must enumerate ALL locations where `4` or `3` (as max tone) appears and specify the fix for each. Alternatively, introduce `MAX_TONE = 4` as a named constant in `constants.py` and reference it from all sites.

---

#### 🔁 Pattern: Tuft definition scope under-specified throughout

**Instances:**
- §1.1: "Replace or extend the TUFT_* arrays with larger 5x5 and 6x6 matrices"
- §1.1: Only `TUFT_CRESCENT_1` matrix given as example; no others defined
- §1.2: References `TUFT_CRESCENT`, `TUFT_SWEEP_LEFT` as if they will exist
- §1.2: "Update the tuft lists in `generate_texture`" — which lists? which sub-types?

**Root cause:** The spec defers actual tuft design to the AI coder, treating it as implementation detail. But tuft design IS the visual output of this feature — it is the primary deliverable. Leaving it unspecified means the AI will produce functionally correct but visually arbitrary results.

**Fix:** Provide the complete matrix definition for every new tuft. Even if the exact shapes evolve, the spec must provide at minimum one complete, working example per sub-type.

---

#### ⚔️ Tension: Backward compatibility of palette naming vs. 5-color schema change

**🎯 Scope says:** "Preserve backward compatibility of naming by updating existing tuples to length 5" (anti-pattern §2.5).
**♻️ Evol says:** Any consumer that unpacks palette tuples as exactly-4 will break.

**The tradeoff:**
1. Extend existing palettes to 5 colors → consumers that index by position `[3]` still work; those that unpack as `(a, b, c, d)` will raise `ValueError`.
2. Add 5-color palettes as new names alongside the 4-color originals → safe but doubles the palette count.

**Recommendation:** The spec should state: "No consumer unpacks palette tuples by position — all consumers iterate or index dynamically." This must be verified (it is true in the current `app.py` which uses `sorted_palette[i]`). If true, option 1 is safe. State it explicitly in the spec with a cross-reference to `app.py` line numbers.

---

#### 🕳️ Blind spot: `palette_loader.py` / `palettes.json` path

**Why no lens caught it:** All lenses focused on `constants.py` as the palette source. But `app.py` has a **three-way palette loading priority**: (1) `palettes.json` from a config dir, (2) `palettes.json` from CWD, (3) `DEFAULT_PALETTES` fallback.

**Risk:** If a user has an external `palettes.json` in their config dir with 4-color palettes, the `DEFAULT_PALETTES` update in `constants.py` is never used. The spec's "add 6 new palettes to `DEFAULT_PALETTES`" change silently has no effect for any user with an external palette file.

**Recommendation:** The spec must address the `palettes.json` migration path. Either: (a) update the schema definition in `palette_loader.py` to handle both 4 and 5-color entries, or (b) explicitly document that `palettes.json` users must manually update their files (user-facing documentation change).

---

#### 🕳️ Blind spot: `quantize_image` parameter name mismatch

**Why no lens caught it:** The spec lists the public interface as `quantize_image(noise_map, palette)` — matching the actual source. But in `phase-1-simple-tiles.md` the parameter is named `index_map`. This naming inconsistency is cosmetic but becomes a real issue when AI coders reference either spec to write tests or docstrings.

**Risk:** Low. But it signals that `phase-1-simple-tiles.md` may have other contract drifts worth reviewing.

**Recommendation:** Standardize parameter names across specs. Use `noise_map` as canonical (matches actual source).

---

## Phase 3: Adversarial Stress-Test

### Cross-Lens Signals Used as Input

**Convergences (high confidence):**
- GUI palette picker not updated for 5 colors → silent visual corruption
- Sub-type → tuft routing entirely unspecified → 100% improvised code

**Patterns (systemic):**
- Hardcoded "4" appears in 5 locations — spec only fixes 1
- Tuft scope under-specified in 4 distinct places

**Blind spots (primary targets):**
- `palettes.json` external config bypasses `DEFAULT_PALETTES` update
- `quantize_image` parameter name drift across specs

---

### Findings Table

| Severity | # | Finding | Location | Problem | Fix |
|----------|---|---------|----------|---------|-----|
| **CRITICAL** | C-001 | `quantize_image` `else` branch always picks 4 colors | `quantizer.py` L23–26 + spec §1.3 | Spec says "if L == 5, use all 5 colors." But the current `else` branch: `np.linspace(0, L-1, 4)` always returns 4 indices regardless of L. After change, a 5-color palette passed to `quantize_image` still produces only 4 mapped colors. Tone 4 in the noise map goes to `mapped_palette[4]` which doesn't exist → `IndexError`. Or if the AI adds `if val > 4: val = 4` without fixing linspace, tone 4 maps to the wrong color. | Spec must specify the exact replacement logic: `if L == 5: mapped_palette = sorted_palette` (use all 5 directly). Remove the linspace branch for the 5-color case. |
| **CRITICAL** | C-002 | Cross-spec conflict: `phase-1-simple-tiles.md` TC-002 asserts values `0,1,2,3` | `phase-1-simple-tiles.md` TC-002 | The test `assert all values in {0,1,2,3}` will FAIL after this spec is implemented. No fix is mentioned in the grass spec. | Grass spec must include: "Update `phase-1-simple-tiles.md` TC-002 to accept values `0,1,2,3,4` after this change." |
| **CRITICAL** | C-003 | New tuft matrices never defined | Spec §1.1–1.2 | `TUFT_CRESCENT`, `TUFT_SWEEP_LEFT`, and all other new tufts are referenced but never defined. Only `TUFT_CRESCENT_1` has an example. An AI coder will invent the remaining matrices, producing visually arbitrary output. | Provide the complete 5x5 matrix for every new tuft. This is the primary visual deliverable of the feature. |
| **HIGH** | H-001 | GUI palette picker hard-codes 4 slots, silently drops 5th color | `app.py` L78–83, L144, L54 | After update, grass tufts produce value `4` (5th tone). The GUI's `custom_palette` is always 4 colors. `quantize_image` receives 4 colors. Tone `4` either triggers an `IndexError` or (after clamping fix) renders as color `3`. Tufts lose their brightest highlight. | Spec must require: (a) update `on_palette_write` to extract 5 colors; (b) add 5th label + color button to GUI; (c) update `self.custom_palette` default to include 5th color. |
| **HIGH** | H-002 | Sub-type → tuft routing for new tufts is unspecified | Spec §1.2 | Spec says "update the tuft lists in `generate_texture` to use the new tufts." An AI coder must decide: do new tufts replace classic/short/curly/wild, or create a new sub-type? The GUI subtypes list (`self.subtypes = ["Classic", "Short", "Curly", "Wild"]`) is never mentioned. | Spec must provide explicit mapping: `sub_type -> [TUFT_A, TUFT_B, ...]` for each sub-type after the change. |
| **HIGH** | H-003 | `palettes.json` external config bypasses `DEFAULT_PALETTES` | `app.py` L33–42 | Users with an external `palettes.json` never see the new palettes added to `DEFAULT_PALETTES`. The spec's "add 6 new palettes" has zero effect for these users. | Spec must address: either document the `palettes.json` schema update required, or note this as a known limitation. |
| **MEDIUM** | M-001 | Clamping in `quantizer.py` still caps at 3 | `quantizer.py` L37 | Spec anti-pattern §2.1 correctly identifies this. But the spec §1.3 says "ensure the `val` capping logic correctly bounds between 0 and 4" without specifying the exact code. An AI might add a second clamp instead of replacing the existing one. | Spec must show the exact replacement: `if val > 4: val = 4` replaces `if val > 3: val = 3`. Show the diff. |
| **MEDIUM** | M-002 | "At least 6 new palettes" but only 5 are named | Spec §1.1 | "Add at least 6 new palettes (e.g., Crimson, Teal, Snow, Autumn, Purple)" — 5 examples. AI will add 5. | Change to "Add the following 5 palettes: [list]" or add a 6th to the list. |
| **MEDIUM** | M-003 | IT-002 tests for no-crash, not for correctness | Spec §3 IT-002 | "Verify toroidal wrapping correctly handles a 6x6 tuft placed at the edge without crashing." Crashing is not the risk — incorrect pixel placement after wrap is. | Update IT-002: "Assert that a 6x6 tuft stamped at position (29, 29) on a 32x32 grid produces the same result as the reference stamp with expected wrapped coordinates." |
| **LOW** | L-001 | `apply_composite_stamp` mention in spec is ambiguous | Spec §1.2 | "Update `apply_stamp` and `apply_composite_stamp` (if necessary)" — but `apply_composite_stamp` already writes `val` directly with no clamping. The "(if necessary)" clause leaves it to the AI to decide. | Spec should explicitly state: "`apply_composite_stamp` requires NO changes — it already writes `val` directly. `apply_stamp` also requires no changes (it uses `tone` parameter, not val). The clamping to update is ONLY in `quantize_image`." |
| **LOW** | L-002 | `DEFAULT_COLOR_*` constants in `constants.py` are still 4-color | `constants.py` L91–94 | `DEFAULT_COLOR_SHADOW`, `DEFAULT_COLOR_BASE`, `DEFAULT_COLOR_HIGHLIGHT`, `DEFAULT_COLOR_ACCENT` — 4 single-color defaults. These are not palette tuples, just fallback single colors. They are separate from `DEFAULT_PALETTES`. But the spec doesn't mention them, leaving an AI to wonder if they need a 5th. | Spec should explicitly state these are out of scope — they are not related to the palette change. |

---

## Phase 3: Feature-Specific Requirements Quality Check

### FR-1: 5x5/6x6 Tuft Shapes (F1)

| FR | Dimension | Finding | Tag | Severity |
|----|-----------|---------|-----|----------|
| F1 | Completeness | Only `TUFT_CRESCENT_1` matrix given. `TUFT_CRESCENT`, `TUFT_SWEEP_LEFT`, and all others referenced in §1.2 are not defined. | [Gap] | CRITICAL |
| F1 | Completeness | "Replace or extend" — survival of `TUFT_CLASSIC_RIGHT`, `TUFT_CLASSIC_LEFT`, `TUFT_CLASSIC_V`, `TUFT_SHORT_*`, `TUFT_CURLY_*`, `TUFT_WILD_*` not stated | [Ambiguity] | HIGH |
| F1 | Testability | TC-004 asserts tuft matrices contain only `-1,0,1,2,3,4`. Can assert: `all(v in {-1,0,1,2,3,4} for row in tuft for v in row)`. ✅ Testable. | — | PASS |
| F1 | Cross-Requirement | F1 tufts produce val=4. If F2 palettes only provide 4 colors (via GUI), val=4 is never rendered correctly. | [Conflict] | HIGH (→ C-001, H-001) |
| F1 | Edge Cases | 6x6 tuft at edge (0, 27) → rows 27–32 — last 5 rows partially out of bounds. The generator uses `if 0 <= px < 32 and 0 <= py < 32` — out-of-bound pixels are skipped, not toroidally wrapped, in the all-tufts draw pass. IT-002 tests "at edge without crashing" — but skipping pixels ≠ toroidal wrapping. | [Gap] | MEDIUM |

### FR-2: 5-Color Palettes (F2)

| FR | Dimension | Finding | Tag | Severity |
|----|-----------|---------|-----|----------|
| F2 | Completeness | "At least 6 new palettes" — only 5 named. | [Ambiguity] | MEDIUM |
| F2 | Completeness | 5th color extraction path in `quantize_image` is not fully specified (linspace branch always picks 4) | [Gap] | CRITICAL (→ C-001) |
| F2 | Testability | TC-001: "Handles a 5-color palette and correctly maps values 0–4." Can assert: `image = quantize_image(np.array([[0,1,2,3,4]]*1), 5-color-palette); assert len(set(image.getdata())) == 5`. ✅ Testable — once C-001 is fixed. |  — | PASS (pending fix) |
| F2 | Cross-Requirement | F2 palette update in `DEFAULT_PALETTES` is invisible to users with `palettes.json` config. | [Gap] | HIGH (→ H-003) |
| F2 | Edge Cases | TC-002: "Gracefully handles palettes with fewer than 5 colors by repeating the lightest color." Current spec behavior for `L < 4` pads to 4. For `L = 4`, linspace picks 4. Spec needs to clarify the behavior for `L = 4` specifically after the change (it's neither "< 5" nor "== 5"). | [Ambiguity] | MEDIUM |

---

## Convergence Status

**Round 1 findings:**

| ID | Severity | Status |
|----|----------|--------|
| C-001 | CRITICAL | ❌ Open — must fix before BUILD |
| C-002 | CRITICAL | ❌ Open — must fix before BUILD |
| C-003 | CRITICAL | ❌ Open — must fix before BUILD |
| H-001 | HIGH | ❌ Open — must fix before BUILD |
| H-002 | HIGH | ❌ Open — must fix before BUILD |
| H-003 | HIGH | ❌ Open — must fix before BUILD |
| M-001 | MEDIUM | ❌ Open |
| M-002 | MEDIUM | ❌ Open |
| M-003 | MEDIUM | ❌ Open |
| L-001 | LOW | ❌ Open |
| L-002 | LOW | ❌ Open |

**Status: NOT CONVERGED — 3 CRITICALs require spec fixes before BUILD entry.**

---

## Exit Criteria

- [x] Pre-scan: cross-doc consistency, verifiable claims, hidden assumptions checked
- [x] Multi-lens: all 7 lenses applied, findings documented
- [x] Cross-synthesis: matrix built, signals identified (2 tensions, 2 convergences, 2 patterns, 2 blind spots)
- [ ] Zero CRITICAL issues remaining — **BLOCKED: 3 CRITICALs open**
- [x] All HIGH issues documented with explicit decision: fix now / accept risk / defer
- [ ] Spec Gate re-run after CRITICAL fixes — pending

**BUILD is blocked until C-001, C-002, C-003 are resolved in the spec.**
