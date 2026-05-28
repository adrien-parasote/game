# Blueprint: 2D Diagonal Wall Tile Transformation Utility

> **Implementation Spec:** [`docs/tooling/specs/diagonal_wall_spec.md`](../specs/diagonal_wall_spec.md)  
> **Date:** 2026-05-28  
> **Status:** Strategic Review  

This blueprint outlines the strategy, architecture decisions, and scope boundaries for creating an automated Python utility to transform flat front-facing walls into 45-degree diagonal wall assets.

---

## 1. 7 Questions Strategy

### 1.1 What exact problem are you solving?
We are building a Python utility script `scripts/assets/flat_wall_to_diagonal.py` that automates the transformation of flat 2D walls (with patterns, borders, and window cutouts) into $45^\circ$ diagonal wall assets (NW-SE and NE-SW slopes). Map designers currently have no way to quickly generate these angled tiles, making it tedious to construct diagonal buildings in Tiled/RPG Maker.

### 1.2 What are your success metrics?
* The script successfully processes all three inputs in `scripts/input/` (`asset1.png` ($32\times96$), `asset2.png` ($96\times192$), `asset3.png` ($128\times224$)) and outputs generated tilesets directly to the project's `assets/images/tilesets/` directory.
* The output tiles are mathematically precise, pixel-sharp, and visually consistent with the original textures (no sub-pixel resampling blur).
* The generated diagonal tiles tile seamlessly in a staggered $32\times32$ tile grid.
* The `scripts/input/` directory itself is tracked in git, but its actual image contents are completely ignored.

### 1.3 Why will you win?
Instead of manually slicing and shearing layers in GIMP/Photoshop (which is slow and error-prone), or using naive rotation filters (which blur pixels and break grid alignment), we implement a precise column-by-column vertical shear in Python. Shifting each column $x$ vertically by exactly $x$ pixels is a lossless pixel translation that maintains perfect alignment with the grid boundaries and preserves the crisp pixel-art styling.

### 1.4 What's the core architecture decision?
* The conversion script will be located at `scripts/assets/flat_wall_to_diagonal.py`.
* Inputs are read from the local `scripts/input/` folder, which is structured with a `.gitignore` to track only itself.
* Outputs are written to `assets/images/tilesets/` under clean, standardized names (e.g. `01-walls-ext-diagonal.png`).
* The script is pure CLI, adhering to standard POSIX argument parsing and logging.

### 1.5 What's the tech stack rationale?
Python 3.13 and Pillow (PIL). Pillow provides lightweight, fast, and lossless operations (`Image.crop` and `Image.paste`) which are ideal for pixel-perfect sprite manipulation. Paths will be handled natively with `pathlib.Path` to remain compatible with project standards.

### 1.6 What are the features?
* **Vertical Shear Mapping:** Lossless vertical shifting of columns based on slope parameters.
* **Dual-Direction support:** Batch generates both NW-to-SE (slope $= 1.0$) and NE-to-SW (slope $= -1.0$) variations in one run.
* **Automatic Grid Slicing & Compilation:** Assembles the Top and Bottom diagonal tiles into a single structured tileset PNG ready for import.
* **Clear Console Logging:** Structured console output detailing dimensions, source files, and success messages.

### 1.7 What are you NOT building?
* We are not modifying the game's runtime physics or collision engine to support diagonal sliding collisions (this is purely an asset generation utility).
* We are not building a GUI; the script is developer-facing and runs entirely via CLI.
* We are not committing the raw input images to the git repository.

---

## 2. Assumption Audit

Before moving to the technical specification, we audit all core assumptions:

| # | Assumption | Risk Rating | Status / Verification Method |
|---|---|---|---|
| 1 | **32x32 Grid Alignment:** The input assets are structured on a $32\times32$ grid. | Low | **VERIFIED:** Inspected the sizes of `asset1.png` ($32\times96$), `asset2.png` ($96\times192$), and `asset3.png` ($128\times224$). All are exact multiples of 32. |
| 2 | **Vertical Height Scaling:** Shearing a flat wall of width $W$ and height $H$ by a slope of $1.0$ increases the canvas height to $H + W$. | Low | **VERIFIED:** Run via our prototype Python script in `scratch/`. The $128\times224$ wall sheared perfectly into a $128\times352$ canvas ($224 + 128 = 352$). |
| 3 | **Git Ignore Safety:** The git rules successfully prevent committing input assets. | Low | **VERIFIED:** Added a `.gitignore` to `scripts/input/` that ignores all contents except itself, and verified with `git status` that only `scripts/input/` (representing the `.gitignore` file) is listed. |
| 4 | **Window Shearing Alignment:** Shearing transparent cutout windows along with the wall doesn't cause alignment issues. | Medium | **VERIFIED:** Sheared the entire $224\times224$ wall+window assembly in `scratch/sheared_assembly_nw_se.png` and confirmed visually that the window frames and stone borders sheared beautifully and aligned perfectly. |

Proceeding with these verified assumptions.

---

## 3. Boundary & Layer Rationale
This utility is a developer tool and lives outside the core game engine package `src/`. It does not import from or export to the runtime game files, keeping the layer boundary perfectly clean. The output assets are written directly to the game's shared asset registry in `assets/images/tilesets/`.
