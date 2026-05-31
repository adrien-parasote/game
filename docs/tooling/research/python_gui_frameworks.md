# Research: Python GUI Frameworks for Tileset/Texture Generation Tool

> **Date:** 2026-05-31
> **Context:** Asset Creator Tool (`tools/asset_creator/`) currently uses Pygame-CE for preview-only display. Need a proper GUI toolkit with sliders, buttons, file browsers, and real-time PIL image preview for a 32×32 pixel art tileset generator.
> **Decision:** Adopt / Adapt / Build-New

---

## Executive Summary

**Recommendation: ADOPT [Dear PyGui](https://github.com/hoffstadt/DearPyGui)**

Dear PyGui is the optimal framework for this tool. Its GPU-accelerated raw texture API provides zero-overhead real-time preview of PIL Images. Built-in float sliders, color pickers, and file dialogs cover every parameter in the existing `TextureParams` dataclass. MIT licensed, pip-installable, lightweight, works natively on macOS ARM via Metal.

**Fallback: ADAPT PySide6** if Dear PyGui's maintenance-mode status becomes a blocker or if complex desktop UI features (docking, menus, undo/redo stacks) are needed later.

---

## Requirements Matrix

| Requirement | Weight | Description |
|-------------|--------|-------------|
| R1: Live image preview | Critical | Display PIL/Pillow RGBA images, update in real-time as parameters change |
| R2: Slider controls | Critical | Float sliders (scale, persistence), int sliders (octaves, seed), with callbacks |
| R3: Buttons | High | Trigger generation, export, regenerate minimap |
| R4: File browser | High | Select output directory for PNG/TSX export |
| R5: macOS compatibility | Critical | Must work on macOS ARM (Apple Silicon) |
| R6: Modern look | Medium | Dark mode, professional appearance — not 90s Tk widgets |
| R7: Python 3.12+ | Critical | Project targets `py312` (see `pyproject.toml`) |
| R8: Low install complexity | Medium | `pip install` only, no system deps or Xcode toolchains |
| R9: Licensing | Medium | Permissive for personal/open-source game project |
| R10: Learning curve | Low | Solo dev project, minimize ramp-up time |

---

## Frameworks Evaluated

### 1. Dear PyGui

| Attribute | Detail |
|-----------|--------|
| **Version** | 1.x (maintenance mode, active bug fixes) |
| **GitHub Stars** | ~15,500 |
| **License** | MIT |
| **Rendering** | GPU-accelerated (Metal on macOS, DirectX/OpenGL on others) |
| **Architecture** | Immediate-mode (Dear ImGui-based), exposed as retained-mode Python API |
| **Install** | `pip install dearpygui` — lightweight, minimal dependencies |
| **macOS ARM** | ✅ Native support via Metal backend, pre-built wheels |
| **Python 3.12+** | ✅ Supported |
| **Maintenance** | Maintenance mode — bug fixes only. Successor "Pilot Light UI" in development |

#### Image Display

Dear PyGui provides the best image display pipeline for this use case:

```python
# Convert PIL Image → Dear PyGui raw texture
import numpy as np
from PIL import Image

pil_image = Image.new("RGBA", (32, 32))  # Your generated tile
img_data = np.array(pil_image, dtype=np.float32) / 255.0
raw_data = img_data.ravel()

# Register once
with dpg.texture_registry():
    dpg.add_raw_texture(width=32, height=32, default_value=raw_data,
                        format=dpg.mvFormat_Float_rgba, tag="preview")

# Update: modify raw_data array in-place → texture updates automatically
```

**Key advantage:** Raw textures bind directly to a numpy buffer. Modify the buffer → GPU texture updates on next frame. No conversion overhead, no garbage collection issues, no base64 encoding.

#### Widget Coverage

| Widget Need | Dear PyGui Widget | Notes |
|-------------|-------------------|-------|
| Float slider | `add_slider_float()` | `min_value`, `max_value`, `callback` |
| Int slider | `add_slider_int()` | Same API |
| Color picker | `add_color_picker()` | RGB/HSV/HEX, alpha bar optional |
| Dropdown | `add_combo()` | Texture type selector |
| Button | `add_button()` | Generate, export, regenerate |
| File dialog | `add_file_dialog()` | Built-in with extension filters |
| Text input | `add_input_text()` | Filename, seed input |
| Checkbox | `add_checkbox()` | Toggle V1/V2, dithering, smooth ramp |

#### Look & Feel

- Dark theme by default (Dear ImGui style — looks like a game engine tool)
- Themeable: colors, fonts, rounding, spacing all configurable
- Game-dev aesthetic is *ideal* for a gamedev asset tool
- No native OS widgets — consistent look across platforms

#### Concerns

- **Maintenance mode**: Active bug fixes only, no new features. Successor "Pilot Light UI" being developed. Risk: if a critical bug is found, fix timeline is uncertain.
- **Not traditional desktop**: No menu bars, no native file dialogs (uses own rendered ones), no system tray. Fine for a tool, problematic for a full application.
- **Community**: Smaller than Qt ecosystem, fewer tutorials and Stack Overflow answers.

#### Score: 9/10 for this use case

---

### 2. PySide6 (Qt for Python)

| Attribute | Detail |
|-----------|--------|
| **Version** | 6.x (actively maintained by The Qt Company) |
| **GitHub Stars** | Part of Qt ecosystem (~100k+ combined) |
| **License** | LGPLv3 — free for commercial closed-source use |
| **Rendering** | Retained-mode, CPU-based with optional OpenGL acceleration |
| **Install** | `pip install PySide6` — large (~500MB-1GB installed) |
| **macOS ARM** | ✅ Native Apple Silicon wheels |
| **Python 3.12+** | ✅ Supported |
| **Maintenance** | Actively maintained by The Qt Company |

#### Image Display

```python
from PIL import Image, ImageQt
from PySide6.QtGui import QPixmap

pil_image = Image.new("RGBA", (32, 32))
qimage = ImageQt.ImageQt(pil_image)
pixmap = QPixmap.fromImage(qimage)
label.setPixmap(pixmap)  # Update QLabel
```

**Note:** Import PySide6 *before* PIL to ensure `ImageQt` detects the correct Qt backend. The `ImageQt` → `QPixmap` conversion adds overhead per frame but is negligible for 32×32 images.

#### Widget Coverage

| Widget Need | PySide6 Widget | Notes |
|-------------|----------------|-------|
| Float slider | `QSlider` + `QDoubleSpinBox` | QSlider is int-only; need wrapper for floats |
| Int slider | `QSlider` / `QSpinBox` | Native |
| Color picker | `QColorDialog` | System-native dialog |
| Dropdown | `QComboBox` | Full-featured |
| Button | `QPushButton` | Standard |
| File dialog | `QFileDialog` | Native OS file picker |
| Text input | `QLineEdit` | Full-featured |
| Checkbox | `QCheckBox` | Standard |

#### Look & Feel

- Native look by default (follows macOS system theme)
- Highly customizable via Qt Style Sheets (QSS)
- Dark mode via third-party: `pyqtdarktheme` (auto-syncs with macOS dark mode), `qt-material` (Material Design)
- Professional appearance — used in VFX, CAD, scientific software

#### Concerns

- **Heavy**: ~500MB-1GB installed footprint. Overkill for a parameter-tweaking tool.
- **Learning curve**: Signal/slot architecture, QObject hierarchy, layout managers — significant ramp-up.
- **Float sliders**: QSlider is integer-only. Need custom wrapper or QDoubleSpinBox pairing for float parameters like `scale: 0.15`.
- **Complexity**: Thread safety with QThread for heavy generation, signal/slot wiring for reactive updates.

#### Score: 7/10 for this use case (overkill, but best fallback)

---

### 3. CustomTkinter

| Attribute | Detail |
|-----------|--------|
| **Version** | 5.x |
| **GitHub Stars** | ~13,400 |
| **License** | MIT |
| **Rendering** | Tkinter-based (Tk canvas) |
| **Install** | `pip install customtkinter` — lightweight |
| **macOS ARM** | ✅ Works (Tk ships with Python) |
| **Python 3.12+** | ✅ Supported (fixed in 5.2.1) |
| **Maintenance** | ⚠️ Slowing — community concerns about responsiveness |

#### Image Display

```python
from PIL import Image
import customtkinter as ctk

pil_image = Image.new("RGBA", (32, 32))
ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(256, 256))
label = ctk.CTkLabel(root, image=ctk_image, text="")
# Update: label.configure(image=new_ctk_image)
```

**Note:** `CTkImage` handles HiDPI scaling. For real-time updates, must create a new `CTkImage` object each time → garbage collection pressure. Use `root.after()` for scheduling updates.

#### Widget Coverage

| Widget Need | CustomTkinter Widget | Notes |
|-------------|----------------------|-------|
| Float slider | `CTkSlider` | `from_`, `to`, `command` callback |
| Int slider | `CTkSlider` | Same (float-based, round to int) |
| Color picker | ❌ None built-in | Must use `tkinter.colorchooser` or third-party |
| Dropdown | `CTkOptionMenu` / `CTkComboBox` | Available |
| Button | `CTkButton` | Modern look |
| File dialog | `tkinter.filedialog` | Standard Tk file dialog |
| Checkbox | `CTkCheckBox` | Available |

#### Look & Feel

- Modern dark theme by default — significant improvement over vanilla Tk
- Three built-in color themes: blue, green, dark-blue
- System appearance mode support (Dark/Light/System)
- Limited customization compared to Qt or Dear PyGui

#### Concerns

- **Maintenance**: Development has slowed significantly. Merge activity for PRs is limited.
- **Performance**: Tk canvas is CPU-bound. Creating new `CTkImage` objects for each preview update is slower than GPU-backed solutions.
- **No color picker**: Missing a built-in color picker widget — critical for palette editing.
- **Underlying Tk limitations**: Complex layouts are harder, no advanced widget features.

#### Score: 5/10 for this use case

---

### 4. Flet

| Attribute | Detail |
|-----------|--------|
| **Version** | 1.x |
| **License** | Apache 2.0 |
| **Rendering** | Flutter-based (Dart runtime) |
| **Install** | `pip install flet` — requires Rosetta 2 for some build tools |
| **macOS ARM** | ✅ Supported (universal binaries) |
| **Python 3.12+** | ✅ Supported |

#### Image Display

```python
# Must convert PIL → base64 string for every update
buffered = BytesIO()
pil_image.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
image_control.src_base64 = img_str
image_control.update()
```

**Critical flaw for this use case:** Every image update requires PIL → PNG encode → base64 encode → string transfer. For real-time slider-driven preview, this adds significant latency compared to GPU-backed or direct memory approaches.

#### Score: 4/10 (base64 overhead is a dealbreaker for real-time preview)

---

### 5. Kivy

| Attribute | Detail |
|-----------|--------|
| **License** | MIT |
| **Best for** | Touch/mobile applications |
| **macOS ARM** | ✅ Supported |

**Rejected:** Touch-oriented framework. No standard desktop widgets (sliders, file dialogs must be custom-built). Steep learning curve for desktop-style parameter tools. Custom rendering engine means non-native feel.

#### Score: 2/10

---

### 6. wxPython

| Attribute | Detail |
|-----------|--------|
| **License** | wxWindows Library License (permissive) |
| **Best for** | Traditional native desktop apps |
| **macOS ARM** | ✅ Supported |

**Rejected:** Native widgets but dated appearance. No advantage over PySide6 for this use case. Smaller community than Qt. Verbose API.

#### Score: 3/10

---

### 7. Toga (BeeWare)

| Attribute | Detail |
|-----------|--------|
| **License** | BSD |
| **Best for** | Cross-platform native apps (including mobile) |
| **macOS ARM** | ✅ Native Cocoa backend |

**Rejected:** Limited widget set — missing color pickers, advanced sliders. Still maturing. No built-in support for real-time image texture display. Better suited for simple mobile-first apps.

#### Score: 2/10

---

### 8. NiceGUI

| Attribute | Detail |
|-----------|--------|
| **License** | Apache 2.0 |
| **Best for** | Modern web-based dashboards |
| **macOS ARM** | ✅ (runs in browser) |

**Rejected:** Web-based architecture (`native=True` launches a browser window). Unnecessary overhead for a local desktop tool. Image updates go through WebSocket → browser rendering pipeline. Not suitable for real-time pixel-level preview.

#### Score: 3/10

---

## Comparison Matrix

| Criterion | Dear PyGui | PySide6 | CustomTkinter | Flet | Kivy | wxPython | Toga | NiceGUI |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **R1: Live preview** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ❌ | ⭐ | ⭐ | ❌ | ❌ |
| **R2: Sliders** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| **R3: Buttons** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **R4: File browser** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| **R5: macOS ARM** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **R6: Modern look** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| **R7: Python 3.12+** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **R8: Low install** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **R9: Licensing** | MIT | LGPL | MIT | Apache | MIT | wxWin | BSD | Apache |
| **R10: Learning curve** | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Overall score** | **9/10** | **7/10** | **5/10** | **4/10** | **2/10** | **3/10** | **2/10** | **3/10** |

Legend: ⭐ = basic, ⭐⭐ = good, ⭐⭐⭐ = excellent, ❌ = inadequate

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Dear PyGui enters end-of-life | Medium | API is stable; maintenance mode means no breaking changes. Successor "Pilot Light UI" is in development. If needed, migrate to PySide6 — the GUI layer is a thin wrapper over the existing generation core. |
| Dear PyGui file dialog is non-native | Low | Acceptable for a developer tool. The built-in dialog works, just doesn't match macOS Finder style. |
| Dear PyGui community smaller than Qt | Low | Documentation is comprehensive. API is simple enough that Stack Overflow coverage is less critical. |
| numpy dependency for image conversion | Low | numpy is standard in the Python ecosystem and likely already needed for image processing. |

---

## Migration Path from Pygame Preview

The current `tools/asset_creator/preview/pygame_preview.py` provides:
1. PIL Image → Pygame Surface conversion
2. Tileset strip display
3. Random minimap preview
4. SPACE to regenerate, ESC to quit

The new Dear PyGui GUI would **replace and extend** this:

| Current (Pygame) | New (Dear PyGui) |
|-------------------|-------------------|
| Static display only | Interactive parameter adjustment |
| No sliders/controls | Full slider panel for all `TextureParams` fields |
| PIL → Pygame Surface | PIL → numpy → raw texture (simpler, faster) |
| SPACE to regenerate | Button + automatic regeneration on slider change |
| No file selection | Built-in file dialog for output path |
| No terrain selection | Dropdown for terrain presets |
| 218 lines | Estimated ~300-400 lines for full GUI |

### Parameters to expose as GUI controls

From `TextureParams` dataclass:
- `texture_type` → Dropdown (`noise`, `solid`, `dithered`, `stippled`, `striped`)
- `scale` → Float slider (0.01 – 1.0)
- `octaves` → Int slider (1 – 8)
- `persistence` → Float slider (0.0 – 1.0)
- `lacunarity` → Float slider (1.0 – 4.0)
- `thresholds` → 3× float sliders (-1.0 – 1.0)
- `density` → Float slider (0.0 – 1.0)
- `use_smooth_ramp` → Checkbox
- `detail_scale` → Float slider (0.0 – 2.0)
- `detail_strength` → Float slider (0.0 – 0.5)
- `use_dithering` → Checkbox
- `dither_matrix_size` → Int slider (2, 4, 8)

From CLI args:
- `terrain` → Dropdown (from `get_builtin_presets()`)
- `seed` → Int input / slider
- `quality` → Radio (`v1` / `v2`)
- `output_dir` → File dialog
- `name` → Text input

---

## Decision

### ADOPT: Dear PyGui

**Rationale:**
1. **GPU-accelerated raw texture API** is a perfect match for real-time PIL image preview with zero conversion overhead
2. **Built-in widgets** (float sliders, color pickers, file dialogs) cover 100% of the parameter surface
3. **Lightweight** — minimal dependencies, fast startup, small install footprint
4. **Game-dev aesthetic** — dark theme by default, looks like professional game tooling
5. **Simple API** — no signal/slot ceremony, no layout managers, no QObject hierarchy
6. **MIT license** — no restrictions
7. **macOS ARM native** — Metal backend, pre-built wheels

**When to escalate to PySide6:**
- If the tool evolves into a full application with menu bars, docking panels, undo/redo stacks
- If Dear PyGui is officially deprecated without a viable successor
- If native OS file dialogs become a hard requirement

---

## Sources

| Source | Type | URL |
|--------|------|-----|
| Dear PyGui GitHub | Official repo | https://github.com/hoffstadt/DearPyGui |
| Dear PyGui Docs | Official docs | https://dearpygui.readthedocs.io |
| PySide6 Docs | Official docs | https://doc.qt.io/qtforpython-6/ |
| PythonGUIs | Comparison site | https://www.pythonguis.com |
| CustomTkinter GitHub | Official repo | https://github.com/TomSchimansky/CustomTkinter |
| Flet Docs | Official docs | https://flet.dev/docs/ |
| PyPI - dearpygui | Package registry | https://pypi.org/project/dearpygui/ |
| PyPI - PySide6 | Package registry | https://pypi.org/project/PySide6/ |
| PyQtDarkTheme | Theme library | https://pypi.org/project/pyqtdarktheme/ |
| Stackademic comparison | Blog analysis | https://blog.stackademic.com |
