# Specification: 2D Diagonal Wall Tile Transformation Utility

> Document Type: Implementation  
> Strategic Blueprint: [`docs/tooling/strategic/diagonal_wall_blueprint.md`](../strategic/diagonal_wall_blueprint.md#blueprint-2d-diagonal-wall-tile-transformation-utility)  
> Date: 2026-05-28  
> Status: Spec Gate Review  

---

## Blueprint Coverage Matrix

**Covers:** F1 (CLI Tool), F2 (Vertical Shear Engine), F3 (Automatic Grid Slicing), F4 (Batch Processing), F5 (Gitignore Safety)

| Feature ID | Description | Spec Section Coverage |
|---|---|---|
| **F1** | CLI tool with arguments `--input`, `--output-dir`, and `--direction` | Section 5.1 (CLI Reference) |
| **F2** | Lossless column-by-column vertical shear PIL engine | Section 5.2 (Transformation Engine) |
| **F3** | Slicing and layout compilation into $32\times32$ tilesets | Section 5.3 (Tiling Layout) |
| **F4** | Batch processing of `asset1.png`, `asset2.png`, and `asset3.png` | Section 5.4 (Batch Pipeline) |
| **F5** | Gitignore configuration for untracked inputs and tracked folder | Section 5.5 (Git Safety) |

---

## Constraints

| Tier | Autonomous Agent Boundaries |
|---|---|
| **Always do** | Run Python unit tests before completing execution; use standard logging for error reporting; use `pathlib.Path` for all path manipulations; preserve 100% of horizontal pixel-art alignment (no horizontal scaling). |
| **Ask first** | Adding dependencies outside `Pillow` (PIL) to `requirements.txt` or `pyproject.toml`; changing the CLI argument contract names. |
| **Never do** | Commit raw image assets inside `scripts/input/` to git; use lossy compression (JPEG) for tileset outputs; apply horizontal interpolation or antialiasing (no fuzzy pixels). |

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | $32\times32$ Grid Alignment | Low | Verified via PIL size check on input files |
| 2 | Height scaling formula is $H + W$ | Low | Verified in Python prototype script |
| 3 | Pillow is installed in the system | Low | Verified by import check in python |

---

## Cross-Spec Contracts

### Produces
* **Tileset Images:**
  | Path | Format | Dimensions | Consumers |
  |---|---|---|---|
  | `assets/images/tilesets/<name>_nw_se.png` | PNG (RGBA) | $W \times (H + W)$ | Tiled, RPG Maker, Map Manager |
  | `assets/images/tilesets/<name>_ne_sw.png` | PNG (RGBA) | $W \times (H + W)$ | Tiled, RPG Maker, Map Manager |

### Consumes
* **Input Assets:**
  | Path | Format | Dimensions | Producer |
  |---|---|---|---|
  | `scripts/input/asset1.png` | PNG (RGBA) | $32\times96$ (Window) | Map Designer |
  | `scripts/input/asset2.png` | PNG (RGBA) | $96\times192$ (Window Frame) | Map Designer |
  | `scripts/input/asset3.png` | PNG (RGBA) | $128\times224$ (Brick Wall) | Map Designer |

### Public Interface
| Type | Identifier | Purpose | Documented at |
|---|---|---|---|
| CLI Command | `python3 scripts/assets/flat_wall_to_diagonal.py` | Run the batch diagonal transformation | Section 5.1 (CLI Reference) |
| CLI Argument | `--input-dir` | Path to directory containing flat wall assets | Section 5.1 (CLI Reference) |
| CLI Argument | `--output-dir` | Path to export generated diagonal tilesets | Section 5.1 (CLI Reference) |
| CLI Argument | `--direction` | Angle direction: `nw-se`, `ne-sw`, or `both` | Section 5.1 (CLI Reference) |

### External Invocations
| Type | Invoked | Defined in |
|---|---|---|
| System Library | `PIL.Image` | Pillow dependency |

---

## Bundling & Native-Module Audit
- **BM1:** PASS — Every file listed in the File Tree (§ 6) is annotated with `[SERVER]` (or `[DEV-TOOL]`) as this is a local asset-processing utility.
- **BM2:** PASS — No client-server boundary issues exist; this script runs strictly in a developer workflow and does not enter game runtime bundle.
- **BM3:** N/A — No native (C/C++ or Rust-binding) Node.js modules or Node-gyp modules are introduced.
- **BM4:** PASS — This spec introduces a new script and does not modify any active constants in existing test fixtures.

---

## Technical Implementation Details

### 5.1 CLI Reference
The conversion utility must run with the following signature:
```bash
python3 scripts/assets/flat_wall_to_diagonal.py \
  [--input-dir PATH] [--output-dir PATH] [--direction {nw-se,ne-sw,both}]
```
* Default `--input-dir`: `scripts/input` (resolved relative to workspace root).
* Default `--output-dir`: `assets/images/tilesets` (resolved relative to workspace root).
* Default `--direction`: `both`.

### 5.2 Transformation Engine (Vertical Shear)
The script uses column-by-column vertical shifting.
For a flat image source of size $W \times H$:
1. Create a new transparent RGBA canvas of size $W \times (H + W)$.
2. Loop over each column $x$ from $0$ to $W - 1$:
   * Crop a $1$-pixel wide column at $x$ with height $H$: `col = src.crop((x, 0, x + 1, H))`
   * **NW-to-SE (slope = 1.0):** Paste column `col` at $X = x$, $Y = x$.
   * **NE-to-SW (slope = -1.0):** Paste column `col` at $X = x$, $Y = W - 1 - x$.
3. Save the resulting image as lossless PNG (RGBA).

This lossless vertical shift preserves pixel boundaries perfectly, ensuring the pixel art style remains sharp (nearest-neighbor style, with zero blur or interpolation).

### 5.3 Tiling Layout
The generated PNG is a single vertical strip of width $W$. For a $32$-pixel wide grid:
* Every $32\times32$ block in the output canvas represents a portion of the diagonal tiles.
* Map designers can select $32\times32$ tiles from this sheet. The staggering of tiles at $(c, r)$ (Top piece) and $(c, r+1)$ (Bottom piece) forms a continuous diagonal wall.

### 5.5 Git Safety
To keep the workspace clean, `scripts/input/` contains a `.gitignore` file with the following rules:
```gitignore
*
!.gitignore
```
This guarantees the folder structure is tracked, while raw assets are excluded from commits.

---

## Project File Tree

The following files are managed by this specification:
```
scripts/
  input/
    .gitignore                        # [DEV-TOOL] Git ignore rules for raw inputs
  assets/
    flat_wall_to_diagonal.py          # [DEV-TOOL] Main transformation python script
assets/
  images/
    tilesets/
      asset1_nw_se.png                # [DEV-TOOL] Produced NW-SE diagonal window
      asset1_ne_sw.png                # [DEV-TOOL] Produced NE-SW diagonal window
      asset2_nw_se.png                # [DEV-TOOL] Produced NW-SE diagonal window frame
      asset2_ne_sw.png                # [DEV-TOOL] Produced NE-SW diagonal window frame
      asset3_nw_se.png                # [DEV-TOOL] Produced NW-SE diagonal brick wall
      asset3_ne_sw.png                # [DEV-TOOL] Produced NE-SW diagonal brick wall
```

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | Rotational Resampling | Rotating the image by $45^\circ$ using standard rotation algorithms, which introduces sub-pixel sampling blur. | Use column-by-column cropping and pasting (vertical shear), translating pixels along whole-pixel boundaries with zero scaling. |
| 2 | Horizontal Stretching | Stretching the horizontal width to match the diagonal hypotenuse length ($\approx 1.414 \times W$), which distorts patterns. | Keep horizontal columns exactly 1-pixel wide, relying on vertical shear slope to create the perspective incline naturally. |
| 3 | Committing Untracked Assets | Forgetting to ignore input PNG files, resulting in committing heavy, untracked binary assets to the git repo. | Add `*` in `scripts/input/.gitignore` and ensure `git add` does not stage input PNGs. |
| 4 | Hardcoded Paths | Hardcoding absolute paths like `/Users/adrien.parasote/` in the script, which breaks portability. | Resolve all paths relative to the script location or workspace root using `pathlib.Path(__file__).resolve()`. |
| 5 | Lossy Output Compilations | Saving output tilesets as JPEG or lossy PNG, creating compression artifacts around pixel edges. | Always save using `RGBA` format and lossless PNG compression (`Image.save(path, format='PNG')`). |

---

## Test Case Specifications

### Unit Tests (Minimum 5)
* **UT-001 (Path Resolution):** Test that the CLI tool correctly parses relative paths and converts them to absolute paths relative to workspace root using `pathlib`.
* **UT-002 (Input Verification):** Test that the tool detects missing input files and fails gracefully with a standard console error message.
* **UT-003 (Lossless Dimensions):** Test that a flat input of width $W$ and height $H$ correctly produces an output canvas of width $W$ and height $H + W$.
* **UT-004 (Column Shifting NW-SE):** Verify that the column $x$ of the source is pasted at Y-offset $x$ in the output image (pixel-by-pixel color verification).
* **UT-005 (Column Shifting NE-SW):** Verify that the column $x$ of the source is pasted at Y-offset $W - 1 - x$ in the output image.

### Integration Tests (Minimum 3)
* **IT-001 (Batch Directory Processing):** Verify that running the script with `--input-dir` containing multiple flat assets successfully batch converts all files in one execution.
* **IT-002 (Output Writing & Permissions):** Verify that the output directories are created automatically if missing, and outputs are written with correct permissions.
* **IT-003 (Tiling Boundaries):** Verify that the top-right and bottom-left corner pixels of the output image meet exactly at the expected $45^\circ$ diagonal bounds, proving seamless grid mapping.

---

## Error Handling Matrix

| Scenario | Impact | Action |
|---|---|---|
| Input directory does not exist | Critical | Log `ERROR: Input directory <path> not found.` and exit with status 1. |
| Input directory contains no `.png` files | Medium | Log `WARNING: No PNG files found in <input_dir>. Exiting.` and exit with status 0. |
| Pillow is not installed in the system | Critical | Gracefully catch `ImportError` on launch, output `ERROR: Pillow is required. Run: pip install pillow` and exit with status 1. |
| Output directory is write-protected | Critical | Catch `PermissionError`/`OSError`, log `ERROR: Cannot write to <output_dir>: <details>` and exit with status 1. |
| Input image is corrupted | High | Catch `UnidentifiedImageError` or `OSError`, log `ERROR: Cannot open corrupted image <file>` and proceed with other files in batch. |
