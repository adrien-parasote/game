<!-- Generated: 2026-06-04 | Files scanned: 8 | Token estimate: ~450 -->

# Asset Creator — Autotile Converter Architecture

## Tool Purpose
Converts RPG Maker XP/MV/MZ autotile PNG files into Tiled-compatible 47-tile blob tilesets (PNG sheet + TSX wangset).

## Entry Point
`tools/src/asset_creator/__main__.py` → `gui/app.py:App`

## Conversion Pipeline
User loads PNG → GUI validates → `convert_xp` or `convert_mv` → `assemble_sheet` + `generate_tsx` → writes PNG + TSX

### XP Path (96x128 → 32px tiles)
`gui/app.py:_convert` → `converter_xp.convert_xp(img)` → `list[47 PIL.Image]`
`converter_xp.py:_extract_subtile` → crops 16x16 sub-tiles from 6x8 XP grid
`converter_xp.py:_assemble_tile` → builds each blob tile from 4 quadrants using lookup

### MV/MZ Path (64x96 or 96x144 → normalized to 32px)
`gui/app.py:_convert` → `converter_mv.convert_mv(img)` → `list[47 PIL.Image]`
`converter_mv.py:detect_tile_size(img)` → returns 32 or 48 from `_VALID_BLOCK_SIZES`
`converter_mv.py:_pick_tl/tr/bl/br(n,s,e,w,diag)` → selects source quadrant coords
`converter_mv.py:_build_mv_tile(img, bitmask, tile_size)` → assembles tile, resizes to 32px if 48px

### Export Path
`tsx_generator.assemble_sheet(tiles, tile_size)` → 256x192 PNG (8x6 grid, slot 47=transparent)
`tsx_generator.generate_tsx(name, size, png_path)` → XML string with 47 wangtile entries
`tsx_generator.export(tiles, name, output_dir, tile_size)` → writes .png + .tsx, returns paths

## Key Files
```
tools/src/asset_creator/
  __main__.py              entry point → App()
  core/
    converter_xp.py        XP → 47 tiles (BLOB_BITMASKS, _quarter_*, convert_xp)
    converter_mv.py        MV/MZ → 47 tiles (detect_tile_size, _pick_*, convert_mv)
    constants.py           shared constants (used by legacy generator.py)
  exporters/
    tsx_generator.py       PNG sheet + TSX writer (assemble_sheet, export, bitmask_to_wangid)
  gui/
    app.py                 customtkinter 3-panel GUI (App, AppState)
    state.py               GUI state dataclass
```

## Public API Contracts
| Symbol | File | Signature | Returns |
|--------|------|-----------|---------|
| `convert_xp` | converter_xp.py | `(img: Image) -> list[Image]` | 47 RGBA 32x32 tiles |
| `convert_mv` | converter_mv.py | `(img: Image) -> list[Image]` | 47 RGBA 32x32 tiles |
| `detect_tile_size` | converter_mv.py | `(img: Image) -> int` | 32 or 48 |
| `assemble_sheet` | tsx_generator.py | `(tiles, tile_size) -> Image` | PNG sprite sheet |
| `export` | tsx_generator.py | `(tiles, name, dir, size) -> tuple[str,str]` | (png_path, tsx_path) |
| `BLOB_BITMASKS` | converter_xp.py | `tuple[int, ...]` | 47 valid blob bitmasks |

## Bitmask Convention (shared)
NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128

## Sample Files
```
tools/src/input/
  sample_xp.png        96x128 px (XP autotile)
  sample_mv_32px.png   64x96 px  (MV, tile_size=32)
  sample_mv_48px.png   96x144 px (MV, tile_size=48)
```

## Test Coverage (77 tests)
```
tools/tests/asset_creator/
  core/test_converter_xp.py        TC-001..010 (unit)
  core/test_converter_mv.py        TC-011..020 (unit)
  exporters/test_tsx_generator.py  TC-021..035 (unit)
  core/test_converter_integration.py  IT-001..009 (integration, requires sample files)
  gui/test_app.py                  App init + validation (unit, headless)
```

## Spec
`tools/docs/specs/autotile_converter_spec.md`
