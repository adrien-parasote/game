> Document type: Implementation

# Phase 1: Procedural Kitbashing Tiles Generator Spec

**Covers:** F1, F2, F3, F4 (from [STRATEGIC_BLUEPRINT.md](./STRATEGIC_BLUEPRINT.md#6-feature-matrix--dependency-ordering))

> ℹ️ **Correction Log (2026-06-04 — Architecture Pivot to Kitbashing):**
> - Replaced Perlin/Cellular noise with **Procedural Kitbashing (Stamp Scattering)**.
> - Grass, Dirt, Stone etc. are no longer mathematical formulas, but are assembled from predefined 2D binary matrix clusters (Slynyrd's Key Clusters methodology).
> - No external PNG assets or `PIL.ImageDraw` vector shapes are required. The tool stamps these pixel-perfect clusters directly onto the grid.
> - Scale slider renamed to **Density**.
> - Generation happens directly at **32x32** natively (true pixel art). No downscaling required.
> - Seamlessness is guaranteed by 2D modulo wrapping during the stamping process.
> - Color quantization is mapped to 4 logical tones: Background (0), Shadow (1), Midtone (2), Highlight (3) matching the TofuPixel drawing tutorial method.

## Overview
A local Python desktop application that generates seamless pixel art tiles by intelligently scattering small user-provided "stamps" (Kitbashing). It maps the grayscale values of the stamps to a strict hex color palette, guarantees seamless tiling via mathematical wrapping, and exports a Tiled-compatible `.tsx` + `.png` file pair. **Fully offline. No API. No GPU. No internet required.**

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Wrap stamp drawing coordinates using modulo `% 32` to guarantee seamless tiling. Use `Image.NEAREST` for all UI resizing. Export `.tsx` with paths relative to the `.png`. Create "output/" with `os.makedirs('output', exist_ok=True)` before writing files. |
| **Ask first** | Adding a new external Python dependency to `requirements.txt`. Changing the GUI framework. |
| **Never do** | Make any HTTP request or external API call. Use `asyncio` with `CustomTkinter`. Use bilinear or Lanczos resize. Hardcode palette colors in Python source. |

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|---|---|---|---|
| 1 | Predefined 2D binary matrices (Key Clusters) are sufficient to simulate pixel art textures. | Medium | SHOW | Verified: A test script stamping Slynyrd's matrix clusters generates perfect pixel-art grass. |
| 2 | Modulo wrapping during pixel writing accurately simulates seamless toroidal wrapping. | Low | SHOW | Verified: `(x + dx) % 32` effectively loops the drawing from the right edge back to the left without intermediate logic. |
| 3 | Users want palettes applied logically (Dark = Background, Light = Highlight). | Low | SHOW | Verified: Based on the TofuPixel tutorial provided, this exact mapping creates the 3-tone grass style perfectly. |

## 1. System Architecture

- **GUI Layer** (`app.py` — `CustomTkinter` root window):
  - Dropdown: **Type de Texture** (Stone, Grass, Dirt, Wood — hardcoded available generators)
  - Dropdown: **Sous-type** (Classic, Short, Curly, Wild) — only active when 'Grass' is selected.
  - Dropdown: **Palette** (loaded from `tools/src/asset_creator/config/palettes.json`).
  - Setup: Injects the application icon using `AppKit` when running on macOS.
  - Slider + number input: **Graine** (integer 0–9999). Modifying triggers debounced preview.
  - Slider: **Densité** (number of stamps to scatter, 1–100, default 20). Replaces the old 'Scale' slider. Modifying triggers debounced preview.
  - Button: **"Exporter vers Tiled"** — saves the currently previewed tile to the "output/" folder.
  - Live Preview mechanism: Any change triggers a background generation thread (debounced 300ms).
  - Main Preview panel ("gros plan"): displays the 32×32 tile scaled to 256×256 using `image.resize((256, 256), Image.NEAREST)`.
  - 3x3 Grid Preview panel: displays a 96x96 image (32x32 tiled 3x3) to verify seamlessness.

- **Generation Layer** (`tools/src/asset_creator/core/generator.py`):
  - Input: `texture_type: str`, `seed: int`, `density: int`, `sub_type: str = "classic"`
  - Initialize a `32x32` numpy array filled with `1` (Index 1 = Background/Shadow tone).
  - Dynamically generate procedural pixel art in memory based on the texture type, using predefined 2D binary matrix clusters (Slynyrd's Key Clusters method).
  - For example, "Grass" generation uses 2 additional layers over the background, and its specific Key Clusters change based on the `sub_type` parameter ("classic", "short", "curly", "wild"):
    - **Layer 2 (Tufts/Midtones):** Stamp `density * 2` random midtone clusters (Tone 2) chosen from a predefined set of binary matrices.
    - **Layer 3 (Highlights):** Stamp `density * 0.8` random highlight clusters (Tone 3) chosen from a predefined set of highlight matrices.
  - Apply 2D modulo wrapping `((x + dx) % 32, (y + dy) % 32)` for every pixel stamped to guarantee seamless toroidal tiling.
  - Output: `numpy.ndarray` of shape `(32, 32)`, values strictly in `[0, 1, 2, 3]`.

- **Quantization Layer** (`tools/src/asset_creator/core/quantizer.py`):
  - Input: `numpy.ndarray (32, 32)` of indices, `palette: list[tuple[int,int,int]]`
  - Sort palette by perceived luminance (`0.299*R + 0.587*G + 0.114*B`) from darkest to lightest.
  - Map the 4 logical tones (0, 1, 2, 3) to the available palette colors. If palette has `L` colors:
    - Tone `0` -> `palette[0]`
    - Tone `1` -> `palette[max(1, (L-1)//3)]`
    - Tone `2` -> `palette[max(1, 2*(L-1)//3)]`
    - Tone `3` -> `palette[L-1]`
  - Create a `PIL.Image` of 32x32 RGB pixels.
  - Output: `PIL.Image` (32×32, RGB).

- **Export Layer** (`tools/src/asset_creator/exporters/exporter.py`):
  - Derives `tile_name` from texture type + seed: `f"{texture_type}_{seed}"`.
  - Creates "output/": `os.makedirs('output', exist_ok=True)`
  - Saves PNG: `image.save(f"output/{tile_name}.png")`
  - Generates and writes TSX: `f"output/{tile_name}.tsx"` (see template in TC-004)
  - Returns `(png_path, tsx_path)`.

## 2. Anti-Patterns

| Anti-Pattern | Violation | Correct Behavior |
|---|---|---|
| Non-wrapping stamp drawing | If a stamp goes past `x=31`, cutting it off breaks seamlessness. | Use `(x + dx) % 32` and `(y + dy) % 32` when applying stamp pixels to the canvas. |
| Using Antialiasing on Resize | Lanczos/bilinear downscaling introduces new intermediate colors. | Use `Image.NEAREST` — the only acceptable resize filter for pixel art. |
| Unsorted palette | Assigning Tone 3 (Highlight) to the 4th array element without sorting. | Sort palette by luminance at load time before mapping. |
| Absolute Tiled Paths | "C:/Users/.../tile.png" in .tsx. | Filename only: `<image source="stone_42.png"/>` |
| Using asyncio with CustomTkinter | `asyncio.run()` blocks the CTk event loop. | Query widget states synchronously on the main thread and pass them to a standard `threading.Thread`. |

## 3. Test Case Specifications

| TC ID | Type | Description | Expected Result |
|---|---|---|---|
| `TC-001` | Unit | Toroidal seamlessness — stamp wrapping. | Drawing a 4x4 stamp at `x=30, y=30` correctly sets values at `x=30,31,0,1` and `y=30,31,0,1` via modulo math. |
| `TC-002` | Unit | Generator output format and sub_type. | `generator.generate_texture("grass", seed=42, density=10, sub_type="wild")` returns a `(32, 32)` numpy array containing only values `0, 1, 2, 3, 4`. *(Updated 2026-06-04: range extended to 0–4 after 5-tone grass upgrade — see `grass_rendering_spec.md`)* |
| `TC-003` | Unit | Color quantization strictness. | The output image only contains colors present in the provided sorted palette. |
| `TC-004` | Unit | `.tsx` XML generation structure. | Given `tile_name="stone_42"`, the generated XML parses successfully as valid XML with correct `tilewidth="32"`. |
| `TC-005` | Unit | Generator output fallback. | If an unknown `texture_type` is provided, `generate` handles it gracefully (e.g. renders programmatic default squares or returns all zeros) instead of crashing. |
| `TC-006` | Unit | Palette loader. | `tools/src/asset_creator/config/palettes.json` is successfully parsed from hex strings to RGB tuples. |
| `TC-007` | Unit | Determinism — same seed = same output. | `generate("grass", seed=42, density=10)` called twice returns identical ndarrays. |
| `IT-001` | Integration | GUI → Live Preview flow. | Changing the density slider triggers the debounced thread and updates `lbl_preview`. |
| `IT-002` | Integration | End-to-end pipeline (Preview + Export). | GUI Layer triggers Generation Layer, which passes output to Quantization Layer generating `img_32`. Clicking "Export" triggers Export Layer which writes valid PNG and TSX to `output/`. |
| `IT-003` | Integration | 3x3 Grid Preview Generation | Upon successful generation, GUI creates a 96x96 image repeating the 32x32 output 3x3 times perfectly. |

## 4. Error Handling Matrix

| Error Condition | Handled In | User-Visible Message | Action |
|---|---|---|---|
| Write permission denied | Export Layer | "Cannot save files: permission denied in output/." | Catch `PermissionError` |
| Unknown texture type | Generation Layer | *(transparent)* | Generate programmatic placeholder blocks |
| `tools/src/asset_creator/config/palettes.json` missing | GUI Layer | "Could not load palettes.json. Using built-in defaults." | Fall back to bundled palette dict |
| Generation thread crash | Generation Layer | "Generation failed. See console for details." | Catch `Exception` in thread, log to stderr, update GUI status |

## 5. Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema | Consumers |
|---|---|---|---|
| `output/{tile_name}.tsx` | XML | See TC-004 | Tiled Editor |
| `output/{tile_name}.png` | PNG, 32×32, RGB | Pillow-saved PNG | Tiled Editor |

### Consumes
| Path / Identifier | Format | Schema | Producer |
|---|---|---|---|
| `None` (procedural) | Memory | Predefined binary matrices (Key Clusters). | Generator |
| `tools/src/asset_creator/config/palettes.json` | JSON | `{"Name": ["#RRGGBB", ...]}` | Bundled |

### Public Interface
| Type | Identifier | Signature | Documented at |
|---|---|---|---|
| Module | `generator.generate_texture` | `(texture_type: str, seed: int, density: int, sub_type: str) -> np.ndarray` | This spec §1 |
| Module | `quantizer.quantize_image` | `(index_map: np.ndarray, palette: list[tuple[int,int,int]]) -> PIL.Image` | This spec §1 |
| Module | `exporter.export` | `(image: PIL.Image, tile_name: str) -> tuple[str, str]` | This spec §1 |
