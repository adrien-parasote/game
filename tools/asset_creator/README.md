# Asset Creator Tool

Blob tileset (47 tiles) generation tool for [Tiled Map Editor](https://www.mapeditor.org/), featuring an **interactive GUI** and **CLI**.

Generates **PNG** files (horizontal tileset strip) + **TSX** files (Wang set XML) directly usable in Tiled, built from color palettes and procedural textures.

## Interactive GUI (V3)

Launch the Dear PyGui graphical interface to create tilesets in real time:

```bash
python3 -m tools.asset_creator gui
```

### Features

- **Real-time Preview** — 4× preview of a single tile with instant updates
- **Parameter Sliders** — control texture, detail, border, and seed
- **Color Palette** — 4 color pickers (Shadow, Base, Highlight, Accent) with OKLCh gradient generation
- **Painting Canvas** — autotile mode (Wang blob 47 tiles) + standalone mode
- **History** — panel with undo functionality: click to restore any previous state
- **Export** — PNG + TSX directly from the interface
- **macOS Theme** — native dark mode appearance (Apple HIG)

## CLI

```bash
# List available terrains
python3 -m tools.asset_creator list

# Generate a grass tileset
python3 -m tools.asset_creator generate --terrain grass

# Generate with V2 quality (OKLCh gradient + dithering + details)
python3 -m tools.asset_creator generate --terrain grass --quality v2

# Generate with a specific seed + Pygame preview
python3 -m tools.asset_creator generate --terrain dirt --seed 42 --preview

# Generate 3 variants
python3 -m tools.asset_creator generate --terrain water --variants 3

# Custom output name
python3 -m tools.asset_creator generate --terrain sand --name desert_sand

# Preview an existing tileset
python3 -m tools.asset_creator preview assets/images/autotiles/grass.png
```

## Available Terrains

| Preset | Palette | Texture | Edge |
|--------|---------|---------|------|
| `grass` | forest_grass (greens) | noise | organic |
| `dirt` | dry_dirt (browns) | noise | organic |
| `paving_stone` | stone_path (greys) | stippled | straight |
| `sand` | sand (sand yellows) | noise | dithered |
| `snow` | snow (whites/blues) | stippled | dithered |
| `water` | water (blues) | noise | organic |

## Output

By default:
- **PNG** → `assets/images/autotiles/<name>.png` — horizontal strip of 47 tiles (32×32 each)
- **TSX** → `assets/tiled/autotiles/<name>.tsx` — Wang set with `mixed` type for blob autotiling

TSX files reference the PNG via a relative path and are directly importable into Tiled.

## Architecture

```
tools/asset_creator/
├── __main__.py          # Entry point (python3 -m tools.asset_creator)
├── cli.py               # CLI commands (generate, list, preview, gui)
├── config/
│   ├── palettes/        # 6 YAML palettes (4 colors + roles + V2 gradient config)
│   └── terrain_presets.yaml  # Terrain definitions
├── core/
│   ├── color_ramp.py    # OKLCh color space, gradients with hue-shift
│   ├── detail_overlay.py  # Procedural details (grass blades, dirt specks, stone cracks, sand grains)
│   ├── minimap.py       # Wang blob bitmask computation (framework-agnostic)
│   ├── palette.py       # YAML palette loader → Palette dataclass
│   ├── subtile.py       # 20 sub-tiles 16×16 (4 quadrants × 5 types)
│   ├── terrain.py       # Terrain configuration (TerrainConfig, DetailConfig, EdgeConfig)
│   ├── texture.py       # Procedural generation (toroidal noise, patterns, V2 smooth ramp)
│   └── tile_assembler.py  # Blob autotile assembly (47 tiles) from sub-tiles
├── exporters/
│   ├── png_exporter.py  # PNG export with validation
│   └── tsx_exporter.py  # TSX export (Wang set XML)
├── gui/
│   ├── app.py           # Dear PyGui application (window, layout, callbacks)
│   ├── canvas.py        # Painting canvas state (CanvasState)
│   ├── pipeline.py      # Generation pipeline (texture → tiles → export)
│   ├── preview.py       # PIL → DPG texture conversion (RGBA float32)
│   └── state.py         # AppState (frozen dataclass), presets loader
└── preview/
    └── pygame_preview.py  # Pygame legacy previewer (strip + mini-map)
```

## Generation Pipeline

### V1 (basic)
```
YAML Palette ─→ Procedural Texture ─→ 20 Sub-tiles ─→ 47 Blob tiles ─→ PNG + TSX
     │                  │                     │                │
  4 colors        toroidal noise         edge masks       NW/N/NE bitmask
  + roles         (seamless tiling)      + borders        W/E/SW/S/SE
```

### V2 (improved quality)
```
YAML Palette ─→ OKLCh Gradient ─→ Smooth Interpolation ─→ Bayer Dithering
     │              │                   │                     │
  4 colors     hue-shift          perceptually           ordered matrix
  + ramp_config shadow/highlight   uniform (Oklab)       (2×2, 4×4, 8×8)
                                                               │
                                                    ─→ Detail overlay ─→ Sub-tiles ─→ ...
                                                         (grass blades, dirt
                                                          specks, stone cracks)
```

1. **Palette** — 4 colors (shadow, base, highlight, accent) loaded from a YAML file.
2. **OKLCh Gradient** *(V2)* — generates a 7-11 color gradient with hue-shift (cool shadows, warm highlights).
3. **Texture** — toroidal 4D Simplex noise for perfectly seamless tiling, or patterns (solid, dithered, stippled, striped).
4. **Smooth Interpolation** *(V2)* — continuous mapping in OKLCh space (avoids banding).
5. **Dithering** *(V2)* — ordered Bayer matrix for smooth transitions.
6. **Detail Overlay** *(V2)* — procedural stamps (grass blades, dirt specks, stone cracks, sand grains).
7. **Sub-tiles** — 20 parts of 16×16 (fill, edge_v, edge_h, outer_corner, inner_corner) × 4 quadrants.
8. **Assembly** — composition of the 47 blob configurations (8-neighbor bitmask) by selecting the correct sub-tile per quadrant.
9. **Export** — validated PNG strip (no transparent tiles) + TSX file with Wang IDs.

## Creating a Custom Terrain

### 1. Create a Palette

```yaml
# config/palettes/my_palette.yaml
name: my_palette
colors:
  - "#2d5a1e"   # shadow (the darkest)
  - "#3e7c27"   # base
  - "#5a9e3a"   # highlight
  - "#7bc04f"   # accent (the lightest)
roles:
  shadow: 0
  base: 1
  highlight: 2
  accent: 3
# Optional — V2 gradient with hue-shift
ramp:
  base_color: "#5a9e3a"
  steps: 9
  shadow_hue_shift: -15
  highlight_hue_shift: 10
  lightness_range: 0.25
```

### 2. Add the Terrain in `config/terrain_presets.yaml`

```yaml
terrains:
  my_terrain:
    palette: my_palette
    texture:
      type: noise        # noise | solid | dithered | stippled | striped
      scale: 0.15         # noise scale (smaller = smoother)
      octaves: 3          # layers of detail (octaves)
      persistence: 0.5    # persistence per octave
      thresholds: [-0.2, 0.4, 0.8]  # color mapping thresholds
    edge:
      style: organic      # organic | straight | dithered
      width: 3            # transition width in pixels
      noise_scale: 0.3    # noise amplitude on edges
    detail:
      type: grass_blades  # grass_blades | dirt_specks | stone_cracks | sand_grains | none
      density: 0.12
      max_height: 4
      max_length: 4
```

### 3. Generate

```bash
# Via CLI
python3 -m tools.asset_creator generate --terrain my_terrain --quality v2 --preview

# Via GUI
python3 -m tools.asset_creator gui
```

## Pygame Preview (legacy)

The Pygame preview displays:
- **Top**: the complete strip of 47 tiles
- **Bottom**: a random mini-map showing the tiles in a layout context

Controls:
- `SPACE` — regenerate the mini-map
- `ESC` — quit

## Dependencies

- `Pillow` — image manipulation
- `opensimplex` — Simplex noise for procedural textures
- `numpy` — numerical computations (OKLCh gradient, dithering)
- `PyYAML` — configuration file loading
- `dearpygui` — interactive GUI (V3)
- `pygame-ce` — legacy preview (optional)

## Tests

```bash
# All tests (371 tests)
python3 -m pytest tests/tools/asset_creator/ -v

# Integration tests only
python3 -m pytest tests/tools/asset_creator/test_integration.py -v

# GUI tests (state, preview, canvas)
python3 -m pytest tests/tools/asset_creator/test_gui_state.py tests/tools/asset_creator/test_gui_preview.py tests/tools/asset_creator/test_canvas.py -v
```
