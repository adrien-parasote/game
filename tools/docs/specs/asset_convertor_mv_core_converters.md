# Spec — MV Autotile Converters: A3 (Building) + A4 (Wall)

> Document Type: Implementation
> **Covers:** F3 (A3 converter), F4 (A4 converter)
> **Blueprint:** [asset_convertor_ui_v2_blueprint.md](../strategic/asset_convertor_ui_v2_blueprint.md)
> **ADR:** [ADR-007-3](../ADRs/ADR-007-asset-convertor-ui-v2.md#adr-007-3-autotile-tables-from-official-corescript)

---

## Deep Links

- [Blueprint § Feature List](../strategic/asset_convertor_ui_v2_blueprint.md#5-feature-list)
- [Blueprint § ADR-UI-003 (corescript tables)](../strategic/asset_convertor_ui_v2_blueprint.md#adr-ui-003-autotile-tables-from-official-corescript-verified)
- [Existing A2 converter (reference implementation)](../../src/asset_convertor/core/converter_mv.py)
- [WALL_AUTOTILE_TABLE source](https://github.com/rpgtkoolmv/corescript/blob/master/js/rpg_core/Tilemap.js)
- [GUI State spec — mode constants](./asset_convertor_mv_gui.md#appstate-fields)
- [TSX exporter](../../src/asset_convertor/exporters/tsx_exporter.py)

---

## Goal

Implement two new converter modules for RPG Maker MV autotile formats:
- `converter_mv_a3.py` — A3 Building/Roof tiles (roof autotiles using WALL_AUTOTILE_TABLE, 16 shapes)
- `converter_mv_a4.py` — A4 Wall tiles (hybrid: wall-tops via FLOOR_AUTOTILE_TABLE 47 shapes, wall-sides via WALL_AUTOTILE_TABLE 16 shapes, interleaved by row parity)

- Both converters follow the same contract as the existing `converter_mv.py` (A2):
- Input: PIL Image (source tileset PNG)
- Output: `convert_mv_a3` → `tuple[Image.Image, Image.Image]` (roof strip, wall strip); `convert_mv_a4` → `tuple[Image.Image, Image.Image]` (tops strip, sides strip)
- No side effects, no file I/O, no GUI imports

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Return a new PIL Image (never mutate input). Use `Image.NEAREST` for all resizing. Validate source dimensions before processing. Match mini-tile coordinate system from `converter_mv.py` (24px half-tiles). |
| **Ask first** | Changing the public function signature `convert_mv_a3(img: Image) -> tuple[Image.Image, Image.Image]`. Adding new parameters not in this spec. Supporting non-MV formats (XP/MZ) for A3/A4 — out of scope. |
| **Never do** | Import from `gui/` packages. Mutate the input PIL Image. Use pixel-by-pixel loops where PIL paste operations suffice. Raise unhandled exceptions (always wrap in `ValueError` with message). |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `core/converter_mv_a3.py` | Python Module | This spec § "A3 Converter" | `gui/app.py` via `AppState.resource_type == "A3"` |
| `core/converter_mv_a4.py` | Python Module | This spec § "A4 Converter" | `gui/app.py` via `AppState.resource_type == "A4"` |
| `tests/tools/asset_convertor/test_converter_mv_a3.py` | Python Tests | This spec § "Test Cases" | Pytest runner |
| `tests/tools/asset_convertor/test_converter_mv_a4.py` | Python Tests | This spec § "Test Cases" | Pytest runner |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `core/converter_mv.py` | Python Module | `autotile_converter_spec.md` | A2 spec |
| `exporters/png_exporter.py` | Python Module | Existing codebase | Exporter |
| `exporters/tsx_exporter.py` | Python Module | Existing codebase | Exporter |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Function | `convert_mv_a3(img: Image.Image) -> tuple[Image.Image, Image.Image]` | This spec § "A3 Converter — Public API" |
| Function | `convert_mv_a4(img: Image.Image) -> tuple[Image.Image, Image.Image]` | This spec § "A4 Converter — Public API" |

### External Invocations

N/A — these modules are pure functions with no external calls.

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| WALL_AUTOTILE_TABLE (16 shapes) | Defined and implemented | Blueprint ADR-UI-003, gui spec |
| FLOOR_AUTOTILE_TABLE (47 shapes) | Consumed (A4 wall-tops) | `converter_mv.py` (A2 uses this too) |
| Mini-tile (24×24 px) | Used throughout | `converter_mv.py` |

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| A1 | A3 source blocks are 96×96 px each (2×2 mini-tiles of 24px) | Low | **VERIFIED** — visual inspection of real A3 file shared by user; matches corescript formula `bx = tx * 2`, 2 mini-tiles wide |
| A2 | A4 wall-top rows use `FLOOR_AUTOTILE_TABLE` (47 shapes); wall-side rows use `WALL_AUTOTILE_TABLE` (16 shapes), alternating by `ty % 2` | Low | **VERIFIED** — confirmed from corescript `Tilemap.js` blob `9ff2991` and validated against real A4 file (even rows = tops, odd rows = sides) |
| A3 | `FLOOR_AUTOTILE_TABLE` can be imported from `converter_mv.py` without circular imports | Low | **ASSUMED** — `converter_mv.py` does not import from `converter_mv_a3.py` or `converter_mv_a4.py`; dependency is one-directional |
| A4 | All RPG Maker MV A3/A4 source files use 48×48 px base tiles (24×24 px mini-tiles) | Low | **SUPERSEDED** — 32px community assets also exist. Both 32px (block_size=64) and 48px (block_size=96) are supported. See `_VALID_BLOCK_SIZES_A4 = {64: 32, 96: 48}` in `converter_mv_a4.py`. |
| A5 | A4 convert returns a tuple of 2 images; the TSX exporter and GUI can handle this by treating the two strips as separate exports | Medium | **VERIFIED** — GUI exports two strips as `{name}_tops.tsx` (blob wangset) and `{name}_sides.tsx` (corner-or-edge wangset). |
| A6 | A3 split rule: first `n_rows // 2` block rows → roof strip; remaining block rows → wall strip. Works for all even row counts (2×4, 3×6, 4×4, etc.) | Medium | **VERIFIED** — confirmed by user: "les deux première lignes sont le toit et les deux seconde le mur". Generalised to `n_rows // 2`. |

---

## Reference: Autotile Tables

Sourced from `rpgtkoolmv/corescript` blob `9ff2991`, `js/rpg_core/Tilemap.js`:

### WALL_AUTOTILE_TABLE (16 entries, used by A3 and A4-sides)

Each entry = 4 mini-tile source coordinates `[qsx, qsy]` for the 4 quadrants of one output tile:
```python
WALL_AUTOTILE_TABLE = [
    # shape: [top-left, top-right, bottom-left, bottom-right] as [qsx, qsy]
    [[2,2],[1,2],[2,1],[1,1]],  # shape 0
    [[0,2],[1,2],[0,1],[1,1]],  # shape 1
    [[2,0],[1,0],[2,1],[1,1]],  # shape 2
    [[0,0],[1,0],[0,1],[1,1]],  # shape 3
    [[2,2],[3,2],[2,1],[3,1]],  # shape 4
    [[0,2],[3,2],[0,1],[3,1]],  # shape 5
    [[2,0],[3,0],[2,1],[3,1]],  # shape 6
    [[0,0],[3,0],[0,1],[3,1]],  # shape 7
    [[2,2],[1,2],[2,3],[1,3]],  # shape 8
    [[0,2],[1,2],[0,3],[1,3]],  # shape 9
    [[2,0],[1,0],[2,3],[1,3]],  # shape 10
    [[0,0],[1,0],[0,3],[1,3]],  # shape 11
    [[2,2],[3,2],[2,3],[3,3]],  # shape 12
    [[0,2],[3,2],[0,3],[3,3]],  # shape 13
    [[2,0],[3,0],[2,3],[3,3]],  # shape 14
    [[0,0],[3,0],[0,3],[3,3]],  # shape 15
]
```

### FLOOR_AUTOTILE_TABLE (47 entries, used by A2 and A4-tops)

Already implemented in `converter_mv.py`. **Do not redefine** — import from there:
```python
from .converter_mv import FLOOR_AUTOTILE_TABLE
```

---

## A3 Converter

### Source Format (MV)

- **File dimensions:** 768×384 px (full sheet) or smaller (partial, slots filled with transparency/white)
- **Tile size:** 48×48 px
- **Mini-tile size:** 24×24 px
- **Block layout:** Each autotile block = 2 columns × 2 rows of mini-tiles = 96×96 px per block
- **Block grid:** 8 columns × 4 rows = 32 autotile kinds (but WALL_AUTOTILE_TABLE has 16 shapes → each kind produces 16 output tiles)
- **Content:** Roof tiles (row 0-1 of blocks) and building faces (row 2-3 of blocks)

### Source Coordinate Formula (from corescript)

For kind `k` where `tx = k % 8`, `ty = k // 8`:
```
bx = tx * 4   # block column offset in mini-tiles
by = ty * 4   # block row offset in mini-tiles (A3 starts at ty=0 in the source file)
```

For shape `s` (0–15), quadrant `q` (0=TL, 1=TR, 2=BL, 3=BR):
```
[qsx, qsy] = WALL_AUTOTILE_TABLE[s][q]
src_x = (bx + qsx) * mini
src_y = (by + qsy) * mini
```

Each quadrant is a mini×mini px crop from `(src_x, src_y)` to `(src_x+mini, src_y+mini)`.

### Output Format (Tiled)

`convert_mv_a3` returns **two separate strips** — one for roof kinds, one for wall kinds:

- **Roof strip** — first `n_rows // 2` block rows of the source
- **Wall strip** — remaining block rows (last `n_rows // 2`)
- **Output tile size:** 48×48 px (assembled from 4 × 24×24 quadrants)
- **Output layout per strip:** 16 tiles wide × N kinds tall (one row per autotile kind)
- Strip width = `16 * tile_size` (768 px for 48px, 512 px for 32px)
- Strip height = `number_of_kinds_in_that_half * tile_size`

### Public API

```python
def convert_mv_a3(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Convert an RPG Maker MV A3 (Building/Roof) source tileset
    to two Tiled-compatible tileset strips: one for roof, one for wall.

    Split rule: first n_rows // 2 block rows → roof strip;
    remaining block rows → wall strip.
    Works for any even-row grid: 2×4, 3×6, 4×4, etc.

    Args:
        img: PIL Image, source A3 PNG (768×384 or smaller, RGBA or RGB).
             Must be at least 96×96 px (or 64×64 for 32px tiles).

    Returns:
        tuple[Image.Image, Image.Image]: (roof_img, wall_img)
            roof_img: RGBA, width=16*tile_size, height=N_roof*tile_size
            wall_img: RGBA, width=16*tile_size, height=N_wall*tile_size

    Raises:
        ValueError: If img dimensions are smaller than minimum block size.
        ValueError: If img width is not a multiple of 64 or 96.
    """
```

### Processing Steps

1. Convert input to RGBA if not already.
2. Detect block grid dimensions: `n_cols = img.width // block_size`, `n_rows = img.height // block_size`.
3. Compute `split_row = n_rows // 2` — first half = roof, second half = wall.
4. For each block row `ty` from 0 to `n_rows - 1`:
   a. Determine target strip: `roof_strips` if `ty < split_row`, else `wall_strips`.
   b. Compute `by = ty * 4` in mini-tile units.
   c. For each block column `tx` from 0 to `n_cols - 1`:
      - Compute `bx = tx * 4` in mini-tile units.
      - For each shape `s` in range(16): assemble tile from WALL_AUTOTILE_TABLE.
      - Place assembled tile at `(s * tile_size, kind_index * tile_size)` in the target strip.
5. Stack each list of strips vertically using `_stack_strips(strips, tile_size)` → one Image per half.
6. Return `(roof_img, wall_img)`.

---

## A4 Converter

### Source Format (MV)

- **File dimensions:** 768×720 px (48px, full sheet), 512×480 px (32px), or smaller (partial)
- **Mini-tile size:** `tile_size // 2` px (24px for 48px tiles, 16px for 32px tiles)
- **Tile size:** Detected dynamically from `img.width`:
  - `width % 96 == 0` → 48px tiles (standard MV)
  - `width % 64 == 0` → 32px tiles (community/custom assets)
  - Otherwise → `ValueError`
- **Row interleaving:** Even block-rows (`ty % 2 == 0`) = wall-tops (FLOOR table); odd block-rows (`ty % 2 == 1`) = wall-sides (WALL table)

### Geometry Detection (`_detect_a4_geometry`)

```python
_VALID_BLOCK_SIZES_A4: dict[int, int] = {64: 32, 96: 48}  # block_size → tile_size

def _detect_a4_geometry(img: Image.Image) -> tuple[int, int, int]:
    """Returns (tile_size, mini, block_size) from image width."""
    for block_size, tile_size in _VALID_BLOCK_SIZES_A4.items():
        if img.width % block_size == 0:
            return tile_size, tile_size // 2, block_size
    raise ValueError(f"Largeur invalide : {img.width}px. Doit être multiple de 64 (32px) ou 96 (48px).")
```

### Row Parity Logic (from corescript)

For A4, `ty` runs from 0 to 5 (6 rows of autotile blocks in the source):

| ty | ty % 2 | Table | Shapes | Description |
|---|---|---|---|---|
| 0 | 0 (even) | FLOOR_AUTOTILE_TABLE | 47 | Wall tops (viewed from above) |
| 1 | 1 (odd)  | WALL_AUTOTILE_TABLE  | 16 | Wall sides (facades, arches) |
| 2 | 0 (even) | FLOOR_AUTOTILE_TABLE | 47 | Wall tops |
| 3 | 1 (odd)  | WALL_AUTOTILE_TABLE  | 16 | Wall sides |
| 4 | 0 (even) | FLOOR_AUTOTILE_TABLE | 47 | Wall tops |
| 5 | 1 (odd)  | WALL_AUTOTILE_TABLE  | 16 | Wall sides |

The source Y coordinate for A4 uses this formula (from corescript):
```python
# For FLOOR rows (ty % 2 == 0):
by_floor = int((ty - 0) * 2.5)  # simplified for ty starting at 0
# For WALL rows (ty % 2 == 1):
by_wall = int((ty - 0) * 2.5 + 0.5)
```

Explicit lookup table for source block Y offset (in mini-tiles):

| ty | by |
|---|---|
| 0 | 0  |
| 1 | 3  |
| 2 | 5  |
| 3 | 8  |
| 4 | 10 |
| 5 | 13 |


### Public API

```python
def convert_mv_a4(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Convert an RPG Maker MV A4 (Wall) source tileset to two
    Tiled-compatible tileset strips — one for wall tops, one for wall sides.

    Supports both standard 48px (block_size=96) and community 32px (block_size=64) assets.
    Tile size is detected automatically from img.width.

    Args:
        img: PIL Image, source A4 PNG (RGBA or RGB).
             48px: 768×720 or smaller. Min: 96×120 px.
             32px: 512×480 or smaller. Min: 64×120 px.

    Returns:
        tuple: (wall_tops_img, wall_sides_img)
            wall_tops_img:  RGBA, width=8*tile_size, height=N_top_kinds*6*tile_size
                            (47 shapes per kind in FLOOR_AUTOTILE_TABLE blob layout)
            wall_sides_img: RGBA, width=16*tile_size, height=N_side_kinds*tile_size
                            (16 shapes per kind from WALL_AUTOTILE_TABLE)

    Raises:
        ValueError: If img width is not a multiple of 64 or 96.
        ValueError: If img height is too small to contain any valid block.
    """
```

### Processing Steps

1. Convert input to RGBA.
2. Separate block rows by parity:
   - Even ty rows → wall-top blocks (process with FLOOR_AUTOTILE_TABLE, same algorithm as A2/A3)
   - Odd ty rows → wall-side blocks (process with WALL_AUTOTILE_TABLE)
3. For **wall-top blocks** (FLOOR table, 47 shapes):
   - Use `by` from `_BY_LOOKUP_A4[ty]` directly (correct for floor blocks).
   - Reuse `_assemble_floor_tile()` helper.
   - Output strip: 47 tiles wide × N_top_kinds rows.
4. For **wall-side blocks** (WALL table, 16 shapes):
   - ⚠️ **Do NOT use `_BY_LOOKUP_A4[ty]` for wall rows.** The lookup gives the Y offset
     of the *floor template block* directly above the wall data, not the wall data itself.
     The actual wall source always occupies the **last `_WALL_MINI_ROWS` (=4) mini-tile rows**
     of the source image, regardless of `ty`.
   - Compute wall source origin: `wall_mini_y0 = (src.height // mini) - _WALL_MINI_ROWS`
   - Call `_assemble_wall_tile(src, bx, wall_mini_y0, shape, tile_size, mini)`.
   - Output strip: 16 tiles wide × N_side_kinds rows.
5. Return `(wall_tops_strip, wall_sides_strip)`.

### WALL_AUTOTILE_TABLE Coordinate Convention

`WALL_AUTOTILE_TABLE[shape][q]` returns `[qsx, qsy]` — the mini-tile column and row
offset **within the 4×4 mini-tile wall source block**.

- **No axis inversion needed.** `qsx` and `qsy` map directly to pixel offsets:
  ```python
  src_x = (bx + qsx) * mini
  src_y = wall_mini_y0 * mini + qsy * mini
  ```
- Row layout in the wall source block:
  - `qsy = 0`: top row — edge cap / decorative border (top of wall visual)
  - `qsy = 1, 2`: interior rows — stone/material body
  - `qsy = 3`: bottom row — edge cap / decorative border (bottom of wall visual)
- Column layout: `qsx = 0` = left border column, `qsx = 3` = right border column.

> **Anti-pattern:** Do NOT invert `qsx` or `qsy` before computing source coordinates.
> The table was authored to work with direct offsets. Inverting produces mirrored/
> upside-down tiles that appear correct on symmetric textures but break on asymmetric ones.

### Helper Functions (private)

```python
def _get_wall_source_mini_y0(src: Image.Image, mini: int) -> int:
    """Return the mini-tile row index of the wall source block origin.

    Wall data always occupies the last _WALL_MINI_ROWS (=4) mini-rows of the
    A4 source image. Use this as `by` when calling _assemble_wall_tile().
    Do NOT use _BY_LOOKUP_A4 values for wall-side blocks.
    """

def _assemble_wall_tile(
    src: Image.Image,
    bx: int,     # block column offset in mini-tile units
    by: int,     # MUST be _get_wall_source_mini_y0() — NOT _BY_LOOKUP_A4
    shape: int,  # 0–15
    tile_size: int,
    mini: int,
) -> Image.Image:
    """Assemble one tile_size×tile_size tile from WALL_AUTOTILE_TABLE[shape].
    Use qsx/qsy directly. No axis inversion."""

def _assemble_floor_tile(
    src: Image.Image,
    bx: int,
    by: int,     # from _BY_LOOKUP_A4 — correct for floor blocks
    shape: int,  # 0–46
    tile_size: int,
    mini: int,
) -> Image.Image:
    """Assemble one tile_size×tile_size tile from FLOOR_AUTOTILE_TABLE[shape]."""
```

---

## Project File Tree

```
tools/src/asset_convertor/
  core/
    converter_mv.py          # [EXISTING] A2 converter — reference implementation
    converter_mv_a3.py       # [NEW] A3 Building/Roof converter
    converter_mv_a4.py       # [NEW] A4 Wall converter (hybrid)
tests/tools/asset_convertor/
  test_converter_mv_a3.py    # [NEW] A3 unit + integration tests
  test_converter_mv_a4.py    # [NEW] A4 unit + integration tests
```

---

## Error Handling Matrix

| Error | Trigger | Handling |
|-------|---------|----------|
| Source too small (< 96×96) | User opens wrong file | `raise ValueError(f"Image trop petite: {img.size}. Minimum 96×96 px pour A3.")` |
| Width not multiple of 96 | Corrupted or XP-format file | `raise ValueError(f"Largeur {img.width} invalide. Doit être multiple de 96 px pour A3 MV.")` |
| All blocks empty/transparent | Wrong file loaded (e.g. A2 given to A3 converter) | `raise ValueError("Aucun bloc valide détecté. Le fichier est-il bien un A3 MV ?")` |
| Source too small | height too small | `raise ValueError(f"Image trop petite: {img.size}. Minimum {block_size}×120 px pour A4.")` |
| Width not multiple of 64 or 96 | Corrupted / wrong format | `raise ValueError(f"Largeur invalide : {img.width}px. Doit être multiple de 64 (32px tiles) ou 96 (48px tiles).")` |
| WALL_AUTOTILE_TABLE index out of bounds | Bug in shape iteration (shape > 15) | Should never happen with `range(16)` — caught by `assert shape < 16` in debug builds |

All errors propagate to the GUI's error handler in `app.py` which displays them in the log bar.

---

## Anti-Patterns

| # | Anti-Pattern | Why Wrong | Do Instead |
|---|---|---|---|
| AP-A3-01 | Duplicating `FLOOR_AUTOTILE_TABLE` in `converter_mv_a3.py` | Single source of truth violation. Table drift = wrong output tiles. | `from .converter_mv import FLOOR_AUTOTILE_TABLE` |
| AP-A3-02 | Pixel-by-pixel copy loop instead of `Image.paste()` | 10-100× slower. A 768×720 file with 30 kinds would take seconds. | Use `Image.paste(crop, (x, y))` for each 24×24 mini-tile. |
| AP-A3-03 | Returning a single merged strip for A3 (not splitting roof/wall) | GUI needs separate strips to show Toit/Mur toggle and export two files. A single strip breaks the export pipeline. | Return `(roof_img, wall_img)` — first `n_rows // 2` block rows → roof, rest → wall. |
| AP-A3-04 | Treating A4 as a single-table converter | A4 alternates between FLOOR (47 shapes) and WALL (16 shapes) by row parity. A single-table approach produces wrong output for half the tiles. | Check `ty % 2` per row and apply the correct table. |
| AP-A3-05 | Hard-coding `ty` offset as absolute pixel Y | The source Y depends on the `by` lookup table (non-linear for A4). Hard-coding breaks when rows are partial. | Use the `BY_LOOKUP_A4 = {0:0, 1:3, 2:5, 3:8, 4:10, 5:13}` dict. |
| AP-A3-06 | Not validating source dimensions | Wrong file (e.g., A2 given to A3 converter) produces garbled output silently. | Validate dimensions at function entry and raise `ValueError`. |
| AP-A3-07 | Returning `None` instead of raising on invalid input | Caller has no way to distinguish empty output from error. GUI shows blank preview with no error message. | Always raise `ValueError` with a French user-friendly message. |
| AP-A4-01 | Hard-coding `tile_size = 48` in A4 converter or GUI | Breaks 32px community assets (block_size=64). Both converter and GUI must derive tile_size dynamically from image dimensions. | Use `_detect_a4_geometry(img)` in converter; `tile_size = sides_img.width // 16` in GUI. |

---

## Test Case Specifications

### Unit Tests — `test_converter_mv_a3.py`

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-001 | Valid 2-block source returns tuple of two Images | 96×192 RGBA (2 block rows) | `isinstance(result, tuple)` and `len(result) == 2` |
| TC-002 | 2-block source: 1 roof kind + 1 wall kind | 96×192 RGBA | `roof.height == tile_size`, `wall.height == tile_size` |
| TC-003 | Output width is always `16 * tile_size` | Any valid input | `roof.width == wall.width == 16 * tile_size` |
| TC-004 | 4-block source: 2 roof kinds + 2 wall kinds | 96×384 RGBA | `roof.height == 2*tile_size`, `wall.height == 2*tile_size` |
| TC-005 | A3 roof/wall pixel separation | 2-row source, row 0 red, row 1 green | Roof pixels = red, Wall pixels = green |
| TC-006 | Source too small raises ValueError | 48×48 image | `ValueError` with message containing "96" |
| TC-007 | Width not valid raises ValueError | 100×96 image | `ValueError` with message containing "invalide" |
| TC-008 | Both outputs are RGBA | RGB input | `roof.mode == "RGBA"`, `wall.mode == "RGBA"` |
| TC-009 | Input not mutated | Image before/after | `before.tobytes() == after.tobytes()` |
| TC-010 | Output tile count = 16 per strip | Any valid input | `roof.width // tile_size == 16` |
| TC-011 | 32px source (block_size=64) accepted | 64×128 RGBA | `isinstance(roof, Image.Image)` — no error |

### Unit Tests — `test_converter_mv_a4.py`

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-001 | Returns tuple of 2 images | Minimal 96×120 RGBA | `isinstance(result, tuple)` and `len(result) == 2` |
| TC-002 | Wall-tops strip width = 47×48 = 2256 | Any valid A4 input with ≥1 even row | `wall_tops.width == 2256` |
| TC-003 | Wall-sides strip width = 16×48 = 768 | Any valid A4 input with ≥1 odd row | `wall_sides.width == 768` |
| TC-004 | Even ty rows go to FLOOR table (47 shapes) | Source with ty=0 block only filled | `wall_tops.height == 48`, `wall_sides.height == 0 or None` |
| TC-005 | Odd ty rows go to WALL table (16 shapes) | Source with ty=1 block only filled | `wall_sides.height == 48`, `wall_tops.height == 0 or None` |
| TC-006 | BY_LOOKUP_A4 used for by offset | Mock source — check crop coordinates | Crops taken from `by=3` (not `by=1`) for `ty=1` |
| TC-007 | Source too small raises ValueError | 48×48 image | `ValueError` |
| TC-008 | Both output images are RGBA | RGB input | `wall_tops.mode == "RGBA"`, `wall_sides.mode == "RGBA"` |
| TC-009 | Input not mutated | Image before/after | Identical size and mode |
| TC-010 | Full A4 sheet produces 3 top kinds + 3 side kinds | 768×720 with all 6 rows filled | `wall_tops.height == 3*48`, `wall_sides.height == 3*48` |

### Integration Tests

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-001 | A3 converter → TSX exporter | Convert real A3 file, export TSX | TSX valid XML, `tilecount = num_kinds * 16` |
| IT-002 | A3 converter output is tileable in Tiled | Known input → inspect output pixels | Shape 0 (isolated tile) has correct edges: all corners present |
| IT-001 | A4 converter → two TSX files | Convert real A4 file, export both strips | Two TSX files, wall_tops has 47 tiles/row, wall_sides has 16 |
| IT-002 | A4 hybrid: row 0 and row 1 both produce valid output | Real A4 source with bushes (top) and arches (side) | Both strips are non-empty and valid RGBA |
