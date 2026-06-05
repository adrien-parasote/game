# A4 Canvas — 4-Neighbor Wall Sides Preview

> Document type: Implementation

**Covers:** A4 canvas mode (APERÇU CANVAS for wall sides)
**Status:** SPEC v1.0 — 2026-06-05
**Parent spec:** `./asset_convertor_mv_gui.md`

## Summary

When resource type is A4 (Mur), the APERÇU CANVAS must display wall **side** tiles
(the vertical face visible in-game) using a 4-neighbor bitmask (N/S/E/W only),
not the 8-neighbor blob system used for A1/A2 floor tiles.

The 16 wall side shapes from `WALL_AUTOTILE_TABLE` map to 2^4 = 16 cardinal
neighbor combinations. The canvas grid and click interaction remain unchanged;
only the bitmask computation and tile lookup change for A4.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run full pytest suite before committing; scope changes strictly to A4 canvas path; update spec if behavior changes |
| **Ask first** | Changing `_GRID_DEFAULT` pattern; adding a new AppState field beyond `tiles`/`tile_size`; changing `_redraw_canvas_grid` signature |
| **Never do** | Modify the A1/A2/A3 blob canvas path; change `_compute_cell_bitmask` (8N); touch `converter_mv_a4.py` core logic; store more than 16 tiles for A4 canvas |

---

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|-----------|------|-------------|------------|
| 1 | `WALL_AUTOTILE_TABLE` coordinate analysis (qsx=0→W, qsx=3→E, qsy=0→N, qsy=3→S) correctly yields the 16-shape bitmask mapping | High | SHOW — `grep -n "WALL_AUTOTILE_TABLE" tools/src/asset_convertor/core/converter_mv_a3.py` confirms shapes 0,3,7,15 coords | Cross-verified manually in DISCOVER; all 4 match expected N/W/E/S combinations |
| 2 | `sides_img` returned by `convert_mv_a4` always has width=768 and height≥48 when non-empty | Medium | SHOW — `grep "_SIDE_OUTPUT_W\|_TILE_SIZE" tools/src/asset_convertor/core/converter_mv_a4.py` → `_SIDE_OUTPUT_W = 768`, `_TILE_SIZE = 48` | Verified from source constants. Note: converter guarantees height≥48 even for empty source (L132-133 of `converter_mv_a4.py` inserts a placeholder) — the `sides_img.height == 0` branch in `_convert_a4` is thus unreachable in practice, but retained as a defensive guard. |
| 3 | The 4-neighbor bitmask produces values strictly in 0–15 | Low | SHOW — mathematical: 4 binary bits = 2^4 = 16 values; `len(_WALL_4N_BITMASK_TO_IDX) == 16` verified at test TC-005 | dict has all 16 keys, no gaps |
| 4 | No other resource type triggers `resource_type == "A4"` branch | Low | SHOW — `grep "_TYPE_LABEL_MAP" tools/src/asset_convertor/gui/app.py` → labels are `"A1","A3","A4","Recolor","A2"`; exact string match only | String comparison; other types never equal `"A4"` |
| 5 | Tiles in `sides_img` row 0 are ordered by shape index 0–15 left-to-right, so `crop((i*48, 0, …))` for i in range(16) yields tiles in shape order | Low | SHOW — `converter_mv_a4.py` L218-220: `strip.paste(tile, (shape * _TILE_SIZE, 0))` — shape 0 at x=0, shape 15 at x=720 | Verified from source |

---

## Cross-Spec Contracts

### Produces
| Artifact | Format | Schema | Consumers |
|----------|--------|--------|-----------|
| `AppState.tiles` for A4 | `list[Image.Image]`, len=16 | This spec § "AppState.tiles contract" | `_redraw_canvas_grid` |

### Consumes
| Artifact | Format | Schema | Producer |
|----------|--------|--------|----------|
| `sides_img` from `convert_mv_a4` | RGBA, width=768, height=N*48 | `converter_mv_a4.py` docstring | `_convert_a4` in `app.py` |
| `WALL_AUTOTILE_TABLE` | 16-entry list | `converter_mv_a3.py` § constants | `_WALL_4N_BITMASK_TO_IDX` derivation |

### Public Interface
| Type | Identifier | Documented at |
|------|-----------|---------------|
| Module constant | `_WALL_4N_BITMASK_TO_IDX: dict[int,int]` | This spec § "Bitmask mapping" |
| Module function | `_compute_wall_bitmask_4n(grid, row, col) -> int` | This spec § "4-neighbor bitmask function" |

### External Invocations
N/A — this spec invokes no external interfaces.

### Tracked Concepts
| Concept | Status in this spec | Mentioned in |
|---------|--------------------|----|
| `AppState.tiles` | Contracted to hold 16 `Image.Image` for A4 | `asset_convertor_mv_gui.md` § "State fields" |
| `_redraw_canvas_grid` | Extended with A4 branch | `asset_convertor_mv_gui.md` § "Canvas panel" |

---

## AppState.tiles contract

For A4, `AppState.tiles` stores a **flat `list[Image.Image]` of exactly 16 tiles**,
extracted from the first row of `sides_img` (the first wall-side kind).

```
sides_img layout: 768px wide (16 tiles * 48px), height = N_kinds * 48px
Tile i: crop((i*48, 0, i*48+48, 48))   for i in range(16)
```

- `tiles[shape_idx]` is the 48×48 RGBA tile for `WALL_AUTOTILE_TABLE[shape_idx]`
- If `sides_img.height == 0` (no valid wall side blocks), tiles = [] and canvas shows grey fallback

---

## Bitmask mapping

### 4-neighbor bitmask convention
```
N = 2   (bit 1)
W = 8   (bit 3)
E = 4   (bit 2)
S = 1   (bit 0)
```

Bitmask value = N*2 | W*8 | E*4 | S*1 using the cardinal neighbor flags.

### _WALL_4N_BITMASK_TO_IDX

Derived from `WALL_AUTOTILE_TABLE` coordinate analysis (qsx=0→W present,
qsx=3→E present, qsy=0→N present, qsy=3→S present):

```python
_WALL_4N_BITMASK_TO_IDX: dict[int, int] = {
    0:  0,   # isolated
    8:  1,   # W
    2:  2,   # N
    10: 3,   # N+W
    4:  4,   # E
    12: 5,   # W+E
    6:  6,   # N+E
    14: 7,   # N+W+E
    1:  8,   # S
    9:  9,   # W+S
    3:  10,  # N+S
    11: 11,  # N+W+S
    5:  12,  # E+S
    13: 13,  # W+E+S
    7:  14,  # N+E+S
    15: 15,  # N+W+E+S
}
```

All 16 bitmask values (0–15) must be present. No fallback for missing values.

---

## 4-neighbor bitmask function

```python
def _compute_wall_bitmask_4n(
    grid: list[list[bool]], row: int, col: int
) -> int:
    """Compute 4-neighbor wall bitmask. N=2, W=8, E=4, S=1."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    def f(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < cols and grid[r][c]

    return (
        (2 if f(row - 1, col) else 0)   # N
        | (8 if f(row, col - 1) else 0) # W
        | (4 if f(row, col + 1) else 0) # E
        | (1 if f(row + 1, col) else 0) # S
    )
```

**Must NOT read diagonal neighbors.** Must NOT reuse `_compute_cell_bitmask`.

---

## Changes to `_convert_a4`

Current: extracts 47 wall-top tiles → store in `AppState.tiles`.
**New**: extract 16 wall-side tiles from first row of `sides_img`.

```python
# Extract 16 wall-side tiles from the first strip of sides_img
tile_size = 48
wall_side_tiles: list[Image.Image] = [
    sides_img.crop((i * tile_size, 0, (i + 1) * tile_size, tile_size))
    for i in range(16)
] if sides_img.height > 0 else []

self._state = dataclasses.replace(
    self._state,
    result_img=stitched,
    tiles=wall_side_tiles,   # ← 16 tiles, not 47
    tile_size=tile_size,
)
```

The success callback `_on_convert_success_a4` passes `wall_side_tiles` to
`_draw_canvas_pattern`.

---

## Changes to `_redraw_canvas_grid`

Add a branch **before** the tile lookup to select the bitmask function and index map:

```python
resource_type = self._state.resource_type
is_wall = resource_type == "A4"
```

Inside the per-cell loop, when `filled and active_tiles`:
```python
if is_wall:
    bm = _compute_wall_bitmask_4n(grid, r, c)
    idx = _WALL_4N_BITMASK_TO_IDX.get(bm, 0)
else:
    bm = _compute_cell_bitmask(grid, r, c)
    idx = _BITMASK_TO_IDX.get(bm, 0)
tile = active_tiles[idx]
```

`active_tiles` for A4 has len=16, so `idx` from `_WALL_4N_BITMASK_TO_IDX` is always 0–15.

---

## Changes to `_on_convert_success_a4`

Signature unchanged. The `wall_top_tiles` parameter is renamed `wall_side_tiles`
and carries the 16 tiles instead of 47. The canvas info label updates to:

```
"Cliquez pour dessiner — bitmask 4-voisins (Mur)"
```

---

## Changes to `_draw_canvas_pattern`

The method already delegates to `_redraw_canvas_grid`. The `tiles` argument is
stored in `AppState.tiles` before `_redraw_canvas_grid` reads it — no signature
change needed.

Replace the **entire method body** with the following (the existing grid reset and
`_redraw_canvas_grid` call must be preserved — only the label line changes):

```python
def _draw_canvas_pattern(
    self, tiles: list[list[Image.Image]] | list[Image.Image], tile_size: int
) -> None:
    self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
    self._redraw_canvas_grid()
    if self._state.resource_type == "A4":
        self.lbl_canvas_info.configure(
            text="Cliquez pour dessiner — bitmask 4-voisins (Mur)"
        )
    else:
        self.lbl_canvas_info.configure(
            text="Cliquez pour dessiner — bitmask 8-voisins"
        )
```

> ⚠️ **Do NOT replace only the label line.** Replace the full method. The grid reset
> (`self._canvas_grid = [row[:] for row in _GRID_DEFAULT]`) and the
> `self._redraw_canvas_grid()` call are existing behavior that must be preserved.

---

## Anti-Patterns

| # | Anti-pattern | Why wrong | Correct approach |
|---|-------------|-----------|-----------------|
| AP-1 | Reusing `_compute_cell_bitmask` for A4 | Returns 8-bit value; index can exceed 15 → IndexError on `active_tiles[idx]` | Use `_compute_wall_bitmask_4n` which returns 0–15 only |
| AP-2 | Extracting 47 tops tiles for the canvas instead of 16 sides tiles | Tops are not what the player sees; blob bitmask doesn't match wall behavior in Tiled | Extract from `sides_img` row 0, 16 tiles, map via `_WALL_4N_BITMASK_TO_IDX` |
| AP-3 | Hardcoding the tile count check `len(tiles) == 47` in tests after this change | A4 now produces 16 tiles — existing test would fail with wrong message | Update test to assert `len(tiles) == 16` |
| AP-4 | Applying the 4N bitmask path for A1/A2/A3 | Those use 47-tile blob — wrong shape count | Branch strictly on `resource_type == "A4"` |
| AP-5 | Storing tops tiles AND sides tiles separately in AppState | AppState.tiles is a single `list[Image.Image]`; adding a second field violates YAGNI and breaks the canvas contract | Use one field; for A4 canvas = sides only |
| AP-6 | Silently using `idx=0` fallback when bitmask is not in `_WALL_4N_BITMASK_TO_IDX` | The table is complete (all 16 values); a miss means a bug in the bitmask function | `.get(bm, 0)` is acceptable as a safety net but log a warning: `import logging; logger = logging.getLogger(__name__)` at module level, then `if bm not in _WALL_4N_BITMASK_TO_IDX: logger.warning("A4 bitmask %d not in table — fallback to idx 0", bm)` before the `.get()` call |

---

## Test Case Specifications

### Unit tests (new)

| ID | Description | Input | Expected |
|----|-------------|-------|---------|
| TC-001 | `_compute_wall_bitmask_4n` isolated cell | all neighbors absent | `0` |
| TC-002 | `_compute_wall_bitmask_4n` N only | N present, W/E/S absent | `2` |
| TC-003 | `_compute_wall_bitmask_4n` all four cardinal | N+W+E+S present | `15` |
| TC-004 | `_compute_wall_bitmask_4n` ignores diagonals | NW corner present, N and W absent | `0` (diag not counted) |
| TC-005 | `_WALL_4N_BITMASK_TO_IDX` completeness | keys of dict | `set(range(16))` |
| TC-006 | `_WALL_4N_BITMASK_TO_IDX` values coverage | values of dict | `set(range(16))` (bijection) |

### Unit tests (update existing)

| ID | Description | Change |
|----|-------------|--------|
| TC-007 | `test_a4_conversion_populates_tiles_for_canvas` | Assert `len(tiles) == 16` (was 47); assert first tile is `Image.Image` |

### Integration tests (new)

| ID | Description | Setup | Expected |
|----|-------------|-------|---------|
| IT-001 | A4 conversion → canvas shows 16 tiles in AppState | Load 96×120 px A4 source (at least 1 non-transparent pixel in each block, or use a valid real fixture), call `_convert_a4()` | `state.tiles` is list of 16 `Image.Image` |
| IT-002 | `_redraw_canvas_grid` uses 4N path for A4 | Set `state.resource_type = "A4"`, tiles=16-list, filled grid | Canvas draws without IndexError |
| IT-003 | `_redraw_canvas_grid` uses 8N blob path for A2 | Set `state.resource_type = "A2"`, tiles=47-list | Canvas draws without IndexError |

---

## Error Handling Matrix

| Failure | Trigger | Behaviour | Classification |
|---------|---------|-----------|----------------|
| `sides_img.height == 0` (no valid wall blocks in source) | Source image is all-transparent or invalid | `wall_side_tiles = []`; canvas falls back to grey rectangle cells | ASSUMED — consistent with existing empty-image guard |
| `bm not in _WALL_4N_BITMASK_TO_IDX` | Bug in `_compute_wall_bitmask_4n` returning value > 15 | `.get(bm, 0)` → tile at index 0 (isolated shape); no crash | VERIFIED — `.get` fallback is safe |
| `sides_img` first row crop out-of-bounds | `sides_img.height < 48` | `sides_img.height > 0` guard ensures at least 1 row; crop is safe | CITED — Pillow `crop` clips to image bounds silently |

---

## Deep Links

- `WALL_AUTOTILE_TABLE`: [`converter_mv_a3.py`](../src/asset_convertor/core/converter_mv_a3.py#L27) lines 27–44
- `convert_mv_a4` return contract: [`converter_mv_a4.py`](../src/asset_convertor/core/converter_mv_a4.py#L63) lines 63–135
- `_redraw_canvas_grid` current implementation: [`app.py`](../src/asset_convertor/gui/app.py#L1200) ~line 1200
- `_convert_a4` current implementation: [`app.py`](../src/asset_convertor/gui/app.py#L758) ~line 758
- `_on_convert_success_a4` current: [`app.py`](../src/asset_convertor/gui/app.py#L857) ~line 857
- Parent GUI spec: [`./asset_convertor_mv_gui.md`](./asset_convertor_mv_gui.md#L288) § "A4 Converter note"
- Test file: [`tests/asset_convertor/gui/test_app.py`](../tests/asset_convertor/gui/test_app.py#L1)
