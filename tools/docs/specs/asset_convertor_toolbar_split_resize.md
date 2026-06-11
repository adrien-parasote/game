# Spec — Toolbar Split (Import Tiled / Modifications) + Resize Tool 48px→32px

> Document Type: Implementation
> **Covers:** F-TOOLBAR-SPLIT (visual separation into two groups), F-RESIZE-TOOL (resize tool 48px→32px)
> **Parent spec:** [asset_convertor_mv_gui.md](./asset_convertor_mv_gui.md)

---

## Deep Links

- [app.py — `_build_primary_toolbar()`](../../src/asset_convertor/gui/app.py#L254)
- [app.py — `_TILED_TYPE_MAP` + `_MOD_TYPE_MAP`](../../src/asset_convertor/gui/app.py#L99)
- [app.py — `_on_tiled_type_change()` / `_on_mod_type_change()`](../../src/asset_convertor/gui/app.py#L697)
- [app.py — `_on_type_change_internal()`](../../src/asset_convertor/gui/app.py#L714)
- [app.py — `_validate_resize_dimensions()`](../../src/asset_convertor/gui/app.py#L1418)
- [app.py — `_convert_resize()` + `_on_convert_success_resize()`](../../src/asset_convertor/gui/app.py#L907)
- [app.py — `_export_resize()`](../../src/asset_convertor/gui/app.py#L1380)
- [app.py — `_swap_secondary()`](../../src/asset_convertor/gui/app.py#L304)
- [state.py — `ResourceType` Literal](../../src/asset_convertor/gui/state.py#L25)
- [test_gui_state_v2.py — existing tests](../../../tools/tests/asset_convertor/gui/test_gui_state_v2.py)
- [test_resize_logic.py — resize tests](../../../tools/tests/asset_convertor/gui/test_resize_logic.py)
- [Spec GUI parent § "Primary Toolbar"](./asset_convertor_mv_gui.md#primary-toolbar-_build_primary_toolbar)
- [Spec GUI parent § "Anti-Patterns"](./asset_convertor_mv_gui.md#anti-patterns)

---

## Goal

Divide the primary toolbar into **two visually distinct groups**:

- **Import Tiled Group**: `🎮 Animé | 🏠 Bâtiment | 🧱 Mur | 🌱 Sol` (types A1/A3/A4/A2 — produce assets for Tiled)
- **Modifications Group**: `🎨 Recolor | 🔄 Resize` (post-import transformation tools)

And add a **Resize tool** in the Modifications group: loads a 48px PNG, produces a 32px PNG via `Image.NEAREST`.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Labels in French. `dataclasses.replace()` for all AppState updates. UI updates via `self.after(0, callback)` from threads. Deselect the opposing group when the user clicks inside a group. |
| **Ask first** | Add Python dependencies other than Pillow and CustomTkinter. Modify the signatures of existing converters (`convert_mv`, `convert_xp`, etc.). |
| **Never do** | Modify the existing A1/A2/A3/A4/Recolor conversion logic. Put the conversion logic in `core/` for Resize (too simple, < 10 lines). Use a filter other than `Image.NEAREST` for the pixel art resize. Break existing exported behaviors (TSX/PNG). |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `gui/app.py` — `_build_primary_toolbar()` modified | Python function | This spec § "Primary Toolbar — New Layout" | `_build_ui()` (same file) |
| `gui/state.py` — `ResourceType` extended | Python Literal | This spec § "AppState — ResourceType Extension" | `app.py`, `test_gui_state_v2.py` |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `core/converter_mv.py` | Python module | `autotile_converter_spec.md` | A2/A1 |
| `core/converter_mv_a3.py` | Python module | `asset_convertor_mv_core_converters.md` | A3 |
| `core/converter_mv_a4.py` | Python module | `asset_convertor_mv_core_converters.md` | A4 |
| `core/recolor.py` → `apply_remap()` | Function | `asset_convertor_mv_recolor.md` | Recolor |

### Public Interface

| Type | Identifier | Documented here |
|---|---|---|
| Python Literal | `ResourceType = Literal["A1","A2","A3","A4","Recolor","Resize"]` | This spec § "AppState — ResourceType Extension" |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Pillow | `Image.open(path).resize((32, 32), resample=Image.NEAREST)` | Pillow stdlib |

### Tracked Concepts

| Concept | Status | Mentioned in |
|---|---|---|
| `resource_type` | Extended with `"Resize"` | `asset_convertor_mv_gui.md` |
| `_TYPE_LABEL_MAP` | Replaced by `_TILED_TYPE_MAP` + `_MOD_TYPE_MAP` | `asset_convertor_mv_gui.md` |

---

## Primary Toolbar — New Layout

**File:** `gui/app.py` → `_build_primary_toolbar()`

### Visual Layout

```
Row 0 of the primary toolbar (CTkFrame height=56):

col 0    col 1                                   col 2         col 3     col 5(weight spacer)  col 6
[Ouvrir] [🎮 Animé | 🏠 Bâtiment | 🧱 Mur | 🌱 Sol]  [separator]  [🎨 Recolor | 🔄 Resize]  ←spacer→      [⚙ Convertir]
          seg_tiled (CTkSegmentedButton)          CTkFrame 2px   seg_mod (CTkSegmentedButton)
```

> **Column Note:** Columns 0, 1, 2, 3 are widgets. Column 5 receives `weight=1` (extensible spacer via `grid_columnconfigure`). Column 6 contains `btn_convert`. There is no widget in column 4.

### Implementation

```python
# ── Group Variables ─────────────────────────────────────────────────────────

# Import Tiled dictionary: label → ResourceType
_TILED_TYPE_MAP: dict[str, str] = {
    "🎮 Animé":    "A1",
    "🏠 Bâtiment": "A3",
    "🧱 Mur":      "A4",
    "🌱 Sol":      "A2",
}

# Modifications dictionary: label → ResourceType
_MOD_TYPE_MAP: dict[str, str] = {
    "🎨 Recolor": "Recolor",
    "🔄 Resize":  "Resize",
}

# [REMOVED] _LABEL_BY_TYPE inverse lookup — no documented consumer (YAGNI).
# If necessary, calculate on demand: {v: k for k, v in {**_TILED_TYPE_MAP, **_MOD_TYPE_MAP}.items()}
```

```python
def _build_primary_toolbar(self) -> None:
    bar = ctk.CTkFrame(self, height=56, corner_radius=0)
    bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
    bar.grid_columnconfigure(5, weight=1)  # spacer before Convert

    # col 0 — Open
    self.btn_open = ctk.CTkButton(bar, text="📂 Ouvrir", width=130, command=self._open_file)
    self.btn_open.grid(row=0, column=0, padx=(12, 8), pady=10)

    # col 1 — Import Tiled Group
    self._tiled_type_var = ctk.StringVar(value="🌱 Sol")
    self.seg_tiled = ctk.CTkSegmentedButton(
        bar,
        values=list(_TILED_TYPE_MAP.keys()),
        variable=self._tiled_type_var,
        command=self._on_tiled_type_change,
    )
    self.seg_tiled.grid(row=0, column=1, padx=(4, 4), pady=10)

    # col 2 — Visual Separator (vertical CTkFrame 2px)
    ctk.CTkFrame(bar, width=2, height=28, fg_color="gray40").grid(
        row=0, column=2, padx=6, pady=14,
    )

    # col 3 — Modifications Group
    self._mod_type_var = ctk.StringVar(value="")
    self.seg_mod = ctk.CTkSegmentedButton(
        bar,
        values=list(_MOD_TYPE_MAP.keys()),
        variable=self._mod_type_var,
        command=self._on_mod_type_change,
    )
    self.seg_mod.grid(row=0, column=3, padx=(4, 4), pady=10)

    # col 5 (spacer — weight configured by grid_columnconfigure(5, weight=1))
    ctk.CTkLabel(bar, text="").grid(row=0, column=5, sticky="ew")

    # col 6 — Convert / Apply
    self.btn_convert = ctk.CTkButton(
        bar, text="⚙ Convertir", width=140,
        state="disabled", command=self._run_conversion,
    )
    self.btn_convert.grid(row=0, column=6, padx=(8, 12), pady=10)
```

### Group Callbacks — Mutual Exclusive Selection

```python
def _on_tiled_type_change(self, label: str) -> None:
    """Selection in the Import Tiled group → deselects the Modifications group."""
    if label == "":  # defensive guard — set("") can trigger the callback depending on the CTk version
        return
    self._mod_type_var.set("")
    resource_type = _TILED_TYPE_MAP.get(label, "A2")
    self._on_type_change_internal(resource_type)

def _on_mod_type_change(self, label: str) -> None:
    """Selection in the Modifications group → deselects the Import Tiled group."""
    if label == "":  # defensive guard — set("") can trigger the callback depending on the CTk version
        return
    self._tiled_type_var.set("")
    resource_type = _MOD_TYPE_MAP.get(label, "Recolor")
    self._on_type_change_internal(resource_type)
```

> **Note:** Existing `_on_type_change()` is renamed to `_on_type_change_internal()`. Both new callbacks call `_on_type_change_internal()`. No change in internal logic.

### Deselection via `set("")`

When `CTkSegmentedButton.variable.set("")`, no segment is visually active (native CustomTkinter behavior). This is the cross-deselection mechanism between the two groups.

**Callback Behavior:** `set("")` called programmatically does NOT trigger the `command` callback in CustomTkinter — only user interaction triggers it. [ASSUMED Medium — validate visually during BUILD.] The guard `if label == "": return` is present in both callbacks defensively for all CustomTkinter versions.

**Rule:** One of the two groups ALWAYS has a selected segment, except during the transition between groups (window of ~1 frame).

---

## AppState — ResourceType Extension

**File:** `gui/state.py`

```python
# Before
ResourceType = Literal["A1", "A2", "A3", "A4", "Recolor"]

# After
ResourceType = Literal["A1", "A2", "A3", "A4", "Recolor", "Resize"]
```

No other AppState field changes. The `Resize` type behaves like `Recolor` for TSX rules:
- `export_tsx` = **False** when `resource_type == "Resize"` (no Tiled tileset produced)
- `export_tsx` = True for all other types

---

## Secondary Toolbar — Resize

**File:** `gui/app.py` → new `_build_secondary_resize()`

```python
def _build_secondary_resize(self, parent: ctk.CTkFrame) -> None:
    """Resize: hint label — expected source 48px."""
    ctk.CTkLabel(
        parent,
        text="📐 Source attendue : PNG 48px (multiples de 48) — Produit une image 32px (ratio 1.5×, pixel-perfect)",
        text_color="gray",
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=0, padx=(16, 4), pady=10)
```

Added to `_swap_secondary()`:

```python
builders = {
    "A2":     self._build_secondary_a2,
    "A3":     self._build_secondary_a3,
    "A4":     self._build_secondary_a4,
    "A1":     self._build_secondary_a1,
    "Recolor": self._build_secondary_recolor,
    "Resize": self._build_secondary_resize,  # ← new
}
```

---

## Conversion Resize — `_convert_resize()`

**File:** `gui/app.py`

> **Threading:** `_convert_resize()` is called via `threading.Thread(target=self._convert_resize, daemon=True)` in `_run_conversion()` — same pattern as `_convert_a2`, `_convert_a3`, etc. Never call directly from the UI thread.

```python
def _convert_resize(self) -> None:
    """Resize PNG 48px → 32px via NEAREST (pixel art, exact 1.5× ratio).

    Called in a daemon thread by _run_conversion() — do not call from the UI thread.
    """
    try:
        img = self._state.source_img
        if img is None:
            msg = "⚠️ Aucun fichier source chargé."
            self.after(0, lambda m=msg: self._on_convert_error(m))
            return

        src_w, src_h = img.size
        # Proportional calculation: 48→32 = exact 2/3 ratio
        target_w = round(src_w * 32 / 48)
        target_h = round(src_h * 32 / 48)

        result = img.resize((target_w, target_h), resample=Image.NEAREST)

        self._state = dataclasses.replace(self._state, result_img=result)
        self.after(0, lambda: self._on_convert_success_resize(result))
    except Exception as err:
        msg = str(err)
        self.after(0, lambda m=msg: self._on_convert_error(m))

def _on_convert_success_resize(self, result: Image.Image) -> None:
    """Displays the resize result in the OUTPUT panel."""
    self.btn_convert.configure(state="normal")
    self.btn_export.configure(state="normal")
    self._display_result_image(result)
    w, h = result.size
    self.lbl_output_info.configure(text=f"Resize : {w}×{h} px (32px)")
    self._set_status(f"Resize terminé — {w}×{h} px.")
```

Added to `_run_conversion()` dispatch:

```python
dispatch = {
    "A2":     self._convert_a2,
    "A3":     self._convert_a3,
    "A4":     self._convert_a4,
    "A1":     self._convert_a1,
    "Recolor": self._apply_recolor,
    "Resize": self._convert_resize,  # ← new
}
# Actual call: threading.Thread(target=dispatch[resource_type], daemon=True).start()
```

### Canvas Behavior for Resize

The CANVAS PREVIEW panel is hidden for the Resize type (no autotiles to preview). Identical behavior to Recolor mode: no canvas, no toggle.

> **Implementation:** In `_on_type_change_internal()`, add `resource_type in ("Recolor", "Resize")` for branches that hide/restore the canvas panel.

---

## Dimension Validation — Extension

**File:** `gui/app.py` → `_validate_dimensions()` + `_open_file()` + `_on_type_change_internal()`

For the Resize type, validation accepts any image whose width and height are multiples of 48:

```python
if resource_type == "Resize":
    if img.width % 48 != 0 or img.height % 48 != 0:
        return (
            f"⚠️ Resize : dimensions {img.width}×{img.height} px non multiples de 48. "
            "Attendu : multiples de 48 px (ex: 48×48, 96×96, 192×192)."
        )
    return None  # OK
```

### Re-validation during type change (F-VALIDATION-TIMING-01)

The above validation is called in `_open_file()`. It must also be called in `_on_type_change_internal()` when the type transitions to "Resize" and a file is already loaded — otherwise the user could convert a file that is not a multiple of 48 without error.

```python
# In _on_type_change_internal(), after the canvas/export_tsx block:
if resource_type == "Resize" and self._state.source_img is not None:
    err_msg = self._validate_resize_dimensions(self._state.source_img)
    if err_msg:
        self._set_status(err_msg)
        self.btn_convert.configure(state="disabled")
    elif self._state.source_img is not None:
        self.btn_convert.configure(state="normal")
```

> **Covered sequence:** (1) User opens 64×64 file in Recolor mode → valid. (2) Switches to Resize → re-validation → dimensions not multiples of 48 → `btn_convert` disabled + status message. Convert remains unreachable.

---

## Export Behavior for Resize

- `export_tsx` = False (auto-set in `_on_type_change_internal()` when `resource_type == "Resize"`)
- `export_png` = True (standard behavior)
- Exported filename: `{source_stem}_32px.png`

Added to `_export()` (Resize section):

```python
if self._state.resource_type == "Resize":
    stem = Path(self._state.source_path).stem
    out_path = Path(self._state.output_dir) / f"{stem}_32px.png"
    self._state.result_img.save(str(out_path))
    self._log(f"✅ Export Resize : {out_path.name}")
    return
```

---

## Error Handling Matrix

| Trigger | User message | Recovery |
|--------|-------------|--------------|
| Click Convert without open file (Resize) | `"⚠️ Aucun fichier source chargé."` (log) | No-op |
| Opening PNG where w or h % 48 ≠ 0 | `"⚠️ Resize : dimensions NxM px non multiples de 48."` (status) | Disable btn_convert |
| Switching to Resize with already loaded image not a multiple of 48 | `"⚠️ Resize : dimensions NxM px non multiples de 48."` (status) | Disable btn_convert |
| Unexpected Pillow error | `"❌ Erreur resize : {error}"` (log) | Preserve previous state |
| Click Export without conversion | `"⚠️ Aucun résultat à exporter."` (log) | No-op |
| `{stem}_32px.png` exists in output_dir | Silent overwrite | App convention — identical behavior to other exporters |

**Claim Status:**
- Pillow `Image.NEAREST` 1.5× ratio → **VERIFIED** (research + official Pillow documentation)
- `CTkSegmentedButton.variable.set("")` deselects all segments → **ASSUMED** (Medium — to be visually validated during BUILD)
- `set("")` does not programmatically trigger the `command` callback → **ASSUMED** (Medium — defensive guard `if label == "": return` present in both callbacks)

---

## Anti-Patterns

| # | Anti-Pattern | Why Incorrect | What to Do Instead |
|---|---|---|---|
| AP-SPLIT-01 | Keep a single `CTkSegmentedButton` and add "Resize" inside it | Mixes the two logical groups in a single widget that is not visually separable | Two distinct `CTkSegmentedButton` + 2px `CTkFrame` separator |
| AP-SPLIT-02 | Handle cross-deselection in `_on_type_change_internal()` rather than in group callbacks | `_on_type_change_internal()` does not know which group was just activated | Deselection in `_on_tiled_type_change()` and `_on_mod_type_change()` BEFORE calling common logic |
| AP-SPLIT-03 | Use `Image.LANCZOS` or `Image.BILINEAR` for resize | Introduces blur/anti-aliasing on pixel edges — destroys pixel art sharpness | `Image.NEAREST` only |
| AP-SPLIT-04 | Calculate `target_w = src_w // 48 * 32` (integer division) | `//` introduces rounding errors if `src_w` is not a multiple of 48. `round(src_w * 32 / 48)` is more precise. | `round(src_w * 32 / 48)` |
| AP-SPLIT-05 | Display the PREVIEW canvas for Resize mode | Resize does not produce an autotile — the 5×5 canvas has no meaning for a resized image | Hide the canvas panel (`grid_remove()`) like for Recolor |
| AP-SPLIT-06 | Modify `_on_type_change()` directly without renaming it to `_on_type_change_internal()` | The name `_on_type_change(label: str)` takes a `CTkSegmentedButton` label — with two groups, this contract is ambiguous | Rename to `_on_type_change_internal(resource_type: str)` which takes the internal type, not the label |
| AP-SPLIT-07 | Export a TSX for the Resize type | Resize produces a simple PNG image, not a Tiled autotile. A TSX would be invalid. | Force `export_tsx=False` in `_on_type_change_internal()` when `resource_type == "Resize"` |

---

## Test Case Specifications

### Unit Tests — to be added to `test_gui_state_v2.py`

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-RSZ-U-001 | `ResourceType` accepts `"Resize"` | `AppState(resource_type="Resize")` | No error, `state.resource_type == "Resize"` |
| TC-RSZ-U-002 | AppState Resize forces `export_tsx=False` (business rule) | `AppState(resource_type="Resize", export_tsx=False)` | `state.export_tsx is False` |
| TC-RSZ-U-003 | `dataclasses.replace()` preserves `resource_type="Resize"` | `replace(AppState(), resource_type="Resize")` | `state.resource_type == "Resize"` |
| TC-RSZ-U-004 | AppState frozen with `resource_type="Resize"` | `state = AppState(resource_type="Resize"); state.resource_type = "A2"` | `FrozenInstanceError` |
| TC-RSZ-U-005 | `result_img` None by default for Resize | `AppState(resource_type="Resize")` | `state.result_img is None` |

### Unit Tests — resize logic (to be added to new file `test_resize_logic.py`)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-RSZ-U-010 | Resize 48×48 → 32×32 | `Image.new("RGBA", (48, 48)).resize((32, 32), Image.NEAREST)` | `result.size == (32, 32)` |
| TC-RSZ-U-011 | Resize 96×96 → 64×64 | `Image.new("RGBA", (96, 96)).resize((64, 64), Image.NEAREST)` | `result.size == (64, 64)` |
| TC-RSZ-U-012 | Resize 192×48 (wide) → 128×32 | `Image.new("RGBA", (192, 48)).resize((128, 32), Image.NEAREST)` | `result.size == (128, 32)` |
| TC-RSZ-U-013 | Validation: 48×48 → None (no error) | `_validate_resize_dimensions(48, 48)` | `None` |
| TC-RSZ-U-014 | Validation: 46×48 → error message | `_validate_resize_dimensions(46, 48)` | non-None string containing `"non multiples de 48"` |
| TC-RSZ-U-015 | Validation: 48×46 → error message | `_validate_resize_dimensions(48, 46)` | non-None string containing `"non multiples de 48"` |
| TC-RSZ-U-016 | Calculation target_w = round(192 * 32 / 48) == 128 | Arithmetic calculation | `128` |
| TC-RSZ-U-017 | `Image.NEAREST` preserves exact colors | Pure red pixel `(255, 0, 0, 255)` in 48×48 image → resize 32×32 | Corresponding pixel == `(255, 0, 0, 255)` |

### Integration Tests

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-RSZ-001 | Selection Resize forces `export_tsx=False` | Simulate `_on_type_change_internal("Resize")` | `self._state.export_tsx == False` |
| IT-RSZ-002 | Selection A2 after Resize restores `export_tsx=True` | `_on_type_change_internal("A2")` after Resize | `self._state.export_tsx == True` |
| IT-RSZ-003 | `_run_conversion()` dispatch → `_convert_resize` for Resize | `self._state.resource_type = "Resize"` | `threading.Thread` launched with `target=self._convert_resize` |

---

## Project File Tree

```
tools/src/asset_convertor/gui/
  app.py              # [MODIFY] toolbar split + _convert_resize + _build_secondary_resize
  state.py            # [MODIFY] ResourceType Literal + "Resize"
tools/tests/asset_convertor/gui/
  test_gui_state_v2.py  # [MODIFY] addition TC-RSZ-U-001 to TC-RSZ-U-005
  test_resize_logic.py  # [NEW] TC-RSZ-U-010 to TC-RSZ-U-017
```

---

## Correction Log

| Date | Issue | Fix | Author |
|------|-------|-----|--------|
| 2026-06-06 | F-COLNUM-01 — Mismatch diagram/code (col 4 vs col 5 spacer) | Diagram updated: col 5 = spacer weight, col 6 = Convert. Code comment corrected. | Adversarial review |
| 2026-06-06 | F-LABEL-BY-TYPE-01 — `_LABEL_BY_TYPE` without consumer | Removed from snippet. Replaced by YAGNI comment with on-demand formula. | Adversarial review |
| 2026-06-06 | F-CROSS-DESEL-01 — `set("")` can trigger callback | Guard `if label == "": return` added in `_on_tiled_type_change()` and `_on_mod_type_change()`. Behavior documented in § Deselection. | Adversarial review |
| 2026-06-06 | F-ASSERT-01 — `assert img is not None` removed by `-O` | Replaced by `if img is None: ... return`. Explicit error message. | Adversarial review |
| 2026-06-06 | F-THREADING-01 — Threading not declared in `_convert_resize()` | Threading note added at head of section. Docstring and dispatch comment updated. | Adversarial review |
| 2026-06-06 | F-VALIDATION-TIMING-01 — No re-validation upon type change | Section "Re-validation during type change" added in § Validation. Snippet `_on_type_change_internal()`. New line in Error Handling Matrix. | Adversarial review |
| 2026-06-06 | F-EXPORT-OVERWRITE-01 — Undocumented silent overwrite | Line added in Error Handling Matrix: app convention documented. | Adversarial review |
| 2026-06-06 | /doc-update — Stale deep links | `_TYPE_LABEL_MAP` → `_TILED_TYPE_MAP`+`_MOD_TYPE_MAP`, `_on_type_change` → `_on_type_change_internal`. Added deep links `_validate_resize_dimensions`, `_convert_resize`, `_export_resize`, `test_resize_logic.py`. Re-validation snippet corrected (`_validate_resize_dimensions` vs `_validate_dimensions`). | HARDEN /doc-update |
