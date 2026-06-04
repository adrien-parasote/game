# Autotile Converter Spec — RPG Maker → Tiled

> Document Type: Implementation
> **Covers:** F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, F13
> **Blueprint:** [autotile_converter_blueprint.md](../strategic/autotile_converter_blueprint.md#strategic-blueprint--autotile-converter-rpg-maker--tiled)
> **Research:** [animated_autotiles.md](../../docs/research/animated_autotiles.md#research-animated-autotiles-conversion)

---

## Blueprint Coverage Matrix

| Feature ID | Description | Spec section |
|---|---|---|
| F1 | File picker — load PNG, validate format | `gui/app.py § File Loading` |
| F2 | Mode selector — XP / MV / MZ | `gui/app.py § Mode Selection` |
| F3 | Input preview — display source image | `gui/app.py § Preview Panels` |
| F4 | Conversion engine — XP + MV lookup tables | `converter_xp.py` + `converter_mv.py` |
| F5 | Output preview — 47-tile sheet display | `gui/app.py § Preview Panels` |
| F6 | Canvas validator — 5×5 test pattern | `gui/app.py § Canvas Validator` |
| F7 | Export — PNG + TSX one-click | `tsx_generator.py` + `gui/app.py § Export` |
| F8 | Auto-detect MV tile size (32px vs 48px) | `converter_mv.py § detect_tile_size` |
| F9 | Animation mode selection (Statique / Horizontale / Verticale) | `gui/app.py § Animation Selection` |
| F10| Animation speed selector (configurable loop speed) | `gui/app.py § Animation Selection` |
| F11| Canvas animation loop (real-time canvas ticks) | `gui/app.py § Canvas Animation Loop` |
| F12| Multi-frame TSX generator (writes local offsets and frames) | `tsx_generator.py` |
| F13| Waterfall converter (translates 4 waterfall shapes to 47-tile blob) | `converter_mv.py § Waterfall Conversion` |

---

## Deep Links

- [Blueprint § Success Metrics](../strategic/autotile_converter_blueprint.md#2-success-metrics)
- [Blueprint § Core Architecture Decisions](../strategic/autotile_converter_blueprint.md#4-core-architecture-decisions)
- [Research § Domain Context](../../docs/research/animated_autotiles.md#axis-1-domain-context)
- [Research § Tiled Animation Format](../../docs/research/animated_autotiles.md#tiled-animation-format-tsx)
- [ADR-005 § Cycle Rules](../ADRs/ADR-005-animated-autotile-tileset-layout.md#cycle-rules)

---

## Assumptions

| # | Assumption | Risk | Source Type | Status |
|---|---|---|---|---|
| A1 | XP input always 96×128 px | Low | SHOW | VERIFIED |
| A2 | MV/MZ input = extracted single autotile block | Low | SHOW | VERIFIED |
| A3 | MV tile_size = block_width // 2 (64→32, 96→48) | Low | SHOW | VERIFIED |
| A4 | XP sub-tile lookup table is deterministic and fixed | Medium | SHOW | VERIFIED |
| A5 | MV sub-tile lookup table is deterministic and fixed | Medium | SHOW | VERIFIED |
| A6 | TSX wangset type="mixed" works in Tiled 1.10+ | Low | SHOW | VERIFIED |
| A7 | MZ uses identical autotile block format to MV | Low | TELL | ASSUMED |
| A8 | tkinter Canvas widget handles 47 tile PhotoImages | Low | SHOW | VERIFIED |
| A9 | Tiled handles animated tiles cleanly via `<animation>` tags | Low | SHOW | VERIFIED |
| A10| Waterfalls animate vertically by stacking 3 frames of height 1 tile | Medium | SHOW | VERIFIED |
| A11| 4-frame animation formats loop linearly from 0 to 3 | Low | SHOW | VERIFIED |

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Validate input image dimensions before conversion. Use Pillow for all image ops. Output PNG as RGBA. Run tests before any commit. |
| **Ask first** | Adding dependencies beyond Pillow + customtkinter + stdlib. Changing output tile size or sheet layout. Modifying the TSX wangid mapping order. |
| **Never do** | Mutate the source image (always work on copies). Hardcode output paths (use user-selected dir). Put image processing logic inside `gui/app.py`. Skip input validation. |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `tools/src/asset_convertor/core/converter_xp.py` | Python Module | This spec § `converter_xp.py` | `gui/app.py` |
| `tools/src/asset_convertor/core/converter_mv.py` | Python Module | This spec § `converter_mv.py` | `gui/app.py` |
| `tools/src/asset_convertor/exporters/tsx_generator.py` | Python Module | This spec § `tsx_generator.py` | `gui/app.py` |
| `tools/src/asset_convertor/gui/app.py` | Python Module | This spec § `gui/app.py` | `tools/src/asset_convertor/__main__.py` |
| `tools/src/output/{name}.png` | PNG image | This spec § Output Format | Tiled editor |
| `tools/src/output/{name}.tsx` | TSX XML | This spec § TSX Format | Tiled editor |
| `tests/tools/asset_convertor/test_converter_xp.py` | Python Test | This spec § Test Cases | Pytest |
| `tests/tools/asset_convertor/test_converter_mv.py` | Python Test | This spec § Test Cases | Pytest |
| `tests/tools/asset_convertor/test_tsx_generator.py` | Python Test | This spec § Test Cases | Pytest |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/src/input/*.png` | PNG image | This spec § Input Validation | User |
| `tools/src/asset_convertor/core/minimap.py` | Python Module | asset_convertor_spec.md § Modules | asset_convertor_spec |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Python function | `convert_xp(img: Image, is_animated: bool = False, animation_mode: str = "Horizontale") -> list[list[Image]]` | This spec § `converter_xp.py` |
| Python function | `convert_mv(img: Image, is_animated: bool = False, animation_mode: str = "Horizontale") -> list[list[Image]]` | This spec § `converter_mv.py` |
| Python function | `detect_tile_size(img: Image) -> int` | This spec § `converter_mv.py` |
| Python function | `export(tiles_by_frame: list[list[Image]], name: str, output_dir: str, tile_size: int, is_animated: bool = False, animation_mode: str = "Horizontale", duration: int = 150) -> tuple[str, str]` | This spec § `tsx_generator.py` |

### External Invocations

N/A — this spec invokes no external interfaces beyond the Python stdlib and Pillow.

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| 47-tile blob bitmask | Produced (output tileset) | asset_convertor_spec.md (canvas autotile mode) |
| minimap.py bitmask engine | Consumed (canvas validator) | asset_convertor_spec.md |

---

## Bundling & Native-Module Audit

- BM1: N/A — not a bundled framework project
- BM2: N/A — no client/server split
- BM3: N/A — no native modules introduced (Pillow is pure Python + C but no gyp)
- BM4: N/A — no constant renames in this spec

---

## Architecture Overview

```
tools/src/asset_convertor/
├── core/
│   ├── converter_xp.py     [MODIFY] XP sub-tile assembly → 47 PIL Images per frame
│   ├── converter_mv.py     [MODIFY] MV/MZ sub-tile assembly → 47 PIL Images per frame
│   └── minimap.py          [EXISTING] bitmask engine (consumed by canvas)
├── exporters/
│   └── tsx_generator.py    [MODIFY] PNG sheet + TSX animation nodes writer
└── gui/
    └── app.py              [MODIFY] customtkinter GUI with mode/speed dropdowns and Tk.after animation tick
```

### Data Flow

```
User selects file + mode + animation + speed
        │
        ▼
validate_input(img, mode, animation)
        │
        ▼
[XP mode] converter_xp.convert_xp(img, animation)
[MV/MZ]   converter_mv.convert_mv(img, animation)
        │
        ▼
list[list[PIL.Image]] — N frames of 47 tiles
  └── tile_size = frames[0][0].width   ← ALWAYS index [frame][tile], never [frame].width
        │
        ├──► Canvas: Tkinter.after tick cycles frame index → draw 5×5 pattern (F11)
        └──► Export:
                 ├── assemble_sheet() → PNG stacked vertically (8 cols × 6*N rows)
                 └── generate_tsx()  → TSX wangset XML with <animation> nodes (F12)
```

---

## Module Specifications

### `core/converter_xp.py`

**Covers:** F4 (XP conversion), F9 (Animation mode)

#### Responsibilities
- Accept an RGBA PIL Image and an animation mode string.
- Detect frame count based on the width relative to the standard 96x128 block size.
- Crop each horizontal frame, compile its 47 transition tiles using the XP lookup table.
- Return `list[list[PIL.Image]]` containing a list of 47 tiles for each frame.

#### Input Contract & Slicing
```python
def convert_xp(img: Image.Image, is_animated: bool = False, animation_mode: str = "Horizontale") -> list[list[Image.Image]]:
    """
    Args:
        img: RGBA PIL Image.
        is_animated: True if animated autotile conversion is requested.
        animation_mode: "Horizontale" or "Verticale".
    """
```
- **If `is_animated` is False:**
  - Width must be 96 px, height 128 px. Returns 1 frame.
- **If `is_animated` is True:**
  - If `animation_mode` is `Verticale`: not supported for XP. Raises a `ValueError`.
  - If `animation_mode` is `Horizontale`: width must be a multiple of 96 (e.g. 288 for 3 frames, 384 for 4 frames). Height must be 128 px. Slice width into $N = \text{width} // 96$ frames of size 96x128. Convert each separately.

---

### `core/converter_mv.py`

**Covers:** F4 (MV conversion), F8 (auto-detect tile size), F9 (Animation mode), F13 (Waterfall conversion)

#### Slicing Rules & Input Validation

```python
def convert_mv(img: Image.Image, is_animated: bool = False, animation_mode: str = "Horizontale") -> list[list[Image.Image]]:
```

- **If `is_animated` is False:**
   - Width $W$ must be 64 or 96. Height $H$ must be $W \times 1.5$ (96 or 144).
   - Tile size $T = W // 2$.
   - Returns 1 frame of 47 tiles.
- **If `is_animated` is True:**
   - If `animation_mode` is `Horizontale`:
     - Height $H$ must be 96 or 144. Tile size $T = H // 3$.
     - Width $W$ must be a multiple of $2T$ ($6T$ for 3 frames, $8T$ for 4 frames).
     - Returns $N = W // (2T)$ frames. Each frame is converted using the standard floor autotile logic on its corresponding $2T \times 3T$ crop.
   - If `animation_mode` is `Verticale`:
     - Width $W$ must be 64 or 96. Tile size $T = W // 2$.
     - Height $H$ must be a multiple of $T$ ($3T$ for 3 frames, $4T$ for 4 frames).
     - Returns $N = H // T$ frames.
     - Slicing: frame $f$ is cropped at $x \in [0, 2T]$ and $y \in [f \times T, (f+1) \times T]$.
     - Conversion: each frame is 2 tiles wide × 1 tile high ($2T \times T$ px). Convert using the waterfall lookup rules described below.

#### Waterfall Conversion Algorithm
For each of the 3 or 4 frames, extract 4 quadrants using `Tilemap.WATERFALL_AUTOTILE_TABLE` coordinates:
- Shape 0 (Center): `[[2,0],[1,0],[2,1],[1,1]]`
- Shape 1 (Left Edge): `[[0,0],[1,0],[0,1],[1,1]]`
- Shape 2 (Right Edge): `[[2,0],[3,0],[2,1],[3,1]]`
- Shape 3 (Isolated): `[[0,0],[3,0],[0,1],[3,1]]`

Assemble a 47-tile blob sheet using these 4 shapes. Map the shapes to the 47 bitmasks based on horizontal neighbor presence:
- Check if bitmask has East neighbor (bit 16) and West neighbor (bit 8):
  - **No West and No East:** use Shape 3.
  - **West but No East:** use Shape 2.
  - **East but No West:** use Shape 1.
  - **Both West and East:** use Shape 0.

---

### `exporters/tsx_generator.py`

**Covers:** F7 (export), F12 (Multi-frame TSX generator)

#### Stacking Format
The generated PNG sheet will stack frames vertically. The dimensions will be:
- Width: $8 \times \text{tile\_size}$
- Height: $6 \times N \times \text{tile\_size}$ (where $N$ is the number of frames)

```python
def assemble_sheet(tiles_by_frame: list[list[Image.Image]], tile_size: int) -> Image.Image:
    """
    Args:
        tiles_by_frame: list of N frames, each containing 47 tiles.
    """
```
Pastes tiles from frame $f$ starting at $y = f \times 6 \times \text{tile\_size}$. Slot 47 of each frame (last cell of the 8x6 grid) is kept transparent.

#### TSX Animation XML Generation
For `is_animated == True`, the XML will contain `<animation>` definitions for each tile `i` from 0 to 46:
```xml
  <tile id="{i}">
    <animation>
      <!-- Generated based on loop patterns -->
      <frame tileid="{frame0_id}" duration="{duration}"/>
      ...
    </animation>
  </tile>
```

#### Loop Sequences (ADR-005):
- **3-frame ping-pong** (Horizontale 3-frame): frame sequence `0 → 1 → 2 → 1`
  - `<frame tileid="i" duration="D"/>`
  - `<frame tileid="i + 48" duration="D"/>`
  - `<frame tileid="i + 96" duration="D"/>`
  - `<frame tileid="i + 48" duration="D"/>`
- **3-frame linear** (Verticale 3-frame): frame sequence `0 → 1 → 2`
  - `<frame tileid="i" duration="D"/>`
  - `<frame tileid="i + 48" duration="D"/>`
  - `<frame tileid="i + 96" duration="D"/>`
- **4-frame linear** (4-frame Horizontale/Verticale): frame sequence `0 → 1 → 2 → 3`
  - `<frame tileid="i" duration="D"/>`
  - `<frame tileid="i + 48" duration="D"/>`
  - `<frame tileid="i + 96" duration="D"/>`
  - `<frame tileid="i + 144" duration="D"/>`

---

### `gui/app.py`

**Covers:** F1, F2, F3, F5, F6, F7, F9, F10, F11

#### Animation Mode Selection (F9, F10)
- Add a checkbox `Autotile Animé` (`ctk.CTkCheckBox`):
  - Label: "Autotile Animé"
  - Default state: Unchecked (not animated)
- Add dropdown for `Type d'animation` (`ctk.CTkOptionMenu`):
  - Label: "Type d'animation"
  - Values: `Horizontale (Eau/Sol)`, `Verticale (Cascade)`
  - Default: `Horizontale (Eau/Sol)`
  - Enabled only when `Autotile Animé` is checked. Otherwise disabled/grayed out.
- Add dropdown for `Vitesse` (`ctk.CTkOptionMenu`):
  - Label: "Vitesse"
  - Values: `100 ms`, `150 ms`, `200 ms`, `300 ms`, `500 ms`
  - Default: `150 ms`
  - Enabled only when `Autotile Animé` is checked. Otherwise disabled/grayed out.

#### Real-time Canvas Animation Loop (F11)
- If `Autotile Animé` is checked:
  - Launch a looping Tkinter timer using `self.after(duration, self._tick_animation)` on convert success.
  - Keep track of `self._current_frame_idx` according to cycle rules:
    - 3-frame ping-pong: `[0, 1, 2, 1]` index list.
    - 3-frame linear: `[0, 1, 2]` index list.
    - 4-frame linear: `[0, 1, 2, 3]` index list.
  - In `_tick_animation`, increment step, update frame index, and request canvas repaint.
  - Pass the active frame's 47 tiles (`tiles_by_frame[frame_idx]`) to `_redraw_canvas_grid` for rendering.
- Cancel the active timer when loading a new file or changing modes.

---

## Error Handling Matrix

| Error | Trigger | User-visible message (French) | Recovery |
|---|---|---|---|
| File not found | path deleted after picker | "Fichier introuvable : {path}" | Reset to initial state |
| Wrong dimensions for mode | Image size mismatch | "Format {mode} ({anim_mode}) invalide. Attendu: {expected}, obtenu: {w}×{h}" | Block Convert button, keep UI active |
| Corrupted PNG | PIL fails to open | "Impossible de lire l'image. Vérifiez que le fichier est un PNG valide." | Reset file picker |
| Conversion error | Bug in lookup table | "Erreur de conversion : {error}. Vérifiez le format de l'autotile." | Show error in red, keep source display |
| Output dir not writable | Permission denied | "Impossible d'écrire dans {dir}. Choisissez un autre dossier." | Open dir picker |
| tiles != 47 per frame | Internal bug | "Erreur interne : {n} tiles générées au lieu de 47 pour la frame {f}." | Show error, block export |

### UI Error & Empty States
- **Loading State:** Not applicable (instant conversion).
- **Error State:** Status bar turns red (`#ff6b6b`).
- **Empty State:** Preview panels show "Aucun autotile chargé".
- **Empty Output State:** Tiled Output panel shows "Aucune conversion".

---

## Anti-Patterns

| # | Anti-Pattern | Why It's Wrong | Do Instead |
|---|---|---|---|
| AP-01 | Putting image processing in `gui/app.py` | Untestable, GUI-coupled. | Keep all pixel operations in `core/converter_*.py`. GUI only calls and displays. |
| AP-02 | Hardcoding output path to `tools/src/output/` | Breaks for users in other directories. | Default = `tools/src/output/`, user can override via dir picker. |
| AP-03 | Mutating the source PIL Image | Side effects corrupt re-conversions. | Always `img.copy()` before any crop/paste. |
| AP-04 | Using `Image.BILINEAR` for preview scaling | Blurs pixel art. | Always `Image.NEAREST` for integer scaling of tile graphics. |
| AP-05 | Using wrong wangset type in TSX | `type="edge"` → only 4 directions, no corners. Broken terrain brush. | `type="mixed"` for 47-tile blob. |
| AP-06 | Hardcoding tile_size=32 in MV converter | Breaks for official 48px MV packs. | Always call `detect_tile_size(img)` first. |
| AP-07 | Stacking animation frames horizontally in PNG | Breaks Tiled standard column width assumptions. | Stack frames vertically (8 columns, $6 \times N$ rows) as defined in ADR-005. |
| AP-08 | Using 48-shape lookup table for waterfalls | Waterfalls only tile horizontally. Standard table contains N/S outer/inner corners, which waterfalls lack. | Use `Tilemap.WATERFALL_AUTOTILE_TABLE` and map to 47 blob tiles based on West/East neighbors. |
| AP-09 | Infinite recursion in Tkinter timer ticks | Ticking without canceling old loops creates multiple concurrent timers, causing CPU spike and UI flickering. | Always cancel the old timer using `self.after_cancel()` before starting a new one. |
| AP-10 | Hardcoding 3 frames for all animation modes | Horizontale can have 4 frames, and waterfalls could have 4 frames. | Auto-detect frame count dynamically from width/height and cycle accordingly. |
| AP-11 | Reading `tiles[0].width` after `convert_mv` | Both `convert_xp` and `convert_mv` always return `list[list[Image]]`. `tiles[0]` is a frame (a list), not an Image — calling `.width` crashes at runtime. | Always index `tiles[0][0].width` to reach the first tile of the first frame. |

---

## Test Case Specifications

### Unit Tests — `test_converter_xp.py`

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-001 | `convert_xp` static returns 1 frame | `sample_xp.png`, `is_animated=False` | `len(result) == 1` and `len(result[0]) == 47` |
| TC-002 | `convert_xp` animated horizontal | 288x128 image, `is_animated=True` | `len(result) == 3`, each frame has 47 tiles |
| TC-003 | `convert_xp` animated vertical raises error | 96x128 image, `is_animated=True`, mode vertical | `ValueError` raised |
| TC-004 | `convert_xp` invalid dimensions raise error | 100x128 image | `ValueError` raised |
| TC-005 | `convert_xp` does not mutate source | `sample_xp.png` | Source image pixels remain identical |

### Unit Tests — `test_converter_mv.py`

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-006 | `convert_mv` static returns 1 frame | `sample_mv_32px.png`, `is_animated=False` | `len(result) == 1` and `len(result[0]) == 47` |
| TC-007 | `convert_mv` 3-frame horizontal water | 192x96 image, `is_animated=True`, mode Horizontale | `len(result) == 3` frames, each frame has 47 tiles |
| TC-008 | `convert_mv` 4-frame horizontal water | 256x96 image, `is_animated=True`, mode Horizontale | `len(result) == 4` frames |
| TC-009 | `convert_mv` 3-frame vertical waterfall | 64x96 image, `is_animated=True`, mode Verticale | `len(result) == 3` frames, tile width=32 |
| TC-010 | `convert_mv` waterfall horizontal mapping | 64x96 image, `is_animated=True`, mode Verticale | Shapes correctly mapped to 47 blob bitmasks (verified mapping) |
| TC-011 | `convert_mv` invalid sizes raise error | 80x96 image | `ValueError` raised |

### Unit Tests — `test_tsx_generator.py`

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-012 | `assemble_sheet` stacked vertical height | 3 frames of 47 tiles (32px) | Height is 576 px, width is 256 px |
| TC-013 | `generate_tsx` animated includes XML animation nodes | 3 frames of 47 tiles, name="water", size=32, `is_animated=True`, horizontal mode | XML has `<animation>` tags under `<tile>` |
| TC-014 | `generate_tsx` ping-pong cycle verification | 3 frames of 47 tiles, `is_animated=True`, horizontal mode | Node has 4 frames: offset 0, 48, 96, 48 |
| TC-015 | `generate_tsx` linear loop verification | 3 frames of 47 tiles, `is_animated=True`, vertical mode | Node has 3 frames: offset 0, 48, 96 |
| TC-016 | `generate_tsx` static has no animation nodes | 1 frame of 47 tiles, `is_animated=False` | XML does not contain `<animation>` elements |

### Integration Tests — `tests/tools/asset_convertor/test_converter_integration.py`

| ID | Test | Scenario | Expected |
|---|---|---|---|
| IT-001 | MV Animated water conversion and export | Load 192x96 px water → `is_animated=True`, horizontal mode → export | PNG stacked sheet 256x576 + TSX with 47 animation loops |
| IT-002 | MV Waterfall conversion and export | Load 64x96 px waterfall → `is_animated=True`, vertical mode → export | PNG stacked sheet 256x576 + TSX with 3-frame linear loops |
| IT-003 | GUI timer tick animation cycle | Start conversion → check `self._current_frame_idx` ticks over 150ms | `0 → 1 → 2 → 1` index loops correctly |
| IT-004 | Mode change cancels animation timer | Conversion active → change format dropdown | Animation loop cancelled, timer reference reset to None |


---

## Project File Tree

Files managed by this specification:

```
tools/
  src/
    asset_convertor/
      core/
        converter_xp.py         [MODIFY] XP autotile frame parsing & lookup
        converter_mv.py         [MODIFY] MV autotile frame parsing & waterfall mappings
      exporters/
        tsx_generator.py        [MODIFY] Vertically stacked sheet & XML animation loops writer
      gui/
        app.py                  [MODIFY] customtkinter GUI with mode/speed OptionMenus & Tk.after timer
    input/
      sample_xp.png             [EXISTING] XP sample (96x128 px)
      sample_mv_32px.png        [EXISTING] MV sample (64x96 px, tile_size=32)
      sample_mv_48px.png        [EXISTING] MV sample (96x144 px, tile_size=48)
    output/
      .gitkeep                  [EXISTING] keep output dir in git
  docs/
    specs/
      autotile_converter_spec.md  [THIS FILE]
tests/
  tools/
    asset_convertor/
      test_converter_xp.py      [MODIFY] Add unit tests for XP animated inputs
      test_converter_mv.py      [MODIFY] Add unit tests for MV animated & waterfall inputs
      test_tsx_generator.py     [MODIFY] Add unit tests for vertical stacking and TSX loops
      test_converter_integration.py  [MODIFY] Add integration tests for GUI timer and full export
```
