# Spec — GUI Refactor: Dual-Toolbar + AppState + Recolor Panel

> Document Type: Implementation
> **Covers:** F1 (dual-toolbar), F2 (AppState refactor), F7 (recolor UI panel),
>             F8 (export checkboxes), F9–F12 (secondary toolbar contexts),
>             F13 (macOS menu bar), F14 (live preview)
> **Blueprint:** [asset_convertor_ui_v2_blueprint.md](../strategic/asset_convertor_ui_v2_blueprint.md)
> **ADRs:** [ADR-007-1](../ADRs/ADR-007-asset-convertor-ui-v2.md#adr-007-1-dual-toolbar-layout),
>           [ADR-007-2](../ADRs/ADR-007-asset-convertor-ui-v2.md#adr-007-2-mode-first-navigation),
>           [ADR-007-5](../ADRs/ADR-007-asset-convertor-ui-v2.md#adr-007-5-export-checkboxes--tsx-auto-disabled-for-recolor)

---

## Deep Links

- [Blueprint § Feature List](../strategic/asset_convertor_ui_v2_blueprint.md#5-feature-list)
- [Existing `app.py` (864 lines to refactor)](../../src/asset_convertor/gui/app.py)
- [Recolor engine spec (producer)](./asset_convertor_mv_recolor.md)
- [A3/A4 converter spec (producer)](./asset_convertor_mv_core_converters.md)
- [Existing `converter_mv.py` (A2)](../../src/asset_convertor/core/converter_mv.py)
- [Existing `converter_xp.py` (XP)](../../src/asset_convertor/core/converter_xp.py)

---

## Goal

Refactor `gui/app.py` and `gui/state.py` from a single monolithic toolbar to a **dual-toolbar architecture**:
- **Toolbar 1 (Primary):** Resource type selector (`A2 Ground | A3 Bâtiment | A4 Mur | A1 Animé | Recolor`)
- **Toolbar 2 (Secondary):** Contextual frame — swaps content based on selected type

Add `gui/recolor_panel.py` as the right-panel for Recolor mode (palette display + preset grid + remapping table).

The existing A1/A2 conversion logic and 3-panel preview layout are **preserved** — this is a layout and state refactor, not a logic rewrite.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Labels in French (user requirement). Preserve existing A1/A2/XP conversion paths. Use `dataclasses.replace()` for AppState updates (never mutate). Debounce any callback that triggers image processing (300ms). |
| **Ask first** | Changing the existing `convert_mv()` or `convert_xp()` function signatures. Adding new Python dependencies beyond existing ones (customtkinter, Pillow, etc.). |
| **Never do** | Put conversion logic in `gui/` modules. Break existing A1/A2/XP conversion behavior. Remove the 3-panel (Source / Sortie / Aperçu) layout. |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `gui/app.py` | Python Module | This spec § "app.py Architecture" | `__main__.py` (entry point) |
| `gui/state.py` | Python Module | This spec § "AppState" | `gui/app.py`, `gui/recolor_panel.py` |
| `gui/recolor_panel.py` | Python Module | This spec § "Recolor Panel" | `gui/app.py` |
| `tests/asset_convertor/gui/test_app.py` | Python Tests | This spec § "Test Cases" | Pytest runner |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `core/converter_mv.py` → `convert_mv()` | Function | `autotile_converter_spec.md` | A2 spec |
| `core/converter_mv_a3.py` → `convert_mv_a3()` | Function | `asset_convertor_mv_core_converters.md § "A3 Public API"` | This session |
| `core/converter_mv_a4.py` → `convert_mv_a4()` | Function | `asset_convertor_mv_core_converters.md § "A4 Public API"` | This session |
| `core/converter_xp.py` → `convert_xp()` | Function | Existing codebase | Legacy |
| `core/recolor.py` → `extract_palette()`, `apply_remap()` | Functions | `asset_convertor_mv_recolor.md § "Recolor Engine API"` | Recolor spec |
| `core/palettes.py` → `LOSPEC_PALETTES`, `get_palette()` | Module | `asset_convertor_mv_recolor.md § "Lospec Palette Bundle"` | Recolor spec |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Python class | `AppState` (dataclass) | This spec § "AppState" |
| Python class | `RecolorState` (dataclass) | This spec § "RecolorState" |
| Python class | `App(ctk.CTk)` | This spec § "app.py Architecture" |
| Python class | `RecolorPanel(ctk.CTkFrame)` | This spec § "Recolor Panel" |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Function | `convert_mv(img)` | `core/converter_mv.py` |
| Function | `convert_mv_a3(img)` | `core/converter_mv_a3.py` |
| Function | `convert_mv_a4(img)` | `core/converter_mv_a4.py` |
| Function | `convert_xp(img)` | `core/converter_xp.py` |
| Function | `extract_palette(img)` | `core/recolor.py` |
| Function | `apply_remap(img, table)` | `core/recolor.py` |
| Function | `get_palette(name)` | `core/palettes.py` |
| Function | `tkinter.colorchooser.askcolor()` | Python stdlib |

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| `resource_type` (A1/A2/A3/A4/Recolor) | Defined in `AppState` | A3/A4 converter spec |
| `RemapTable` type | Consumed in `RecolorState` | `asset_convertor_mv_recolor.md § "Type Definitions"` |
| WALL_AUTOTILE_TABLE / FLOOR_AUTOTILE_TABLE | Consumed indirectly via converters | `asset_convertor_mv_core_converters.md` |

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| A1 | `CTkSegmentedButton` from CustomTkinter supports 5 values and a callback with the selected value | Low | **ASSUMED** — CTk docs confirm segmented buttons with `values` list and `command` callback. |
| A2 | `AppState.mode` → `AppState.format` rename has zero references in test files | Medium | **ASSUMED** — must run `grep -rn "\.mode" tests/tools/asset_convertor/` before refactoring; see Bundling Audit § BM4. |
| A3 | `tkinter.Menu` + `self.configure(menu=menu)` works on macOS with CustomTkinter (CTk) | Low | **ASSUMED** — standard Tkinter menu integration; CustomTkinter inherits from CTk(tk.Tk) and does not block menu assignment. |
| A4 | Threading with `threading.Thread(target=..., daemon=True)` is safe for all converters (A1/A2/A3/A4/Recolor) since they are pure functions with no shared mutable state | Low | **ASSUMED** — all converter functions take an image and return a new image. PIL Images are not shared between threads. |
| A5 | A4 converter returning a tuple breaks the existing single-Image export contract; a thin wrapper in `_convert_a4()` that produces two named output files and stitches them vertically for the `result_img` preview is sufficient | Medium | **ASSUMED** — TSX exporter takes a single PIL Image. Two calls with `{name}_tops` and `{name}_sides` handle A4 export, and vertically stitching them solves the UI single-image preview constraint without changing the UI architecture. |

---

## AppState

**File:** `gui/state.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from PIL import Image
from asset_convertor.core.recolor import Color, RemapTable

ResourceType = Literal["A1", "A2", "A3", "A4", "Recolor"]
FormatType   = Literal["MV", "XP", "MZ"]

@dataclass(frozen=True)
class AppState:
    # --- Source ---
    source_path: str | None = None
    source_img:  Image.Image | None = None  # raw loaded image, never modified

    # --- Mode ---
    resource_type: ResourceType = "A2"   # PRIMARY axis
    format:        FormatType   = "MV"   # SECONDARY axis (irrelevant for Recolor)

    # --- A1 context ---
    # Note: animated=True is set automatically when resource_type changes to "A1".
    # The A1 toolbar has no "Animé" checkbox — A1 is always animated by design.
    animated:  bool = False
    anim_type: str  = "Horizontale (Eau/Sol)"
    anim_speed_ms: int = 150

    # --- Output ---
    output_dir:  str  = field(default_factory=lambda: _default_output_dir())
    export_png:  bool = True
    export_tsx:  bool = True   # auto-forced False for Recolor in _on_type_change

    # --- Conversion result ---
    result_img: Image.Image | None = None   # produced by converter, displayed in SORTIE panel
    tiles: list[list[Image.Image]] | list[Image.Image] | None = None  # 2D for animated (frames×tiles), flat for static

    # --- Recolor (populated only when resource_type == "Recolor") ---
    recolor: RecolorState | None = None

    # --- Tile display ---
    tile_size: int = 48


@dataclass(frozen=True)
class RecolorState:
    source_palette:  list[Color] = field(default_factory=list)  # extracted from source_img
    remap_table:     RemapTable  = field(default_factory=dict)   # source_color -> target_color
    active_preset:   str | None  = None                          # name of selected Lospec preset
    result_img:      Image.Image | None = None                   # recolored preview image
```

**State update rules:**
- Use `dataclasses.replace(state, field=new_value)` for ALL updates.
- `dataclasses.asdict()` is **forbidden** (fails on nested Image/dataclass fields).
- When `resource_type` changes to `"Recolor"` → set `export_tsx=False` automatically.
- When `resource_type` changes away from `"Recolor"` → restore `export_tsx=True`.
- `source_img` is set once on file open, never modified. All processing produces `result_img`.

---

## app.py Architecture

**File:** `gui/app.py`

The refactored `App` class keeps the same outer structure (CustomTkinter `CTk` subclass, dark theme, macOS icon, `state(zoomed)`, French labels) but replaces the single `_build_toolbar()` with two toolbar builders.

### Layout Grid

```
Row 0: Primary Toolbar      (height=56, sticky=ew)
Row 1: Secondary Toolbar    (height=52, sticky=ew, bg slightly lighter)
Row 2: Panels               (weight=1, expandable)
Row 3: Log                  (height=90, terminal-style)
Row 4: Footer / Status bar  (height=36)
```

### Primary Toolbar (`_build_primary_toolbar()`)

```
[📂 Ouvrir]  [Ground A2] [Bâtiment A3] [Mur A4] [Animé A1] [Recolor]  ←spacer→  [⚙ Convertir/Appliquer]
```

- `[📂 Ouvrir]`: Opens a file dialog, loads source image, calls `_on_file_loaded()`.
- Type buttons: `CTkSegmentedButton` with values `["Ground A2", "Bâtiment A3", "Mur A4", "Animé A1", "Recolor"]`. On change → `_on_type_change(new_type)`.
- `[⚙ Convertir/Appliquer]`: Calls `_run_conversion()`. Label changes to "Appliquer" in Recolor mode.

**Type → ResourceType mapping:**
```python
_TYPE_LABEL_MAP = {
    "Ground A2":    "A2",
    "Bâtiment A3":  "A3",
    "Mur A4":       "A4",
    "Animé A1":     "A1",
    "Recolor":      "Recolor",
}
```

### Secondary Toolbar (`_build_secondary_toolbar()`)

A `CTkFrame` (row 1) that contains a single `CTkFrame` child — the **contextual frame** — which is replaced on each type change by calling `_swap_secondary(resource_type)`.

**Contextual frames per type:**

| Type | Content |
|---|---|
| **A2** | `Format:` radio (MV / MZ / XP) — MZ grayed out (not yet implemented) |
| **A3** | `Format:` radio (MV only) + small hint label "📐 Source attendue : 768×384 px" |
| **A4** | `Format:` radio (MV only) + small hint label "📐 Source attendue : 768×720 px — Produit 2 strips" |
| **A1** | `Format:` radio (MV / MZ / XP) + `Type:` dropdown + `Vitesse:` dropdown. **No "Animé" checkbox** — A1 is always animated. `_on_type_change("🎮 Animé")` sets `animated=True` automatically. |
| **Recolor** | No format selector. `☑ PNG` checkbox (always checked, disabled) + `☑ TSX` checkbox (auto-unchecked, disabled, gray). Label: "Mode Recolor — export TSX non applicable." |

**MZ note:** MZ format selector radio is visible but disabled (no tooltip, CustomTkinter does not support native tooltips). No `convert_mz()` exists yet. Clicking the Convert button with MZ selected shows log message: "Format MZ non encore supporté."

### Panels Area (`_build_panels()`)

**Unchanged for A1/A2/A3/A4 modes:** Source | Sortie Tiled | Aperçu Canvas (3 panels, same as current `app.py`).

**Recolor mode:** The center panel "SORTIE TILED" is relabeled "APERÇU RECOLOR" and shows the recolored image. The right panel "APERÇU CANVAS" is replaced by `RecolorPanel` (embedded as a `CTkFrame`).

Panel swap happens in `_on_type_change()`:
- Non-Recolor → destroy `RecolorPanel` instance (if any), rebuild standard right panel.
- Recolor → hide/destroy standard right panel, instantiate `RecolorPanel`.

### Export Checkboxes

Located in the **footer** row, left side:

```python
self._export_png_var = tk.BooleanVar(value=True)
self._export_tsx_var = tk.BooleanVar(value=True)

self.cb_export_png = ctk.CTkCheckBox(footer, text="PNG", variable=self._export_png_var)
self.cb_export_tsx = ctk.CTkCheckBox(footer, text="TSX", variable=self._export_tsx_var)
```

In `_on_type_change()`:
```python
if resource_type == "Recolor":
    self._export_tsx_var.set(False)
    self.cb_export_tsx.configure(state="disabled")
else:
    self._export_tsx_var.set(True)
    self.cb_export_tsx.configure(state="normal")
```

`cb_export_png` is always `state="disabled"` (always checked — PNG is always produced).

### `_run_conversion()` dispatch

```python
def _run_conversion(self) -> None:
    """Dispatch to the correct converter based on AppState.resource_type."""
    state = self._state
    if state.source_img is None:
        self._log("⚠️ Aucun fichier source chargé.")
        return

    dispatch = {
        "A2":     self._convert_a2,
        "A3":     self._convert_a3,
        "A4":     self._convert_a4,
        "A1":     self._convert_a1,
        "Recolor": self._apply_recolor,
    }
    handler = dispatch.get(state.resource_type)
    if handler:
        threading.Thread(target=handler, daemon=True).start()
```

Each converter method (`_convert_a2`, `_convert_a3`, etc.) runs in a thread, updates `self._state` via `replace()`, then calls `self.after(0, <success_callback>)` to update UI from the main thread. Each type has its own success callback:
- `_on_convert_success_a2(tiles, tile_size)` — used by A1/A2/A3
- `_on_convert_success_a4(result_img, wall_side_tiles, tile_size)` — used by A4 only

**Note for A4 Converter:** The core A4 converter returns a tuple of two images (wall tops and sides). The `_convert_a4` wrapper:
1. Stitches them vertically for the `result_img` SORTIE TILED preview.
2. Extracts **16 wall-side tiles** from the first row of `sides_img` (768px wide, 16 tiles × 48px) into a flat `list[Image.Image]` and stores it in `AppState.tiles` for the **4-neighbor wall canvas** (see `asset_convertor_a4_canvas_4n.md`).
3. Calls `_on_convert_success_a4` which displays both the stitched preview and the canvas pattern.

> ⚠️ **Canvas mode for A4:** `_redraw_canvas_grid` branches on `resource_type == "A4"` to use `_compute_wall_bitmask_4n` (4-voisins, N=2/W=8/E=4/S=1) and `_WALL_4N_BITMASK_TO_IDX` instead of the 8-neighbor blob system used for A1/A2. The canvas label reads "bitmask 4-voisins (Mur)" when A4 is active.


### macOS Menu Bar

```python
# In __init__, after _build_ui():
if sys.platform == "darwin":
    self._build_macos_menu()

def _build_macos_menu(self) -> None:
    menu = tk.Menu(self)
    self.configure(menu=menu)

    file_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Fichier", menu=file_menu)
    file_menu.add_command(label="Ouvrir…", command=self._open_file, accelerator="Cmd+O")
    file_menu.add_separator()
    file_menu.add_command(label="Quitter", command=self.quit, accelerator="Cmd+Q")

    view_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Affichage", menu=view_menu)
    view_menu.add_checkbutton(label="Journal", variable=self._log_visible_var,
                               command=self._toggle_log)
```

---

## Recolor Panel

**File:** `gui/recolor_panel.py`

A `CTkFrame` that occupies the right panel in Recolor mode. Contains three stacked sections.

### Layout

```
┌─ PALETTE DE L'ASSET ────────────────────┐
│ [■] [■] [■] [■] [■] [■] [■] [■]   < >  │   ← scrollable row of color swatches
│ #4a8f3e   #2d5a1b   #8b4513   ...       │   ← hex codes below swatches
└─────────────────────────────────────────┘
┌─ PALETTES PRÉDÉFINIES ──────────────────┐
│ [Endesga 32 ||||]  [Resurrection 64 |||] │   ← 2×3 grid of named chips
│ [Dawnbringer 32 |] [GameBoy ||||]        │
│ [Autumn |||||]     [Winter |||||]        │
└─────────────────────────────────────────┘
┌─ REMAPPAGE ─────────────────────────────┐
│ [■src] → [■dst] #hex   ← row 0          │
│ [■src] → [■dst] #hex   ← row 1          │
│ [■src] → [■dst] #hex   ← row 2          │
│ ...  (scrollable)                        │
└─────────────────────────────────────────┘
```

### Section A: Palette de l'asset

- Populated by `extract_palette(state.source_img)` after file load.
- Each swatch: 28×28 px `CTkButton` with `fg_color=rgb_hex`, no text.
- Clicking a swatch sets it as "selected source" for manual remapping (orange border).
- Max 32 swatches shown. If more, horizontal scroll via `tk.Canvas` + scrollbar.
- Below swatches: hex code label `#rrggbb` (RGB only, no alpha shown).

### Section B: Palettes prédéfinies

- 6 chips in 2×3 `CTkFrame` grid.
- Each chip: `CTkButton` with palette name + 5 micro color swatches (5×12 px rectangles drawn on a `tk.Canvas`).
- On click: calls `propose_remap(state.recolor.source_palette, get_palette(name))` → updates remap table in `RecolorState` → rebuilds Section C → triggers live preview update.

### Section C: Remappage

- Scrollable list via `tk.Canvas + ttk.Scrollbar`.
- One row per source color in `recolor.source_palette`.
- Each row:
  ```
  [src_swatch 20×20]  →  [dst_swatch 20×20 clickable]  [hex_entry 70px wide]
  ```
- Clicking `dst_swatch` OR editing `hex_entry` → calls `_update_remap_row(source_color, new_target)`.
- `dst_swatch` click → opens `tkinter.colorchooser.askcolor()` → on confirm, update `RecolorState.remap_table`.
- `hex_entry` edit → on `<FocusOut>` or `<Return>` → parse hex → validate (6 hex chars) → update.
- Invalid hex: restore previous value, flash entry border red for 1s.

### Live Preview Update

`_update_remap_row()` triggers a debounced (300ms) call to `_refresh_recolor_preview()`:

```python
def _refresh_recolor_preview(self) -> None:
    """Apply current remap table to source image, update center panel."""
    remap = self._state.recolor.remap_table
    if not remap or self._state.source_img is None:
        return
    def worker():
        result = apply_remap(self._state.source_img, remap)
        self._state = dataclasses.replace(
            self._state,
            recolor=dataclasses.replace(self._state.recolor, result_img=result)
        )
        self.after(0, self._refresh_center_panel)
    threading.Thread(target=worker, daemon=True).start()
```

---

## Project File Tree

```
tools/src/asset_convertor/
  gui/
    __init__.py
    app.py              # [MODIFY] Dual-toolbar refactor + Recolor mode dispatch
    state.py            # [MODIFY] AppState: add resource_type, export_png/tsx, RecolorState
    recolor_panel.py    # [NEW] Right panel for Recolor mode
    canvas.py           # [UNCHANGED] Wang blob canvas (existing)
    pipeline.py         # [UNCHANGED] Generation pipeline (existing)
    preview.py          # [UNCHANGED] PIL texture utils (existing)
  core/
    converter_mv.py     # [UNCHANGED] A2 converter
    converter_mv_a3.py  # [NEW] A3 converter
    converter_mv_a4.py  # [NEW] A4 converter
    converter_xp.py     # [UNCHANGED] XP converter
    recolor.py          # [NEW] Recolor engine
    palettes.py         # [NEW] Lospec palette bundle
tests/asset_convertor/gui/
  test_app.py           # [MODIFIED] AppState v2 + RecolorState tests (merged into existing test_app.py)
  # Note: test_recolor_panel.py — deferred, out of scope for initial BUILD cycle
```

---

## Bundling & Native-Module Audit

- BM1: N/A — Pure Python desktop app, no bundled framework.
- BM2: N/A
- BM3: N/A — No native modules. `tkinter.colorchooser` is stdlib.
- BM4: `AppState.mode` renamed to `AppState.format`. Grep affected tests:
  ```bash
  grep -rn "\.mode" tests/tools/asset_convertor/ --include="*.py"
  grep -rn "AppState.*mode" tools/src/asset_convertor/gui/ --include="*.py"
  ```
  All references to `state.mode` must be updated to `state.format`.

---

## Error Handling Matrix

| Error | Trigger | User-visible message | Recovery |
|-------|---------|---------------------|----------|
| No file loaded on Convert | User clicks Convert without opening file | Log: "⚠️ Aucun fichier source chargé." | No-op |
| Converter raises ValueError | Wrong file type (e.g. A2 file given to A3) | Log: "❌ Erreur de conversion : {error.args[0]}" | Keep previous state |
| MZ format selected | User selects MZ format | Log: "i Format MZ non encore supporté." | No-op |
| File open cancelled | User cancels file dialog | (no message) | No-op |
| Invalid hex in remap row | User types "ZZZZZZ" | Flash entry red for 1s, restore previous hex | Restore |
| `colorchooser.askcolor()` cancelled | User closes color picker | No update | Keep previous |
| `extract_palette` raises ValueError (all transparent) | Transparent PNG opened in Recolor mode | Log: "⚠️ Image vide — aucun pixel non-transparent détecté." | Reset recolor panel |
| `apply_remap` thread exception | Unexpected PIL error | Log: "❌ Erreur recolor : {error}" | Show log, keep last preview |
| A4 converter returns tuple — TSX exporter expects Image | A4 produces 2 strips | Export both strips as separate files: `{name}_tops.png` + `{name}_sides.png`. Stitch them vertically into a single image for `result_img` preview. | Two export files auto-named, one preview |

---

## Anti-Patterns

| # | Anti-Pattern | Why Wrong | Do Instead |
|---|---|---|---|
| AP-GUI-01 | Putting conversion logic inside `_run_conversion()` or any `gui/` method | Untestable without launching the full GUI. Couples logic to UI. | `_run_conversion()` is a 1-line dispatch. Logic stays in `core/`. |
| AP-GUI-02 | Calling `self._refresh_panels()` directly from a worker thread | Tkinter is not thread-safe. Will crash intermittently. | Always use `self.after(0, callback)` to schedule UI updates from threads. |
| AP-GUI-03 | Mutating `self._state` directly (`self._state.format = "MV"`) | AppState is frozen. Will raise `FrozenInstanceError`. More importantly breaks the immutable state contract. | `self._state = dataclasses.replace(self._state, format="MV")` |
| AP-GUI-04 | Rebuilding the entire `_build_panels()` on every type change | Tears down and rebuilds 3 panels + all widgets. Slow, causes flicker. | Only swap the secondary toolbar frame and the right panel. Keep Source + center panels. |
| AP-GUI-05 | Calling `extract_palette()` on every remap row update | Palette extraction re-scans the entire image on each color change. Wasteful. | Extract palette once on file load (`_on_file_loaded`), store in `RecolorState.source_palette`. |
| AP-GUI-06 | Opening `colorchooser.askcolor()` synchronously in the main thread loop | Blocks the main thread until the dialog closes. No issue in practice (modal), but causes log delay. | Open with `self.after(0, lambda: self._open_color_picker(...))` to avoid any blocked frame. |
| AP-GUI-07 | Using `state.mode` after renaming to `state.format` | `AttributeError` at runtime. Breaks existing A1/A2 paths. | Run `grep -rn "state\.mode\|_state\.mode" tools/` before and after refactor to find all usages. |

---

## Test Case Specifications

### Unit Tests — `test_gui_state_v2.py`

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-001 | Default `resource_type` is "A2" | `AppState()` | `state.resource_type == "A2"` |
| TC-002 | Default `format` is "MV" | `AppState()` | `state.format == "MV"` |
| TC-003 | `resource_type` and `format` are independent | `replace(state, resource_type="A3", format="XP")` | Both fields set correctly |
| TC-004 | AppState is frozen | `state.format = "XP"` | `FrozenInstanceError` |
| TC-005 | `export_tsx=True` by default | `AppState()` | `state.export_tsx == True` |
| TC-006 | `export_png=True` always | `AppState()` | `state.export_png == True` |
| TC-007 | RecolorState default is None | `AppState()` | `state.recolor is None` |
| TC-008 | RecolorState remap_table is empty dict by default | `RecolorState()` | `state.remap_table == {}` |
| TC-009 | RecolorState source_palette is empty list by default | `RecolorState()` | `state.source_palette == []` |
| TC-010 | `replace()` preserves nested RecolorState | `replace(state, recolor=RecolorState(active_preset="Autumn"))` | `state.recolor.active_preset == "Autumn"` |

### Integration Tests — `test_gui_state_v2.py`

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-001 | Type change to Recolor forces export_tsx=False | Simulate `_on_type_change("Recolor")` | `state.export_tsx == False` |
| IT-002 | Type change from Recolor restores export_tsx=True | Simulate `_on_type_change("A2")` after Recolor | `state.export_tsx == True` |
| IT-003 | RecolorPanel init populates source_palette | Load 4-color image, init RecolorPanel | `len(state.recolor.source_palette) == 4` |
| IT-004 | Preset selection updates remap_table keys | Select "GameBoy" preset | `len(state.recolor.remap_table) == len(source_palette)` |
| IT-005 | Manual remap row update triggers live preview | Update one row, wait 400ms | `state.recolor.result_img is not None` |

---

## Correction Log

| Date | Issue | Fix | Author |
|------|-------|-----|--------|
| 2026-06-05 | `_convert_a2()` always called `convert_mv()`, ignoring XP format — XP images would convert incorrectly | Added format dispatch: `if fmt_val == "XP": convert_xp(…) else: convert_mv(…)` | VERIFY code review |
| 2026-06-05 | Spec Constraint `Never Do: Import from core/recolor.py in app.py` was overly strict — `extract_palette()` must be called in `app.py` at file load time to init `RecolorState.source_palette` before `RecolorPanel` exists | Constraint relaxed: `extract_palette` import allowed in `app.py` for initial palette seed; all other recolor logic stays in `recolor_panel.py` | doc-update |
| 2026-06-05 | Spec referenced `test_gui_state_v2.py` which was never created; AppState v2 tests live in `tests/asset_convertor/gui/test_app.py` | Updated Cross-Spec Contracts and File Tree to reflect actual location | doc-update |
| 2026-06-05 | `_convert_a4()` stored `tiles=None` in `AppState` — APERÇU CANVAS remained empty after A4 conversion. Spec only documented the SORTIE TILED stitch, not the canvas tile extraction. | `_convert_a4` now extracts 47 wall-top tiles from the first strip of `tops_img` and stores them in `AppState.tiles`. New callback `_on_convert_success_a4` calls `_draw_canvas_pattern` with the wall-top tiles. | HARDEN doc-update |
| 2026-06-05 | APERÇU CANVAS A4 affichait des wall-top tiles (47 formes, blob 8-voisins) au lieu des wall-side tiles visibles en jeu. Le canvas blob ne correspond pas au comportement des murs dans Tiled (4-voisins, 16 shapes). | `_convert_a4` extrait désormais 16 wall-side tiles depuis `sides_img` row 0. `_redraw_canvas_grid` branche sur `resource_type == "A4"` pour utiliser `_compute_wall_bitmask_4n` + `_WALL_4N_BITMASK_TO_IDX`. Spec dédiée: `asset_convertor_a4_canvas_4n.md`. | HARDEN doc-update |
| 2026-06-05 | Spec incorrectly stated converters call `self.after(0, self._refresh_panels)`. In practice each type has a dedicated success callback. | Updated § `_run_conversion() dispatch` to list all three callbacks and document their roles. | doc-update |
