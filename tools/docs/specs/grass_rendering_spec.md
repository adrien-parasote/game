# Grass Rendering Improvements Specification

> Document type: Implementation

**Covers:** F1 (Tuft Shapes), F2 (5-Color Palettes)

> **Correction Log (2026-06-04 — Adversarial Review fixes):**
> - C-001: Specified exact `quantize_image` 5-color branch — replace linspace with direct use of all 5 colors.
> - C-002: Cross-spec conflict with `phase-1-simple-tiles.md` TC-002 documented — update required there.
> - C-003: All new tuft matrices defined explicitly (TUFT_CRESCENT_1/2, TUFT_SWEEP_LEFT/RIGHT, TUFT_ARCH).
> - H-001: GUI palette picker update (5th slot) explicitly required in §1.4.
> - H-002: Sub-type → tuft routing table added.
> - H-003: `palettes.json` migration path documented.
> - M-001: Exact clamping replacement shown as code diff.
> - M-002: Palette list changed to exactly 5 entries (removed "at least 6" ambiguity).
> - M-003: IT-002 updated to assert correctness, not just no-crash.
> - L-001: `apply_stamp` / `apply_composite_stamp` scope clarified — no changes required.
> - L-002: `DEFAULT_COLOR_*` constants declared out of scope.

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run tests before committing, validate `val` falls within the `[0, 4]` range before drawing. |
| **Ask first** | Adding new dependencies, fundamentally rewriting the kitbashing algorithm. |
| **Never do** | Remove failing tests without explicit approval, hardcode colors inside `generator.py` or `quantizer.py` instead of reading from the palette. |

## Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| Procedural Grass Grid | 2D int array, values in `{-1, 0, 1, 2, 3, 4}` (tuft matrices) / `{0,1,2,3,4}` (generator output) | This spec § "Tuft Structures" | `quantizer.py`, `gui/preview.py` |

### Consumes
| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `DEFAULT_PALETTES` | Dictionary `{name: list[tuple[int,int,int]]}` | `constants.py` (defined there directly) | `constants.py` |

### Public Interface
| Type | Identifier | Documented at |
|---|---|---|
| Function | `generate_texture(texture_type, seed, density, sub_type)` → `np.ndarray` shape `(32,32)`, values `{0,1,2,3,4}` | This spec §1.2 |
| Function | `quantize_image(noise_map, palette)` → `PIL.Image` | This spec §1.3 |

> ⚠️ **Cross-spec update required (C-002):** `phase-1-simple-tiles.md` TC-002 asserts `generate_texture` returns only values `{0,1,2,3}`. After this spec is implemented, TC-002 must be updated to assert values `{0,1,2,3,4}` for grass textures.

### External Invocations
N/A — this spec only modifies internal procedural logic and invokes no external systems.

### Tracked Concepts
| Concept | Status in this spec | Mentioned in |
|---|---|---|
| TextureParams | Not modified, but its values affect density | `asset_convertor_spec.md` |
| Tuft Kitbashing | Enhanced from 4-tone 3x3/4x5 to 5-tone 5x5 shapes | `asset_convertor_spec.md` |

## Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| 1 | `val` inside tuft matrices only goes up to 4 | Low | `TC-004` validates all matrix entries are in `{-1,0,1,2,3,4}`. |
| 2 | `apply_composite_stamp` safely modulo-wraps via generator's draw loop `if 0 <= px < 32` | Low | Generator's explicit bounds check + neighbor expansion handles this. |
| 3 | 5 colors per palette is sufficient to match reference | Low | Extracted exactly 5 primary tones from the new reference sheet. |
| 4 | No consumer unpacks palette tuples by position (e.g., `a, b, c, d = palette`) | Low | Verified: `app.py` `on_palette_write` uses index access; `quantize_image` uses iteration. Extending tuples to length 5 is safe. |
| 5 | `apply_stamp` (binary stamp + tone parameter) requires no changes | Low | It writes a fixed `tone` value, not a `val` from the matrix. Tone range is controlled by the caller. |
| 6 | `apply_composite_stamp` requires no changes | Low | It writes `val` directly from the matrix with no clamping. Supports any integer tone already. |

## 1. Implementation Plan

### 1.1 `tools/asset_convertor/core/constants.py`

Modify `DEFAULT_PALETTES` to include exactly **5 colors per entry** instead of 4. Update the following existing palettes and add 5 new ones:

**Updated existing palettes** (extend to 5 tones — add a bright highlight as the 5th):
```python
DEFAULT_PALETTES = {
    "Grass (Spring)": [(78, 122, 40), (115, 168, 55), (161, 214, 73), (212, 245, 110), (235, 255, 160)],
    "Grass (Summer)": [(20, 77, 36), (38, 115, 48), (62, 158, 55), (99, 199, 77), (145, 230, 100)],
    "Grass (Autumn)": [(92, 48, 21), (138, 83, 31), (186, 126, 39), (227, 177, 68), (250, 215, 110)],
    "Grass (Winter)": [(45, 66, 74), (74, 105, 112), (116, 153, 158), (174, 209, 214), (220, 240, 242)],
    # New palettes:
    "Grass (Crimson)": [(70, 10, 10), (120, 30, 30), (175, 55, 55), (220, 90, 90), (245, 140, 130)],
    "Grass (Teal)":    [(10, 60, 65), (20, 100, 105), (40, 150, 155), (80, 200, 200), (140, 235, 230)],
    "Grass (Snow)":    [(100, 120, 130), (160, 185, 195), (200, 220, 228), (230, 245, 250), (250, 255, 255)],
    "Grass (Purple)":  [(45, 20, 70), (85, 45, 130), (130, 80, 185), (175, 125, 225), (215, 175, 250)],
    "Grass (Savanna)": [(95, 80, 20), (145, 125, 35), (190, 170, 55), (225, 210, 90), (248, 238, 150)],
}
```

**Keep `DEFAULT_COLOR_*` single-color constants unchanged** — they are out of scope and unrelated to the palette tuple length change.

Add the following **new 5-tone tuft matrices** to `constants.py`:

```python
# --- CRESCENT (curved blade shapes) ---
TUFT_CRESCENT_1 = [
    [-1, -1,  4,  4, -1],
    [-1,  3,  4,  4,  3],
    [ 2,  3,  3,  3,  2],
    [ 1,  2,  2,  2,  1],
    [-1,  0,  0,  0, -1]
]
TUFT_CRESCENT_2 = [
    [-1,  4, -1, -1, -1],
    [ 4,  4,  3, -1, -1],
    [ 3,  3,  2,  3, -1],
    [ 2,  2,  1,  2,  2],
    [-1,  0, -1,  0,  0]
]

# --- SWEEP (diagonal blade forms) ---
TUFT_SWEEP_LEFT = [
    [-1, -1, -1,  4,  4],
    [-1, -1,  3,  4, -1],
    [-1,  3,  3, -1, -1],
    [ 2,  2,  2, -1, -1],
    [ 0,  0,  1,  2, -1]
]
TUFT_SWEEP_RIGHT = [
    [ 4,  4, -1, -1, -1],
    [-1,  4,  3, -1, -1],
    [-1, -1,  3,  3, -1],
    [-1, -1,  2,  2,  2],
    [-1,  2,  1,  0,  0]
]

# --- ARCH (wide dome shape) ---
TUFT_ARCH = [
    [-1,  4,  4,  4, -1],
    [ 3,  4,  4,  4,  3],
    [ 2,  3,  3,  3,  2],
    [ 1,  2,  2,  2,  1],
    [ 0,  0,  0,  0,  0]
]
```

**Old tufts (`TUFT_CLASSIC_*`, `TUFT_SHORT_*`, `TUFT_CURLY_*`, `TUFT_WILD_*`) must NOT be deleted.** They are used by existing sub-types and must be preserved for backward compatibility. The new tufts are additions, not replacements.

### 1.2 `tools/asset_convertor/core/generator.py`

Update the `generate_texture` function's sub-type → tuft list mapping. Add the new `"crescent"` sub-type. The complete routing table after the change:

| `sub_type` value | Tuft list |
|-----------------|-----------|
| `"classic"` | `[TUFT_CLASSIC_RIGHT, TUFT_CLASSIC_LEFT, TUFT_CLASSIC_V]` *(unchanged)* |
| `"short"` | `[TUFT_SHORT_1, TUFT_SHORT_2, TUFT_SHORT_3]` *(unchanged)* |
| `"curly"` | `[TUFT_CURLY_1, TUFT_CURLY_2, TUFT_CURLY_3]` *(unchanged)* |
| `"wild"` | `[TUFT_WILD_1, TUFT_WILD_2]` *(unchanged)* |
| `"crescent"` *(new)* | `[TUFT_CRESCENT_1, TUFT_CRESCENT_2, TUFT_SWEEP_LEFT, TUFT_SWEEP_RIGHT, TUFT_ARCH]` |

Add the import of the 5 new tuft constants. Add `"crescent"` as a new `elif` branch in `generate_texture`.

**Background noise initialization:** Keep using tones `1` and `2` for background scatter (`rng.choice([1, 2])`). The 5-tone system leaves:
- Tone `0`: deep shadow (under tuft bases)
- Tone `1`: background fill (grid init `np.ones` + scatter)
- Tone `2`: midtone (scatter + lower tuft body)
- Tone `3`: upper blade / highlight
- Tone `4`: bright tip highlight (top of tufts only)

The grid initialization `np.ones((32, 32))` (tone 1) is correct and unchanged.

**`apply_stamp` and `apply_composite_stamp` require NO code changes** — they are already tone-agnostic. `apply_composite_stamp` writes `val` directly; `apply_stamp` uses a `tone` parameter. The only file that needs clamping changes is `quantizer.py`.

### 1.3 `tools/asset_convertor/core/quantizer.py`

Replace the current `quantize_image` tone-mapping logic. The exact replacement:

**Before:**
```python
# Handle if palette has fewer or more than 4 colors
L = len(sorted_palette)
if L == 0:
    mapped_palette = [(0,0,0), (85,85,85), (170,170,170), (255,255,255)]
elif L < 4:
    # Repeat the lightest color if not enough colors
    mapped_palette = sorted_palette + [sorted_palette[-1]] * (4 - L)
else:
    # Take 4 evenly distributed colors (first, last, and two in between)
    indices = np.linspace(0, L - 1, 4, dtype=int)
    mapped_palette = [sorted_palette[i] for i in indices]
```

**After:**
```python
# Handle if palette has fewer or more than 5 colors
L = len(sorted_palette)
if L == 0:
    mapped_palette = [(0,0,0), (64,64,64), (128,128,128), (192,192,192), (255,255,255)]
elif L < 5:
    # Pad to 5 by repeating the lightest color for missing highlights
    mapped_palette = sorted_palette + [sorted_palette[-1]] * (5 - L)
elif L == 5:
    # Use all 5 colors directly
    mapped_palette = sorted_palette
else:
    # More than 5: pick 5 evenly distributed colors
    indices = np.linspace(0, L - 1, 5, dtype=int)
    mapped_palette = [sorted_palette[i] for i in indices]
```

**Also update the val clamping** (Anti-Pattern §2.1). The exact replacement:

**Before (line ~37):**
```python
if val > 3:
    val = 3
```

**After:**
```python
if val > 4:
    val = 4
```

### 1.4 `tools/asset_convertor/gui/app.py`

> **Scope note:** GUI changes are required to avoid the silent palette truncation bug (H-001). All changes are confined to palette handling and subtype list.

**Change 1 — `self.custom_palette` default (line ~54):** Update from 4 to 5 slots:
```python
# Before:
self.custom_palette = [(0,0,0), (85,85,85), (170,170,170), (255,255,255)]
# After:
self.custom_palette = [(0,0,0), (64,64,64), (128,128,128), (192,192,192), (255,255,255)]
```

**Change 2 — `on_palette_write` callback (lines ~78–83):** Update to extract 5 colors:
```python
# Before:
self.custom_palette = [
    pal[0],
    pal[max(1, (L-1)//3)],
    pal[max(1, 2*(L-1)//3)],
    pal[L-1]
]
# After:
self.custom_palette = [
    pal[0],
    pal[max(1, (L-1)//4)],
    pal[max(1, (L-1)//2)],
    pal[max(1, 3*(L-1)//4)],
    pal[L-1]
]
```

**Change 3 — Palette slot labels (line ~144):** Update from 4 to 5 labels:
```python
# Before:
labels = ["Shadow", "Midtone 1", "Midtone 2", "Highlight"]
# After:
labels = ["Shadow", "Midtone 1", "Midtone 2", "Midtone 3", "Highlight"]
```

**Change 4 — Color button loop (line ~145):** Update `range(4)` to `range(5)`.

**Change 5 — Subtypes list (line ~51):** Add `"Crescent"`:
```python
# Before:
self.subtypes = ["Classic", "Short", "Curly", "Wild"]
# After:
self.subtypes = ["Classic", "Short", "Curly", "Wild", "Crescent"]
```

**`palettes.json` migration note (H-003):** The `DEFAULT_PALETTES` update in `constants.py` is the fallback for users without an external `palettes.json`. Users with an existing `palettes.json` must manually add 5th colors to their palette entries, or delete `palettes.json` to use the updated defaults. This is a **known limitation** — no code change required. Document it in the GUI status bar: the app will work with 4-color palettes (the padding logic handles `L < 5`).

## 2. Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|--------------|-----------|------------------|
| 1 | Hardcoding max tones | Using `if val > 3: val = 3` without updating to 4, crushing the 5th highlight color. | Use `if val > 4: val = 4` in `quantize_image`. |
| 2 | Symmetric Tufts | Creating perfectly symmetrical tuft matrices. | Organic grass must be slightly asymmetrical (sweeping left or right). |
| 3 | Ignoring Y-Sorting | Failing to append new tufts to the `all_tufts` list before Y-sorting. | All tufts must go through the Y-sort pass to preserve depth rules. |
| 4 | Resizing the Grid | Changing the `grid` from 32x32 to 48x48. | Maintain the base 32x32 grid and fit the new tufts inside it. |
| 5 | Deleting old palettes | Removing original palettes instead of updating them to 5 tones. | Preserve backward compatibility of naming by extending existing tuples to length 5. |
| 6 | Deleting old tufts | Removing `TUFT_CLASSIC_*`, `TUFT_SHORT_*`, `TUFT_CURLY_*`, `TUFT_WILD_*` constants. | Old tufts must be preserved — they are used by existing sub-types. New tufts are additions. |
| 7 | Changing `apply_stamp` or `apply_composite_stamp` | These functions are tone-agnostic and require no modification. | Only `quantize_image` clamping and mapping need to change. |
| 8 | Linspace-based 4-slot quantizer | Using `np.linspace(..., 4)` for a 5-color palette still produces 4 colors. | The `L == 5` branch must use all 5 colors directly: `mapped_palette = sorted_palette`. |

## 3. Test Case Specifications

### Unit Tests

| TC ID | Target | Description |
|-------|--------|-------------|
| `TC-001` | `quantize_image` | Handles a 5-color palette: pass a noise map with values 0–4, assert output image contains exactly 5 distinct RGB colors matching the sorted palette entries. |
| `TC-002` | `quantize_image` | Handles palettes with fewer than 5 colors: pass a 3-color palette, assert val=4 maps to the lightest color (padding applied). |
| `TC-003` | `quantize_image` | Handles palettes with more than 5 colors: pass a 7-color palette, assert exactly 5 evenly-spaced colors are selected. |
| `TC-004` | `constants.py` | All new 5x5 tuft matrices (`TUFT_CRESCENT_1`, `TUFT_CRESCENT_2`, `TUFT_SWEEP_LEFT`, `TUFT_SWEEP_RIGHT`, `TUFT_ARCH`) contain only integers from `{-1, 0, 1, 2, 3, 4}`. |
| `TC-005` | `generate_texture` | With sub_type="crescent", returns a numpy array where `np.max(result) >= 4` (confirms tone 4 is actually produced). |
| `TC-006` | `generate_texture` | With sub_type="crescent", returns a `(32, 32)` array with values only in `{0, 1, 2, 3, 4}`. |
| `TC-007` | `app.py` | `on_palette_write` with a 5-color palette produces `self.custom_palette` with exactly 5 elements. |

### Integration Tests

| TC ID | Target | Description |
|-------|--------|-------------|
| `IT-001` | `generate_texture` → `quantize_image` | End-to-end: `generate_texture("grass", seed=42, density=20, sub_type="crescent")` → `quantize_image(result, 5-color palette)` → PIL Image. Assert: (a) no exception, (b) image has exactly 5 distinct RGB colors. |
| `IT-002` | `generate_texture` toroidal wrapping | Stamp `TUFT_CRESCENT_1` (5x5) at position `(30, 30)` on a 32x32 grid via `apply_composite_stamp`. Assert: pixels at `(30,30)`, `(31,31)`, `(0,32%32)=(0,0)`, `(1,33%32)=(1,1)` receive correct values per the matrix (no IndexError, no missed wrapping). The generator uses explicit bounds checking (`if 0 <= px < 32`) — assert at least one pixel beyond position 31 is correctly excluded (not an out-of-bounds crash). |
| `IT-003` | `gui/app.py` | With `DEFAULT_PALETTES` loaded (5 colors per entry), `self.custom_palette` has 5 elements after `on_palette_write` fires. No crash. Tone-4 highlights are not silently dropped. |

## 4. Error Handling Matrix

| Error Condition | Client/UI State | Server/Console Output | Verification |
|-----------------|-----------------|-----------------------|--------------|
| Palette has < 5 colors | UI shows image with lightest available color repeated for higher tones | Info: "Palette has fewer than 5 colors — highlights will repeat lightest." | `TC-002` |
| Palette has 0 colors | UI shows grayscale image using 5-step gray fallback | Warning: empty palette fallback applied | ASSUMED |
| Matrix contains invalid value > 4 | val is clamped to 4 in `quantize_image` — no crash | No error output | `TC-001` |
| Texture size exceeds 32x32 | UI renders clipped or wrapped texture | No explicit error, bounds checking applies | VERIFIED — generator uses `if 0 <= px < 32` |
| `palettes.json` has 4-color entries | App uses 4-color palette, padded to 5 | No error — `L < 5` path pads automatically | `TC-002` |

## 5. Deep Links
- [quantizer.py](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/core/quantizer.py) — full file replacement (see §1.3 for exact diff)
- [generator.py:L33-L91](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/core/generator.py#L33-L91) — `generate_texture` function to update
- [constants.py:L104-L152](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/core/constants.py#L104-L152) — Palettes and tuft definitions to extend
- [app.py:L51-L90](file:///Users/adrien.parasote/Documents/perso/game/tools/src/asset_convertor/gui/app.py#L51-L90) — Palette picker and subtype list
- [phase-1-simple-tiles.md:L92](file:///Users/adrien.parasote/Documents/perso/game/tools/docs/specs/phase-1-simple-tiles.md#L92) — TC-002 to update (values 0–4 for grass)
