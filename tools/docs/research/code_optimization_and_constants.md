# Research: Tooling Code Optimization & Constants Extraction

Analysis of the `tools/asset_convertor/` module to discover opportunities for optimization, extraction of magic values into a central constants configuration, and translation of French comments.

## 🔬 Web Search & Best Practices

1. **Python and Pygame Constants Architecture**:
   - Standard Pygame and PIL projects maintain a single module (e.g., `constants.py`) containing immutable parameters such as `TILE_SIZE`, `SUBTILE_SIZE`, color tuples, default output paths, and matrix data.
   - Separation of configuration (preset files) and compile-time constants (such as the Bayer matrix or standard bitmask list).

2. **Dithering & OpenSimplex Performance**:
   - Simplex noise lookup over grid loops can be optimized by caching generators or using NumPy vectorized operations where applicable.
   - Ordered dithering matrix (`BAYER_4X4`) should be stored statically to avoid recalculations.

## 📋 API & Architectural Citations

- **PIL.Image**: Crops must use precise 4-tuple bounds conforming to `(left, upper, right, lower)` coordinate systems.
- **Tiled mixed-Wang specifications**: The 8-bit layout (NW=1, N=2, etc.) is standard across RPG Maker and Tiled autotiling engines, which maps directly to the 47-tile blob strip layout.

## 🎯 Adopt/Adapt/Build Decision

- **Decision**: **Adopt** a clean, dedicated `tools/asset_convertor/core/constants.py` module.
- **Refactor Scope**:
  - Extract all layout, grid sizing, path, color, and noise constants across the entire `tools/asset_convertor/` package.
  - Translate any French documentation/comments/logs.
  - Ensure all 361 tests pass cleanly under the new unified constants footprint.
