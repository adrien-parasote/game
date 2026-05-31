# Asset Creator Tool — Implementation Plan

> Document Type: Implementation

## Deep Links
- [Project Master Spec](../game/specs/00_MASTER.md#L1)
- [Tileset Format Reference](https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#tileset)

## Assumptions
| Assumption | Impact | Risk | Source Type |
|---|---|---|---|
| Tiled 1.10 XML format remains stable for TSX output | Breaks map loading | Low | [SHOW] verified via CLI call to `tiled` |
| `opensimplex` noise generation is deterministic across platforms for a given seed | Procedural generation irreproducibility | Medium | [SHOW] verified via API call `noise4d()` |
| Project uses 32x32 tiles | Autotile blob generation breaks if tile size differs | Low | [SHOW] verified via CLI call `python` |
## Goal

Build an independent Python tool (`tools/asset_creator/`) that generates Tiled-native
tileset assets (47-tile blob PNG + TSX with Wang sets) from terrain definitions,
eliminating the RPG Maker XP intermediate format.

**V1 Scope:** Procedural generation (noise + patterns) with Pygame preview.
**V2 Scope:** AI-assisted generation + animated water tiles.

---

## Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `assets/images/autotiles/<name>.png` | PNG (RGBA) | This spec § "PNG Exporter" | Tiled Map Editor, Game Engine |
| `assets/tiled/autotiles/<name>.tsx` | TSX (XML) | This spec § "TSX Exporter" | Tiled Map Editor |

### Consumes
| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/asset_creator/config/terrain_presets.yaml` | YAML | This spec § "Terrain Presets" | Map Designer |
| `tools/asset_creator/config/palettes/*.yaml` | YAML | This spec § "Palette System" | Map Designer |

### Public Interface
| Type | Identifier | Documented at |
|---|---|---|
| CLI Command | `python -m tools.asset_creator` | This spec § "Core Infrastructure" |
| CLI subcommand | `generate` | This spec § "Core Infrastructure" |
| CLI subcommand | `list` | This spec § "Core Infrastructure" |
| CLI subcommand | `preview` | This spec § "Core Infrastructure" |
| CLI subcommand | `gui` | V3 GUI spec § "Step 2" |

### External Invocations
| Type | Invoked | Defined in |
|---|---|---|
| Python Library | `opensimplex` | External library (opensimplex) |
| Python Library | `numpy` | External library (numpy) |
| Python Library | `PIL` | External library (Pillow) |
| Python Library | `pygame` | External library (pygame-ce) |
| Python Library | `dearpygui` | External library (Dear PyGui) |

### Tracked Concepts
| Concept | Status in this spec | Mentioned in |
|---|---|---|
| 47-Tile Blob | Implemented natively | [blob_autotile_pipeline_spec.md](./blob_autotile_pipeline_spec.md#L1) |

---

## Anti-patterns
| Anti-pattern | Why it fails | Correct Approach |
|---|---|---|
| Generating fully transparent sub-tiles | Breaks Tiled rendering and occlusion | Ensure at least 1 opaque pixel or reject generation |
| Hardcoding tile sizes in assembly | Fails if project switches to 16x16 or 48x48 | Use constants or `terrain_config` parameters |
| Outputting `wangset` without `wangid` for all 47 | Map editor tools fail to autocomplete tiles | Enforce 47 `wangtile` entries in XML |
| Using standard random instead of seeded noise | Cannot recreate a specific tileset variation | Pass `--seed` to noise generator consistently |
| Missing error states for invalid palette YAML | Tool crashes without context during build | Catch YAML parse errors, return explicit error message |

## Error Handling
| Error Condition | Detection | Fallback | User Impact |
|---|---|---|---|
| Palette YAML missing/invalid | `FileNotFoundError` or YAML syntax error | Abort generation | Tool fails, developer must fix YAML |
| Target export directory unwriteable | `PermissionError` on PNG/TSX write | Abort generation | Tool fails |
| Invalid bits in bitmask generation | Bitmask > 255 | Throw `ValueError` | Tool halts, prevents corrupt tilesets |

## Directory Structure

```text
tools/asset_creator/
  __init__.py
  __main__.py
  cli.py
  config/
    palettes/
      dry_dirt.yaml
      forest_grass.yaml
      sand.yaml
      snow.yaml
      stone_path.yaml
      water.yaml
    terrain_presets.yaml
  core/
    __init__.py
    color_ramp.py
    detail_overlay.py
    minimap.py
    palette.py
    subtile.py
    terrain.py
    texture.py
    tile_assembler.py
  exporters/
    __init__.py
    png_exporter.py
    tsx_exporter.py
  gui/
    __init__.py
    app.py
    canvas.py
    pipeline.py
    preview.py
    state.py
  preview/
    __init__.py
    pygame_preview.py

tests/tools/asset_creator/
  test_canvas.py
  test_cli.py
  test_color_ramp.py
  test_detail_overlay.py
  test_exporters.py
  test_gui_integration.py
  test_gui_preview.py
  test_gui_state.py
  test_integration.py
  test_minimap.py
  test_palette.py
  test_subtile.py
  test_texture.py
  test_tile_assembler.py
```

## Proposed Changes

### Core Infrastructure

#### [NEW] `tools/asset_creator/__init__.py`
Package init. Version string.

#### [NEW] `tools/asset_creator/__main__.py`
Entry point for `python -m tools.asset_creator`. Delegates to CLI.

#### [NEW] `tools/asset_creator/cli.py`
argparse-based CLI:
- `generate` — generate a terrain tileset
  - `--terrain <name>` (preset name or path to custom YAML)
  - `--output-dir <path>` (default: `assets/images/autotiles/`)
  - `--tsx-dir <path>` (default: `assets/tiled/autotiles/`)
  - `--seed <int>` (reproducible generation)
  - `--variants <N>` (generate N variants)
  - `--preview` (open Pygame preview before export)
  - `--name <stem>` (output filename stem, e.g. `00-grass-1`)
- `list` — list available terrain presets
- `preview` — preview an existing tileset PNG in Pygame

---

### Palette System (Step 1)

#### [NEW] `tools/asset_creator/core/palette.py`
- `Palette` dataclass: `name`, `colors` (list of RGB tuples), `roles` dict mapping semantic names to color indices
  - Roles: `base`, `shadow`, `highlight`, `accent`, `transition`
- `load_palette(path)` — load from YAML/HEX file
- `load_lospec(slug)` — fetch from Lospec API, cache locally
- `PaletteRole` enum for semantic color roles

**Palette YAML format:**
```yaml
name: forest_grass
colors:
  - "#2d5a1e"  # dark (shadow)
  - "#3e7c27"  # base
  - "#5a9e3a"  # highlight
  - "#7bc04f"  # accent
roles:
  shadow: 0
  base: 1
  highlight: 2
  accent: 3
```

#### [NEW] `tools/asset_creator/config/palettes/`
Bundled palette files:
- `palettes/forest_grass.yaml`, `palettes/dry_dirt.yaml`, `palettes/stone_path.yaml`
- `palettes/sand.yaml`, `palettes/snow.yaml`, `palettes/water.yaml`

---

### Texture Generation (Step 2)

#### [NEW] `tools/asset_creator/core/texture.py`
Procedural texture generation using opensimplex + NumPy:
- `generate_noise_texture(width, height, palette, params)` → `PIL.Image`
  - `params`: `scale`, `octaves`, `persistence`, `lacunarity`, `thresholds`
  - Noise values in `[-1, 1]` are mapped to `PaletteRole` colors based on the `thresholds` list.
- `generate_pattern_texture(width, height, palette, pattern_type, params)` → `PIL.Image`
  - Pattern types: `solid`, `noise`, `dithered`, `stippled`, `striped` (V1 restricted to patterns reproducible via simplex noise)
- Toroidal Seamless Noise:
  To ensure the procedural texture tiles perfectly without visual seam borders or snapping/dithering artifacts, noise coordinates $(x, y)$ must be mapped onto a 2D torus in 4D noise space:
  ```python
  import math
  def sample_toroidal_noise(x, y, width, height, scale, opensimplex_generator):
      angle_x = (x / width) * 2 * math.pi
      angle_y = (y / height) * 2 * math.pi
      # Calibrate radius to avoid flat colors on 32x32 tiles
      rx = (width * scale) / (2 * math.pi)
      ry = (height * scale) / (2 * math.pi)
      nx = math.cos(angle_x) * rx
      ny = math.sin(angle_x) * rx
      nz = math.cos(angle_y) * ry
      nw = math.sin(angle_y) * ry
      return opensimplex_generator.noise4d(nx, ny, nz, nw)
  ```

**Anti-patterns from learnings:**
- L-MAP-003: Never generate fully transparent sub-tiles — validate alpha channel
- Use `Image.Resampling.NEAREST` exclusively — no anti-aliasing for pixel art

---

### Sub-tile Generation (Step 3)

#### [NEW] `tools/asset_creator/core/subtile.py`
The heart of the tool. Generates 20 distinct sub-tiles (16×16) grouped by quadrant (TL, TR, BL, BR) that define a terrain:

```
Sub-tile set for one terrain (20 sub-tiles total):
┌─────────────────────────────────────────────────────┐
│  For each quadrant (TL, TR, BL, BR), generate a     │
│  distinct 16x16 sub-tile for the following types:   │
│  - FILL (center seamless texture)                   │
│  - EDGE_V (vertical edge)                           │
│  - EDGE_H (horizontal edge)                         │
│  - OUTER_CORNER (convex corner)                     │
│  - INNER_CORNER (concave corner)                    │
└─────────────────────────────────────────────────────┘
```

- `SubTileSet` dataclass containing all 20 sub-tiles as `PIL.Image` (16×16). The assembler will construct isolated tiles from the 4 `OUTER_CORNER` quadrants.
- `generate_subtiles(base_texture: Image, edge_config: dict, seed: int)` → `SubTileSet`
- Each sub-tile is generated by combining:
  1. Base texture (fill area from `core/texture.py`)
  2. Edge mask (determines where the terrain fades to transparent)
  3. Border effects (darker edge pixels, highlight along the border)

**Edge generation algorithm:**
- Cardinal edges: use a distance field $D(p)$ (from the pixel to the border) combined with 2D simplex noise to create organic variation:
  `mask(p) = (D_cardinal(p) + noise(p)) > threshold`.
- Outer corners: combine adjacent horizontal and vertical distance fields using minimum:
  `mask(p) = (min(D_h(p), D_v(p)) + noise(p)) > threshold`.
- Inner corners: combine adjacent distance fields using maximum:
  `mask(p) = (max(D_h(p), D_v(p)) + noise(p)) > threshold`.
- Isolated: combine all 4 cardinal distance fields:
  `mask(p) = (min(D_t(p), D_r(p), D_b(p), D_l(p)) + noise(p)) > threshold`.

---

### Tile Assembler (Step 4)

#### [NEW] `tools/asset_creator/core/tile_assembler.py`
Assembles the 47 blob tiles from the sub-tile set.

**Reuse from existing code:** The blob bitmask logic from
`scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py` is adapted here:

- `BLOB_BITMASKS` — 47 valid bitmask values (already defined in project)
- `assemble_tile(subtile_set, bitmask)` → `PIL.Image` (32×32)
  - For each quadrant (TL/TR/BL/BR), select the appropriate sub-tile based on
    cardinal + diagonal neighbor state
- `assemble_tileset(subtile_set)` → `PIL.Image` (strip: 47×32 wide, 32 tall)
  - Calls `assemble_tile()` for each of the 47 bitmasks

**wangid mapping (L-MAP-002 — CRITICAL):**
Order is `Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft`
```python
def blob_wang_id(bitmask: int) -> str:
    n  = (bitmask >> 1) & 1
    ne = (bitmask >> 2) & 1
    e  = (bitmask >> 4) & 1
    se = (bitmask >> 7) & 1
    s  = (bitmask >> 6) & 1
    sw = (bitmask >> 5) & 1
    w  = (bitmask >> 3) & 1
    nw = (bitmask >> 0) & 1
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
```

---

### Exporters (Step 5)

#### [NEW] `tools/asset_creator/exporters/png_exporter.py`
- `export_png(tileset_image, output_path)` → saves PNG strip
- Validates: no fully transparent tiles (L-MAP-003), correct dimensions
- Naming follows project convention: `NN-category[-variant].png`

#### [NEW] `tools/asset_creator/exporters/tsx_exporter.py`
- `export_tsx(output_path, png_path, name, wang_tiles)` → writes TSX XML
- Generates valid Wang set with `type="mixed"` and all 47 wangtile entries
- References PNG via relative path (matching existing convention)
- Uses `xml.etree.ElementTree` (same as existing scripts)

**TSX structure (from project convention):**
```xml
<?xml version='1.0' encoding='utf-8'?>
<tileset version="1.10" tiledversion="1.10.0" name="{name}"
         tilewidth="32" tileheight="32" tilecount="47" columns="47">
  <image source="{relative_png_path}" width="1504" height="32"/>
  <wangsets>
    <wangset name="{name}" type="mixed" tile="-1">
      <wangcolor name="{name}" color="{color}" tile="-1" probability="1"/>
      <!-- 47 wangtile entries -->
    </wangset>
  </wangsets>
</tileset>
```

---

### Terrain Presets (Step 6)

#### [NEW] `tools/asset_creator/config/terrain_presets.yaml`
```yaml
terrains:
  grass:
    palette: forest_grass
    texture:
      type: noise
      scale: 0.15
      octaves: 3
      persistence: 0.5
      thresholds: [-0.2, 0.4, 0.8]
    edge:
      style: organic      # organic | straight | dithered
      width: 3             # border width in pixels
      noise_scale: 0.3     # edge irregularity
    border:
      shadow_width: 1
      highlight_width: 1

  dirt:
    palette: dry_dirt
    texture:
      type: noise
      scale: 0.2
      octaves: 2
      persistence: 0.6
      thresholds: [-0.2, 0.4, 0.8]
    edge:
      style: organic
      width: 2
      noise_scale: 0.25

  paving_stone:
    palette: stone_path
    texture:
      type: stippled
      density: 0.5
    edge:
      style: straight
      width: 2

  sand:
    palette: sand
    texture:
      type: noise
      scale: 0.1
      octaves: 2
      persistence: 0.4
      thresholds: [-0.2, 0.4, 0.8]
    edge:
      style: dithered
      width: 4

  snow:
    palette: snow
    texture:
      type: stippled
      density: 0.3
    edge:
      style: dithered
      width: 3

  water:
    palette: water
    texture:
      type: noise
      scale: 0.12
      octaves: 2
    edge:
      style: organic
      width: 2
    # Note: V1 = static water only. V2 adds animated frames.
```

---

### Pygame Preview (Step 7)

#### [NEW] `tools/asset_creator/preview/pygame_preview.py`
- Opens a Pygame window showing:
  1. The 47-tile strip (scrollable)
  2. A mini-map (e.g. 8×8 tiles) with simulated autotiling
- Autotiling simulation: randomly place terrain on a grid, compute bitmasks, display correct tiles
- Controls:
  - `R` — regenerate with new seed
  - `S` — save/export to files
  - `ESC` — close without saving
  - Click to toggle terrain on mini-map cells
- Window size: ~640×480, scaled ×2 for visibility

---

### Test Suite (Step 8)

#### Unit Tests

| Test ID | Module | Description |
|---|---|---|
| TC-001 | test_palette.py | Load palette from YAML |
| TC-002 | test_palette.py | Validate color count and format |
| TC-003 | test_palette.py | Role mapping correctness |
| TC-004 | test_texture.py | Noise texture dimensions and palette conformance |
| TC-005 | test_texture.py | Pattern texture correctness (solid, cobblestone) |
| TC-006 | test_texture.py | Seamless tiling validation (edge pixel comparison) |
| TC-007 | test_subtile.py | Sub-tile set completeness (20 sub-tiles generated) |
| TC-008 | test_subtile.py | Dimensions (all 16x16) |
| TC-009 | test_subtile.py | No fully transparent sub-tiles (L-MAP-003) |
| TC-010 | test_subtile.py | Edge mask correctness (center pixels opaque, edge pixels follow mask) |
| TC-011 | test_tile_assembler.py | 47 tiles generated |
| TC-012 | test_tile_assembler.py | All tiles 32x32 |
| TC-013 | test_tile_assembler.py | Bitmask 0 = isolated tile |
| TC-014 | test_tile_assembler.py | Bitmask 255 = full center tile |
| TC-015 | test_tile_assembler.py | Wang ID correctness for all 47 bitmasks (L-MAP-002) |
| TC-016 | test_tile_assembler.py | No fully transparent tiles |
| TC-017 | test_exporters.py | PNG export: correct dimensions, file exists, readable |
| TC-018 | test_exporters.py | TSX export: valid XML, correct wangid values, correct image reference |
| TC-019 | test_exporters.py | Relative path computation |
| TC-020 | test_cli.py | `generate` command produces PNG + TSX |
| TC-021 | test_cli.py | `list` command shows presets |
| TC-022 | test_cli.py | `--seed` produces reproducible output |
| TC-023 | test_cli.py | `--variants` generates N files |
| TC-024 | test_cli.py | Error handling (invalid terrain, bad path) |

#### Integration Tests (Pipeline Seams)

| Test ID | Description |
|---|---|
| IT-001 | Run full pipeline (texture -> subtiles -> assembly -> export) and verify valid PNG and TSX exist without crashing |
| IT-002 | Verify that palette loading correctly passes through to texture generation |
| IT-003 | Verify that sub-tile assembly successfully exports an image matching expected dimensions |

---

## Verification Plan

### Automated Tests
```bash
# Run all tool tests
pytest tests/tools/ -v --tb=short

# Coverage check
pytest tests/tools/ --cov=tools.asset_creator --cov-report=term-missing

# Verify output is valid Tiled format
python -c "import xml.etree.ElementTree as ET; ET.parse('assets/tiled/autotiles/00-grass-1.tsx')"
```

### Manual Verification
1. Generate a grass tileset: `python -m tools.asset_creator generate --terrain grass --preview`
2. Import the generated `.tsx` into Tiled
3. Paint a small map using the Wang terrain tool
4. Verify seamless tiling (no visible seams between tiles)
5. Load the map in-game to verify rendering compatibility

---

## Dependencies to Add

```
# In requirements.txt or pyproject.toml (tools section)
opensimplex
PyYAML
# Pillow and pygame-ce already present
```

---

## File Tree

```
assets/
  images/
    autotiles/
      00-grass-1.png
      input.png
      foo.png
  tiled/
    autotiles/
      00-grass-1.tsx
      foo.tsx
tools/
  asset_creator/
    __init__.py
    __main__.py
    cli.py
    core/
      palette.py
      texture.py
      subtile.py
      tile_assembler.py
    exporters/
      png_exporter.py
      tsx_exporter.py
    config/
      terrain_presets.yaml
      palettes/
        forest_grass.yaml
        dry_dirt.yaml
        stone_path.yaml
        sand.yaml
        snow.yaml
        water.yaml
    preview/
      pygame_preview.py
tests/
  tools/
requirements.txt
pyproject.toml
```
