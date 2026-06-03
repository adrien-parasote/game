> Document type: Strategic

# Strategic Blueprint: Pixel Art Asset Generator
Enable a solo developer to generate seamless, tileable background/wall assets (32×32) that strictly adhere to specific pixel art color palettes (e.g., PICO-8, Endesga) and are natively exportable to Tiled — with zero external dependencies, zero internet, zero API key.

> ℹ️ **Architecture decision (2026-06-03):** The generation engine uses **procedural noise algorithms** (Perlin noise, cellular automata) — no AI API, no external model, no GPU. The app is 100% offline and autonomous.

## 2. Success Metrics
- Generate a 32×32 seamless tile in under 2 seconds (local computation only).
- **Mathematically guaranteed seamlessness** — not prompt-dependent.
- 100% adherence to a chosen hex color palette (zero interpolated/soft colors in the output).
- Output must include both the `.png` and a ready-to-use `.tsx` Tiled file format.

## 3. Competitive Advantage
Focuses on **deterministic, reproducible** output with strict color quantization and Tiled workflow integration. The tool guarantees the output is actual usable pixel art — seamless by construction (not by luck), reproducible via seed, directly importable into Tiled.

## 4. Core Architecture Decision
**Local Desktop Application — fully offline.** No internet connection required. No API key. No GPU. No Docker. Pure Python.

## 5. Tech Stack Rationale
**Python (Backend + GUI)**:
- `CustomTkinter` for the GUI — native, standalone desktop window without a browser.
- `numpy` for procedural noise generation (Perlin noise, cellular automata, value noise).
- `Pillow` (PIL) for image output, nearest-neighbor downscaling, and PNG export.
- No networking library required.

## 6. Feature Matrix & Dependency Ordering
| Feature ID | Feature Name | Description | Covered By |
|---|---|---|---|
| F1 | Procedural Generation Engine | Generate a seamless base texture using Perlin noise or cellular automata, parameterized by type, scale, and seed | `phase-1-simple-tiles.md` |
| F2 | Quantization Engine | Downscale output to 32×32 using nearest-neighbor and snap colors to a strict hex palette | `phase-1-simple-tiles.md` |
| F3 | Tiled Export | Generate `.tsx` XML and save `.png` to `output/` folder | `phase-1-simple-tiles.md` |
| F4 | Desktop GUI | Window to select texture type, palette, seed, and trigger generation | `phase-1-simple-tiles.md` |
| F5 | UI 3x3 Grid Preview | Display the generated 32x32 tile in a 3x3 grid at 1x scale (96x96 pixels total) to instantly verify edge seamlessness | `phase-1-simple-tiles.md` |

## 7. What We Are NOT Building (Exclusions)
- No complex autotiling (15-tile or 47-tile rulesets).
- No animated sprites or character generation.
- No Web/SaaS deployment.
- No AI model (local or remote) — procedural only.
- No text prompt input — texture type is selected from a predefined list.
- No 16×16 tile support in Phase 1 (32×32 only — deferred to Phase 2).
- Visual quality of generated textures is subjective and not code-verified. Noise parameters require manual tuning per texture type. Automated tests verify structural properties (seamlessness, palette adherence, determinism) but not aesthetic quality.

## Deep Links
- [Phase 1 Spec](./phase-1-simple-tiles.md#overview)
