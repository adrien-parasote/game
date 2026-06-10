<!-- Generated: 2026-06-11 | Files scanned: 11 | Token estimate: ~650 -->

# Asset Convertor — Autotile & Recolor Tool Architecture

## Tool Purpose
Converts RPG Maker XP/MV/MZ autotile PNG files into Tiled-compatible 47-tile blob tilesets (PNG sheet + TSX wangset), handles building A3 and wall A4 sheets, recolors sprites with presets/manual remapping, and resizes 48px assets to 32px.

## Entry Point
`tools/src/asset_convertor/__main__.py` → `gui/app.py:App` (CustomTkinter GUI)

## Main GUI Architecture
- **Primary Toolbar:** Mode Selection [🎮 Animé (A1) | 🏠 Bâtiment (A3) | 🧱 Mur (A4) | 🎨 Recolor | 🌱 Sol (A2)]
- **Secondary Toolbar:** Dynamic context panels (Format XP/MV/MZ, speed, or resize scale hints).
- **3-Panel Layout:** SOURCE | SORTIE | APERÇU (Canvas grid for A1/A2/A3/A4, or RecolorPanel for Recolor mode).

## Conversion Pathways

### A2/A1 Ground Path (XP or MV)
- XP: `converter_xp.convert_xp(img, is_animated, mode)` (crops 16x16 sub-tiles → 47 blob tiles)
- MV: `converter_mv.convert_mv(img, is_animated, mode)` (crops 24px mini-tiles → 47 normalized 32px/48px tiles)
- Returns `list[list[Image.Image]]` (frames × tiles)

### A3 Building/Roof Path (MV only)
- `converter_mv_a3.convert_mv_a3(img) -> tuple[Image, Image]` (roof_strip, wall_strip)
- Roofs are assembled via WALL_AUTOTILE_TABLE (16 shapes)

### A4 Wall Path (MV only)
- `converter_mv_a4.convert_mv_a4(img) -> tuple[Image, Image]` (tops_strip, sides_strip)
- Row parity mapping: even rows → tops (FLOOR 47 shapes), odd rows → sides (WALL 16 shapes)
- Canvas supports **Mur** (4-neighbor sides) and **Sol** (8-neighbor tops) toggle

### Recolor Engine
- `recolor.extract_palette(img) -> list[Color]` (max 32 colors extracted)
- `recolor.apply_remap(img, table) -> Image` (re-indexes colors via mapping table)
- `gui/recolor_panel.py`: Swatches display + Lospec presets (Dawnbringer, Endesga) + manual color mapping

### Resize Tool
- `gui/app.py`: resizes 48px inputs to 32px using crisp `Image.NEAREST` scaling

### Exporters
- `tsx_generator.assemble_sheet()`: stacks animation frames vertically into a single PNG sheet
- `tsx_generator.generate_tsx()`: writes Tiled TSX file with `<animation>` cycle nodes (ping-pong or linear)
- `tsx_generator.export()`: writes .png + .tsx files

## Key Files
```
tools/src/
├── asset_convertor/
│   ├── core/
│   │   ├── constants.py       # Centralized constants (BLOB_BITMASKS, tufts)
│   │   ├── converter_mv.py    # MV A2/A1 converter & waterfall lookup
│   │   ├── converter_mv_a3.py # A3 converter (roof/wall split)
│   │   ├── converter_mv_a4.py # A4 converter (interleaved tops/sides)
│   │   ├── converter_xp.py    # XP converter
│   │   ├── palettes.py        # Predefined Lospec palettes
│   │   └── recolor.py         # Recolor palette extractor & remapper
│   ├── exporters/
│   │   ├── exporter.py        # Exporter interface
│   │   └── tsx_generator.py   # PNG assembly + TSX XML animation loop writer
│   └── gui/
│       ├── app.py             # App CTk main UI loop & state coordinator
│       ├── recolor_panel.py   # Palette list, preset grid, remapping table
│       └── state.py           # Immutable AppState & RecolorState dataclasses
├── assets/
│   └── flat_wall_to_diagonal.py # CLI converter for diagonal wall segments
└── calibration/
    └── calibrate_halos.py     # Torch halo light mask calibration tool
```

## Public API Contracts
| Symbol | Signature | Role |
|---|---|---|
| `convert_xp` | `(img, is_animated, mode) -> list[list[Image]]` | XP Autotile parsing |
| `convert_mv` | `(img, is_animated, mode) -> list[list[Image]]` | MV A2 Autotile parsing |
| `convert_mv_a3` | `(img) -> tuple[Image, Image]` | A3 split roof & wall parsing |
| `convert_mv_a4` | `(img) -> tuple[Image, Image]` | A4 split tops & sides parsing |
| `extract_palette` | `(img) -> list[Color]` | Palette extraction |
| `apply_remap` | `(img, table) -> Image` | Color reindexing |
| `export` | `(tiles, name, dir, size, is_animated, mode, duration) -> tuple[str,str]` | Writes PNG + TSX |

## Test Coverage
- `tools/tests/asset_convertor/core/`: XP, MV, A3, A4, recolor, and quantizer tests.
- `tools/tests/asset_convertor/gui/`: CTk app, AppState, resize, and RecolorPanel tests.
- `tools/tests/assets/`: Flat-to-diagonal wall converter tests.
- `tools/tests/calibration/`: Halo light mask calibration tests.
