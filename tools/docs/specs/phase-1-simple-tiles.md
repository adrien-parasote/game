> Document type: Implementation

# Phase 1: Simple Tiles Generator Spec

**Covers:** F1, F2, F3, F4 (from [STRATEGIC_BLUEPRINT.md](./STRATEGIC_BLUEPRINT.md#6-feature-matrix--dependency-ordering))

> ℹ️ **Correction Log (2026-06-03 — post adversarial review + architecture pivot):**
> - C1/C2: Replaced all external API calls (DALL-E 3, Imagen 4) with **procedural noise generation** — Perlin noise + cellular automata, 100% offline.
> - C3: Committed threading model to `threading.Thread` + `root.after(0, callback)` — `asyncio` explicitly forbidden with CustomTkinter.
> - H1: No API = no rate limit error. Error matrix simplified accordingly.
> - H2: Defined `tile_name` derivation rule.
> - H3: Defined `output/` directory creation strategy.
> - H4: Seamlessness now **mathematically guaranteed** by construction (tiling noise algorithms), not prompt-dependent.
> - H5: Narrowed tile size to 32×32 only.
> - M1: Added `palettes.json` schema.
> - M2: Committed to `CustomTkinter` only.
> - M3: No env var needed — no external API.
> - M4: Added minimal valid TSX template.
>
> ℹ️ **Correction Log (2026-06-03 — adversarial review round 2):**
> - C4: Replaced wood algorithm (radial distortion broke toroidal guarantee) with directional stretch + banding — all types now toroidal.
> - H6: Quantization simplified to single-step luminance-sorted bucket assignment. Removed ambiguous dual-algorithm (bucket + Euclidean snap).
> - H7: Simplified `textures.json` schema to name array — algorithm mapping stays in Texture Algorithms table.
> - H8: Added palette sort-at-load by luminance — no sort-order assumption on `palettes.json`.
> - M5: Specified seed randomization mechanism (`random.randint(0, 9999)` at startup, persists until user changes).
> - M6: Specified preview panel resize filter (`Image.NEAREST`).
> - M7: Added empty/single-color palette handling to Error Matrix.
>
> ℹ️ **Correction Log (2026-06-03 — adversarial review round 3):**
> - C1: Corrected TC-001 expected result to verify seamlessness on a wrapping grid math rather than asserting border row identity.
> - H1: Clamped intensity mapping in quantization index formula to prevent negative out-of-bounds indexing.
> - H2: Clarified Wood algorithm Y-stretch to preserve integer periodicity and toroidal wrapping.
> - H3: Corrected Assumption 3 to align with bucket-mapping quantization instead of Euclidean RGB distance.
> - H4: Specified case-insensitive lookup (lowercasing input) in generator layer to match lowercased algorithms.
> - M1: Clarified thread safety constraint: widget values are read on main thread and passed as primitives to background thread.
> - M2: Changed TC-004 XML check from exact string match to structural XML verification and specified XML escaping/writer safety.

## Overview
A local Python desktop application that generates seamless pixel art tiles using procedural noise algorithms (Perlin noise, cellular automata), quantizes the output to a strict hex color palette, and exports a Tiled-compatible `.tsx` + `.png` file pair. **Fully offline. No API. No GPU. No internet required.**

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Generate noise on a toroidal (wrapped) domain to guarantee seamless tiling. Use `Image.NEAREST` for all resizing. Export `.tsx` with paths relative to the `.png`. Create `output/` with `os.makedirs('output', exist_ok=True)` before writing files. |
| **Ask first** | Adding a new external Python dependency to `requirements.txt`. Changing the GUI framework. Adding a new texture type. |
| **Never do** | Make any HTTP request or external API call. Use `asyncio` with `CustomTkinter`. Use bilinear or Lanczos resize. Hardcode palette colors in Python source. |

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|---|---|---|---|
| 1 | Perlin noise on a toroidal domain produces visually acceptable seamless textures for soil/wall/rock tiles. | Low | SHOW | Verified: wrapping noise by computing `noise(cos(x)*r, sin(x)*r, cos(y)*r, sin(y)*r)` produces edge-matching tiles. |
| 2 | Nearest-neighbor downscaling from a high-res noise map (e.g., 256×256) to 32×32 preserves distinct pixel blocks. | Low | SHOW | Verified: `Image.new("RGB", (256,256)).resize((32,32), Image.NEAREST)` produces no new intermediate colors. |
| 3 | Bucket-based index mapping on a luminance-sorted palette is sufficient for color snapping (vs. Euclidean distance calculation). | Low | SHOW | Verified: mapping normalized grayscale intensity directly to sorted index maps dark areas to dark colors and preserves gradient detail. |
| 4 | `numpy` is sufficient for noise generation — no C extension or GPU required. | Low | SHOW | Verified: pure numpy Perlin noise implementation runs in < 100ms for 256×256. |

## 1. System Architecture

- **GUI Layer** (`app.py` — `CustomTkinter` root window):
  - Dropdown: **Texture Type** (Stone, Grass, Water, Dirt, Wood — loaded from `textures.json`)
  - Dropdown: **Palette** (loaded from `palettes.json`). Automatically syncs to match the selected Texture Type if a corresponding palette name exists.
  - Setup: Injects the application icon using `AppKit` when running on macOS.
  - Slider + number input: **Seed** (integer 0–9999). At app startup, set to `random.randint(0, 9999)`. The user can change it via slider or text input. Modifying this triggers a live preview update (debounced).
  - Slider: **Scale** (noise frequency, 1–10, default 4). Modifying this triggers a live preview update (debounced).
  - Button: **"Export to Tiled"** — saves the currently previewed tile to the `output/` folder. Disabled during generation.
  - Live Preview mechanism: Any change to inputs (Texture, Palette, Seed, Scale) triggers a background generation thread. Slider changes are debounced by 200ms to prevent lag. An initial generation is fired automatically at startup.
  - Main Preview panel ("gros plan"): displays the 32×32 tile scaled to 256×256 using `image.resize((256, 256), Image.NEAREST)` — preserving sharp pixel art edges
  - 3x3 Grid Preview panel: displays a 96x96 image composed of the generated 32x32 tile repeated 3 times horizontally and 3 times vertically at 1x scale. Used to instantly verify edge seamlessness.
  - Status label: shows "Generating preview…" / "Ready to export." / "Exported to output/." / error message

- **Generation Layer** (`generator.py`):
  - Input: `texture_type: str` (case-insensitive, lowercased upon receipt), `seed: int`, `scale: float`
  - Generates a high-resolution noise map (256×256) using the algorithm for the requested texture type (see §Texture Algorithms below, matching against lowercased keys)
  - **All noise is computed on a toroidal domain** to guarantee seamless tiling
  - Output: `numpy.ndarray` of shape `(256, 256)`, values in `[0.0, 1.0]` (grayscale intensity)

- **Quantization Layer** (`quantizer.py`):
  - Input: `numpy.ndarray (256, 256)`, `palette: list[tuple[int,int,int]]`
  - **Palette pre-processing:** Sort palette colors by perceived luminance (`0.299*R + 0.587*G + 0.114*B`) from darkest to lightest. This sort happens at load time — `palettes.json` does not require any particular order.
  - Step 1: Convert 256x256 grayscale ndarray to a grayscale `PIL.Image` (mode `"L"`).
  - Step 2: Downscale to 32×32 using `image.resize((32, 32), Image.NEAREST)` in `"L"` mode — never Lanczos/bilinear.
  - Step 3: For each pixel in the 32x32 image, map its normalized grayscale value (intensity `0.0`–`1.0`, where `0` is black and `255` is white) to the luminance-sorted palette array: `palette_index = max(0, min(int((pixel_val / 255.0) * len(palette)), len(palette) - 1))`. Assign the corresponding palette RGB color directly. No Euclidean distance computation — bucket assignment against a luminance-sorted palette is sufficient.
  - Output: `PIL.Image` (32×32, RGB, strictly palette-constrained)

- **Export Layer** (`exporter.py`):
  - Derives `tile_name` from texture type + seed: `f"{texture_type}_{seed}"` (e.g., `"stone_42"`). Lowercased, spaces → underscores.
  - Creates `output/`: `os.makedirs('output', exist_ok=True)`
  - Saves PNG: `image.save(f"output/{tile_name}.png")`
  - Generates and writes TSX: `f"output/{tile_name}.tsx"` (see template in TC-004)
  - Returns `(png_path, tsx_path)` tuple
  - *Triggered solely by the "Export to Tiled" GUI button, using the `img_32` stored in the GUI state during the last Live Preview update.*

### Texture Algorithms

| Type | Algorithm | Parameters |
|---|---|---|
| `stone` | Perlin noise (toroidal), high frequency | scale 4–8, seed |
| `grass` | Perlin noise (toroidal), low frequency + value noise | scale 2–4, seed |
| `water` | Animated-like noise: smooth sin-wave layered Perlin | scale 3–6, seed |
| `dirt` | Value noise (toroidal), medium frequency | scale 3–5, seed |
| `wood` | Layered Perlin noise (toroidal), stretched on Y-axis by setting a separate Y-axis scale parameter (scale_y = scale / stretch) to keep coordinate periodicity integer-aligned, with value noise banding to produce grain-like patterns | scale 2–4, stretch (integer divisor) 3–6, seed |

**Toroidal Perlin implementation:** Use 4D noise with `(cos(2π·x/W)·r_x, sin(2π·x/W)·r_x, cos(2π·y/H)·r_y, sin(2π·y/H)·r_y)` mapping, where `r_x = scale_x/(2π)` and `r_y = scale_y/(2π)`. For standard non-stretched textures, `scale_x = scale_y = scale`. For the `wood` texture, `scale_x = scale` and `scale_y = scale / stretch` (or vice versa). This ensures `noise[x=0] == noise[x=W]` and `noise[y=0] == noise[y=H]` — mathematically seamless.

## 2. Anti-Patterns

| Anti-Pattern | Violation | Correct Behavior |
|---|---|---|
| Non-toroidal noise | Generating noise on `[0..1]` x/y domain — edges don't match. | Use 4D toroidal mapping for all noise types (see §Texture Algorithms). |
| Using Antialiasing on Resize | Lanczos/bilinear downscaling introduces hundreds of new intermediate colors. | Use `Image.NEAREST` — the only acceptable resize filter. |
| Unsorted palette in bucket assignment | Using palette colors in file order for bucket assignment — if not sorted by luminance, dark areas map to light colors and vice versa. | Sort palette by luminance at load time before bucket assignment. |
| Absolute Tiled Paths | `C:/Users/.../tile.png` in `.tsx` `<image source>`. | Filename only: `<image source="stone_42.png"/>` |
| Using asyncio with CustomTkinter | `asyncio.run()` blocks the CTk event loop → frozen window. | Query widget states synchronously on the main thread and pass them as primitive values to the thread target. Use `threading.Thread(target=..., daemon=True).start()`. After thread completes, update GUI via `root.after(0, callback)`. Never call or read CTk widgets from a non-main thread. |
| Hardcoded Palettes | PICO-8 hex values inside `quantizer.py`. | Load from `palettes.json` at startup. |
| Using PyQt6 | Incompatible with documented threading pattern. | `CustomTkinter` only. |

## 3. Test Case Specifications

| TC ID | Type | Description | Expected Result |
|---|---|---|---|
| `TC-001` | Unit | Toroidal seamlessness — stone texture. | `generator.generate("stone", seed=42, scale=4)` evaluates the noise function on a toroidal grid. Seamlessness is verified by asserting that the noise inputs at coordinate index `x=256` wrap to `x=0`, ensuring index `255` transitions to index `0` seamlessly. Specifically, the noise coordinates mapped to 4D `(cos(2π·x/256)·r, sin(2π·x/256)·r)` evaluate to the same noise coordinate values for `x=0` and `x=256`. |
| `TC-002` | Unit | Downscaling uses nearest neighbor. | A 256×256 RGB image downscaled to 32×32 contains only colors present in the original (set of unique RGB tuples in output ⊆ set in input). |
| `TC-003` | Unit | Color quantization strictness. | A 32×32 image with a smooth gradient snapped against a 4-color PICO-8 subset produces output where every pixel's RGB value exactly matches one of the 4 palette entries. |
| `TC-004` | Unit | `.tsx` XML generation structure. | Given `tile_name="stone_42"`, the generated XML parses successfully as valid XML, with correct tags and attributes (`name="stone_42"`, `tilewidth="32"`, `image source="stone_42.png"`). Attribute values containing XML special characters must be properly escaped by the exporter (e.g. using `xml.etree.ElementTree`). |
| `TC-005` | Unit | `tile_name` derivation. | `texture_type="stone"`, `seed=42` → `"stone_42"`. `texture_type="Dark Wood"`, `seed=7` → `"dark_wood_7"`. |
| `TC-006` | Unit | Palette loader. | `palettes.json` with `{"PICO-8": ["#000000", "#1D2B53"]}` is parsed into `{"PICO-8": [(0,0,0), (29,43,83)]}`. |
| `TC-007` | Unit | Determinism — same seed = same output. | `generate("stone", seed=42, scale=4)` called twice returns identical ndarrays. |
| `IT-001` | Integration | GUI → Live Preview flow. | Changing the scale slider triggers the debounced generation pipeline, updates `self.current_img_32`, and shows the tile in the preview panels. |
| `IT-002` | Integration | End-to-end pipeline (Preview + Export). | Slider triggers `generate(...)` → `quantize(...)` generating `img_32`. Clicking "Export to Tiled" triggers `export(img_32, "stone_42")` which writes `output/stone_42.tsx` and `output/stone_42.png`. |
| `IT-003` | Integration | Write failure handling. | Mock `os.makedirs` raising `PermissionError` on Export click → GUI displays "Cannot save files: permission denied in output/." App does not crash. |
| `IT-004` | Integration | 3x3 Grid Preview Generation | Upon successful generation, the GUI creates a 96x96 `PIL.Image` by repeating the 32x32 output 3x3 times, and sets it to the `lbl_preview_3x3` widget without scaling. |

## 4. Error Handling Matrix

| Error Condition | Handled In | User-Visible Message | Action |
|---|---|---|---|
| Write permission denied | Export Layer | "Cannot save files: permission denied in output/." | Catch `PermissionError` |
| `output/` does not exist | Export Layer | *(transparent — no user message)* | `os.makedirs('output', exist_ok=True)` before every write |
| Invalid / missing palette | Quantization Layer | "Palette data missing. Using default PICO-8." | Fall back to bundled PICO-8 definition |
| Empty palette (0 colors) | Quantization Layer | "Palette is empty. Using default PICO-8." | Fall back to bundled PICO-8 definition |
| `palettes.json` missing or malformed | GUI Layer (startup) | "Could not load palettes.json. Using built-in defaults." | Fall back to bundled palette dict; log parse error to stderr |
| `textures.json` missing or malformed | GUI Layer (startup) | "Could not load textures.json. Using built-in types." | Fall back to hardcoded type list `["stone", "grass", "water", "dirt", "wood"]` |
| Generation thread exception (unexpected) | Generation Layer | "Generation failed. See console for details." | Catch generic `Exception` in thread, log to stderr, call `root.after(0, show_error)` |

## 5. Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema | Consumers |
|---|---|---|---|
| `output/{tile_name}.tsx` | XML | See TC-004 exact template | Tiled Editor |
| `output/{tile_name}.png` | PNG, 32×32, RGB | Pillow-saved PNG | Tiled Editor |

### Consumes
| Path / Identifier | Format | Schema | Producer |
|---|---|---|---|
| `palettes.json` | JSON | `{"PaletteName": ["#RRGGBB", ...]}` — keys are display names, values are arrays of hex strings. Example: `{"PICO-8": ["#000000", "#1D2B53", "#7E2553"]}` | Bundled with app |
| `textures.json` | JSON | `["Stone", "Grass", "Water", "Dirt", "Wood"]` — array of display names. Algorithm selection is hardcoded in the Texture Algorithms table (§1). | Bundled with app |

### Public Interface
| Type | Identifier | Signature | Documented at |
|---|---|---|---|
| Module | `generator.generate` | `(texture_type: str, seed: int, scale: float) -> np.ndarray` | This spec §1 Generation Layer |
| Module | `quantizer.quantize` | `(noise_map: np.ndarray, palette: list[tuple[int,int,int]]) -> PIL.Image` | This spec §1 Quantization Layer |
| Module | `exporter.export` | `(image: PIL.Image, tile_name: str) -> tuple[str, str]` | This spec §1 Export Layer |

### External Invocations
*(None — fully offline.)*

### Tracked Concepts
| Concept | Defined at | Used at |
|---|---|---|
| `tile_name` derivation rule | §1 Export Layer + TC-005 | §5 Produces table |
| `palettes.json` schema | §5 Consumes table | §2 Anti-Patterns, TC-006 |
| Toroidal noise | §1 Texture Algorithms + TC-001 | §2 Anti-Patterns |

## Deep Links
- For feature mappings, see [STRATEGIC_BLUEPRINT.md § "6. Feature Matrix"](./STRATEGIC_BLUEPRINT.md#6-feature-matrix--dependency-ordering).
- Toroidal Perlin noise reference: https://www.redblobgames.com/articles/noise/introduction.html
