# Research: Tools Directory Code Check & Optimization

This research document analyzes code optimization, constant extraction, and localization cleanup within the `tools` directory of the RPG Tile Engine.

## Domain Context: Best Practices in Codebase Standards

1. **Single Source of Truth (SSOT)**: Hardcoded values (magic numbers) scattered across source files make codebase updates error-prone and reduce maintainability. Standard engineering practices advocate centralizing all global configuration parameters in dedicated constants modules (e.g., `constants.py`).
2. **Internationalization & Codebase Consistency**: Multi-language code comments (e.g., mixing French and English) complicate team onboarding and cross-developer contributions. Standardizing all inline comments, docstrings, and logger statements to English ensures a unified codebase.
3. **Dead Code Elimination**: Unused constants and dead functions increase cognitive load, bloat code size, and slow down static analysis. Periodic checks to prune unused assets are critical for clean code health.

---

## Competitive Landscape & Current Codebase Audit

An audit of the `tools/src/` directory reveals three primary areas of focus:

### 1. Centralized Constants vs. Redundant Definitions
- **Current State**:
  - `tools/src/asset_creator/core/constants.py` contains several unused/dead parameters from previous procedural noise/rendering specs (e.g., `MASK_THRESHOLD`, `DEFAULT_NOISE_SCALE`, `DEFAULT_LACUNARITY`, `BORDER_SHADOW_FACTOR`, `BAYER_4X4`, `DEFAULT_PALETTES`, etc.) that are never imported.
  - `tools/src/asset_creator/core/converter_xp.py` redefines constants locally (`SUBTILE = 16`, `TILE_SIZE = 32`, `BLOB_BITMASKS`) instead of importing them from `constants.py`.
  - `tools/src/asset_creator/gui/app.py` has local GUI parameters (`_CELL_SIZE`, default window sizes, background colors) that can be centralized.
  - `tools/src/assets/flat_wall_to_diagonal.py` has local check parameters that can be linked to standard tile size constants.
  - `tools/src/calibration/calibrate_halos.py` defines color maps, radius arrays, and local paths.

### 2. Localization Audit (French Comments)
- **Current State**:
  - `converter_xp.py` contains French comments:
    - Line 44: `A=isolated, X=absence-de-surface, B=inner-corner`
    - Line 53: `B tile (col 4-5, row 0-1) = virages internes (inner-corner pieces...)`
    - Line 58: `X tile (col 2-3, row 0-1) = "absence de surface"`
  - `calibrate_halos.py` contains French labels and comments:
    - Line 6: `FIRE mode (lanternes)`
    - Line 43: `FIRE_LABELS = {R_FIRE_L: "lanterne", R_FIRE_M: "fenêtre", R_FIRE_S: "petite fenêtre"}`
    - Line 54: `MUSH_LABELS = {R_MUSH_L: "cyan large", R_MUSH_M: "rouge", R_MUSH_S: "cyan petit"}`
    - Line 78: `MUSH_LABELS.get(r, 'champignon')`
  - `gui/app.py` contains extensive French comments, docstrings, and localized logs/labels:
    - Lines 2-7: Docstring description
    - Line 36: `taille d'affichage de chaque cellule dans le canvas interactif`
    - Line 38: `Grille de test par defaut 5x5 - correspondance avec l'ancien _TEST_PATTERN`
    - Line 78: `Dataclass état interne`
    - Line 91: `Application principale`
    - Line 112: `Icone macOS via AppKit (silencieux si non disponible).`
    - Line 121: `non-macOS ou pyobjc non installe`
    - Line 123: `Construction UI`
    - Line 139: `Bouton ouvrir`
    - Line 148: `Sélecteur de format`
    - Line 161: `Bouton convertir`
    - Line 254: `Boutons canvas`
    - Line 323: `Valider les dimensions selon le mode`
    - Line 611: `Conversion pas encore faite : placeholder coloré`
    - Line 617: `Cellule vide`
    - Line 566: `Toggle la cellule cliquée et redessine le canvas.`
    - Line 575: `Reinitialise la grille avec le motif de test 5x5.`
    - Line 579: `Efface toutes les cellules du canvas.`
    - Line 586: `Redessine le canvas interactif depuis self._canvas_grid.`

### 3. Dead Code Analysis
- **Unused Constants**: `tools/src/asset_creator/core/constants.py` contains many variables (e.g. noise configurations, shadow/highlight factors, dither matrices, preset palettes) which are entirely unused in the active source files. They must be safely removed.
- **Unused Imports / Code**: General import cleanup is required across the refactored files.

---

## Technical Feasibility & Action Plan

### Adopt vs. Adapt vs. Build-New
- **Decision**: **Adapt & Refactor**. We will optimize our local codebase directly.

### Transition Action Plan
1. **Prune Dead Constants**: Remove all unused variables from `tools/src/asset_creator/core/constants.py`.
2. **Centralize Constants**:
   - Clean up `converter_xp.py` to import `TILE_SIZE` and `SUBTILE_SIZE` from `constants.py`.
   - Update `app.py` and other modules to import shared sizes.
3. **Translate to English**:
   - Translate all docstrings and comments in `gui/app.py` from French to English.
   - Translate all comments in `converter_xp.py` from French to English.
   - Translate all labels/comments in `calibrate_halos.py` from French to English.
4. **Verification**:
   - Run `venv/bin/pytest tools/` at every step to ensure zero functional regressions.
