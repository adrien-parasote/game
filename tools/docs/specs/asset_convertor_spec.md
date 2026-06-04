# Asset Convertor Spec — Interactive GUI

> Document Type: Implementation
> **Covers:** F1, F2, F3, F4, F5, F6, F6a, F6b, F6c, F7, F8, F9, F10, F11, F12, F_HIST, F_COLOR, F_MACUI, F_LOG

## Deep Links

- [V3 Blueprint](../strategic/asset_convertor_blueprint.md#L1)
- [ADR-001: Dear PyGui](../ADRs/adr-001-dearpygui-replaces-pygame.md#L1)
- [GUI Framework Research](../research/python_gui_frameworks.md#L1)
- [V2 Spec](./asset_convertor_spec.md#L1)
- [CLI module](../../../tools/asset_convertor/cli.py#L1)
- [Pygame preview](../../../tools/asset_convertor/preview/pygame_preview.py#L1)
- [Terrain module](../../../tools/asset_convertor/core/terrain.py#L1)
- [Texture module](../../../tools/asset_convertor/core/texture.py#L1)
- [Palette module](../../../tools/asset_convertor/core/palette.py#L1)
- [Detail overlay](../../../tools/asset_convertor/core/detail_overlay.py#L1)
- [Tile assembler](../../../tools/asset_convertor/core/tile_assembler.py#L1)
- [Subtile module](../../../tools/asset_convertor/core/subtile.py#L1)

## Goal

Replace the Pygame-based read-only preview with an interactive Dear PyGui GUI application. The GUI exposes all texture parameters as sliders/dropdowns, provides a real-time single tile preview, and includes a paint canvas where users can draw terrain in autotile mode (Wang blob tiling) or standalone mode (free tile placement). The complete workflow — from preset selection to PNG + TSX export — happens within the GUI.

**Current workflow:** Edit YAML → run CLI → view static Pygame preview → close → repeat.
**V3 target:** Select preset → tweak sliders → see live preview → paint on canvas → export. All in one window.

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|---|---|---|---|
| A1 | Dear PyGui 2.3.1 works on Python 3.13 macOS ARM | Low | [SHOW] | verified via CLI call `pip install --dry-run` |
| A2 | 47-tile tileset regeneration < 1s | Low | [SHOW] | verified via API call `assemble_tileset` profiling |
| A3 | Dear PyGui raw texture API supports RGBA float32 | Low | [SHOW] | verified via API call `dpg.add_raw_texture` |
| A4 | PIL Image.resize with `Image.NEAREST` preserves pixel art crispness | Low | [SHOW] | verified via API call `Image.resize` nearest |
| A5 | Dear PyGui mouse position polling works for canvas hit-testing | Low | [SHOW] | verified via API call `dpg.get_mouse_pos` |
| A6 | 192 raw textures (16×12 canvas) performant in Dear PyGui | Medium | [SHOW] | verified via API call `update_tile_texture` profiling |

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `tools/asset_convertor/core/minimap.py` | Python Module | This spec § "Modules & Responsibilities" | `gui/app.py`, `gui/canvas.py`, `preview/pygame_preview.py` |
| `tools/asset_convertor/gui/app.py` | Python Module | This spec § "Modules & Responsibilities" | `tools/asset_convertor/__main__.py` (GUI entry point) — contains main window, layout, callbacks, theme, all DPG rendering |
| `tools/asset_convertor/gui/state.py` | Python Module | This spec § "Modules & Responsibilities" | `gui/app.py`, `gui/pipeline.py` |
| `tools/asset_convertor/gui/preview.py` | Python Module | This spec § "Modules & Responsibilities" | `gui/app.py`, `gui/pipeline.py` — framework-agnostic PIL/numpy utilities (no DPG imports) |
| `tools/asset_convertor/gui/canvas.py` | Python Module | This spec § "Modules & Responsibilities" | `gui/app.py` — framework-agnostic `CanvasState` dataclass + coordinate helpers (no DPG imports) |
| `tools/asset_convertor/gui/pipeline.py` | Python Module | This spec § "Modules & Responsibilities" | `gui/app.py` — generation pipeline (texture → tiles) and export functions (no DPG imports) |
| `tests/tools/asset_convertor/test_minimap.py` | Python Test | This spec § "Test Cases" | Pytest Runner |
| `tests/tools/asset_convertor/test_gui_state.py` | Python Test | This spec § "Test Cases" | Pytest Runner |
| `tests/tools/asset_convertor/test_gui_preview.py` | Python Test | This spec § "Test Cases" | Pytest Runner |
| `tests/tools/asset_convertor/test_gui_integration.py` | Python Test | This spec § "Test Cases" | Pytest Runner |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/asset_convertor/core/texture.py` | Python Module | V2 spec § "Step 3" | V2 spec |
| `tools/asset_convertor/core/palette.py` | Python Module | V2 spec § "Step 2" | V2 spec |
| `tools/asset_convertor/core/terrain.py` | Python Module | Codebase | Pipeline |
| `tools/asset_convertor/core/subtile.py` | Python Module | Codebase | Pipeline |
| `tools/asset_convertor/core/tile_assembler.py` | Python Module | Codebase | Pipeline |
| `tools/asset_convertor/core/detail_overlay.py` | Python Module | V2 spec § "Step 4" | V2 spec |
| `tools/asset_convertor/exporters/png_exporter.py` | Python Module | Codebase | Exporter |
| `tools/asset_convertor/exporters/tsx_exporter.py` | Python Module | Codebase | Exporter |
| `tools/asset_convertor/config/terrain_presets.yaml` | YAML | V2 spec § "Step 5" | Terrain designer |
| `tools/asset_convertor/config/palettes/*.yaml` | YAML | V2 spec § "Step 2" | Palette designer |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| CLI command | `python -m tools.asset_convertor gui` | This spec § "Step 2" |
| Python function | `run_gui()` | This spec § "Step 2" |
| Python method | `AppState.to_texture_config() -> TextureParams` | This spec § "Modules & Responsibilities" item 3. Maps all AppState slider fields — including `warp_scale` and `warp_strength` (per [terrain_generation_core_spec.md](./terrain_generation_core_spec.md#L1)) — to a `TextureParams` instance. |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| CLI | `pip install --dry-run` | Python Package Manager (External) |

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| Wang blob tiling (47 bitmasks) | Consumed (canvas autotile mode) | `core/tile_assembler.py` |
| TextureParams dataclass | Consumed (slider ↔ state binding) | V2 spec, `core/texture.py` |
| TerrainConfig / DetailConfig | Consumed (preset loading) | V2 spec, `core/terrain.py` |
| SubTileSet | Consumed (tileset generation) | `core/subtile.py` |

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run tests before committing. Use frozen dataclasses for state. Never mutate PIL images (always copy). Use `Image.NEAREST` for pixel art scaling. Debounce slider callbacks (300ms). |
| **Ask first** | Adding new dependencies beyond `dearpygui` and `numpy`. Changing any existing `core/` module's public API. Modifying `tools/asset_convertor/cli.py` behavior. |
| **Never do** | Put generation logic in `gui/` modules. Import `dearpygui` from `core/` modules. Break existing CLI or test suite (263 tests). Remove `preview/pygame_preview.py` (kept as optional legacy). |

---

## Architecture Overview

```
tools/asset_convertor/
├── gui/                     # NEW — V3 GUI package
│   ├── __init__.py
│   ├── app.py               # Main window, layout, callbacks, theme, all DPG rendering (882 lines)
│   ├── state.py             # AppState frozen dataclass, preset loading, config converters
│   ├── preview.py           # PIL → numpy conversion utilities (no DPG imports, testable)
│   ├── canvas.py            # CanvasState dataclass + grid coordinate helpers (no DPG imports, testable)
│   └── pipeline.py          # Generation pipeline: texture → tiles, export functions (no DPG imports)
├── core/
│   ├── minimap.py           # NEW — extracted bitmask engine
│   └── ... (unchanged)
└── ... (unchanged)
```

### Data Flow

```
User action (slider/click)
    │
    ▼
AppState (frozen dataclass)
    │
    ├──► TextureParams + DetailConfig + EdgeConfig
    │         │
    │         ▼
    │    generate_noise_texture_v2()
    │         │
    │         ▼
    │    apply_detail_overlay()
    │         │
    │         ▼
    │    generate_subtiles()
    │         │
    │         ▼
    │    assemble_tileset()
    │         │
    │         ▼
    │    47 PIL Images (one per Wang tile)
    │         │
    │         ├──► Tile Preview (single base texture, 4× zoomed)
    │         └──► Canvas cells (via bitmask → tile index lookup)
    │
    └──► Export (export_png + export_tsx)
```

---

## Modules & Responsibilities

1. **Bitmask Engine (`core/minimap.py`)**: Computes 8-bit Wang blob bitmasks for 47-tile autotiles, independent of any UI framework.
2. **GUI Application Shell (`gui/app.py`)**: Main Dear PyGui window containing the left control panel, center canvas, and right history panel. Includes the **Eraser Mode** toggle switch under the drawing tool widgets.
3. **Application State (`gui/state.py`)**: Centralized `AppState` dataclass managing UI inputs, sliders, tool selections (Paint/Eraser), and preset loading.

   **State update pattern:** Use `dataclasses.replace(state, field=new_value)` exclusively for all slider callbacks. Do NOT use `dataclasses.asdict()` — it fails for nested dataclass fields (`DetailConfig`, `EdgeConfig`). Each slider callback produces a new frozen `AppState` instance via `replace()`.
4. **Preview Utilities (`gui/preview.py`)**: Conversion pipeline from PIL RGBA images to DPG raw textures.
5. **Canvas Data (`gui/canvas.py`)**: Grid state and cell interaction logic for the center paint area. Manages coordinates and state maps. Supports clearing/erasing painted cells: when **Eraser Mode** is active, click/drag operations set cell state to `False` (empty). Empty grid cells are rendered visually using a standard 32x32 transparent checkered texture to represent empty canvas slots. **Drag erase is continuous:** holding the left mouse button and moving over cells erases them sequentially (same `mouse_drag` callback as Paint mode, gated by active tool state). **Tool state is read at each drag event (not locked at drag-start):** a tool switch mid-drag takes effect immediately on the next drag event. Test TC-ERASE-001: single click in Eraser Mode on cell (1,1) sets `grid[1][1] = False`. Test TC-ERASE-002: drag from (0,0) to (2,0) in Eraser Mode → `grid[0][0]`, `grid[0][1]`, `grid[0][2]` all `False`.
6. **Generation Pipeline (`gui/pipeline.py`)**: Combines settings and grid state to run the texture assembly and export flow.

## Error Handling Matrix

| Error | Trigger | User Message | Recovery |
|-------|---------|-------------|----------|
| Invalid preset name | Corrupt/missing YAML | "Preset '{name}' not found. Using 'grass'." | Fallback to grass |
| Palette file missing | Deleted `.yaml` file | "Palette '{name}' not found." | Show error in status bar, skip regen |
| Export path not writable | Permission denied | "Cannot write to '{path}'. Choose another directory." | Open file dialog |
| Dear PyGui init failure | GPU/driver issue | "Failed to initialize GUI. Check GPU drivers." | Exit with error code |
| Texture generation error | Invalid params | "Generation failed: {error}. Check parameters." | Show error, keep last preview |
| Canvas out of bounds | Mouse outside grid | (no message) | Silently ignore |

---

## Project File Tree

The following files are managed by this specification:
```
tools/
  src/
    asset_convertor/
      __main__.py                       # [DEV-TOOL] GUI application entry point
      cli.py                            # [DEV-TOOL] CLI interface for assets creation
      config/
        palettes.json                   # [DEV-TOOL] Color palettes data
      preview/
        pygame_preview.py               # [DEV-TOOL] Legacy pygame-based viewer
      gui/
        __init__.py                     # [DEV-TOOL] Package init
        app.py                          # [DEV-TOOL] Dear PyGui main application layout and logic
        canvas.py                       # [DEV-TOOL] Interactive painting canvas state and helpers
        pipeline.py                     # [DEV-TOOL] Texture generation and export pipeline
        preview.py                      # [DEV-TOOL] PIL texture rendering utilities
        state.py                        # [DEV-TOOL] Immutable app state and preset loader
      core/
        __init__.py
        generator.py                    # [DEV-TOOL] Texture generation layer
        quantizer.py                    # [DEV-TOOL] Quantization layer
        minimap.py                      # [DEV-TOOL] Extracted 47-tile bitmask engine
      exporters/
        exporter.py                     # [DEV-TOOL] Exporter interface
        png_exporter.py                 # [DEV-TOOL] PNG image exporter
        tsx_exporter.py                 # [DEV-TOOL] TSX tileset exporter
  docs/
    strategic/
      simple_tiles_blueprint.md         # Simple tiles strategic blueprint
    specs/
      asset_convertor_spec.md             # This GUI specification
      terrain_generation_core_spec.md   # Domain warping spec
      phase-1-simple-tiles.md           # Simple tiles spec
      code_quality_constants_and_translation.md # Code quality spec
      diagonal_wall_spec.md             # Diagonal walls spec
tests/
  tools/
    asset_convertor/
      test_minimap.py                 # [DEV-TOOL] Unit tests for minimap engine
      test_gui_state.py               # [DEV-TOOL] Unit tests for application state
      test_gui_preview.py             # [DEV-TOOL] Unit tests for PIL texture rendering
      test_gui_integration.py         # [DEV-TOOL] Integration tests for full pipeline
output/
  {tile_name}.png                       # Generated PNG output
  {tile_name}.tsx                       # Generated TSX XML output
```

---

## Anti-Patterns

| # | Anti-Pattern | Why It's Wrong | Do Instead |
|---|-------------|----------------|------------|
| AP-01 | Putting generation logic in `gui/` modules | Couples business logic to GUI framework. Untestable without DPG. | Keep all generation in `core/`. GUI calls core functions. |
| AP-02 | Mutable global state for app parameters | Race conditions, hidden dependencies, untestable. | Frozen `AppState` dataclass. New instance on each change. |
| AP-03 | Regenerating on every slider micro-movement | Floods the CPU with generation calls. Laggy UI. | Debounce 300ms. Only regenerate after pause. |
| AP-04 | Using `Image.BILINEAR` for pixel art scaling | Blurs sharp pixel edges. Ruins the pixel art aesthetic. | Always `Image.NEAREST` for integer scaling. |
| AP-05 | Updating all 192 canvas textures on every param change | O(192) texture updates even for empty cells. Slow. | Only update filled cells. Track dirty state. |
| AP-06 | Importing `dearpygui` in `core/` modules | Creates circular dependency GUI→core→GUI. Breaks CLI. | `core/` never imports from `gui/`. One-way dependency. |
| AP-07 | Blocking UI thread during generation | GUI freezes while 47 tiles generate. Bad UX. | Run generation, then update textures. If needed, show progress. |

---

## Test Case Specifications

### Unit Tests — `tests/tools/asset_convertor/test_minimap.py` (F1)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-001 | Empty grid → all bitmasks are 0 | 4×4 grid, all False | `compute_bitmask(grid, x, y) == 0` for all cells |
| TC-002 | Single filled cell → bitmask 0 (no neighbors) | 4×4 grid, only (1,1)=True | `compute_bitmask(grid, 1, 1) == 0` |
| TC-003 | Full row → correct horizontal bitmask | Row of 4 filled cells | Middle cells have N=0, S=0, W=8, E=16 → bitmask=24 |
| TC-004 | 2×2 block → correct corner bitmasks | (1,1),(2,1),(1,2),(2,2) filled | Each cell has correct 3-neighbor bitmask with diagonal |
| TC-005 | Full grid → bitmask 255 for inner cells | 4×4 all True | `compute_bitmask(grid, 1, 1) == 255` |
| TC-006 | `find_closest_bitmask_index` exact match | Known BLOB_BITMASK value | Returns exact index |
| TC-007 | `find_closest_bitmask_index` approximate | Bitmask not in BLOB_BITMASKS | Returns closest by Hamming similarity |
| TC-008 | `generate_empty_grid` dimensions | cols=10, rows=8 | Grid is 8 rows × 10 cols, all False |

### Unit Tests — `tests/tools/asset_convertor/test_gui_state.py` (F3, F4)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-009 | `state_from_preset("grass")` loads correct values | Grass preset | `state.scale == 0.12`, `state.detail_type == "grass_blades"`. Expected values sourced from `tools/asset_convertor/config/terrain_presets.yaml` grass preset — update this test if the YAML changes. |
| TC-010 | `to_texture_config()` produces valid TextureConfig | Default AppState | TextureConfig with matching fields |
| TC-011 | `to_detail_config()` produces valid DetailConfig | Default AppState | DetailConfig with matching fields |
| TC-012 | `to_edge_config()` produces valid EdgeConfig | Default AppState | EdgeConfig with matching fields |
| TC-013 | AppState is frozen (immutable) | `state.scale = 0.5` | Raises `FrozenInstanceError` |
| TC-014 | `state_from_preset` works for all 6 presets | Each preset name | No exceptions, valid AppState |

### Unit Tests — `tests/tools/asset_convertor/test_gui_preview.py` (F5)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-015 | `pil_to_dpg_rgba` output length | 32×32 RGBA image | `len(result) == 32 * 32 * 4` |
| TC-016 | `pil_to_dpg_rgba` value range | Image with max (255,255,255,255) | All values ≤ 1.0, ≥ 0.0 |
| TC-017 | `scale_nearest` preserves pixel sharpness | 4×4 checkerboard, factor=8 | Result is 32×32, each original pixel is an 8×8 block of same color |
| TC-018 | `extract_tiles_from_strip` count | 49×32 wide strip (1568px — full pipeline output incl. transparent slots 41 and 48) | Returns exactly 49 tile images |
| TC-019 | `extract_tiles_from_strip` dimensions | 49-slot strip | Each tile is 32×32 |

### Integration Tests — `tests/tools/asset_convertor/test_gui_integration.py`

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-001 | Full pipeline: preset → state → texture → tiles | Load grass preset, build state, generate | Returns 47 valid PIL Images |
| IT-002 | Canvas autotile bitmask → tile selection | Paint 3×3 block, check center cell | Center cell bitmask=255, tile index matches full fill |
| IT-003 | Preset switch resets state correctly | Switch grass → sand → grass | State matches grass preset values exactly |
| IT-004 | Export produces valid PNG + TSX | Generate + export to temp dir | PNG exists, TSX valid XML, `tilecount=49` (49 slots including transparent pads 41 and 48), exactly 47 wangtile entries |
| IT-005 | `to_texture_config()` maps warp fields | Build AppState with `warp_scale=0.1`, `warp_strength=5.0`, call `to_texture_config()` | Returned `TextureParams` has `warp_scale=0.1`, `warp_strength=5.0` |
| IT-006 | Full data flow: state → pipeline → canvas tiles | Build state, regenerate, verify canvas tiles update | All filled canvas cells show correct Wang tile for their bitmask |

---


### macOS Native Icon Support
When running on macOS, `gui/app.py` dynamically injects the application icon (`assets/icon.png`) into the macOS Dock using the `AppKit.NSApplication` API (via the `pyobjc-framework-Cocoa` package). This overrides the default Python rocket icon.

**Platform guard:** Wrap the AppKit import and injection call with `if sys.platform == "darwin":`. On non-macOS platforms (Linux, Windows), skip the injection silently — no error, no log message. A missing `pyobjc-framework-Cocoa` on macOS should also be caught with a `try/except ImportError` and silently skipped.

### UI Language Constraint
**Exception to Global Translation Rules:** The GUI interface of `asset_convertor` MUST strictly remain in French. While the internal code, variables, and comments follow English conventions, all user-facing labels in `gui/app.py` are strictly defined in French as per user request.
