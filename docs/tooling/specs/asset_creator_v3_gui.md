# Asset Creator V3 — Interactive GUI with Paint Canvas

> Document Type: Implementation
> **Covers:** F1, F2, F3, F4, F5, F6, F6a, F6b, F6c, F7, F8, F9, F10, F11, F12, F_HIST, F_COLOR, F_MACUI, F_LOG

## Deep Links

- [V3 Blueprint](../strategic/asset_creator_v3_blueprint.md#L1)
- [ADR-001: Dear PyGui](../ADRs/adr-001-dearpygui-replaces-pygame.md#L1)
- [GUI Framework Research](../research/python_gui_frameworks.md#L1)
- [V2 Spec](./asset_creator_v2_texture_quality.md#L1)
- [CLI module](../../../tools/asset_creator/cli.py#L1)
- [Pygame preview](../../../tools/asset_creator/preview/pygame_preview.py#L1)
- [Terrain module](../../../tools/asset_creator/core/terrain.py#L1)
- [Texture module](../../../tools/asset_creator/core/texture.py#L1)
- [Palette module](../../../tools/asset_creator/core/palette.py#L1)
- [Detail overlay](../../../tools/asset_creator/core/detail_overlay.py#L1)
- [Tile assembler](../../../tools/asset_creator/core/tile_assembler.py#L1)
- [Subtile module](../../../tools/asset_creator/core/subtile.py#L1)

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
| `tools/asset_creator/core/minimap.py` | Python Module | This spec § "Step 1" | `gui/app.py`, `gui/canvas.py`, `preview/pygame_preview.py` |
| `tools/asset_creator/gui/app.py` | Python Module | This spec § "Step 2" | `__main__.py` (GUI entry point) — contains main window, layout, callbacks, theme, all DPG rendering |
| `tools/asset_creator/gui/state.py` | Python Module | This spec § "Step 3" | `gui/app.py`, `gui/pipeline.py` |
| `tools/asset_creator/gui/preview.py` | Python Module | This spec § "Step 4" | `gui/app.py`, `gui/pipeline.py` — framework-agnostic PIL/numpy utilities (no DPG imports) |
| `tools/asset_creator/gui/canvas.py` | Python Module | This spec § "Step 5" | `gui/app.py` — framework-agnostic `CanvasState` dataclass + coordinate helpers (no DPG imports) |
| `tools/asset_creator/gui/pipeline.py` | Python Module | This spec § "Step 6" | `gui/app.py` — generation pipeline (texture → tiles) and export functions (no DPG imports) |
| `tests/tools/asset_creator/test_minimap.py` | Python Test | This spec § "Test Cases" | Pytest Runner |
| `tests/tools/asset_creator/test_gui_state.py` | Python Test | This spec § "Test Cases" | Pytest Runner |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/asset_creator/core/texture.py` | Python Module | V2 spec § "Step 3" | V2 spec |
| `tools/asset_creator/core/palette.py` | Python Module | V2 spec § "Step 2" | V2 spec |
| `tools/asset_creator/core/terrain.py` | Python Module | Codebase | Pipeline |
| `tools/asset_creator/core/subtile.py` | Python Module | Codebase | Pipeline |
| `tools/asset_creator/core/tile_assembler.py` | Python Module | Codebase | Pipeline |
| `tools/asset_creator/core/detail_overlay.py` | Python Module | V2 spec § "Step 4" | V2 spec |
| `tools/asset_creator/exporters/png_exporter.py` | Python Module | Codebase | Exporter |
| `tools/asset_creator/exporters/tsx_exporter.py` | Python Module | Codebase | Exporter |
| `tools/asset_creator/config/terrain_presets.yaml` | YAML | V2 spec § "Step 5" | Terrain designer |
| `tools/asset_creator/config/palettes/*.yaml` | YAML | V2 spec § "Step 2" | Palette designer |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| CLI command | `python -m tools.asset_creator gui` | This spec § "Step 2" |
| Python function | `run_gui()` | This spec § "Step 2" |

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
| **Ask first** | Adding new dependencies beyond `dearpygui` and `numpy`. Changing any existing `core/` module's public API. Modifying `cli.py` behavior. |
| **Never do** | Put generation logic in `gui/` modules. Import `dearpygui` from `core/` modules. Break existing CLI or test suite (263 tests). Remove `preview/pygame_preview.py` (kept as optional legacy). |

---

## Architecture Overview

```
tools/asset_creator/
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

## Step 1: Bitmask Engine Extraction — `core/minimap.py`

**Covers:** F1

Extract pure computation from `preview/pygame_preview.py` into a framework-agnostic module.

### Functions to extract

```python
"""Bitmask computation for Wang blob autotiling.

Provides grid-based bitmask calculation for 47-tile blob tilesets.
Framework-agnostic — used by both GUI canvas and Pygame preview.
"""
from __future__ import annotations

from tools.asset_creator.core.tile_assembler import BLOB_BITMASKS


def generate_empty_grid(cols: int, rows: int) -> list[list[bool]]:
    """Create an empty terrain grid (all cells False)."""
    return [[False for _ in range(cols)] for _ in range(rows)]


def compute_bitmask(
    grid: list[list[bool]], x: int, y: int,
) -> int:
    """Compute 8-bit Wang blob bitmask for cell (x, y).

    Checks 8 neighbors (NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128).
    Only counts diagonal neighbors if both adjacent cardinals are filled.

    Args:
        grid: 2D boolean grid (True = terrain, False = empty).
        x: Column index.
        y: Row index.

    Returns:
        8-bit bitmask value.
    """
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    def _filled(gx: int, gy: int) -> bool:
        if 0 <= gx < cols and 0 <= gy < rows:
            return grid[gy][gx]
        return False

    n = _filled(x, y - 1)
    s = _filled(x, y + 1)
    w = _filled(x - 1, y)
    e = _filled(x + 1, y)

    bitmask = 0
    if n:
        bitmask |= 2
    if s:
        bitmask |= 64
    if w:
        bitmask |= 8
    if e:
        bitmask |= 16
    # Diagonals only if both adjacent cardinals are filled
    if n and w and _filled(x - 1, y - 1):
        bitmask |= 1   # NW
    if n and e and _filled(x + 1, y - 1):
        bitmask |= 4   # NE
    if s and w and _filled(x - 1, y + 1):
        bitmask |= 32  # SW
    if s and e and _filled(x + 1, y + 1):
        bitmask |= 128  # SE

    return bitmask


def find_closest_bitmask_index(bitmask: int) -> int:
    """Find the index in BLOB_BITMASKS closest to the given bitmask.

    Exact match preferred. If no exact match, finds the entry with the
    most bits in common (Hamming similarity).

    Args:
        bitmask: 8-bit Wang blob bitmask.

    Returns:
        Index into BLOB_BITMASKS (0-46).
    """
    for i, known in enumerate(BLOB_BITMASKS):
        if known == bitmask:
            return i

    # Fallback: closest by bit overlap
    best_idx = 0
    best_score = -1
    for i, known in enumerate(BLOB_BITMASKS):
        common = bin(bitmask & known).count("1")
        diff = bin(bitmask ^ known).count("1")
        score = common - diff
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx
```

### Update `preview/pygame_preview.py`

Replace the internal `_compute_bitmask_for_cell` and `_find_closest_bitmask_index` with imports from `core/minimap.py`. The Pygame preview keeps working but delegates computation.

---

## Step 2: GUI Application Shell — `gui/app.py`

**Covers:** F2, F3, F9, F10, F11, F12

### Entry Point

Add `gui` subcommand to CLI:

```python
# In cli.py, add to _build_parser():
gui_parser = subparsers.add_parser("gui", help="Launch interactive GUI")
gui_parser.set_defaults(func=cmd_gui)

def cmd_gui(args: argparse.Namespace) -> None:
    from tools.asset_creator.gui.app import run_gui
    run_gui()
```

### Window Structure

```python
def run_gui() -> None:
    """Launch the Asset Creator V3 GUI."""
    import dearpygui.dearpygui as dpg

    dpg.create_context()
    dpg.create_viewport(title="Createur de Tiles V3", width=1400, height=850)

    _presets = get_builtin_presets()
    _state = state_from_preset("grass", _presets, "v2")
    _canvas = CanvasState(cols=CANVAS_COLS, rows=CANVAS_ROWS)

    _apply_theme()           # macOS Sonoma dark mode (F_MACUI)
    _register_textures()     # dpg.add_dynamic_texture for preview + 192 canvas cells

    # Initial generation
    _tiles = regenerate_tileset(_state, _presets)

    # Layout: 3-column (left config, center preview+canvas+logs, right history)
    with dpg.window(tag="primary_window"):
        with dpg.group(horizontal=True):
            _build_left_panel()      # Left: 280px — presets, sliders, colors, actions
            _build_center_panel()    # Center: preview tile, canvas drawlist, journal
            _build_history_panel()   # Right: remaining — undo history list

    # Mouse handler for canvas painting
    with dpg.handler_registry():
        dpg.add_mouse_move_handler(callback=lambda s, d: _handle_mouse_input())

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("primary_window", True)

    # Main loop — manual frame loop for debounced regeneration
    while dpg.is_dearpygui_running():
        _frame_tick()                      # debounce check → _do_regenerate()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
```

### Control Panel Widgets (Left Panel — 280px)

All labels are in French. Sections use `dpg.collapsing_header`.

| Section | Widgets | Callback |
|---------|---------|----------|
| Preset terrain | `add_combo(items=preset_names)` | `_on_preset_change` → reload all sliders + colors |
| Texture | 4× `add_slider_float` (Scale, Persistence, Lacunarité, +) + 1× `add_slider_int` (Octaves) + 2× `add_checkbox` (Rampe lisse, Tramage) | `_on_param_change` (debounced) |
| Couleurs | 4× `add_color_edit` (Ombre, Base, Lumière, Accent) — overrides palette colors | `_on_param_change` |
| Detail | 2× `add_slider_float` + 3× `add_slider_int` | `_on_param_change` |
| Bordure | `add_combo` (Organique/Droit/Trame) + 1× `add_slider_int` + 1× `add_slider_float` — hidden in standalone mode | `_on_param_change` |
| Graine | `add_input_int` + `add_button("Aléa")` | `_on_random_seed` |
| Sortie | 2× `add_input_text` (Dossier PNG, Dossier TSX) | (read at export time) |
| Actions | `add_button("Régénérer")` + `add_button("Exporter PNG + TSX")` | `_do_regenerate`, `_on_export` |

### Center Panel

| Section | Description |
|---------|-------------|
| Aperçu tile (4×) | 128×128 scaled preview of center tile (autotile) or standalone tile |
| Canvas | Mode selector (`add_radio_button ["autotile", "standalone"]`) + 16×12 drawlist + "Effacer" button |
| Journal | Collapsible log panel (F_LOG) — 120px scrollable child window showing timestamped messages |

### History Panel (Right — remaining width)

| Section | Description |
|---------|-------------|
| Historique | Scrollable list of `HistoryEntry` snapshots. Click to restore state (undo). Newest first. Each entry shows index, timestamp, description, mode. |

### Debounce Pattern

Debouncing is frame-based, not thread-based. Each frame, `_frame_tick()` checks whether `DEBOUNCE_SECONDS` (0.3s) have elapsed since the last parameter change. If so, it triggers `_do_regenerate()`.

```python
_last_change_time: float = 0.0
_pending_regen: bool = False

def _on_param_change(sender, app_data, _user):
    """Widget value changed → update state + schedule debounced regen."""
    global _state, _last_change_time, _pending_regen
    _state = _read_state_from_widgets()
    _last_change_time = time.time()
    _pending_regen = True

def _frame_tick():
    """Called each frame — handles debounced regeneration."""
    global _pending_regen
    if _pending_regen and (time.time() - _last_change_time) >= DEBOUNCE_SECONDS:
        _pending_regen = False
        _do_regenerate()
```

---

## Step 3: Application State — `gui/state.py`

**Covers:** F3, F4

### State Dataclass — `AppState`

```python
"""GUI application state management.

Immutable state pattern — each parameter change creates a new AppState.
Widget values are synced to/from the state via read/write functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tools.asset_creator.core.terrain import (
    DetailConfig,
    EdgeConfig,
    TextureConfig,
)


@dataclass(frozen=True)
class AppState:
    """Complete UI state. Immutable — create new instance on change."""

    # Preset
    terrain_name: str = "grass"
    quality: str = "v2"

    # Texture params
    texture_type: str = "noise"
    scale: float = 0.12
    octaves: int = 3
    persistence: float = 0.5
    lacunarity: float = 2.0
    use_smooth_ramp: bool = True
    detail_scale: float = 0.5
    detail_strength: float = 0.06
    use_dithering: bool = True
    dither_matrix_size: int = 4

    # Detail overlay
    detail_type: str = "grass_blades"
    detail_density: float = 0.12
    detail_max_height: int = 4
    detail_max_length: int = 4

    # Edge
    edge_style: str = "organic"
    edge_width: int = 3
    edge_noise_scale: float = 0.3

    # Generation
    seed: int = 0

    # Export
    output_dir: str = "assets/images/autotiles"
    tsx_dir: str = "assets/tiled/autotiles"
    name: str = "grass"
```

### State Conversion Methods

```python
    # Palette colors (RGBA tuples, overridable via color pickers) — F_COLOR
    color_shadow: tuple[int, int, int] = (45, 90, 30)
    color_base: tuple[int, int, int] = (62, 124, 39)
    color_highlight: tuple[int, int, int] = (90, 158, 58)
    color_accent: tuple[int, int, int] = (123, 192, 79)

    # Methods on AppState:

    def to_texture_config(self) -> TextureConfig:
        """Convert to TextureConfig for generation pipeline."""
        return TextureConfig(
            texture_type=self.texture_type,
            scale=self.scale,
            octaves=self.octaves,
            persistence=self.persistence,
            lacunarity=self.lacunarity,
            use_smooth_ramp=self.quality == "v2" and self.use_smooth_ramp,
            detail_scale=self.detail_scale,
            detail_strength=self.detail_strength,
            use_dithering=self.quality == "v2" and self.use_dithering,
            dither_matrix_size=self.dither_matrix_size,
        )

    def to_detail_config(self) -> DetailConfig:
        """Convert to DetailConfig for generation pipeline."""
        return DetailConfig(
            detail_type=self.detail_type,
            density=self.detail_density,
            max_height=self.detail_max_height,
            max_length=self.detail_max_length,
        )

    def to_edge_config(self) -> EdgeConfig:
        """Convert to EdgeConfig for generation pipeline."""
        return EdgeConfig(
            style=self.edge_style,
            width=self.edge_width,
            noise_scale=self.edge_noise_scale,
        )
```

### Preset Loading — `state_from_preset`

```python
def state_from_preset(
    terrain_name: str,
    presets: dict,
    quality: str = "v2",
) -> AppState:
    """Create AppState from a terrain preset name."""
    config = presets[terrain_name]
    return AppState(
        terrain_name=terrain_name,
        quality=quality,
        texture_type=config.texture.texture_type,
        scale=config.texture.scale,
        octaves=config.texture.octaves,
        persistence=config.texture.persistence,
        lacunarity=config.texture.lacunarity,
        use_smooth_ramp=config.texture.use_smooth_ramp,
        detail_scale=config.texture.detail_scale,
        detail_strength=config.texture.detail_strength,
        use_dithering=config.texture.use_dithering,
        dither_matrix_size=config.texture.dither_matrix_size,
        detail_type=config.detail.detail_type,
        detail_density=config.detail.density,
        detail_max_height=config.detail.max_height,
        detail_max_length=config.detail.max_length,
        edge_style=config.edge.style,
        edge_width=config.edge.width,
        edge_noise_scale=config.edge.noise_scale,
        name=terrain_name,
    )
```

### Slider ↔ State Sync

```python
def write_state_to_widgets(state: AppState) -> None:
    """Push state values into Dear PyGui widget values."""
    dpg.set_value("combo_terrain", state.terrain_name)
    dpg.set_value("radio_quality", state.quality)
    dpg.set_value("slider_scale", state.scale)
    dpg.set_value("slider_octaves", state.octaves)
    # ... etc for all widgets

def read_state_from_widgets(base: AppState) -> AppState:
    """Read current widget values into a new AppState."""
    from dataclasses import replace
    return replace(
        base,
        scale=dpg.get_value("slider_scale"),
        octaves=dpg.get_value("slider_octaves"),
        # ... etc
    )
```

---

## Step 4: Preview Utilities — `gui/preview.py`

**Covers:** F5

> **Implementation note:** `preview.py` is a framework-agnostic utility module — it does NOT import `dearpygui`. It provides PIL→numpy conversion functions consumed by `gui/app.py` and `gui/pipeline.py`. DPG texture registration and updates are done directly in `app.py` via `_register_textures()` using `dpg.add_dynamic_texture`.

### PIL → Dear PyGui Raw Texture Pipeline

```python
"""PIL Image to Dear PyGui raw texture conversion.

Handles RGBA PIL images → numpy float32 arrays → DPG raw textures.
Uses Image.NEAREST for pixel art scaling (no bilinear blur).
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def pil_to_dpg_rgba(img: Image.Image) -> list[float]:
    """Convert PIL RGBA image to flat float32 list for DPG raw texture.

    Args:
        img: PIL Image in RGBA mode.

    Returns:
        Flat list of floats [r,g,b,a, r,g,b,a, ...] in [0.0, 1.0].
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32) / 255.0
    return arr.ravel().tolist()


def scale_nearest(img: Image.Image, factor: int) -> Image.Image:
    """Scale PIL image by integer factor using nearest-neighbor.

    Args:
        img: Source image.
        factor: Integer scale factor (e.g., 4 for 32→128).

    Returns:
        Scaled image with crisp pixel art edges.
    """
    w, h = img.size
    return img.resize((w * factor, h * factor), Image.NEAREST)


def extract_tiles_from_strip(
    strip: Image.Image, tile_size: int = 32,
) -> list[Image.Image]:
    """Extract individual tiles from a horizontal tileset strip.

    Args:
        strip: Horizontal strip image (width = N × tile_size).
        tile_size: Size of each square tile.

    Returns:
        List of tile PIL Images.
    """
    count = strip.width // tile_size
    return [
        strip.crop((i * tile_size, 0, (i + 1) * tile_size, tile_size))
        for i in range(count)
    ]
```

### Texture Registry Management (in `gui/app.py`)

> **Implementation note:** Texture registration moved to `app.py::_register_textures()` using `dpg.add_dynamic_texture` (not `add_raw_texture`) for macOS Metal backend compatibility.

```python
# In app.py:
def _register_textures() -> None:
    """Register all DPG dynamic textures (preview + canvas cells)."""
    preview_size = CELL_SIZE * PREVIEW_SCALE  # 128
    preview_data = _make_empty_cell_rgba(preview_size)
    empty_cell = _make_empty_cell_rgba(CELL_SIZE)

    with dpg.texture_registry():
        dpg.add_dynamic_texture(
            preview_size, preview_size, preview_data,
            tag="preview_texture",
        )
        for y in range(CANVAS_ROWS):
            for x in range(CANVAS_COLS):
                tag = f"cell_{x}_{y}"
                dpg.add_dynamic_texture(
                    CELL_SIZE, CELL_SIZE, list(empty_cell),
                    tag=tag,
                )
                _cell_textures[(x, y)] = tag
```

---

## Step 5: Canvas State — `gui/canvas.py` (data) + `gui/app.py` (DPG rendering)

**Covers:** F6, F6a, F6b, F6c

> **Implementation note:** `canvas.py` contains only the framework-agnostic `CanvasState` dataclass and `grid_to_canvas_coords()` helper — no DPG imports, fully testable. All DPG rendering (drawlist, mouse handling, cell texture updates) lives in `app.py`.

### Canvas State

```python
@dataclass
class CanvasState:
    """Mutable canvas grid state."""

    cols: int = 16
    rows: int = 12
    mode: str = "autotile"  # "autotile" | "standalone"
    grid: list[list[bool]] = field(default_factory=list)  # autotile mode
    tile_grid: list[list[int]] = field(default_factory=list)  # standalone: tile index per cell, -1 = empty
    selected_tile_index: int = 0  # standalone mode

    def __post_init__(self) -> None:
        if not self.grid:
            self.grid = generate_empty_grid(self.cols, self.rows)
        if not self.tile_grid:
            self.tile_grid = [[-1] * self.cols for _ in range(self.rows)]

    def clear(self) -> None:
        self.grid = generate_empty_grid(self.cols, self.rows)
        self.tile_grid = [[-1] * self.cols for _ in range(self.rows)]
```

### Canvas State (`canvas.py`)

```python
def grid_to_canvas_coords(
    px: float, py: float, cell_size: int,
) -> tuple[int, int]:
    """Convert pixel coordinates to grid cell indices."""
    gx = max(0, int(px) // cell_size)
    gy = max(0, int(py) // cell_size)
    return gx, gy
```

### Canvas Widget (in `app.py::_build_center_panel()`)

The canvas is built as a DPG drawlist inside the center panel. Cell textures are pre-registered as `dpg.add_dynamic_texture` in `_register_textures()`. Tags follow the pattern `cell_{x}_{y}`.

```python
# In app.py::_build_center_panel():
with dpg.group(horizontal=True):
    dpg.add_text("Canvas")
    dpg.add_radio_button(
        ["autotile", "standalone"], default_value="autotile",
        tag="radio_mode", callback=_on_mode_change, horizontal=True,
    )
    dpg.add_text("Gauche=peindre  Droit=effacer", color=(130, 135, 140, 255))
    dpg.add_button(label="Effacer", callback=_on_clear_canvas)

with dpg.drawlist(width=canvas_w, height=canvas_h, tag="canvas_drawlist"):
    for y in range(CANVAS_ROWS):
        for x in range(CANVAS_COLS):
            dpg.draw_image(f"cell_{x}_{y}", (x0, y0), (x0 + CELL_SIZE, y0 + CELL_SIZE))
```

### Mouse Interaction (in `app.py`)

Registered as a `dpg.add_mouse_move_handler` callback. Uses `dpg.get_item_rect_min("canvas_drawlist")` for position calculation, delegating coordinate conversion to `canvas.grid_to_canvas_coords()`.

```python
# In app.py:
def _handle_mouse_input() -> None:
    """Check canvas hover + mouse buttons for paint/erase each frame."""
    if not dpg.is_item_hovered("canvas_drawlist"):
        return
    mouse_pos = dpg.get_mouse_pos(local=False)
    canvas_rect = dpg.get_item_rect_min("canvas_drawlist")
    rel_x = mouse_pos[0] - canvas_rect[0]
    rel_y = mouse_pos[1] - canvas_rect[1]
    gx, gy = grid_to_canvas_coords(rel_x, rel_y, CELL_SIZE)
    if gx >= _canvas.cols or gy >= _canvas.rows:
        return
    if dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
        _paint_cell(gx, gy)
    elif dpg.is_mouse_button_down(dpg.mvMouseButton_Right):
        _erase_cell(gx, gy)

def _paint_cell(gx: int, gy: int) -> None:
    """Fill a cell. Both modes use the boolean grid."""
    if _canvas.grid[gy][gx]:
        return  # already filled — skip redundant update
    _canvas.grid[gy][gx] = True
    if _canvas.mode == "autotile":
        _update_canvas_region(gx, gy)  # update cell + 8 neighbors
    else:
        _update_cell(gx, gy)

def _erase_cell(gx: int, gy: int) -> None:
    """Clear a cell."""
    if not _canvas.grid[gy][gx]:
        return
    _canvas.grid[gy][gx] = False
    if _canvas.mode == "autotile":
        _update_canvas_region(gx, gy)
    else:
        _update_cell(gx, gy)
```

### Cell Rendering (in `app.py`)

Each cell texture is updated via `dpg.set_value(tag, data)` where `data` is a flat float32 RGBA list from `pil_to_dpg_rgba()`. Empty cells show a dark fill (`_make_empty_cell_rgba`). Filled autotile cells compute bitmask → tile index → composite tile on dark background.

```python
# In app.py:
def _tile_for_cell(x: int, y: int) -> list[float]:
    """Get the RGBA data for a canvas cell based on current mode."""
    if _canvas.mode == "autotile":
        if not _canvas.grid[y][x]:
            return _make_empty_cell_rgba(CELL_SIZE)
        bitmask = compute_bitmask(_canvas.grid, x, y)
        idx = find_closest_bitmask_index(bitmask)
        if idx < len(_tiles):
            composited = _composite_on_dark(_tiles[idx].copy())
            return pil_to_dpg_rgba(composited)
        return _make_empty_cell_rgba(CELL_SIZE)
    # standalone mode
    if not _canvas.grid[y][x]:
        return _make_empty_cell_rgba(CELL_SIZE)
    if _standalone_tile is not None:
        composited = _composite_on_dark(_standalone_tile.copy())
        return pil_to_dpg_rgba(composited)
    return _make_empty_cell_rgba(CELL_SIZE)
```

> **Note:** The standalone mode tile palette from the original spec was not implemented. In standalone mode, the single generated tile is painted directly. There is no tile picker for selecting individual tiles from the 47-tile set.

---

## Step 6: Generation Pipeline — `gui/pipeline.py`

**Covers:** F7, F8, F12

> **Implementation note:** The generation and export logic was extracted into `gui/pipeline.py` — a standalone module with no DPG dependency, making it fully testable. Functions include `regenerate_tileset()`, `generate_standalone_tile()`, `do_export_autotile()`, `do_export_standalone()`, `tiles_to_strip()`, and the internal `_build_texture()`.

### Regenerate Flow

```python
# In pipeline.py:
def regenerate_tileset(
    state: AppState, presets: dict[str, TerrainConfig],
) -> list[Image.Image]:
    """Run the full autotile pipeline and return individual tiles.

    Generates texture → applies detail → processes edges → assembles
    47-tile Wang blob tileset.
    """
    texture = _build_texture(state, presets)
    edge_config = {
        "style": state.edge_style,
        "width": state.edge_width,
        "noise_scale": state.edge_noise_scale,
    }
    subtiles = generate_subtiles(texture, edge_config, seed=state.seed)
    tileset_strip = assemble_tileset(subtiles)
    return extract_tiles_from_strip(tileset_strip, tile_size=32)


def generate_standalone_tile(
    state: AppState, presets: dict[str, TerrainConfig],
) -> Image.Image:
    """Generate a single 32x32 standalone tile (texture + detail only)."""
    return _build_texture(state, presets)
```

`_build_texture()` handles palette color overrides from `state.color_*` fields, building a custom `Palette` with the user's 4 colors.

### Export Flow

```python
# In pipeline.py:
def do_export_autotile(
    state: AppState, tiles: list[Image.Image],
    png_dir: Path | None = None, tsx_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Export autotile as PNG strip + TSX file."""
    strip = tiles_to_strip(tiles, 32)
    png_path = Path(png_dir or state.output_dir) / f"{state.name}.png"
    tsx_path = Path(tsx_dir or state.tsx_dir) / f"{state.name}.tsx"
    export_png(strip, png_path)
    export_tsx(tsx_path, png_path, state.name)
    return png_path, tsx_path

def do_export_standalone(
    state: AppState, tile: Image.Image,
    png_dir: Path | None = None,
) -> Path:
    """Export standalone tile as a single 32x32 PNG."""
    png_path = Path(png_dir or state.output_dir) / f"{state.name}_tile.png"
    export_png(tile, png_path)
    return png_path
```

The `_on_export()` callback in `app.py` dispatches to `do_export_autotile()` or `do_export_standalone()` based on canvas mode, and displays the result in the status text and journal.

---

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

### Unit Tests — `tests/test_minimap.py` (F1)

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

### Unit Tests — `tests/test_gui_state.py` (F3, F4)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-009 | `state_from_preset("grass")` loads correct values | Grass preset | `state.scale == 0.12`, `state.detail_type == "grass_blades"` |
| TC-010 | `to_texture_config()` produces valid TextureConfig | Default AppState | TextureConfig with matching fields |
| TC-011 | `to_detail_config()` produces valid DetailConfig | Default AppState | DetailConfig with matching fields |
| TC-012 | `to_edge_config()` produces valid EdgeConfig | Default AppState | EdgeConfig with matching fields |
| TC-013 | AppState is frozen (immutable) | `state.scale = 0.5` | Raises `FrozenInstanceError` |
| TC-014 | `state_from_preset` works for all 6 presets | Each preset name | No exceptions, valid AppState |

### Unit Tests — `tests/test_gui_preview.py` (F5)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-015 | `pil_to_dpg_rgba` output length | 32×32 RGBA image | `len(result) == 32 * 32 * 4` |
| TC-016 | `pil_to_dpg_rgba` value range | Image with max (255,255,255,255) | All values ≤ 1.0, ≥ 0.0 |
| TC-017 | `scale_nearest` preserves pixel sharpness | 4×4 checkerboard, factor=8 | Result is 32×32, each original pixel is an 8×8 block of same color |
| TC-018 | `extract_tiles_from_strip` count | 47×32 wide strip | Returns exactly 47 tiles |
| TC-019 | `extract_tiles_from_strip` dimensions | 47-tile strip | Each tile is 32×32 |

### Integration Tests — `tests/test_gui_integration.py`

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-001 | Full pipeline: preset → state → texture → tiles | Load grass preset, build state, generate | Returns 47 valid PIL Images |
| IT-002 | Canvas autotile bitmask → tile selection | Paint 3×3 block, check center cell | Center cell bitmask=255, tile index matches full fill |
| IT-003 | Preset switch resets state correctly | Switch grass → sand → grass | State matches grass preset values exactly |
| IT-004 | Export produces valid PNG + TSX | Generate + export to temp dir | PNG exists, TSX valid XML, tile count=47 |
| IT-006 | Full data flow: state → pipeline → canvas tiles | Build state, regenerate, verify canvas tiles update | All filled canvas cells show correct Wang tile for their bitmask |

---

## Implementation Order

| Step | Module | Tests | Depends On |
|------|--------|-------|-----------|
| 1 | `core/minimap.py` | `tests/test_minimap.py` (TC-001→TC-008) | Nothing |
| 2 | `gui/state.py` | `tests/test_gui_state.py` (TC-009→TC-014) | Step 1 |
| 3 | `gui/preview.py` | `tests/test_gui_preview.py` (TC-015→TC-019) | Nothing |
| 4 | `gui/canvas.py` | (tested via integration) | Step 1 |
| 5 | `gui/pipeline.py` | `tests/test_gui_integration.py` (IT-001→IT-006) | Steps 2, 3 |
| 6 | `gui/app.py` + CLI integration | Manual + integration tests | Steps 2, 3, 4, 5 |
| 7 | Visual validation | Manual — launch GUI, paint, export | Step 6 |

---

## Divergence Log

> Documents differences between the pre-implementation spec and the actual code as built.

| # | Spec Section | Spec Said | Actual Implementation | Rationale |
|---|---|---|---|---|
| D-01 | Architecture (§ file tree) | 4 modules: `app.py`, `state.py`, `preview.py`, `canvas.py` | 5 modules: added `pipeline.py` | Generation/export logic extracted to a DPG-free module for testability |
| D-02 | `preview.py` (§ Step 4) | Contains DPG texture registry management (`add_raw_texture`, `update_tile_texture`) | Framework-agnostic PIL/numpy utilities only — no DPG imports | DPG texture ops moved to `app.py::_register_textures()` |
| D-03 | `canvas.py` (§ Step 5) | Contains DPG drawlist, mouse handler, tile palette, all canvas rendering | Framework-agnostic `CanvasState` dataclass + `grid_to_canvas_coords()` only | DPG rendering moved to `app.py::_build_center_panel()` and mouse handler functions |
| D-04 | Texture API | `dpg.add_raw_texture` with `mvFormat_Float_rgba` | `dpg.add_dynamic_texture` | macOS Metal backend compatibility |
| D-05 | Main loop | `dpg.start_dearpygui()` | Manual `while dpg.is_dearpygui_running(): _frame_tick(); dpg.render_dearpygui_frame()` | Required for frame-based debounce pattern |
| D-06 | Window | Title `"Asset Creator V3"`, size 1100×750, 2-column layout | Title `"Createur de Tiles V3"`, size 1400×850, 3-column layout (left/center/right) | Added history panel (F_HIST), wider for 3 panels |
| D-07 | Control Panel | Had "Quality" radio (`v1`/`v2`), English labels | Quality radio removed entirely (V1 pipeline deleted), French UI throughout | Quality toggle removed; French UI throughout |
| D-08 | Control Panel | No color controls | 4 color pickers: Ombre, Base, Lumière, Accent (F_COLOR) | Custom palette color overrides added |
| D-09 | Debounce | `threading.Timer` based | Frame-based: `_frame_tick()` checks elapsed time each render frame | Simpler, avoids threading in single-threaded DPG loop |
| D-10 | Standalone mode | Tile palette UI for selecting from 47 tiles | Single tile generated and painted directly, no tile picker | Simplified standalone UX |
| D-11 | N/A (new) | Not in spec | macOS Sonoma dark mode theme (F_MACUI) — Apple HIG colors and geometry | Consistent with macOS dark mode conventions |
| D-12 | N/A (new) | Not in spec | History panel with undo (F_HIST) — right panel, `HistoryEntry` snapshots, click to restore | State time-travel for iterative design |
| D-13 | N/A (new) | Not in spec | Journal/log panel (F_LOG) — collapsible bottom panel with timestamped messages | Debugging and generation feedback |
| D-14 | N/A (new) | Not in spec | French UI translation throughout — all labels, messages, status text in French | Consistency with user's language preference |
| D-15 | `AppState` (§ Step 3) | No color fields | Added `color_shadow`, `color_base`, `color_highlight`, `color_accent` tuple fields | Supports F_COLOR feature |
| D-16 | `state_from_preset` (§ Step 3) | Does not load palette colors | Loads palette, reads `PaletteRole` colors into `AppState.color_*` fields | Preset colors initialize color pickers |
