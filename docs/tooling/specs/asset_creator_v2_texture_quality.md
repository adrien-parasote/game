# Asset Creator V2 — Texture Quality Upgrade

> Document Type: Implementation

## Deep Links
- [V1 Spec](./asset_creator_spec.md#L1)
- [V1 Palette module](../../../tools/asset_creator/core/palette.py#L1)
- [V1 Texture module](../../../tools/asset_creator/core/texture.py#L1)
- [V1 Terrain presets](../../../tools/asset_creator/config/terrain_presets.yaml#L1)

## Goal

Upgrade the procedural texture pipeline from 4-color hard-threshold noise to
multi-color hue-shifted ramps with per-pixel variation, ordered dithering, and
detail overlays. The output should approach hand-drawn pixel art quality.

**V1 result:** 4 flat color bands from simplex noise → monotone, lifeless.
**V2 target:** 8-12 color hue-shifted ramps with smooth interpolation, micro-variation,
and terrain-specific detail stamps → rich, organic textures comparable to hand-drawn.

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | OKLCh color space gives uniform ramps without external deps | Low | [SHOW] verified via API call to `core/color_ramp.py` |
| 2 | 4×4 Bayer matrix is optimal at 32×32 scale | Low | [SHOW] verified via API call to `core/texture.py` |
| 3 | Grass blade height 2-4px reads well at 32×32 | Low | [SHOW] verified via API call to `core/detail_overlay.py` |
| 4 | Existing tests remain green (backward compat) | Medium | [SHOW] verified via CLI call to `pytest` |

## Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `tools/asset_creator/core/color_ramp.py` | Python Module | This spec § "Step 1" | `core/palette.py`, `core/texture.py` |
| `tools/asset_creator/core/detail_overlay.py` | Python Module | This spec § "Step 4" | `core/texture.py` |
| `tests/tools/asset_creator/test_color_ramp.py` | Python Test | This spec § "Test Case Specifications" | Pytest Runner |
| `tests/tools/asset_creator/test_detail_overlay.py` | Python Test | This spec § "Test Case Specifications" | Pytest Runner |

### Consumes
| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/asset_creator/config/terrain_presets.yaml` | YAML | This spec § "Step 5" | Map Designer |
| `tools/asset_creator/config/palettes/*.yaml` | YAML | This spec § "Step 2" | Map Designer |

### Public Interface
| Type | Identifier | Documented at |
|---|---|---|
| CLI parameter | `--quality v2` | This spec § "Step 6" |

### External Invocations
| Type | Invoked | Defined in |
|---|---|---|
| Python Library | `PIL` | Pillow dependency |

### Tracked Concepts
| Concept | Status in this spec | Mentioned in |
|---|---|---|
| Extended Palette | Upgraded to 8-12 colors | `specs/asset_creator_spec.md` |

---

## Anti-patterns

| Anti-pattern | Why it fails | Correct Approach |
|---|---|---|
| RGB interpolation for color ramps | Produces muddy mid-tones (brown between green and blue) | Use OKLCh for perceptually uniform interpolation |
| Bayer matrix > 4×4 at 32×32 scale | Creates visible grid patterns larger than tile features | Use 2×2 or 4×4 Bayer matrix |
| Detail noise amplitude > 10% of ramp range | Creates visual noise instead of subtle texture | Keep detail variation at 5-8% |
| Grass blades > 4px tall at 32×32 | Unreadable mush at game zoom level | 2-4px blade height max |
| Breaking `PaletteRole` enum backward compat | All existing tests fail | Keep SHADOW/BASE/HIGHLIGHT/ACCENT, add new roles as optional |

## Error Handling

| Error Condition | Detection | Fallback | User Impact |
|---|---|---|---|
| Palette YAML has < 4 colors but requests extended ramp | Validation at load time | Auto-generate from base color | Warning, generates anyway |
| Invalid hue_shift params | Range check (±60° max) | Clamp to valid range | Warning logged |
| Detail overlay density too high (> 0.5) | Bounds check | Clamp to 0.5 | Warning logged |

---

## Proposed Changes

### Step 1: Color Ramp Engine (OKLCh)

#### [NEW] `tools/asset_creator/core/color_ramp.py`

Color space utilities and hue-shifted ramp generation.

**Functions:**
```python
def rgb_to_oklch(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB (0-255) to OKLCh (lightness, chroma, hue°)."""

def oklch_to_rgb(L: float, C: float, h: float) -> tuple[int, int, int]:
    """Convert OKLCh back to clamped sRGB (0-255).
    
    Must explicitly clamp r, g, b values to [0, 255] using max(0, min(255, int(val)))
    to prevent gamut overflow and Pillow ValueError traceback.
    """

def generate_hue_shifted_ramp(
    base_rgb: tuple[int, int, int],
    num_steps: int = 9,
    shadow_hue_shift: float = -30.0,  # degrees, negative = cooler
    highlight_hue_shift: float = 20.0, # degrees, positive = warmer
    lightness_range: float = 0.35,     # total L spread
    saturation_curve: float = 0.02,    # shadows slightly more saturated
) -> list[tuple[int, int, int]]:
    """Generate a hue-shifted color ramp from a base color.
    
    Shadows shift toward cooler hues, highlights toward warmer hues.
    Saturation increases slightly in shadows, decreases in highlights.
    """

def interpolate_oklch(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Interpolate between two RGB colors in OKLCh space."""
```

**Reference analysis of existing hand-drawn grass:**
- 11 unique colors, hue range 94-95° (minimal hue shift in grass-1)
- Lightness range: 0.28 - 0.48 (spread = 0.20)
- Saturation: consistent at 0.30
- Grass-2 variant shows hue range 34°-120° (much more hue shift)

---

### Step 2: Extended Palette System

#### [MODIFY] `tools/asset_creator/core/palette.py`

Expand from 4 to 8-12 colors while keeping backward compatibility.

**Changes:**
1. Keep `PaletteRole` enum as-is (SHADOW, BASE, HIGHLIGHT, ACCENT) for backward compat
2. Add `Palette.extended_colors` property that returns the full ramp (8-12 colors)
3. Add `Palette.interpolate(t: float) -> tuple[int,int,int]` — map [0,1] to smooth ramp position
4. Add `generate_extended_palette(base_color, params) -> Palette` factory

**New YAML format (backward compatible):**
```yaml
name: forest_grass
# V1 colors still work
colors:
  - "#2d5a1e"
  - "#3e7c27"
  - "#5a9e3a"
  - "#7bc04f"
roles:
  shadow: 0
  base: 1
  highlight: 2
  accent: 3
# V2 extension: auto-generate ramp from base color
ramp:
  base_color: "#5a9e3a"    # anchor color
  steps: 9                  # number of colors in ramp
  shadow_hue_shift: -15     # degrees toward blue/teal
  highlight_hue_shift: 10   # degrees toward yellow
  lightness_range: 0.25     # total lightness spread
```

When `ramp` section exists, `palette.extended_colors` returns the auto-generated
9-step ramp. When absent, it interpolates between the 4 manual colors.

#### [MODIFY] `tools/asset_creator/config/palettes/*.yaml`

Update all 6 palette files with `ramp` parameters calibrated from hand-drawn reference analysis:

| Palette | Base Color | Steps | Shadow Shift | Highlight Shift | Reference |
|---------|-----------|-------|-------------|----------------|-----------|
| forest_grass | `#618447` | 11 | -15° (→teal) | +10° (→yellow) | 00-grass-1.png analysis |
| dry_dirt | `#7d6b3a` | 9 | -10° (→olive) | +15° (→amber) | 01-dirt.png analysis |
| stone_path | `#ced4c7` | 11 | -5° (→blue-gray) | +5° (→warm gray) | 02-paving_stone.png |
| sand | `#d4b85a` | 9 | -20° (→brown) | +10° (→cream) | Warm sand reference |
| snow | `#dce8f0` | 7 | -10° (→ice blue) | +5° (→warm white) | Cold snow reference |
| water | `#2a5a8a` | 9 | -10° (→deep blue) | +15° (→cyan) | Water reference |

---

### Step 3: Smooth Ramp Texture Generation

#### [MODIFY] `tools/asset_creator/core/texture.py`

Replace `_noise_to_color()` hard thresholds with smooth ramp interpolation + micro-variation.

**Key changes:**

1. **Replace `_noise_to_color()` with `_noise_to_ramp_color()`:**
   - Map noise value [-1,1] → [0,1] → position in extended color ramp
   - Interpolate between adjacent colors in OKLCh space
   - No more hard bands

2. **Add per-pixel micro-variation:**
   - Second high-frequency noise layer (scale ~0.5)
   - Jitters ramp position by ±5-8% 
   - Breaks flat-color-band look

3. **Add Bayer ordered dithering:**
   - 4×4 Bayer matrix at color ramp boundaries
   - Threshold determines rounding direction
   - Creates pixel art-style smooth transitions

4. **Add `TextureParams` fields (backward compat via defaults):**
   ```python
   # V2 additions
   use_smooth_ramp: bool = False      # enable smooth interpolation
   detail_scale: float = 0.5          # micro-variation noise frequency
   detail_strength: float = 0.06      # micro-variation amplitude
   use_dithering: bool = False         # enable Bayer dithering
   dither_matrix_size: int = 4         # 2 or 4
   ```

5. **New `generate_noise_texture_v2()` function** (V1 function kept for compat):
   ```python
   def generate_noise_texture_v2(
       width, height, palette, params, seed=0
   ) -> Image.Image:
       """V2 texture: smooth ramp + micro-variation + dithering."""
       base_noise = OpenSimplex(seed=seed)
       detail_noise = OpenSimplex(seed=seed + 1000)
       
       for y in range(height):
           for x in range(width):
               # Layer 1: base shape noise (toroidal)
               base_value = _compute_multi_octave_noise(...)
               
               # Normalize to [0, 1]
               t = (base_value + 1.0) / 2.0
               
               # Layer 2: per-pixel detail jitter
               detail = detail_noise.noise2(
                   x * params.detail_scale,
                   y * params.detail_scale
               ) * params.detail_strength
               t = clamp(t + detail, 0.0, 1.0)
               
               # Map to extended ramp with optional dithering
               if params.use_dithering:
                   rgb = _ramp_color_dithered(t, palette, x, y)
               else:
                   rgb = palette.interpolate(t)
               
               pixels[x, y] = (*rgb, 255)
   ```

---

### Step 4: Detail Overlay System

#### [NEW] `tools/asset_creator/core/detail_overlay.py`

Terrain-specific procedural detail stamps applied after base texture generation.

**Functions:**
```python
def apply_detail_overlay(
    img: Image.Image,
    palette: Palette,
    detail_type: str,  # "grass_blades" | "dirt_specks" | "stone_cracks" | "sand_grains" | "none"
    density: float,
    seed: int,
    max_height: int = 4,
    max_length: int = 4,
) -> Image.Image:
    """Apply terrain-specific detail overlay to base texture.

    Args:
        max_height: Maximum height for grass_blades detail (pixels).
        max_length: Maximum length for stone_cracks detail (pixels).
    """
```

**Detail types:**

| Type | Description | Params |
|---|---|---|
| `grass_blades` | 2-4px vertical strokes in highlight/accent colors | density, max_height |
| `dirt_specks` | Single-pixel dark/light dots scattered randomly | density |
| `stone_cracks` | 2-3px thin lines in shadow color | density, max_length |
| `sand_grains` | Single-pixel bright/dark grains | density |
| `none` | No overlay | — |

**Grass blade algorithm:**
```python
def _add_grass_blades(img, palette, seed, density=0.12, max_height=4):
    rng = random.Random(seed)
    w, h = img.size
    pixels = img.load()
    
    num_blades = int(w * h * density)
    highlight = palette.extended_colors[-3]  # near-highlight
    accent = palette.extended_colors[-2]     # bright
    
    for _ in range(num_blades):
        bx = rng.randint(0, w - 1)
        safe_max_height = max(1, max_height)
        by = rng.randint(safe_max_height, h - 1)
        blade_h = rng.randint(2, safe_max_height) if safe_max_height >= 2 else 1
        
        for j in range(blade_h):
            py = by - j
            if 0 <= py < h:
                color = accent if j == blade_h - 1 else highlight
                pixels[bx, py] = (*color, 255)
            # Random bend
            if rng.random() < 0.3:
                bx = max(0, min(w - 1, bx + rng.choice([-1, 1])))
```

---

### Step 5: Updated Terrain Presets

#### [MODIFY] `tools/asset_creator/config/terrain_presets.yaml`

Add V2 texture parameters to each terrain preset:

```yaml
terrains:
  grass:
    palette: forest_grass
    texture:
      type: noise
      version: 2              # NEW: use V2 pipeline
      scale: 0.12
      octaves: 3
      persistence: 0.5
      thresholds: [-0.2, 0.4, 0.8]  # RETAINED for V1 compatibility
      detail_scale: 0.5       # NEW: micro-variation frequency
      detail_strength: 0.06   # NEW: micro-variation amplitude
      use_dithering: true      # NEW: Bayer dithering
    edge:
      style: organic
      width: 3
      noise_scale: 0.3
    detail:                    # NEW: detail overlay config
      type: grass_blades
      density: 0.12
      max_height: 4
    border:
      shadow_width: 1
      highlight_width: 1
```

---

### Step 6: CLI Integration

#### [MODIFY] `tools/asset_creator/cli.py`

Add `--quality` flag to select V1 or V2 pipeline:
- `--quality v1` — original 4-color threshold pipeline
- `--quality v2` — extended ramp + dithering + detail overlays (new default)

---

## Test Case Specifications

### Color Ramp Tests (`asset_creator/test_color_ramp.py`)

| Test ID | Description |
|---|---|
| TC-025 | `rgb_to_oklch` + `oklch_to_rgb` round-trip: input RGB → OKLCh → RGB matches original ±1 |
| TC-026 | `generate_hue_shifted_ramp`: output has exactly `num_steps` colors |
| TC-027 | Ramp lightness monotonically increases from shadow to highlight |
| TC-028 | Shadow colors have hue shifted toward `shadow_hue_shift` direction |
| TC-029 | All generated colors are valid sRGB (0-255 per channel) |
| TC-030 | `interpolate_oklch(a, b, 0.0)` returns `a`, `(a, b, 1.0)` returns `b` |

### Extended Palette Tests (additions to `asset_creator/test_palette.py`)

| Test ID | Description |
|---|---|
| TC-031 | Palette with `ramp` config generates `extended_colors` with correct count |
| TC-032 | `palette.interpolate(0.0)` returns darkest color, `(1.0)` returns brightest |
| TC-033 | Backward compat: palette without `ramp` still works with V1 API |
| TC-034 | Extended palette colors are all unique (no duplicates) |

### Texture V2 Tests (additions to `asset_creator/test_texture.py`)

| Test ID | Description |
|---|---|
| TC-035 | V2 texture uses more than 4 unique colors (at least 7) |
| TC-036 | V2 texture still has correct dimensions (32×32) |
| TC-037 | V2 texture still tiles seamlessly (toroidal noise preserved) |
| TC-038 | Seed reproducibility: same seed → identical image |
| TC-039 | Bayer dithering: no single color occupies > 40% of pixels (band-breaking) |
| TC-040 | V1 texture still works unchanged when `version: 1` |

### Detail Overlay Tests (`asset_creator/test_detail_overlay.py`)

| Test ID | Description |
|---|---|
| TC-041 | Grass blade overlay adds pixels different from base texture |
| TC-042 | Overlay preserves image dimensions |
| TC-043 | Overlay is seed-reproducible |
| TC-044 | `detail_type: "none"` returns image unchanged |
| TC-045 | Blade pixels use highlight/accent colors from palette |

### Integration Tests (Pipeline Seams)

| Test ID | Description |
|---|---|
| IT-004 | Verify full V2 generator pipeline (Proposed Changes, Produces): color ramp engine (OKLCh) to texture generation using dithering and detail overlay stamps. |
| IT-005 | Verify that YAML loader correctly parses extended palette config with hue-shift params and generates correct color ramps. |
| IT-006 | Verify that CLI command `--quality v2` successfully runs the CLI integration, parses terrain presets, and exports V2 PNG/TSX assets. |

---

## Verification Plan

### Automated Tests
```bash
# Run all V2 tests
pytest tests/tools/asset_creator/ -v --tb=short

# Verify backward compat (V1 tests still pass)
pytest tests/tools/asset_creator/test_palette.py tests/tools/asset_creator/test_texture.py -v

# Coverage
pytest tests/tools/asset_creator/ --cov=tools.asset_creator --cov-report=term-missing
```

### Visual Verification
```bash
# Generate V1 vs V2 comparison
python -m tools.asset_creator generate --terrain grass --quality v1 --name grass-v1
python -m tools.asset_creator generate --terrain grass --quality v2 --name grass-v2

# Preview side by side
python -m tools.asset_creator preview assets/images/autotiles/grass-v2.png
```

### Manual Verification
1. Import V2 `.tsx` into Tiled
2. Paint a map using Wang terrain tool
3. Verify seamless tiling (no visible seams)
4. Compare visual quality with hand-drawn 00-grass-1.png

---

## Project File Tree

The following files are managed or modified by this specification:
```
tools/
  asset_creator/
    cli.py                            # [DEV-TOOL] Modified to add --quality flag
    core/
      palette.py                      # [DEV-TOOL] Modified to expand extended palette
      texture.py                      # [DEV-TOOL] Modified to support V2 textures
      color_ramp.py                   # [DEV-TOOL] New OKLCh color ramp engine
      detail_overlay.py               # [DEV-TOOL] New terrain-specific stamps
    config/
      terrain_presets.yaml            # [CONFIG] Presets updated with V2 parameters
      palettes/
        forest_grass.yaml             # [CONFIG] Expanded with ramp details
        dry_dirt.yaml                 # [CONFIG] Expanded with ramp details
        stone_path.yaml               # [CONFIG] Expanded with ramp details
        sand.yaml                     # [CONFIG] Expanded with ramp details
        snow.yaml                     # [CONFIG] Expanded with ramp details
        water.yaml                    # [CONFIG] Expanded with ramp details
tests/
  tools/
    asset_creator/
      test_palette.py                 # [DEV-TOOL] Expanded palette tests
      test_texture.py                 # [DEV-TOOL] Expanded texture tests
      test_color_ramp.py              # [DEV-TOOL] New color ramp tests
      test_detail_overlay.py          # [DEV-TOOL] New detail overlay tests
docs/
  tooling/
    specs/
      asset_creator_spec.md           # [DOC] V1 specification for the tool
      asset_creator_v2_texture_quality.md # [DOC] This upgraded specification
```

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Keep V1 API backward-compatible; all 216 existing tests stay green; use OKLCh not RGB for interpolation; preserve toroidal noise for seamless tiling |
| **Ask first** | Adding `colour-science` as dependency; changing palette YAML schema |
| **Never do** | Break V1 `PaletteRole` enum; use anti-aliasing (NEAREST only); generate more than 12 colors in a ramp (muddy at 32×32) |
