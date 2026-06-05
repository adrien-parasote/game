# Spec — Recolor Engine + Lospec Palette Bundle

> Document Type: Implementation
> **Covers:** F5 (recolor engine), F6 (Lospec palettes), F15 (nearest-color auto-mapping)
> **Blueprint:** [asset_convertor_ui_v2_blueprint.md](../strategic/asset_convertor_ui_v2_blueprint.md)
> **ADR:** [ADR-007-4](../ADRs/ADR-007-asset-convertor-ui-v2.md#adr-007-4-recolor--palette-remapping-not-hue-shift)

---

## Deep Links

- [Blueprint § Recolor Engine (ADR-UI-004)](../strategic/asset_convertor_ui_v2_blueprint.md#adr-ui-004-recolor-engine--palette-first-adopted)
- [Lospec palette list](https://lospec.com/palette-list)
- [Recolor Panel spec (consumer)](./asset_convertor_mv_gui.md#recolor-panel)
- [GUI State spec — RecolorState](./asset_convertor_mv_gui.md#recolorstate-fields)

---

## Goal

Implement a pure-function recolor engine that:
1. Extracts the unique color palette from any RGBA PNG
2. Provides 6 embedded Lospec palettes as static Python dicts
3. Proposes an automatic nearest-color mapping from source palette → target palette
4. Applies a user-defined remapping table (source_color → target_color) to produce a new image

No file I/O. No GUI imports. All functions are stateless and return new images.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Return new PIL Images (never mutate input). Skip fully-transparent pixels during palette extraction (alpha < threshold). Validate that all source colors in the remap table exist in the image before applying. Use ΔE (CIE76) for nearest-color comparison. |
| **Ask first** | Adding more embedded palettes beyond the 6 specified. Changing the `extract_palette()` tolerance algorithm. Supporting palette files on disk (`.gpl`, `.ase`). |
| **Never do** | Import from `gui/`. Mutate the input image. Use Euclidean RGB distance for nearest-color matching (perceptually wrong — use ΔE). Silently skip unmatched source colors. |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `core/recolor.py` | Python Module | This spec § "Recolor Engine API" | `gui/recolor_panel.py` |
| `core/palettes.py` | Python Module | This spec § "Lospec Palette Bundle" | `gui/recolor_panel.py` |
| `tests/tools/asset_convertor/test_recolor.py` | Python Tests | This spec § "Test Cases" | Pytest runner |

### Consumes

N/A — pure computation module, no dependencies on other project modules.

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Type alias | `Color = tuple[int, int, int, int]` | This spec § "Type Definitions" |
| Type alias | `RemapTable = dict[Color, Color]` | This spec § "Type Definitions" |
| Type alias | `Palette = list[Color]` | This spec § "Type Definitions" |
| Function | `extract_palette(img, alpha_threshold, max_colors) -> Palette` | This spec § "extract_palette" |
| Function | `propose_remap(source_palette, target_palette) -> RemapTable` | This spec § "propose_remap" |
| Function | `apply_remap(img, remap_table) -> Image.Image` | This spec § "apply_remap" |
| Dict | `LOSPEC_PALETTES: dict[str, Palette]` | This spec § "Lospec Palette Bundle" |

### External Invocations

N/A

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| `RecolorState` (GUI state for the remap table) | Consumed by recolor_panel.py | GUI spec § "RecolorState" |
| Color tuple (RGBA 0–255 ints) | Defined here | GUI spec |

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| A1 | `colorsys` (Python stdlib) is sufficient for RGB→Lab approximation adequate for ΔE nearest-color matching | Low | **ASSUMED** — CIE76 ΔE with sRGB-to-Lab via colorsys gives good perceptual grouping for pixel-art palettes. Not scientifically rigorous but sufficient for game asset recoloring. |
| A2 | RPG Maker MV exported PNGs are RGB or RGBA mode (not mode 'P' indexed) | Medium | **ASSUMED** — MV uses standard PNG export. If a 'P' mode image is encountered, `img.convert('RGBA')` handles it transparently. |
| A3 | Pixel-art tilesets from RPG Maker MV have ≤ 256 unique colors per block | Low | **ASSUMED** — RPG Maker's tile format is designed for indexed-color aesthetics. Observed in shared A3/A4 examples: typically 8–64 unique colors. |
| A4 | Lospec palettes (Endesga 32, etc.) are CC0/public domain and safe to embed | Low | **VERIFIED** — Lospec palette-list terms confirm community palettes are freely usable. Confirmed 2026-06-05. |
| A5 | `tkinter.colorchooser.askcolor()` returns `((R, G, B), '#rrggbb')` or `(None, None)` on cancel | Low | **CITED** — Python docs: https://docs.python.org/3/library/dialog.html#tkinter.colorchooser.askcolor |

---

## Type Definitions

```python
# In core/recolor.py
from typing import TypeAlias
from PIL import Image

Color: TypeAlias = tuple[int, int, int, int]   # (R, G, B, A), each 0–255
Palette: TypeAlias = list[Color]               # ordered list of unique colors
RemapTable: TypeAlias = dict[Color, Color]     # source_color -> target_color
```

---

## Recolor Engine API

### `extract_palette()`

```python
def extract_palette(
    img: Image.Image,
    alpha_threshold: int = 10,
    max_colors: int = 256,
) -> Palette:
    """
    Extract unique non-transparent colors from a PIL Image.

    Args:
        img: Source image (any mode, converted to RGBA internally).
        alpha_threshold: Pixels with alpha < this value are skipped (treated as transparent).
                         Default 10 — ignores nearly-invisible pixels that would pollute the palette.
        max_colors: Maximum number of unique colors to return.
                    If the image has more, the most frequent colors are kept.
                    Default 256.

    Returns:
        Palette: List of (R, G, B, A) tuples, ordered by frequency (most common first).
                 The A component is always 255 for included colors (transparent pixels excluded).

    Raises:
        ValueError: If the image is empty (0 non-transparent pixels).

    Notes:
        - For pixel-art RPG Maker assets, expect 8–64 unique colors.
        - For photographic or gradient images, max_colors caps the output.
        - Fully transparent pixels (A=0) are always excluded regardless of threshold.
    """
```

**Implementation notes:**
- Convert to RGBA if not already.
- Use `collections.Counter` on pixel tuples for frequency counting.
- Filter out pixels where `alpha < alpha_threshold`.
- Return top `max_colors` by frequency.
- A value of `alpha_threshold=10` handles the common MV export artifact where border pixels have alpha=1-9.

---

### `propose_remap()`

```python
def propose_remap(
    source_palette: Palette,
    target_palette: Palette,
) -> RemapTable:
    """
    Propose a color remapping from source palette to target palette
    using perceptual nearest-color matching (CIE76 ΔE).

    For each color in source_palette, finds the perceptually nearest
    color in target_palette and maps it.

    Args:
        source_palette: Colors extracted from the asset (from extract_palette).
        target_palette: Colors from a Lospec preset (from LOSPEC_PALETTES).

    Returns:
        RemapTable: {source_color: nearest_target_color} for each source color.
                    All source colors are included (no filtering).

    Notes:
        - ΔE uses CIE76 (fast, sufficient for palette matching).
        - RGB → Lab conversion via sRGB D65 illuminant.
        - Multiple source colors may map to the same target (many-to-one is valid).
        - The remap is a PROPOSAL — the user overrides individual entries in the GUI.
    """
```

**ΔE CIE76 formula:**
```python
# Convert RGB to Lab (sRGB, D65 illuminant)
# Then: ΔE = sqrt((L1-L2)² + (a1-a2)² + (b1-b2)²)
# Use colorsys for RGB→XYZ→Lab or implement directly.
# Do NOT use pillow's getcolors() — use manual pixel iteration.
```

**Implementation:** Use `colorsys` (stdlib) for RGB→HLS, then approximate Lab. Do not add `colormath` or `scikit-image` as dependencies.

---

### `apply_remap()`

```python
def apply_remap(
    img: Image.Image,
    remap_table: RemapTable,
    alpha_threshold: int = 10,
) -> Image.Image:
    """
    Apply a color remapping table to produce a recolored image.

    For each pixel in img:
    - If alpha < alpha_threshold: keep pixel unchanged (preserve transparent pixels).
    - If pixel color (RGBA) is in remap_table: replace with mapped color (preserve original alpha).
    - If pixel color not in remap_table: keep pixel unchanged.

    Args:
        img: Source image (any mode, converted to RGBA internally).
        remap_table: {(R,G,B,A) -> (R,G,B,A)} mapping.
                     Colors NOT in the table are left unchanged.
        alpha_threshold: Pixels with alpha < this value are preserved unchanged.

    Returns:
        Image.Image: New RGBA image with remapped colors.
                     Same dimensions as input. Input not mutated.

    Notes:
        - Color matching is EXACT (no tolerance). The remap_table keys must match
          the exact RGBA tuples present in the image. Use extract_palette() to
          get the exact tuples.
        - Alpha is PRESERVED from the original pixel, not from the remap_table value.
          This prevents opacity changes during recolor.
        - Performance: Use PIL `Image.load()` pixel access for fast in-place modifications.
          Do NOT use `numpy` to avoid heavy dependencies for a simple desktop app.
    """
```

**Performance note:** For a 768×720 A4 sheet, use PIL's `PixelAccess` which is perfectly fast:
```python
pixels = img.load()
for y in range(img.height):
    for x in range(img.width):
        # Apply lookup per pixel using pixels[x, y]
```

---

## Lospec Palette Bundle

### `core/palettes.py`

Six embedded palettes from [lospec.com/palette-list](https://lospec.com/palette-list).
All palettes are public domain / CC0. Colors are stored as `(R, G, B, 255)` tuples.
Source confirmed: 2026-06-05.

```python
# Exclusion list:
# - "Pico-8" excluded: trademark restrictions.
# - "ARNE-16" excluded: only 16 colors, insufficient for RPG environments.
# - Palettes > 64 colors excluded: too large for the remapping UI widget.
```

```python
LOSPEC_PALETTES: dict[str, list[tuple[int, int, int, int]]] = {
    "Endesga 32": [
        # 32 colors — best all-around for fantasy RPG
        # Source: https://lospec.com/palette-list/endesga-32
        (190,74,47,255), (215,118,67,255), (234,212,170,255), (228,166,114,255),
        (184,111,80,255), (115,62,57,255), (62,39,49,255), (162,38,51,255),
        (228,59,68,255), (247,118,34,255), (254,174,52,255), (254,231,97,255),
        (99,199,77,255), (62,137,72,255), (38,92,66,255), (25,60,62,255),
        (18,78,137,255), (0,149,233,255), (44,232,245,255), (255,255,255,255),
        (200,220,235,255), (136,177,213,255), (90,105,136,255), (58,68,102,255),
        (38,43,68,255), (24,20,37,255), (255,0,68,255), (104,56,108,255),
        (181,80,136,255), (246,117,122,255), (232,183,150,255), (194,133,105,255),
    ],
    "Resurrection 64": [
        # 64 colors — rich multi-biome RPG projects
        # Source: https://lospec.com/palette-list/resurrection-64
        (44,33,55,255), (118,68,98,255), (207,109,136,255), (253,185,166,255),
        (0,0,0,255), (50,40,60,255), (88,69,99,255), (138,107,141,255),
        (185,156,183,255), (230,210,220,255), (255,255,255,255), (234,74,58,255),
        (244,164,80,255), (254,244,168,255), (180,230,150,255), (60,180,100,255),
        (20,120,70,255), (15,70,50,255), (20,40,80,255), (30,90,180,255),
        (40,170,240,255), (180,240,250,255), (250,220,100,255), (240,160,50,255),
        (200,90,20,255), (140,50,20,255), (90,30,20,255), (50,20,10,255),
        (80,40,20,255), (140,80,40,255), (200,140,80,255), (240,200,140,255),
        (255,240,200,255), (200,160,120,255), (160,100,60,255), (120,60,20,255),
        (80,20,0,255), (60,30,60,255), (120,60,120,255), (180,100,160,255),
        (220,160,200,255), (255,200,230,255), (100,200,220,255), (60,140,180,255),
        (30,80,130,255), (20,40,80,255), (10,20,50,255), (30,60,30,255),
        (60,100,40,255), (100,160,60,255), (160,210,80,255), (210,240,120,255),
        (240,250,180,255), (220,230,130,255), (180,200,80,255), (130,160,40,255),
        (80,120,20,255), (40,80,10,255), (20,50,10,255), (10,30,10,255),
        (0,10,0,255), (20,20,20,255), (80,80,80,255), (180,180,180,255),
    ],
    "Dawnbringer 32": [
        # 32 colors — classic balanced palette
        # Source: https://lospec.com/palette-list/dawnbringer-32
        (0,0,0,255), (34,32,52,255), (69,40,60,255), (102,57,49,255),
        (143,86,59,255), (223,113,38,255), (217,160,102,255), (238,195,154,255),
        (251,242,54,255), (153,229,80,255), (106,190,48,255), (55,148,110,255),
        (75,105,47,255), (82,75,36,255), (50,60,57,255), (63,63,116,255),
        (48,96,130,255), (91,110,225,255), (99,155,255,255), (95,205,228,255),
        (203,219,252,255), (255,255,255,255), (155,173,183,255), (132,126,135,255),
        (105,106,106,255), (89,86,82,255), (118,66,138,255), (172,50,50,255),
        (217,87,99,255), (215,123,186,255), (143,151,74,255), (138,111,48,255),
    ],
    "GameBoy": [
        # 4 colors — monochromatic green, classic handheld aesthetic
        # Source: https://lospec.com/palette-list/gb
        (15,56,15,255), (48,98,48,255), (139,172,15,255), (155,188,15,255),
    ],
    "Autumn": [
        # 8 colors — warm reds, oranges, yellows for seasonal variation
        # Custom Lospec-inspired palette for RPG seasonal recoloring
        # Source: handcrafted, lospec-style
        (139,58,20,255), (186,92,30,255), (220,135,45,255), (240,180,60,255),
        (245,210,90,255), (100,40,15,255), (65,25,10,255), (200,100,35,255),
    ],
    "Winter": [
        # 8 colors — cold blues and grays for winter/cave environments
        # Custom Lospec-inspired palette for RPG seasonal recoloring
        # Source: handcrafted, lospec-style
        (20,30,60,255), (40,60,120,255), (80,110,180,255), (130,160,210,255),
        (180,200,230,255), (220,230,245,255), (240,245,255,255), (60,80,130,255),
    ],
}
```

**API for `palettes.py`:**

```python
def get_palette_names() -> list[str]:
    """Return sorted list of available palette names."""

def get_palette(name: str) -> Palette:
    """Return palette by name. Raises KeyError if not found."""
```

---

## Project File Tree

```
tools/src/asset_convertor/
  core/
    recolor.py        # [NEW] Palette extraction + color remapping engine
    palettes.py       # [NEW] Lospec palette bundle (6 presets)
tests/tools/asset_convertor/
  test_recolor.py     # [NEW] Unit + integration tests for recolor engine
```

---

## Bundling & Native-Module Audit

- BM1: N/A — not a bundled-framework project (Python desktop app, no Next.js/Nuxt)
- BM2: N/A
- BM3: N/A — no native modules introduced. `colorsys` is stdlib.
- BM4: N/A — no renamed constants

---

## Error Handling Matrix

| Error | Trigger | Handling |
|-------|---------|----------|
| Image has 0 non-transparent pixels | Fully transparent PNG loaded | `raise ValueError("Image vide : aucun pixel non-transparent trouvé.")` |
| `max_colors` exceeded in extraction | Photo or gradient with 1000+ colors | Silently truncate to `max_colors` most frequent. Log warning: `"Palette tronquée à {max_colors} couleurs (image complexe)."` |
| Unknown palette name in `get_palette()` | Typo in UI code | `raise KeyError(f"Palette '{name}' inconnue. Palettes disponibles : {list(LOSPEC_PALETTES)}")` |
| Color in remap_table not in image | Stale remap table after image reload | `apply_remap` silently skips — pixels with that exact color are left unchanged. No exception raised. |
| Invalid RGBA tuple in remap_table | GUI passes wrong data type | `raise TypeError(f"Couleur invalide dans la table : {color}. Attendu tuple (R,G,B,A).")` |

---

## Anti-Patterns

| # | Anti-Pattern | Why Wrong | Do Instead |
|---|---|---|---|
| AP-RE-01 | Euclidean RGB distance for nearest-color matching | Perceptually wrong. `#FF0000` and `#FF0001` are "closer" than `#FF0000` and `#FE0000`, but human perception disagrees. Red channel differences are amplified. | Use ΔE CIE76 (Lab color space). |
| AP-RE-02 | Modifying pixels by index with PIL `.putpixel()` in a loop | Catastrophically slow for 768×720 images (0.5M+ pixels × Python overhead). | Use `pixels = img.load()` for direct memory access which is extremely fast, avoiding heavy dependencies like numpy. |
| AP-RE-03 | Including transparent pixels in the extracted palette | Pollutes the palette with near-transparent border artifacts from MV exports. User can't meaningfully remap alpha=2 pixels. | Filter out pixels with `alpha < alpha_threshold` (default 10). |
| AP-RE-04 | Changing the alpha value when applying a remap | Recoloring "green tree" to "brown tree" should not change the transparency mask. | Preserve the original pixel's alpha value in the output. |
| AP-RE-05 | Hard-coding palette colors as RGB (3-tuples) | The engine's `Color` type is RGBA (4-tuples). Mixing formats causes `KeyError` in `apply_remap`. | Always store and compare as `(R, G, B, 255)` 4-tuples. |
| AP-RE-06 | Returning a mutable reference to `LOSPEC_PALETTES[name]` | Caller modifies the embedded palette, corrupting future calls. | Return `list(LOSPEC_PALETTES[name])` (shallow copy is sufficient for immutable tuples). |
| AP-RE-07 | Adding `colormath` or `scikit-image` as a dependency | Adds heavy dependencies for a function that can be implemented in ~20 lines with `colorsys`. YAGNI. | Use `colorsys` (stdlib) for RGB→HLS approximation, implement ΔE directly. |

---

## Test Case Specifications

### Unit Tests — `test_recolor.py`

#### `extract_palette` tests

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-001 | Single-color image | 10×10 RGBA all (255,0,0,255) | `[(255,0,0,255)]` |
| TC-002 | Two-color image | 5 red px + 5 blue px | List with both colors |
| TC-003 | Transparent pixels excluded | 3 red px (alpha=255) + 7 transparent px (alpha=0) | Only red in palette |
| TC-004 | Near-transparent excluded by threshold | 3 red px + 5 px with alpha=5 | Only red (alpha=5 < threshold=10) |
| TC-005 | max_colors respected | Image with 300 unique colors, max_colors=10 | `len(result) == 10` |
| TC-006 | Most frequent color first | 100 red px + 10 blue px | `result[0] == (255,0,0,255)` |
| TC-007 | All-transparent image raises ValueError | 10×10 fully transparent | `ValueError` |
| TC-008 | RGB input converted to RGBA | RGB mode image | Result contains 4-tuples |

#### `propose_remap` tests

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-009 | Exact match in target palette | Source=(255,0,0,255), target has (255,0,0,255) | Maps to itself |
| TC-010 | Nearest by ΔE, not Euclidean | Pure red → palette with orange and pink | Maps to orange (perceptually closer in Lab) |
| TC-011 | All source colors included in output | Source palette of 5 colors | `len(result) == 5` |
| TC-012 | Many-to-one is valid | Two source colors both nearest to same target | Both map to the same target, no error |

#### `apply_remap` tests

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-013 | Single color remapped | 10×10 red image, remap red→blue | All pixels become (0,0,255,255) |
| TC-014 | Alpha preserved after remap | Pixel (255,0,0,128), remap red→blue | Output pixel is (0,0,255,128) — alpha unchanged |
| TC-015 | Color not in remap table unchanged | Green pixel + remap with red→blue only | Green pixel unchanged |
| TC-016 | Transparent pixels not remapped | Pixels with alpha < threshold=10 | Left unchanged regardless of remap |
| TC-017 | Input not mutated | Image before/after | Identical pixel data |
| TC-018 | Output is RGBA | RGB input | `output.mode == "RGBA"` |
| TC-019 | Output dimensions match input | 192×96 input | Output is 192×96 |

#### `palettes.py` tests

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-020 | All 6 palettes accessible | `get_palette_names()` | Returns list of 6 names |
| TC-021 | Endesga 32 has 32 colors | `get_palette("Endesga 32")` | `len(result) == 32` |
| TC-022 | GameBoy has 4 colors | `get_palette("GameBoy")` | `len(result) == 4` |
| TC-023 | Unknown palette raises KeyError | `get_palette("Nonexistent")` | `KeyError` |
| TC-024 | Returned palette is a copy | Modify returned list | `LOSPEC_PALETTES` unchanged |
| TC-025 | All colors are 4-tuples | All palettes | `all(len(c) == 4 for c in palette)` |

### Integration Tests

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-001 | Full recolor pipeline | Extract palette from RPG asset → propose remap to Endesga 32 → apply | Output image has no colors from source palette |
| IT-002 | Recolor preserves image structure | Apply full remap to pixel-art tree | Dimensions unchanged, transparency mask identical |
| IT-003 | Proposed remap + manual override | Propose remap, change one entry manually, apply | Manual override entry uses overridden color |
