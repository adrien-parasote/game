<!-- Generated: 2026-06-05 | Files scanned: 9 | Token estimate: ~520 -->

# Asset Convertor — Autotile Converter Architecture

## Tool Purpose
Converts RPG Maker XP/MV/MZ autotile PNG files into Tiled-compatible 47-tile blob tilesets (PNG sheet + TSX wangset). Supports static and animated autotiles (horizontal water / vertical waterfall).

## Entry Point
`tools/src/asset_convertor/__main__.py` → `gui/app.py:App`

## Conversion Pipeline
User loads PNG → GUI validates → `convert_xp` or `convert_mv` → `assemble_sheet` + `generate_tsx` → writes PNG + TSX

> ⚠️ **Type contract**: both converters always return `list[list[Image.Image]]` (frames × tiles).
> Static = 1 frame. Animated = N frames. `tile_size = result[0][0].width` — never `result[0].width`.

### XP Path (96×128 or multiples → 32px tiles)
- `gui/app.py:_convert` → `converter_xp.convert_xp(img, is_animated, animation_mode)`
- Returns `list[list[Image.Image]]` — 1 frame (static) or N frames (animated horizontal)
- `converter_xp.py:_extract_subtile` → crops 16×16 sub-tiles from 6×8 XP grid
- `converter_xp.py:_build_tile_from_bitmask` → builds blob tile from 4 quadrant lookups
- Vertical animation: not supported for XP — raises `ValueError`

### MV/MZ Path (64×96 or 96×144 → normalized to 32px)
- `gui/app.py:_convert` → `converter_mv.convert_mv(img, is_animated, animation_mode)`
- Returns `list[list[Image.Image]]` — 1 frame (static) or N frames (animated)
- `converter_mv.py:detect_tile_size(img)` → returns 32 or 48 from `_VALID_BLOCK_SIZES`
- `converter_mv.py:_build_mv_tile(img, bitmask, tile_size)` → standard floor tile assembly
- `converter_mv.py:_build_waterfall_tile(img, bitmask, tile_size)` → 4-shape waterfall mapping
- Internal helpers: `_convert_mv_static`, `_convert_mv_animated_horizontal`, `_convert_mv_animated_vertical`

### Animation Cycle Rules (shared by GUI and TSX generator)
| Frames | Mode | Sequence |
|--------|------|----------|
| 3 | Horizontale | `[0, 1, 2, 1]` ping-pong |
| 3 | Verticale | `[0, 1, 2]` linear |
| 4 | Either | `[0, 1, 2, 3]` linear |
| N | Other | `[0..N-1]` linear |

### Export Path
- `tsx_generator.assemble_sheet(tiles_by_frame, tile_size)` → 8×(6×N) PNG (slot 47 = transparent)
- `tsx_generator.generate_tsx(name, size, png, is_animated, animation_mode, duration, num_frames)` → XML with `<animation>` nodes per tile
- `tsx_generator.export(tiles, name, output_dir, tile_size, ...)` → writes .png + .tsx, returns paths

## Key Files
```
tools/src/asset_convertor/
  __main__.py              entry point → App()
  core/
    converter_xp.py        XP → list[list[47 tiles]] (BLOB_BITMASKS, convert_xp)
    converter_mv.py        MV/MZ → list[list[47 tiles]] (detect_tile_size, convert_mv, waterfall)
    constants.py           shared constants (TILE_SIZE, SUBTILE_SIZE, BLOB_BITMASKS)
  exporters/
    tsx_generator.py       PNG sheet + TSX writer (assemble_sheet, generate_tsx, export)
  gui/
    app.py                 customtkinter 3-panel GUI (App, AppState, animation timer)
```

## Public API Contracts
| Symbol | File | Signature | Returns |
|--------|------|-----------|---------| 
| `convert_xp` | converter_xp.py | `(img, is_animated=False, animation_mode="Horizontale") -> list[list[Image]]` | N frames of 47 tiles |
| `convert_mv` | converter_mv.py | `(img, is_animated=False, animation_mode="Horizontale") -> list[list[Image]]` | N frames of 47 tiles |
| `detect_tile_size` | converter_mv.py | `(img: Image) -> int` | 32 or 48 |
| `assemble_sheet` | tsx_generator.py | `(tiles_by_frame, tile_size) -> Image` | 8×(6×N) PNG |
| `export` | tsx_generator.py | `(tiles, name, dir, size, is_animated, animation_mode, duration) -> tuple[str,str]` | (png_path, tsx_path) |
| `BLOB_BITMASKS` | converter_xp.py | `tuple[int, ...]` | 47 valid blob bitmasks |

## Bitmask Convention (shared)
NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128

## Sample Files
```
tools/src/input/
  sample_xp.png        96×128 px (XP autotile)
  sample_mv_32px.png   64×96 px  (MV, tile_size=32)
  sample_mv_48px.png   96×144 px (MV, tile_size=48)
```

## Test Coverage (97 tests)
```
tools/tests/asset_convertor/
  core/test_converter_xp.py           TC-001..010 (unit, static + animated + mutation)
  core/test_converter_mv.py           TC-011..020 (unit, static + animated + waterfall)
  exporters/test_tsx_generator.py     TC-021..035 (unit, sheet assembly + TSX animation XML)
  core/test_converter_integration.py  IT-001..009 (integration, sample files, full pipeline)
  gui/test_app.py                     App init, validation, animation controls (unit, headless)
```

## Spec
`tools/docs/specs/autotile_converter_spec.md`
