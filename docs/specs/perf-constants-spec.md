> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

"""
Implementation Spec — Performance & Constants Hardening
Type: Implementation
Covers: P-PERF-01, P-CONST-01, P-FR-01
Strategy: docs/strategic/perf-constants-audit-strategy.md
-->

# Performance & Constants Hardening — Implementation Spec

## Document Type: Implementation

**Covers:** P-FR-01, P-CONST-01a/b/c/d/e, P-PERF-01a/b/c/d

## Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| A1 | `title_screen.py` halo caching (line 168) is already correct — not touched | Low | Confirmed via code read |
| A2 | `_blit_halo_text()` label text never changes while paused — safe to pre-render | Low | Labels come from i18n at init |
| A3 | `gaussian_blur` is pygame-CE only — fallback path (8-blit offsets) also cached | Low | Both branches pre-rendered |
| A4 | `I18nManager` is a singleton — constructing it once at `__init__` vs each frame is functionally equivalent | Low | Confirmed via `i18n.py` |
| A5 | All 647 tests pass without behavioral change — pure refactor | Medium | Run full test suite after |

---

## Feature P-FR-01 — Fix French comment

### File: `src/engine/game_state_manager.py`

**Line 133** — change:
```python
# Sauvegarder button — find first free slot
```
to:
```python
# Save button — find first free slot
```

---

## Feature P-CONST-01a — Lighting beam colors

### File: `src/engine/lighting_constants.py` — ADD

```python
# Day/night beam colorimetry
BEAM_COLOR_MOON: tuple[int, int, int] = (160, 180, 255)  # Cool moonlight tint
BEAM_COLOR_SUN: tuple[int, int, int] = (255, 248, 220)   # Warm sunlight tint
```

### File: `src/engine/lighting.py` — MODIFY

**Import** `BEAM_COLOR_MOON`, `BEAM_COLOR_SUN` from `lighting_constants`.

**Replace** in `_get_beam_surface_for_time()`:
```python
# BEFORE
color = self._lerp_color(
    (160, 180, 255),  # cool moonlight
    (255, 248, 220),  # warm sunlight (soft, not too yellow)
    b,
)
# AFTER
color = self._lerp_color(BEAM_COLOR_MOON, BEAM_COLOR_SUN, b)
```

---

## Feature P-CONST-01b — Dialogue colors

### File: `src/ui/dialogue_constants.py` — ADD

```python
# Text rendering colors (parchment theme)
DIALOGUE_SHADOW_COLOR: tuple[int, int, int] = (180, 170, 150)  # Light shadow on parchment
DIALOGUE_TEXT_COLOR: tuple[int, int, int] = (60, 40, 30)       # Dark brown, high contrast
```

### File: `src/ui/dialogue.py` — MODIFY

**Import** `DIALOGUE_SHADOW_COLOR`, `DIALOGUE_TEXT_COLOR` from `dialogue_constants`.

**Replace** in `__init__`:
```python
# BEFORE
self._shadow_color = (180, 170, 150)  # Light shadow for parchment
self._text_color = (60, 40, 30)       # Dark brown for high contrast on parchment
# AFTER
self._shadow_color = DIALOGUE_SHADOW_COLOR
self._text_color = DIALOGUE_TEXT_COLOR
```

---

## Feature P-CONST-01c — Chest draw constants

### File: `src/ui/chest_constants.py` — ADD

```python
from src.ui.ui_colors import COLOR_TEXT_STONE

# Draw constants
CHEST_TITLE_TEXT: str = "Chest"
CHEST_TEXT_COLOR: tuple[int, int, int] = COLOR_TEXT_STONE  # (60, 40, 30) — from ui_colors
CHEST_SLOT_FALLBACK_COLOR: tuple[int, int, int] = (200, 200, 200)
CHEST_INV_SLOT_FALLBACK_COLOR: tuple[int, int, int] = (180, 180, 180)
```

### File: `src/ui/chest_draw.py` — MODIFY

**Import** 4 new constants from `chest_constants`. Remove inline `(60, 40, 30)`, `(200, 200, 200)`, `(180, 180, 180)`, `"Chest"` literals.

**Move font init out of `_draw_title()`:**
- `_draw_title()` currently calls `pygame.font.Font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)` every frame.
- Add `_title_font: pygame.font.Font | None = None` to the mixin.
- Lazy-init with `if self._title_font is None: self._title_font = pygame.font.Font(...)` — initialized once on first draw, never again.

```python
def _draw_title(self: "ChestUIProtocol", screen: pygame.Surface) -> None:
    if self._title_rect is None:
        return
    if self._title_font is None:
        self._title_font = pygame.font.Font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
    surf = self._title_font.render(CHEST_TITLE_TEXT, True, CHEST_TEXT_COLOR)
    cx = self._title_rect.centerx + _TITLE_OFFSET_X
    cy = self._title_rect.centery + _TITLE_OFFSET_Y
    screen.blit(surf, surf.get_rect(center=(cx, cy)))
```

> **Anti-pattern**: Do NOT call `pygame.font.Font()` inside a draw method called at 60 FPS. Font objects are expensive to construct.

---

## Feature P-CONST-01d — Pause screen constants extension

### File: `src/ui/pause_screen_constants.py` — ADD

```python
# Cursor raw dimensions (source image px — used for scaling ratio)
CURSOR_RAW_H: int = 535
CURSOR_RAW_W: int = 309

# Fallback surface (error placeholder)
FALLBACK_SURF_SIZE: int = 32

# Panel fallback colors (when 02-panel_background.png fails to load)
PANEL_FALLBACK_FILL: tuple[int, int, int, int] = (10, 18, 22, 210)
PANEL_FALLBACK_BORDER: tuple[int, int, int] = (60, 80, 85)

# Font sizes
PAUSE_SUCCESS_FONT_SIZE: int = 26

# Button click zone dimensions
PAUSE_BTN_W: int = 280
PAUSE_BTN_H: int = 50

# Menu item colors
HOVER_TEXT_COLOR: tuple[int, int, int] = (180, 230, 255)
HOVER_HALO_COLOR: tuple[int, int, int] = (40, 120, 255)
SUCCESS_COLOR: tuple[int, int, int] = (180, 220, 150)

# Timers and layout
CONFIRM_DISPLAY_SECONDS: float = 2.0
CONFIRM_MSG_MARGIN_BOTTOM: int = 40
HALO_BLUR_PADDING: int = 24
HALO_BLUR_RADIUS: int = 8
```

### File: `src/ui/pause_screen.py` — MODIFY

Import all 14 new constants. Replace every inline literal.

**Key replacements:**
- `ratio = target_h / 535` → `ratio = target_h / CURSOR_RAW_H`
- `int(309 * ratio)` → `int(CURSOR_RAW_W * ratio)`
- `pygame.Surface((32, 32))` → `pygame.Surface((FALLBACK_SURF_SIZE, FALLBACK_SURF_SIZE))`
- `(10, 18, 22, 210)` → `PANEL_FALLBACK_FILL`
- `(60, 80, 85)` → `PANEL_FALLBACK_BORDER`
- Font size `26` → `PAUSE_SUCCESS_FONT_SIZE`
- `btn_w, btn_h = 280, 50` → `btn_w, btn_h = PAUSE_BTN_W, PAUSE_BTN_H`
- `(180, 230, 255), (40, 120, 255)` → `HOVER_TEXT_COLOR, HOVER_HALO_COLOR`
- `(180, 220, 150)` → `SUCCESS_COLOR`
- `2.0` → `CONFIRM_DISPLAY_SECONDS`
- `self._sh - 40` → `self._sh - CONFIRM_MSG_MARGIN_BOTTOM`
- `pad = 24` → `pad = HALO_BLUR_PADDING`
- `gaussian_blur(padded, 8)` → `gaussian_blur(padded, HALO_BLUR_RADIUS)`

---

## Feature P-CONST-01e — Save menu constants (new file)

### File: `src/ui/save_menu_constants.py` — NEW

```python
"""
SaveMenu UI constants — layout, colors, dimensions.
Spec: docs/specs/perf-constants-spec.md
"""
from src.ui.ui_colors import COLOR_TEXT_STONE

# ---------------------------------------------------------------------------
# SaveSlotUI — slot background card
# ---------------------------------------------------------------------------
SAVE_SLOT_BG_W: int = 427
SAVE_SLOT_BG_H: int = 200

# Hover halo on gem corners
SAVE_SLOT_HALO_RADIUS: int = 45
SAVE_SLOT_GEM_COORDS: list[tuple[int, int]] = [(26, 27), (413, 27), (26, 170), (414, 171)]

# Thumbnail sub-rect within the 427×200 card (px from card origin)
SAVE_THUMB_X: int = 56
SAVE_THUMB_Y: int = 59
SAVE_THUMB_SIZE: int = 82

# Fallback draw colors
SAVE_THUMB_BG_COLOR: tuple[int, int, int] = (20, 20, 20)
SAVE_THUMB_BORDER_COLOR: tuple[int, int, int] = (80, 80, 80)
SAVE_SLOT_FALLBACK_BG: tuple[int, int, int, int] = (30, 30, 30, 200)
SAVE_SLOT_FALLBACK_BORDER: tuple[int, int, int] = (100, 100, 100)

# Text colors
SAVE_TITLE_COLOR: tuple[int, int, int] = (220, 200, 150)
SAVE_DETAIL_COLOR: tuple[int, int, int] = COLOR_TEXT_STONE  # (60, 40, 30)

# Detail text layout
SAVE_DETAIL_TEXT_X_OFFSET: int = 180   # px from card left edge
SAVE_DETAIL_TEXT_Y_OFFSET: int = 70    # py from card top edge
SAVE_DETAIL_LINE_SPACING: int = 30     # px between level and time lines

# ---------------------------------------------------------------------------
# SaveMenuOverlay — full-screen panel
# ---------------------------------------------------------------------------
SAVE_PANEL_W: int = 600
SAVE_PANEL_H: int = 800
SAVE_PANEL_FILL: tuple[int, int, int, int] = (10, 18, 22, 220)
SAVE_PANEL_Y_OFFSET: int = 30          # shift from vertical center
SAVE_SLOT_SPACING: int = 20            # px gap between slot cards

# ---------------------------------------------------------------------------
# Back button
# ---------------------------------------------------------------------------
BACK_ICON_W: int = 28
BACK_ICON_H: int = 25
BACK_ICON_HOVER_W: int = 32
BACK_ICON_HOVER_H: int = 29
BACK_BTN_W: int = 140
BACK_BTN_H: int = 40
BACK_FONT_SIZE: int = 22
BACK_FONT_PATH: str = "assets/fonts/cormorant-garamond-regular.ttf"
BACK_TEXT_COLOR: tuple[int, int, int] = (150, 255, 220)
BACK_HALO_COLOR: tuple[int, int, int] = (0, 180, 150)
BACK_LABEL_GAP: int = 8               # px between icon and label

# Engraving colors (re-exported for local use — canonical in pause_screen_constants)
from src.ui.pause_screen_constants import ENGRAVE_TEXT, ENGRAVE_SHADOW, ENGRAVE_LIGHT

# Halo blur
SAVE_HALO_BLUR_PADDING: int = 20
SAVE_HALO_BLUR_RADIUS: int = 6

# Font fallback
SAVE_FONT_TITLE_FALLBACK_SIZE: int = 48
```

### File: `src/ui/save_menu.py` — MODIFY

Import all constants from `save_menu_constants`. Replace every inline literal.

**Pre-render optimizations (P-PERF-01d):**

In `SaveSlotUI.draw()`, `font.render()` is called every frame for title, level, and time text. These change only when save data changes (i.e., at `refresh()` time).

- Add `_cached_title_surf`, `_cached_level_surf`, `_cached_time_surf` per slot to `SaveMenuOverlay`.
- Compute these in `refresh()` after loading slot info.
- `draw()` blits cached surfaces — zero `render()` calls per frame.

In `_draw_back_button()`:
- Pre-render `_idle_label_surf` and `_hover_label_surf` (halo + engraved) at `__init__`.
- `draw()` blits the appropriate pre-rendered surface based on `_back_hovered`.

In `_blit_halo_text()` (back button):
- Cache: `dict[bool → Surface]` keyed on hover state → built at init.
- `_draw_back_button()` reads from cache, no allocation.

---

## Feature P-PERF-01a — I18nManager cache in HUD

### File: `src/ui/hud.py` — MODIFY

**In `__init__`:**
```python
self._i18n = I18nManager()
```

**In `draw()`** — replace:
```python
# BEFORE
day_label = I18nManager().get("day_label", "Day").upper()
# AFTER
day_label = self._i18n.get("day_label", "Day").upper()
```

---

## Feature P-PERF-01c — Pre-render pause menu items

### File: `src/ui/pause_screen.py` — MODIFY (extends P-CONST-01d changes)

**In `_load_assets()`**, after fonts are loaded, pre-render all button label surfaces:

```python
self._rendered_idle: list[pygame.Surface] = []
self._rendered_hover: list[pygame.Surface] = []
self._rendered_positions: list[pygame.Rect] = []  # set in _compute_layout

for key, default in zip(_BUTTON_KEYS, _BUTTON_DEFAULTS):
    label = self._i18n.get(key, default)
    # Idle (engraved)
    idle = self._make_engraved_surface(label)
    self._rendered_idle.append(idle)
    # Hover (halo) — pre-render both pygame-CE and fallback paths
    hover = self._make_halo_surface(label)
    self._rendered_hover.append(hover)
```

**Add private factory methods (called once at init):**

```python
def _make_engraved_surface(self, label: str) -> pygame.Surface:
    """Pre-render 3-pass stone engraving to a single composite surface."""
    shadow = self._item_font.render(label, True, ENGRAVE_SHADOW)
    light  = self._item_font.render(label, True, ENGRAVE_LIGHT)
    text   = self._item_font.render(label, True, ENGRAVE_TEXT)
    w = text.get_width() + 2
    h = text.get_height() + 2
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(shadow, (0, 0))
    out.blit(light,  (2, 2))
    out.blit(text,   (1, 1))
    return out

def _make_halo_surface(self, label: str) -> pygame.Surface:
    """Pre-render halo glow + main text to a composite surface."""
    base = self._item_font.render(label, True, HOVER_HALO_COLOR)
    w, h = base.get_size()
    pad = HALO_BLUR_PADDING
    padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    padded.blit(base, (pad, pad))
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    try:
        blurred = pygame.transform.gaussian_blur(padded, HALO_BLUR_RADIUS)
        out.blit(blurred, (0, 0))
        out.blit(blurred, (0, 0))
        out.blit(blurred, (0, 0))
    except AttributeError:
        # Fallback: soft-shadow offsets
        base.set_alpha(80)
        for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3),(0,-4),(0,4),(-4,0),(4,0)]:
            out.blit(base, (pad + dx, pad + dy))
    main = self._item_font.render(label, True, HOVER_TEXT_COLOR)
    out.blit(main, (pad, pad))
    return out
```

**In `draw()`** — replace the `_blit_halo_text` / `_blit_engraved` loop:
```python
for i, (rect, surf_idle, surf_hover) in enumerate(
    zip(self.button_rects, self._rendered_idle, self._rendered_hover)
):
    surf = surf_hover if self._hovered_btn == i else surf_idle
    self._screen.blit(surf, surf.get_rect(center=rect.center))
```

> **Anti-pattern**: Do NOT call `pygame.Surface()` or `gaussian_blur()` inside `draw()`. Allocate once in `__init__` or `_load_assets()`.

---

## Anti-Patterns

| # | Anti-Pattern | Why Forbidden | Correct Approach |
|---|---|---|---|
| AP-01 | `pygame.font.Font()` inside a `draw()` method | Creates font object 60×/s — extremely slow | Initialize font once in `__init__`, store as `self._font` |
| AP-02 | `pygame.Surface(...)` inside `draw()` without cache | Allocates RAM every frame, triggers GC | Pre-render at `__init__` or `refresh()`; blit cached surface |
| AP-03 | `gaussian_blur(...)` called every frame | Expensive per-pixel operation at 60 FPS | Cache blurred surface; invalidate only on content change |
| AP-04 | `I18nManager()` / `AssetManager()` constructed in `draw()` | Constructor call overhead on hot path | Store as `self._i18n = I18nManager()` in `__init__` |
| AP-05 | Engraving color tuples in function body | Hidden magic values, not reusable | Define as module-level constants in `_constants.py` |
| AP-06 | Inline `(R, G, B)` tuples in non-constants files | Violates `_constants.py` architecture | All colors in `ui_colors.py` or module `_constants.py` |
| AP-07 | Magic pixel size tuples `(W, H)` inline | Undocumented layout dimensions | Define as `CONST_W / CONST_H` pair in `_constants.py` |
| AP-08 | `.get_size()` on fixed Surface inside draw loop | Redundant call on known-size surface | Cache size tuple at init |
| AP-09 | `font.render(label, True, (0,0,0))` only for width measurement | Allocates Surface just to measure | Use `font.size(label)[0]` — returns `(w, h)` tuple, no Surface |
| AP-10 | Non-English words in `#` comments | Violates all-English comment policy | Translate to English immediately |

---

## Error Handling Matrix

| Failure | Location | Handling |
|---|---|---|
| `gaussian_blur` not available (standard pygame) | `_make_halo_surface()` | `except AttributeError` → use 8-offset fallback, pre-render same way |
| `pause_screen_constants` import missing | `pause_screen.py` imports | Import error surfaces immediately — test suite catches this |
| `save_menu_constants` import of `ENGRAVE_*` | re-export from `pause_screen_constants` | Circular guard: `pause_screen_constants` has no UI imports |
| `ui_colors.COLOR_TEXT_STONE` missing | `chest_constants.py`, `save_menu_constants.py` | Import error caught at module load — not a runtime risk |
| Font file missing at init | All font loads | Already has `except OSError → SysFont` fallback |

---

## Test Case Specifications

| ID | Type | File | Description |
|---|---|---|---|
| UT-001 | Unit | `tests/ui/test_pause_screen.py` | `PauseScreen.__init__` pre-renders `_rendered_idle` (len == 3, all pygame.Surface) |
| UT-002 | Unit | `tests/ui/test_pause_screen.py` | `PauseScreen.draw()` with hover=0 blits `_rendered_hover[0]` — no new Surface alloc |
| UT-003 | Unit | `tests/ui/test_pause_screen.py` | `_make_halo_surface()` returns Surface even when `gaussian_blur` raises `AttributeError` |
| UT-004 | Unit | `tests/ui/test_save_menu.py` | `SaveMenuOverlay.refresh()` populates `_cached_title_surfs` list of length 3 |
| UT-005 | Unit | `tests/ui/test_perf_hud.py` | `GameHUD.__init__` stores `_i18n`; calling `draw()` does NOT construct `I18nManager` |
| UT-006 | Unit | `tests/engine/test_perf_lighting.py` | `_get_beam_surface_for_time()` called with patched `BEAM_COLOR_MOON` — color used in lerp |
| UT-007 | Unit | `tests/ui/test_dialogue.py` | `DialogueManager._shadow_color == DIALOGUE_SHADOW_COLOR` after `__init__` |
| UT-008 | Unit | `tests/ui/test_perf_constants.py` | `_draw_title()` renders text == `CHEST_TITLE_TEXT` (mock render, capture arg) |
| UT-009 | Unit | `tests/ui/test_perf_constants.py` | `_title_font` is same object on second `_draw_title()` call — lazy-init guard works |
| UT-010 | Unit | `tests/ui/test_save_menu.py` | `SaveSlotUI.__init__` passes `(SAVE_SLOT_BG_W, SAVE_SLOT_BG_H)` to `smoothscale` |
| IT-001 | Integration | grep over `src/` | No file contains `# Sauvegarder` — French comment eliminated |
| IT-002 | Integration | `pytest tests/ -x -q` | All 647 existing tests pass — zero behavioral regression |
| IT-003 | Integration | `python -c "import src.ui.save_menu_constants"` | New constants file imports without error |

---

| Reference | Location |
|---|---|
| Strategy doc | [perf-constants-audit-strategy.md#q1-what-exact-problem-are-you-solving](../strategic/perf-constants-audit-strategy.md#q1-what-exact-problem-are-you-solving) |
| Pre-render pattern (existing) | [title_screen.py L168](../../src/ui/title_screen.py#L168) — `# P3: Pre-render idle menu label surfaces` |
| `_constants.py` architecture | [architecture.md — Key Subsystems](../CODEMAPS/architecture.md#key-subsystems) |
| `ui_colors.py` (COLOR_TEXT_STONE) | [ui_colors.py L9](../../src/ui/ui_colors.py#L9) |
| `pause_screen_constants.py` (ENGRAVE_*) | [pause_screen_constants.py L28](../../src/ui/pause_screen_constants.py#L28) |
| `lighting_constants.py` | [lighting_constants.py#overlay-base-alpha](../../src/engine/lighting_constants.py#L16) |
| `dialogue_constants.py` | [dialogue_constants.py#dialogue-content-margin-x](../../src/ui/dialogue_constants.py#L7) |
| `chest_constants.py` | [chest_constants.py#chest-panel-layout-constants](../../src/ui/chest_constants.py#L22) |
| `save_menu_constants.py` (new) | [save_menu_constants.py#saveслotui-slot-background-card](../../src/ui/save_menu_constants.py#L7) — created in P-CONST-01e |
