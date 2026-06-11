# Spec — Recolor: Fix Palette Swatches + Import Palette from Image

> Document Type: Implementation
> **Covers:** Bug fix AP-RE-SWATCH-01 (white swatches on macOS) + Feature F-PALETTE-IMG (import palette from an image)
> **Parent spec (GUI):** [asset_convertor_mv_gui.md](./asset_convertor_mv_gui.md#recolor-panel)
> **Parent spec (engine):** [asset_convertor_mv_recolor.md](./asset_convertor_mv_recolor.md#L1)

---

## Deep Links

- [GUI spec § Recolor Panel](./asset_convertor_mv_gui.md#recolor-panel)
- [GUI spec § Section A: Asset Palette](./asset_convertor_mv_gui.md#section-a-palette-de-lasset)
- [Recolor engine spec § extract_palette](./asset_convertor_mv_recolor.md#extract_palette)
- [Source: `gui/recolor_panel.py` L139–L158](../../src/asset_convertor/gui/recolor_panel.py#L139)
- [Source: `core/recolor.py` § extract_palette](../../src/asset_convertor/core/recolor.py#L1)

---

## Goal

### Fix 1 — Asset Palette: White Swatches

The asset palette displays as white/empty on macOS even though the label says "16 colors detected".

**Root Cause:** `_rebuild_swatches()` creates `tk.Button`s with `bg=hex_color`. On macOS, the native `tk.Button` renderer **ignores the `bg` property** for textless buttons — it draws a gray/white system background on top. The background color is never visible.

**Fix:** Replace each `tk.Button` with a fixed-size `tk.Canvas` with a colored rectangle painted on it (identical to what is already done in the remap rows and the micro-swatches of the preset chips). `tk.Canvas` is not subject to native macOS rendering and always respects `bg`.

### Feature 2 — Import Palette from an External Image

Allow the user to load another image (e.g., another tileset) and extract its palette to harmonize multiple assets. An "🖼 Importer depuis image…" button opens a `filedialog`, loads the image, extracts the palette using `extract_palette()`, and **replaces the target palette of the remapping** (nearest ΔE CIE76 via `propose_remap()`). In case of an error (unreadable file, transparent image), the message is passed to `app.py` via an `on_error` callback to be displayed in the log at the bottom.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Use `tk.Canvas` for all rendering of colored swatches (source and remap). Call existing `extract_palette()` without modification. Transmit errors via the `on_error` callback to `app.py` (bottom log). Remain in `gui/recolor_panel.py` only — do not touch `core/`. |
| **Ask first** | Modify the signature of `extract_palette()`. Add new Python dependencies. Change the general layout of the `RecolorPanel`. |
| **Never do** | Use `tk.Button` with `bg=` to display a color (broken on macOS). Modify `core/recolor.py` or `core/palettes.py`. Block the main thread during `filedialog` (it is already non-blocking by Tkinter design). Silently ignore an error without propagating it via `on_error`. |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `gui/recolor_panel.py` | Python Module (MODIFY) | This spec § "Implementation" | `gui/app.py` |
| `tests/asset_convertor/gui/test_recolor_panel.py` | Python Tests | This spec § "Test Cases" | Pytest runner |
| Callback `on_error(message: str)` | Callable[[str], None] | This spec § "Interface on_error" | `gui/app.py` (bottom log) |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `core/recolor.py` → `extract_palette()` | Function | `asset_convertor_mv_recolor.md § "extract_palette"` | Recolor spec |
| `core/recolor.py` → `propose_remap()` | Function | `asset_convertor_mv_recolor.md § "propose_remap"` | Recolor spec |
| `tkinter.filedialog.askopenfilename()` | stdlib | Python docs | stdlib |

### Public Interface

N/A — internal module, no public exports.

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Function | `extract_palette(img, max_colors=_MAX_SWATCHES)` | `core/recolor.py` |
| Function | `propose_remap(source_palette, imported_palette)` | `core/recolor.py` |
| Function | `tkinter.filedialog.askopenfilename(filetypes=[...])` | Python stdlib |
| Callback | `on_error(message: str)` | `gui/app.py` (injected at RecolorPanel init) |

### Tracked Concepts

| Concept | Status | Mentioned in |
|---|---|---|
| `tk.Canvas` for swatches | Mandatory fix in this spec | GUI spec § Section A |
| "Import palette from image" | Added feature (mandatory) | No previous mention |
| `on_error` callback | New parameter of `RecolorPanel.__init__` | GUI spec § Recolor Panel |

---

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|---|---|---|---|
| A1 | `tk.Canvas` with `bg=hex_color` respects the background color on macOS (no native theme override) | Low | SHOW | Verified via existing `_build_remap_row()` (L268-L280) and `_build_preset_chip()` micro-swatches (L203-L208) where it works correctly. |
| A2 | `tkinter.filedialog.askopenfilename()` is thread-safe to call from the Tkinter main thread | Low | TELL | Cited from Python standard library docs. |
| A3 | `PIL.Image.open()` + `extract_palette()` can load any PNG/JPEG without visible freeze (<100ms) | Low | SHOW | Verified via benchmark: extract_palette runs in ~12ms on `basement_floor.png`. |
| A4 | Feature 2 only affects `RecolorState.remap_table` — `source_palette` remains the palette of the source asset | Low | TELL | Design decision: target palette is replaced, not source palette. |
| A5 | `app.py` can provide `on_error` to `RecolorPanel.__init__` without structural refactoring | Low | SHOW | Verified via grep of `gui/app.py` showing it uses callables for event wiring. |

---

## Interface on_error

`RecolorPanel` receives a new optional parameter at initialization:

```python
def __init__(
    self,
    parent: ctk.CTkFrame,
    state: AppState,
    on_state_change: Callable[[AppState], None],
    on_preview_update: Callable[[Image.Image], None],
    on_error: Callable[[str], None] | None = None,   # ← NEW
) -> None:
    ...
    self._on_error = on_error
```

**Internal usage:**
```python
if self._on_error:
    self._on_error(f"❌ Import palette : {message}")
```

**On `app.py` side:** The RecolorPanel constructor in `_swap_recolor_panel()` passes `on_error=self._log` (the existing log method that writes to the bottom log).

> **This change implies an update of `gui/app.py`** only at the instantiation of `RecolorPanel` — a single line. No other modification of `app.py` is required.

---

## Implementation

### Bug Fix 1 — `_rebuild_swatches()` : tk.Button → tk.Canvas

**File:** `gui/recolor_panel.py`

**Before (lines 144–153):**
```python
for i, color in enumerate(palette):
    hex_color = _rgb_hex(color)
    btn = tk.Button(
        self._swatch_inner,
        bg=hex_color, activebackground=hex_color,
        width=_SWATCH_SIZE // 8, height=1,
        relief="flat", bd=2,
        command=lambda c=color: self._on_source_swatch_click(c),
    )
    btn.grid(row=0, column=i, padx=1, pady=2)
```

**After:**
```python
for i, color in enumerate(palette):
    hex_color = _rgb_hex(color)
    canvas = tk.Canvas(
        self._swatch_inner,
        width=_SWATCH_SIZE,
        height=_SWATCH_SIZE,
        bg=hex_color,
        highlightthickness=1,
        highlightbackground="#555",
        cursor="hand2",
    )
    canvas.grid(row=0, column=i, padx=1, pady=2)
    canvas.bind("<Button-1>", lambda e, c=color: self._on_source_swatch_click(c))
```

**Why `tk.Canvas` works and `tk.Button` does not work on macOS:**
- `tk.Button` on macOS uses native Aqua rendering which ignores `bg` for buttons without text/image.
- `tk.Canvas` is a raw drawing widget — `bg` is always respected, no native theme override.
- **Proof in existing code:** `_build_remap_row()` L268 and the micro-swatches of the preset chips L203 already use `tk.Canvas` and display correctly.

**Removal of unused imports:** If `tk.Button` is no longer used anywhere in the file after this fix, check and remove the import if applicable.

---

### Feature 2 (Optional) — "Importer depuis image…" Button

**File:** `gui/recolor_panel.py`

#### 2a. Adding the button in `_build_palette_section()`

Add a CTk button under the label `self._lbl_palette_info` (row 4):

```python
self._btn_import_palette = ctk.CTkButton(
    frame,
    text="🖼 Importer depuis image…",
    height=24,
    font=ctk.CTkFont(size=11),
    command=self._import_palette_from_image,
)
self._btn_import_palette.grid(row=4, column=0, pady=(2, 6))
```

#### 2b. Method `_import_palette_from_image()`

```python
def _import_palette_from_image(self) -> None:
    """Open a file dialog, extract palette from chosen image, use it as remap target."""
    path = askopenfilename(
        title="Choisir une image source de palette",
        filetypes=[
            ("Images PNG/JPEG", "*.png *.jpg *.jpeg"),
            ("Tous les fichiers", "*.*"),
        ],
    )
    if not path:
        return  # User cancelled — no-op

    try:
        img = Image.open(path).convert("RGBA")
        imported_palette = extract_palette(img, max_colors=_MAX_SWATCHES)
    except OSError as exc:
        if self._on_error:
            self._on_error(f"❌ Import palette : fichier illisible — {exc}")
        return
    except ValueError as exc:
        # extract_palette raises ValueError when image is fully transparent
        if self._on_error:
            self._on_error(f"❌ Import palette : image vide (aucun pixel non-transparent) — {exc}")
        return

    rs = self._state.recolor
    if rs is None or not rs.source_palette:
        # No source palette yet — nothing to remap against
        if self._on_error:
            self._on_error("⚠️ Import palette : chargez d'abord un asset source.")
        return

    remap = propose_remap(rs.source_palette, imported_palette)
    rs_updated = dataclasses.replace(
        rs,
        remap_table=remap,
        active_preset=None,  # Clear preset selection — custom palette now active
    )
    self._state = dataclasses.replace(self._state, recolor=rs_updated)
    self._on_state_change(self._state)

    self._rebuild_remap_rows(rs_updated.source_palette, remap)
    self._schedule_preview_refresh()
```

**Imports to add at the top of the file (if not already present):**
```python
from tkinter.filedialog import askopenfilename
```

> **Note (resolved divergence):** The initial pattern `from tkinter import filedialog` + `filedialog.askopenfilename(...)` was replaced by the direct import `from tkinter.filedialog import askopenfilename` to allow a reliable `mock.patch("...askopenfilename")` in tests (the sub-attribute `filedialog.askopenfilename` is not patchable in an isolated way within a multi-module pytest context).

#### 2c. Expected Behavior

1. The user opens the asset to be recolored (source).
2. The user clicks "🖼 Importer depuis image…".
3. A filedialog opens → the user chooses another tileset.
4. `extract_palette()` extracts the most frequent colors of the imported image.
5. `propose_remap()` maps the source palette → imported palette (nearest ΔE CIE76).
6. The Remapping section rebuilds with the new target colors.
7. The preview updates (debounce 300ms).

**Limit:** If the imported image has fewer colors than the source, multiple source colors will map to the same target color (many-to-one — behavior already documented in the recolor spec § AP-RE-01).

---

## Project File Tree

```
tools/src/asset_convertor/
  gui/
    recolor_panel.py    # [MODIFY] __init__: added on_error param
                        #          _rebuild_swatches: tk.Button → tk.Canvas
                        #          _build_palette_section: added import button
                        #          _import_palette_from_image: new method
    app.py              # [MODIFY] instantiation of RecolorPanel: added on_error=self._log
tests/asset_convertor/gui/
  test_recolor_panel.py # [NEW] 11 unit tests + 4 integration tests
```

---

## Bundling & Native-Module Audit

- BM1: N/A — Python desktop app, no bundled framework.
- BM2: N/A
- BM3: N/A — `tkinter.filedialog` is stdlib.
- BM4: N/A — no constant renaming.

---

## Error Handling Matrix

| Error / Exception | Trigger / Detection | Response / Action | Recovery / Fallback |
|---|---|---|---|
| `_rebuild_swatches` called with empty palette | No color detected in source | (no message) | Canvas inner empty, label: "0 couleur détectée". No-op. |
| `filedialog` cancelled by user | Import button → Cancel | (no message) | `path` is `""` → early return. |
| Imported image unreadable (`OSError`) | Corrupted file or unsupported format | `on_error("❌ Import palette : fichier illisible — {exc}")` → bottom log | Early return, state unchanged. |
| Imported image fully transparent (`ValueError` from `extract_palette`) | 100% transparent PNG image | `on_error("❌ Import palette : image vide (aucun pixel non-transparent) — {exc}")` → bottom log | Early return, state unchanged. |
| `_import_palette_from_image` called without loaded source asset | `rs.source_palette == []` | `on_error("⚠️ Import palette : chargez d'abord un asset source.")` → bottom log | Early return. |
| `on_error` is `None` (not wired) | `RecolorPanel` instantiated without `on_error=` | Silent errors — graceful degradation. | `if self._on_error: self._on_error(...)` guard everywhere. |

---

## Anti-Patterns

| # | Anti-Pattern | Why Wrong | Do Instead |
|---|---|---|---|
| AP-SW-01 | Use `tk.Button` with `bg=hex_color` to display a color on macOS | The native Aqua renderer ignores `bg` on buttons without text. Swatches appear white. | Use `tk.Canvas` with `bg=hex_color` + `canvas.bind("<Button-1>", ...)` for clicking. |
| AP-SW-02 | Load the imported image in a background thread | `tkinter.filedialog` must be called from the main thread. If a thread is started for the entire operation, the filedialog will be called from that thread → crash or undefined behavior. | Call `filedialog.askopenfilename()` in the main thread (directly inside `_import_palette_from_image`). `Image.open()` + `extract_palette()` are fast enough (< 100ms for an MV tileset) to remain in the main thread. |
| AP-SW-03 | Replace `RecolorState.source_palette` with the imported palette | The user loses the source asset palette — they can no longer see which colors are remapped. | The imported palette is the **target** of the remapping. `source_palette` remains that of the open asset. |
| AP-SW-04 | Call `Image.open(path)` without `.convert("RGBA")` | `extract_palette` calls `.load()` and iterates over tuples — an image in "P" (indexed) mode returns integers, not tuples (R,G,B,A). | Always `.convert("RGBA")` after `Image.open()`. |
| AP-SW-05 | Do not pass `max_colors=_MAX_SWATCHES` to `extract_palette()` in the import | An imported photo can have 10,000+ unique colors → `extract_palette` returns 256 colors → the remapping section has 256 lines → UI unusable. | Always pass `max_colors=_MAX_SWATCHES` (32) in the GUI context. |
| AP-SW-06 | Silently ignore import errors (`except: pass`) | The user clicks "Import", nothing happens — zero feedback. Impossible to diagnose. | Always call `self._on_error(message)` in each error branch. Protect with `if self._on_error:` for graceful degradation if the callback is not wired. |

---

## Test Case Specifications

### Unit Tests — `test_recolor_panel.py`

> These tests verify behavior without launching the full CTk window (mock `ctk.CTk`).

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-001 | `_rebuild_swatches` creates `tk.Canvas`, not `tk.Button` | Palette of 3 colors | `len(swatch_inner.winfo_children()) == 3` + all children are `tk.Canvas` |
| TC-002 | Canvas bg matches hex color | Color `(255, 0, 0, 255)` | `canvas.cget("bg") == "#ff0000"` |
| TC-003 | Label `_lbl_palette_info` displays correct count | Palette of 5 colors | `"5 couleurs détectées"` |
| TC-004 | Empty palette → no children, label "0 couleur détectée" | `palette = []` | `len(children) == 0` + label `"0 couleur détectée"` |
| TC-005 | `_import_palette_from_image`: cancel filedialog → no-op, no error | `askopenfilename` returns `""` | `_state.recolor.remap_table` unchanged, `on_error` not called |
| TC-006 | `_import_palette_from_image`: unreadable image → on_error called, state unchanged | `Image.open` raises `OSError` | `on_error` called with message `"❌ Import palette : fichier illisible"`, state unchanged |
| TC-007 | `_import_palette_from_image`: transparent image → on_error called, state unchanged | `extract_palette` raises `ValueError` | `on_error` called with message `"❌ Import palette : image vide"`, state unchanged |
| TC-008 | `_import_palette_from_image` without loaded source_palette → on_error called, early return | `rs.source_palette == []` | `on_error` called with message `"⚠️ Import palette : chargez d'abord un asset source."`, `propose_remap` not called |
| TC-009 | Valid import → `remap_table` updated | Imported 4-color image, source 3 colors | `len(remap_table) == 3` (len of source_palette) |
| TC-010 | Valid import → `active_preset` set to None | `rs.active_preset == "Autumn"` before import | `rs.active_preset is None` after import |
| TC-011 | `on_error=None` (not wired) → graceful degradation | Instantiate `RecolorPanel` without `on_error`, trigger `OSError` | No exception raised from `RecolorPanel` |

### Integration Tests

| ID | Test | Scenario | Expected |
|---|---|---|---|
| IT-001 | Palette visible after loading an asset | Load `basement_floor.png` → Recolor mode | Palette section non-empty, correct colors (not white) |
| IT-002 | Valid external image import → remap updated + preview refresh scheduled | Load source asset + import palette from another valid PNG tileset | `remap_table` non-empty, `_debounce_id` not None, `on_error` not called |
| IT-003 | Swatches and remap rows use the same `tk.Canvas` component | Inspect widgets after palette extract + preset select | All color swatches are `tk.Canvas` (not `tk.Button`) |
| IT-004 | Import from `app.py` — `on_error` wired to `self._log` | Import a non-image file (e.g. `.txt`) | Error message appears in the bottom log |

---

## Correction Log

| Date | Issue | Fix | Author |
|------|-------|-----|--------|
| 2026-06-09 | Asset palette swatches white on macOS — `tk.Button.bg` ignored by native Aqua rendering | This spec — fix `_rebuild_swatches`: `tk.Button` → `tk.Canvas` | SPEC |
| 2026-06-09 | Feature import palette from image initially marked optional — made mandatory. Initial silent error handling — changed to `on_error` callback → bottom log (option C). | Spec updated | SPEC |
| 2026-06-09 | HARDEN /doc-update — Drift: `filedialog` import replaced by direct `askopenfilename` import. Spec and code examples updated to reflect actual pattern (`from tkinter.filedialog import askopenfilename`). Reason: reliable patchability in multi-module pytest. | Spec corrected (import lines + code example 2b) | HARDEN |
