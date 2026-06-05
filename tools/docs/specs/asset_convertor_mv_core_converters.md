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

Both converters follow the same contract as the existing `converter_mv.py` (A2):
- Input: PIL Image (source tileset PNG)
- Output: PIL Image (Tiled-ready tileset PNG)
- No side effects, no file I/O, no GUI imports

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Return a new PIL Image (never mutate input). Use `Image.NEAREST` for all resizing. Validate source dimensions before processing. Match mini-tile coordinate system from `converter_mv.py` (24px half-tiles). |
| **Ask first** | Changing the public function signature `convert_mv_a3(img: Image) -> Image`. Adding new parameters not in this spec. Supporting non-MV formats (XP/MZ) for A3/A4 — out of scope. |
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
| Function | `convert_mv_a3(img: Image.Image) -> Image.Image` | This spec § "A3 Converter — Public API" |
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
bx = tx * 2   # block column in mini-tiles
by = ty * 2   # block row in mini-tiles (A3 starts at ty=0 in the source file)
```

For shape `s` (0–15), quadrant `q` (0=TL, 1=TR, 2=BL, 3=BR):
```
[qsx, qsy] = WALL_AUTOTILE_TABLE[s][q]
src_x = (bx * 2 + qsx) * 24
src_y = (by * 2 + qsy) * 24
```

Each quadrant is a 24×24 px crop from `(src_x, src_y)` to `(src_x+24, src_y+24)`.

### Output Format (Tiled)

- One PNG per autotile kind, OR a single strip of all 16 shapes per kind
- **Output tile size:** 48×48 px (assembled from 4 × 24×24 quadrants)
- **Output layout:** 16 tiles wide × N kinds tall (one row per autotile kind)
- Output width = `16 * 48 = 768 px`
- Output height = `number_of_kinds * 48`

### Public API

```python
def convert_mv_a3(img: Image.Image) -> Image.Image:
    """
    Convert an RPG Maker MV A3 (Building/Roof) source tileset
    to a Tiled-compatible tileset strip.

    Args:
        img: PIL Image, source A3 PNG (768×384 or smaller, RGBA or RGB).
             Must be at least 96×96 px.

    Returns:
        PIL Image: Output tileset, RGBA, width=768, height=N*48
        where N = number of detected non-empty autotile blocks.

    Raises:
        ValueError: If img dimensions are smaller than 96×96 px.
        ValueError: If img width is not a multiple of 96.
    """
```

### Processing Steps

1. Convert input to RGBA if not already.
2. Detect non-empty autotile blocks (skip blocks where the 96×96 region is fully transparent or fully white).
3. For each non-empty block (kind `k`):
   a. Compute `bx = (k % 8) * 2`, `by = (k // 8) * 2`
   b. For each shape `s` in range(16):
      - For each quadrant `q` in range(4):
        - Read `[qsx, qsy] = WALL_AUTOTILE_TABLE[s][q]`
        - Crop 24×24 region from source at `((bx*2 + qsx)*24, (by*2 + qsy)*24)`
        - Paste into output tile at quadrant position
      - Place assembled 48×48 tile at `(s * 48, kind_index * 48)` in output
4. Return output image.

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
   - Odd ty rows → wall-side blocks (process with WALL_AUTOTILE_TABLE, same algorithm as A3)
3. For **wall-top blocks** (FLOOR table, 47 shapes):
   - Same algorithm as `converter_mv.py` (A2). Reuse `_assemble_floor_tile()` helper.
   - Output strip: 47 tiles wide × N_top_kinds rows.
4. For **wall-side blocks** (WALL table, 16 shapes):
   - Same algorithm as A3. Reuse `_assemble_wall_tile()` helper.
   - Output strip: 16 tiles wide × N_side_kinds rows.
5. Return `(wall_tops_strip, wall_sides_strip)`.

### Helper Functions (private, shared between A3 and A4)

```python
def _assemble_wall_tile(
    src: Image.Image,
    bx: int,  # block column in mini-tiles
    by: int,  # block row in mini-tiles
    shape: int,  # 0–15
) -> Image.Image:
    """Assemble one 48×48 tile from WALL_AUTOTILE_TABLE[shape]."""

def _assemble_floor_tile(
    src: Image.Image,
    bx: int,
    by: int,
    shape: int,  # 0–46
) -> Image.Image:
    """Assemble one 48×48 tile from FLOOR_AUTOTILE_TABLE[shape].
    Import logic from converter_mv.py rather than duplicating."""
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
| AP-A3-03 | Outputting one file per kind | Forces caller to manage N files. Breaks TSX export (needs a single sheet). | Output a single strip image with all kinds × shapes. |
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
| TC-001 | Minimum valid source (96×96) produces output | 96×96 RGBA image with test pattern | Returns Image, size = (768, 48) — 1 kind × 16 shapes |
| TC-002 | Full sheet (768×384) shape count | 768×384 RGBA with all blocks filled | Output height = 32 × 48 = 1536 px (32 kinds) |
| TC-003 | Output width is always 768 (16 shapes × 48px) | Any valid input | `output.width == 768` |
| TC-004 | Empty block skipped | 192×96 source, only block 0 filled | Output height = 1 × 48 (only 1 kind) |
| TC-005 | WALL_AUTOTILE_TABLE shape 0 correct quadrant assembly | Known test pattern with colored quadrants | TL = color from `(bx*2+2)*24, (by*2+2)*24` |
| TC-006 | Source too small raises ValueError | 48×48 image | `ValueError` with message containing "96×96" |
| TC-007 | Width not multiple of 96 raises ValueError | 100×96 image | `ValueError` with message containing "multiple de 96" |
| TC-008 | All-transparent source raises ValueError | 768×384 fully transparent | `ValueError` "Aucun bloc valide" |
| TC-009 | Output is RGBA | RGB input | `output.mode == "RGBA"` |
| TC-010 | Input not mutated | Input image before/after | `original_size == img.size`, `original_mode == img.mode` |

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
