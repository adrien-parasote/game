# Spec: Code Quality Pass — Constants & i18n Text Cleanup

> Document Type: Implementation

**Covers:** F-QUAL-01 (French→EN translation), F-QUAL-02 (magic color constants), F-QUAL-03 (existing constant usage bugs)
**Spec version:** 1.1 | **Last updated:** 2026-06-12

---

## Assumptions

N/A — This is a zero-logic-change refactor. All items verified during BUILD (see BUILD Addendum below). No runtime assumptions remain.

## Overview

This spec covers a targeted code-quality pass across all `src/` Python files:

1. **Translate all French text to English** — comments, docstrings, log strings, i18n fallback defaults.
2. **Move all magic color tuples to their module's `_constants.py`** — or to shared `ui_colors.py` / new `engine_constants.py`.
3. **Fix two pre-existing bugs** where existing constants are defined but not used (hardcoded tuples remain in the implementation file).

This is a **zero-logic-change** refactor: no behavior changes, no new features, no restructuring. Only text and constant references change.

---

## Test Cases

> See **Test Case Specifications** section below for IT-001..TC-007.

## Anti-patterns

> See **Anti-Patterns** section below for AP-01..AP-08.

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run `python -m pytest tests/ -x -q` after all changes; verify zero French chars remain |
| **Ask first** | Any discovered logic change needed beyond the items listed in this spec |
| **Never do** | Rename constants that are already imported elsewhere; change any values (only names/locations); modify test files |

---

## Cross-Spec Contracts

### Produces
N/A - Not applicable

### Consumes
N/A - Not applicable

### Public Interface
N/A - Not applicable

### External Invocations
- N/A

### Tracked Concepts
- N/A

## Bundling & Native-Module Audit
- BM1: N/A — Python project, no client/server boundary.
- BM2: N/A — Python project.
- BM3: N/A — no native modules introduced.
- BM4: Constant renames are purely additive (new constants in constants files). No existing constant is renamed — only new ones added. No test fixtures reference the new names because they don't exist yet. ✅ PASS.

---

## File Tree

All files modified or created by this spec:

```
src/
  engine/
    engine_constants.py          [NEW] — placeholder colors + spritesheet fallback + map constants
    asset_manager.py             [MODIFY] — use COLOR_PLACEHOLDER_MAGENTA
    save_manager.py              [MODIFY] — translate 3 FR occurrences
    game.py                      [MODIFY] — use COLOR_BLACK for fade surface
  ui/
    ui_colors.py                 [MODIFY] — add COLOR_BLACK, COLOR_WHITE
    speech_bubble_constants.py   [MODIFY] — add BUBBLE_CENTER_FILL, BUBBLE_NAME_TEXT_COLOR + 6 layout constants
    speech_bubble.py             [MODIFY] — use 3 new constants
    dialogue_constants.py        [MODIFY] — add 9 new layout/color constants (see BUILD Addendum §C)
    inventory_constants.py       [MODIFY] — add 4 new layout constants (see BUILD Addendum §D)
    save_menu.py                 [MODIFY] — use SAVE_TITLE_COLOR at line 224; translate "Retour"→"Back"
    save_slot.py                 [MODIFY] — use COLOR_BLACK
    pause_screen_constants.py    [MODIFY] — translate _BUTTON_DEFAULTS
    pause_screen.py              [MODIFY] — use PANEL_W/PANEL_H; translate "Sauvegarder la partie"→"Save Game"
    title_screen_constants.py    [MODIFY] — add LABEL_MEASURE_COLOR; translate _MENU_ITEM_DEFAULTS, BACK_BTN_LABEL_DEFAULT
    title_screen_draw.py         [MODIFY] — use LABEL_MEASURE_COLOR; translate docstring
    title_screen.py              [MODIFY] — use COLOR_BLACK
    title_screen_lights.py       [MODIFY] — use COLOR_BLACK
  entities/
    player_constants.py          [NEW] — player spritesheet layout, animation, audio, starting stats
    emote_constants.py           [NEW] — emote animation constants
    interactive_constants.py     [MODIFY] — add PARTICLE_DEFAULT_COLOR
    interactive_particles.py     [MODIFY] — use PARTICLE_DEFAULT_COLOR
    interactive.py               [MODIFY] — translate French comment at line 383
    interactive_lighting.py      [MODIFY] — use COLOR_BLACK
    teleport.py                  [MODIFY] — use COLOR_PLACEHOLDER_MAGENTA
    pickup.py                    [MODIFY] — use COLOR_PLACEHOLDER_MAGENTA
  graphics/
    spritesheet.py               [MODIFY] — use COLOR_PLACEHOLDER_BLUE
  config.py                      [MODIFY] — translate 4 FR comments
```

---

## Detailed Change Specifications

### F-QUAL-01: French → English Translation

#### F-QUAL-01-A: `src/entities/interactive.py` line 383
```python
# BEFORE
# Fermeture : partir de end_row pour jouer l'anim à l'envers
# AFTER
# Closing: play animation in reverse starting from end_row
```

#### F-QUAL-01-B: `src/engine/save_manager.py` — 3 occurrences

Line 121 — docstring:
```python
# BEFORE
"""Sauvegarde une capture d'écran pour la miniature du slot."""
# AFTER
"""Save a screenshot for the slot thumbnail."""
```

Line 133 — docstring:
```python
# BEFORE
"""Retourne la miniature en pygame.Surface, ou None si non trouvée."""
# AFTER
"""Return the slot thumbnail as a pygame.Surface, or None if not found."""
```

Line 158 — log string:
```python
# BEFORE
logging.warning(f"SaveManager: Slot {slot_id} corrompu: {e}")
# AFTER
logging.warning(f"SaveManager: Slot {slot_id} corrupted: {e}")
```

#### F-QUAL-01-C: `src/ui/pause_screen_constants.py` line 35
```python
# BEFORE
_BUTTON_DEFAULTS = ["Menu Principal", "Reprendre", "Sauvegarder"]
# AFTER
_BUTTON_DEFAULTS = ["Main Menu", "Resume", "Save"]
```

#### F-QUAL-01-D: `src/ui/pause_screen.py` line 63
```python
# BEFORE
self._i18n.get("pause_menu.save", "Sauvegarder la partie")
# AFTER
self._i18n.get("pause_menu.save", "Save Game")
```

#### F-QUAL-01-E: `src/ui/title_screen_constants.py` lines 116, 128-129
```python
# BEFORE
_MENU_ITEM_DEFAULTS = ["Nouvelle Partie", "Charger", "Options", "Quitter"]
BACK_BTN_LABEL_DEFAULT = "Retour"
# AFTER
_MENU_ITEM_DEFAULTS = ["New Game", "Load", "Options", "Quit"]
BACK_BTN_LABEL_DEFAULT = "Back"
```

#### F-QUAL-01-F: `src/ui/title_screen_draw.py` line 160
```python
# BEFORE
"""Draw options panel: 'Retour' label (engraved/golden) + back icon."""
# AFTER
"""Draw options panel: 'Back' label (engraved/golden) + back icon."""
```

#### F-QUAL-01-G: `src/ui/save_menu.py` line 100
```python
# BEFORE
label = self._i18n.get("menu.back", "Retour")
# AFTER
label = self._i18n.get("menu.back", "Back")
```

---

### F-QUAL-02: Magic Color Constants

#### F-QUAL-02-A: `src/engine/engine_constants.py` [NEW FILE]

```python
"""
Engine-level constants — placeholder and fallback colors.
These colors appear in error/missing-asset rendering paths only (never in production UI).
Spec: game/docs/specs/code-quality-constants-i18n.md § F-QUAL-02-A
"""

# Fallback colors for missing or fallback assets (debug-visible, non-production)
COLOR_PLACEHOLDER_MAGENTA: tuple[int, int, int] = (255, 0, 255)
COLOR_PLACEHOLDER_BLUE: tuple[int, int, int] = (0, 0, 255)

# SpriteSheet fallback dimensions (used when image load fails)
SPRITESHEET_FALLBACK_SIZE: tuple[int, int] = (32, 32)
SPRITESHEET_FALLBACK_FRAME_COUNT: int = 16

# Map layer depth threshold for grass-eligible tiles
GRASS_MAX_DEPTH: int = 1

# Tiled project file path (relative to workspace root)
TILED_PROJECT_PATH: str = "assets/tiled/game.tiled-project"
```

> **Note (BUILD Addendum):** The original spec defined only `COLOR_PLACEHOLDER_MAGENTA` and `COLOR_PLACEHOLDER_BLUE`. During implementation, 4 additional engine-level constants were extracted here from previously inline values in `spritesheet.py`, `map/manager.py`, and `map/tmj_parser.py`. Recorded per anti-divergence rule.

#### F-QUAL-02-B: `src/ui/ui_colors.py` additions

Add at end of file:
```python
# Shared primitives
COLOR_BLACK: tuple[int, int, int] = (0, 0, 0)
COLOR_WHITE: tuple[int, int, int] = (255, 255, 255)
```

#### F-QUAL-02-C: `src/ui/speech_bubble_constants.py` additions

Add at end of file:
```python
# Bubble rendering colors
BUBBLE_CENTER_FILL: tuple[int, int, int] = (255, 255, 255)   # White fill for the inner content area
BUBBLE_NAME_TEXT_COLOR: tuple[int, int, int] = (255, 255, 255)  # Name plate text color
```

Import `COLOR_TEXT_STONE` from `ui_colors.py` for `BUBBLE_TEXT_COLOR` — no new constant needed.

#### F-QUAL-02-D: `src/entities/interactive_constants.py` addition

Add:
```python
PARTICLE_DEFAULT_COLOR: tuple[int, int, int] = (250, 250, 250)  # Default halo fallback color (near-white)
```

#### F-QUAL-02-E: `src/ui/title_screen_constants.py` addition

Add:
```python
LABEL_MEASURE_COLOR: tuple[int, int, int] = (0, 0, 0)  # Used only for font width measurement (not rendered)
```

---

### F-QUAL-03: Fix Pre-Existing Constant Usage Bugs

#### F-QUAL-03-A: `src/ui/save_menu.py` line 224 (BUG)

`SAVE_TITLE_COLOR` is already imported and defined in `save_menu_constants.py` but `draw()` uses a hardcoded tuple:
```python
# BEFORE (line 224)
title_surf = self._font_title.render(self._title_text, True, (220, 200, 150))
# AFTER
title_surf = self._font_title.render(self._title_text, True, SAVE_TITLE_COLOR)
```

#### F-QUAL-03-B: `src/ui/pause_screen.py` lines 95, 98 (BUG)

`PANEL_W` and `PANEL_H` are already imported but loading panel uses hardcoded `(480, 480)`:
```python
# BEFORE
if panel_raw.get_size() != (FALLBACK_SURF_SIZE, FALLBACK_SURF_SIZE):
    self._panel = pygame.transform.smoothscale(panel_raw, (480, 480))
else:
    self._panel = pygame.Surface((480, 480), pygame.SRCALPHA)
# AFTER
if panel_raw.get_size() != (FALLBACK_SURF_SIZE, FALLBACK_SURF_SIZE):
    self._panel = pygame.transform.smoothscale(panel_raw, (PANEL_W, PANEL_H))
else:
    self._panel = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
```

---

### Implementation Details — Consumer Changes

#### `src/engine/asset_manager.py`
```python
# ADD import at top
from src.engine.engine_constants import COLOR_PLACEHOLDER_MAGENTA

# REPLACE (lines 36, 51)
placeholder.fill((255, 0, 255))  →  placeholder.fill(COLOR_PLACEHOLDER_MAGENTA)
```

#### `src/engine/save_manager.py`
See F-QUAL-01-B above (3 text changes only, no imports needed).

#### `src/engine/game.py`
```python
# ADD import
from src.ui.ui_colors import COLOR_BLACK

# REPLACE (line 272)
fade_surf.fill((0, 0, 0))  →  fade_surf.fill(COLOR_BLACK)
```

#### `src/ui/speech_bubble.py`
```python
# ADD imports
from src.ui.speech_bubble_constants import (
    ...,  # existing
    BUBBLE_CENTER_FILL,
    BUBBLE_NAME_TEXT_COLOR,
)
from src.ui.ui_colors import COLOR_TEXT_STONE

# REPLACE
(255, 255, 255)  →  BUBBLE_CENTER_FILL      (line 128)
(255, 255, 255)  →  BUBBLE_NAME_TEXT_COLOR  (line 180)
(60, 40, 30)    →  COLOR_TEXT_STONE         (line 259)
```

#### `src/ui/save_slot.py`
```python
# ADD import
from src.ui.ui_colors import COLOR_BLACK

# REPLACE (line 49)
self._halo.fill((0, 0, 0))  →  self._halo.fill(COLOR_BLACK)
```

#### `src/ui/title_screen.py`
```python
# ADD import
from src.ui.ui_colors import COLOR_BLACK

# REPLACE (line 115)
self._overlay.fill((0, 0, 0))  →  self._overlay.fill(COLOR_BLACK)
```

#### `src/ui/title_screen_draw.py`
```python
# ADD import
from src.ui.title_screen_constants import (
    ...,  # existing
    LABEL_MEASURE_COLOR,
)

# REPLACE (line 170)
label_surf_measure = self._back_label_font.render(label, True, (0, 0, 0))
→
label_surf_measure = self._back_label_font.render(label, True, LABEL_MEASURE_COLOR)
```

#### `src/ui/title_screen_lights.py`
```python
# ADD import
from src.ui.ui_colors import COLOR_BLACK

# REPLACE (line 57 in _create_radial_gradient)
base.fill((0, 0, 0))  →  base.fill(COLOR_BLACK)
```

#### `src/entities/interactive_lighting.py`
```python
# ADD import
from src.ui.ui_colors import COLOR_BLACK

# REPLACE (line 48)
surf.fill((0, 0, 0))  →  surf.fill(COLOR_BLACK)
```

#### `src/entities/interactive_particles.py`
```python
# ADD import
from src.entities.interactive_constants import (
    ...,  # existing
    PARTICLE_DEFAULT_COLOR,
)

# REPLACE (line 60)
base_color = getattr(self, "halo_color", (250, 250, 250))
→
base_color = getattr(self, "halo_color", PARTICLE_DEFAULT_COLOR)
```

#### `src/entities/interactive.py`
See F-QUAL-01-A above (comment text change only, no imports needed).

#### `src/entities/teleport.py`
```python
# ADD import
from src.engine.engine_constants import COLOR_PLACEHOLDER_MAGENTA

# REPLACE (line 29)
self.image.fill((255, 0, 255))  →  self.image.fill(COLOR_PLACEHOLDER_MAGENTA)
```

#### `src/entities/pickup.py`
```python
# ADD import
from src.engine.engine_constants import COLOR_PLACEHOLDER_MAGENTA

# REPLACE (line 60)
self.image.fill((255, 0, 255))  →  self.image.fill(COLOR_PLACEHOLDER_MAGENTA)
# Also update inline comment:
# BEFORE: self.image.fill((255, 0, 255))  # Magenta placeholder
# AFTER:  self.image.fill(COLOR_PLACEHOLDER_MAGENTA)  # Missing icon fallback
```

#### `src/graphics/spritesheet.py`
```python
# ADD import
from src.engine.engine_constants import COLOR_PLACEHOLDER_BLUE

# REPLACE (line 87)
surf.fill((0, 0, 255))  # Blue default
→
surf.fill(COLOR_PLACEHOLDER_BLUE)  # Blue placeholder for missing spritesheet
```

---

## Anti-Patterns

| ID | Pattern | What to do instead |
|----|---------|--------------------|
| AP-01 | **Renaming existing constants** — renaming `HALO_DEFAULT_COLOR`, `COLOR_TEXT_STONE`, or any constant already imported by other files | Only ADD new constants and update usages of hardcoded tuples. Never rename what already exists. |
| AP-02 | **Changing constant values** — defining `COLOR_BLACK = (0, 0, 1)` or any value that differs from the original tuple | New constants must have identical numeric values to the tuples they replace. Verify each one. |
| AP-03 | **Extracting debug-only colors** — moving `(255, 0, 0)` from inside `if Settings.DEBUG:` or `if HALO_DEBUG:` blocks to constants | Leave debug colors inline. Their inline nature signals "dev tooling, never production." |
| AP-04 | **Editing i18n JSON files** — modifying `assets/langs/fr.json` or any other locale file | Only the Python-side fallback default strings change. JSON files are out of scope. |
| AP-05 | **Creating circular imports** — having `engine_constants.py` import from `ui_colors.py` or vice versa | Both must be independent leaf modules with zero imports from `src/`. |
| AP-06 | **Mixing inline and constant in the same file** — having both `(0, 0, 0)` and `COLOR_BLACK` in the same file | Import once at top; replace ALL occurrences in that file with the constant. |
| AP-07 | **Reusing SAVE_TITLE_COLOR** for non-save-title golden text elements | `SAVE_TITLE_COLOR = (220, 200, 150)` is save-menu-specific. Other golden text may need different values. |
| AP-08 | **Creating a second `from speech_bubble_constants import ...` block** | Add `BUBBLE_CENTER_FILL` and `BUBBLE_NAME_TEXT_COLOR` to the existing import block in `speech_bubble.py`. |

---

## Test Case Specifications

All existing tests cover runtime behavior. These test cases are verification scripts, not new test code. The TDD gate is satisfied by running the full suite and verifying zero regressions.

### IT-001 — Full pytest suite zero regressions (integration)

| Field | Value |
|-------|-------|
| Given | All 21 files modified/created per file tree |
| When | `python -m pytest tests/ -x -q --tb=short` |
| Then | Exit code 0, same pass count as baseline |
| Type | integration |

### IT-002 — All modified files import cleanly (integration)

| Field | Value |
|-------|-------|
| Given | All 21 files modified/created per file tree |
| When | `python -m py_compile <each file>` for all 21 files |
| Then | Exit code 0 for every file — no ImportError or SyntaxError |
| Type | integration |

### IT-003 — No circular imports introduced (integration)

| Field | Value |
|-------|-------|
| Given | `src/engine/engine_constants.py` created and imported by 4 consumers |
| When | `python -c "from src.engine.asset_manager import AssetManager; from src.graphics.spritesheet import SpriteSheet; from src.entities.teleport import Teleport; from src.entities.pickup import Pickup"` |
| Then | No ImportError — confirms engine_constants.py is a true leaf module |
| Type | integration |

### TC-001 — No Python import errors (unit)

| Field | Value |
|-------|-------|
| Given | All modified source files applied |
| When | `python -m py_compile <file>` for each of the 21 files in the file tree |
| Then | Exit code 0 — no ImportError or SyntaxError |
| Type | unit |

### TC-002 — Zero French characters remain (unit)

| Field | Value |
|-------|-------|
| Given | All FR→EN translations applied |
| When | `grep -rn "[àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]" src/ --include="*.py"` |
| Then | Zero matches returned |
| Type | unit |

### TC-003 — No loose magic color tuples (unit)

| Field | Value |
|-------|-------|
| Given | All magic color constants applied |
| When | `grep -rn "(255, 255, 255)\|(60, 40, 30)\|(220, 200, 150)\|(255, 0, 255)\|(0, 0, 255)" src/ --include="*.py"` |
| Then | All matches are ONLY in `*_constants.py` or `ui_colors.py` or `engine_constants.py` |
| Type | unit |

### TC-004 — engine_constants.py importable as leaf module (unit)

| Field | Value |
|-------|-------|
| Given | `src/engine/engine_constants.py` created |
| When | `python -c "from src.engine.engine_constants import COLOR_PLACEHOLDER_MAGENTA, COLOR_PLACEHOLDER_BLUE; assert COLOR_PLACEHOLDER_MAGENTA == (255, 0, 255); assert COLOR_PLACEHOLDER_BLUE == (0, 0, 255)"` |
| Then | No error, assertions pass |
| Type | unit |

### TC-005 — ui_colors.py exports COLOR_BLACK and COLOR_WHITE (unit)

| Field | Value |
|-------|-------|
| Given | `src/ui/ui_colors.py` updated |
| When | `python -c "from src.ui.ui_colors import COLOR_BLACK, COLOR_WHITE; assert COLOR_BLACK == (0,0,0); assert COLOR_WHITE == (255,255,255)"` |
| Then | No error, assertions pass |
| Type | unit |

### TC-006 — SAVE_TITLE_COLOR replaces hardcoded tuple in save_menu.py (unit)

| Field | Value |
|-------|-------|
| Given | `save_menu.py` updated at line 224 |
| When | `grep -n "220, 200, 150" src/ui/save_menu.py` |
| Then | Zero matches — the hardcoded tuple is gone |
| Type | unit |

### TC-007 — PANEL_W/PANEL_H replace hardcoded sizes in pause_screen.py (unit)

| Field | Value |
|-------|-------|
| Given | `pause_screen.py` updated at lines 95, 98 |
| When | `grep -n "(480, 480)" src/ui/pause_screen.py` |
| Then | Zero matches |
| Type | unit |

---

## Error Handling Matrix

| Error | Trigger | Response |
|-------|---------|----------|
| `ImportError` after adding `from src.engine.engine_constants import ...` | Circular import or missing module | Stop immediately. Check that `engine_constants.py` imports nothing from `src/`. |
| `NameError: COLOR_PLACEHOLDER_MAGENTA` | Import added to wrong location or file not created | Verify `engine_constants.py` exists at `src/engine/engine_constants.py`. |
| `AssertionError` in TC-QUAL-05/06 | Wrong value in constant definition | Re-check constant value against the original tuple. Values must be identical. |
| Pytest suite regresses (test count drops or new failures) | Logic accidentally changed | STOP. Revert the offending file. Only text and import changes are permitted. |
| French chars still found after changes | A file was missed | Re-run grep, identify the file, apply the translation. |
| `(480, 480)` still found in `pause_screen.py` | Lines 95 or 98 not updated | Check both occurrences: `smoothscale(panel_raw, (480, 480))` and `Surface((480, 480), ...)`. |

---

## Deep Links

- `src/ui/ui_colors.py` — existing color constants: [ui_colors.py](../../src/ui/ui_colors.py#L1)
- `src/entities/interactive_constants.py` — existing entity constants: [interactive_constants.py](../../src/entities/interactive_constants.py#L1)
- `src/ui/speech_bubble_constants.py` — existing bubble constants: [speech_bubble_constants.py](../../src/ui/speech_bubble_constants.py#L1)
- `src/ui/save_menu_constants.py` — SAVE_TITLE_COLOR defined here: [save_menu_constants.py](../../src/ui/save_menu_constants.py#L36)
- `src/ui/pause_screen_constants.py` — PANEL_W/PANEL_H defined here: [pause_screen_constants.py](../../src/ui/pause_screen_constants.py#L11-L12)
- `docs/specs/development-quality.md` — related quality spec: [development-quality.md](./development-quality.md#L1)
- Implementation plan (DISCOVER output): [implementation_plan.md](file:///Users/adrien.parasote/.gemini/antigravity-ide/brain/3e726d7b-ddd4-4dd3-987b-4de921bf4b9f/implementation_plan.md#L1)

---

## BUILD Addendum — Items Found During Implementation (Anti-Divergence)

The following items were discovered during BUILD and fixed but were not in the original spec.
Recorded here per the Rule of Divergence.

### Extra FR→EN Translations Found

| File | Before | After |
|------|--------|-------|
| `src/ui/save_slot.py` line 98 | `"Niveau: {level}"` | `"Level: {level}"` |
| `src/ui/save_slot.py` line 108 | `"Temps: {hours:02d}h {minutes:02d}m"` | `"Time: {hours:02d}h {minutes:02d}m"` |
| `src/ui/title_screen.py` line 74 | `"Charger une partie"` | `"Load Game"` |
| `src/ui/title_screen.py` line 263 | docstring `"ESC ou clic sur le bouton retour → MAIN_MENU."` | `"ESC or click on back button → MAIN_MENU."` |
| `src/ui/pause_screen.py` line 260 | `"Partie sauvegardée !"` | `"Game saved!"` |
| `src/config.py` | 4 French comments in Settings class | Translated to English inline |

### Extra Constant Adoption Found

| File | Before | After | Constant source |
|------|--------|-------|----------------|
| `src/ui/speech_bubble.py` line 261 | `(60, 40, 30)` | `COLOR_TEXT_STONE` | `src/ui/ui_colors.py` (existing) |
| `src/ui/pause_screen.py` line 91 | `(0, 0, 0)` | `COLOR_BLACK` | `src/ui/ui_colors.py` (new) |

### Intentional Exclusion (Proper Noun)

| File | String | Rationale |
|------|--------|-----------|
| `src/ui/title_screen.py` line 218 | `"L'Éveil de l'Héritier"` | Game's proper title — stays French by design. Marked with inline comment. |

---

### New Constants Files (Commit 06ee7f4)

Two new entity constants files were extracted from inline values in `player.py` and `emote_sprite.py`:

#### §A — `src/entities/player_constants.py` [NEW]

| Constant | Value | Purpose |
|----------|-------|---------|
| `PLAYER_SPRITESHEET_COLS` | `4` | Number of columns in the player spritesheet |
| `PLAYER_SPRITESHEET_ROWS` | `4` | Number of rows in the player spritesheet |
| `PLAYER_ANIM_FRAME_DURATION` | `0.15` | Seconds per animation frame |
| `PLAYER_FRAMES_PER_ROW` | `4` | Frames per direction row |
| `PLAYER_ROW_OFFSETS` | `{"down": 0, "left": 4, "right": 8, "up": 12}` | Row-index start per direction in the spritesheet (4 frames each) |
| `PLAYER_FOOTSTEP_FRAMES` | `(1, 3)` | Animation frame indices that trigger footstep sound |
| `PLAYER_FOOTSTEP_VOLUME` | `0.15` | Footstep audio volume |
| `PLAYER_INITIAL_LEVEL` | `1` | Starting player level |
| `PLAYER_INITIAL_HP` | `100` | Starting player HP |
| `PLAYER_INITIAL_GOLD` | `0` | Starting player gold |

#### §B — `src/entities/emote_constants.py` [NEW]

| Constant | Value | Purpose |
|----------|-------|---------|
| `EMOTE_RISE_PX` | `15` | Vertical rise distance in pixels during emote display animation (matches entities-system.md §6.2) |

#### §C — Extra constants in `src/ui/dialogue_constants.py`

The following 9 constants were added to `dialogue_constants.py` in commit 06ee7f4 (extracted from inline values in `dialogue.py` and `speech_bubble.py`):

| Constant | Value | Purpose |
|----------|-------|---------|
| `DIALOGUE_SHADOW_COLOR` | `(180, 170, 150)` | Light shadow on parchment background |
| `DIALOGUE_TEXT_COLOR` | `(60, 40, 30)` | Dark brown, high-contrast text color |
| `DIALOGUE_SCALE` | `0.5` | Scale factor for dialogue panel relative to screen |
| `DIALOGUE_FONT_SCALE` | `1.5` | Multiplier applied to narrative/noble font sizes |
| `DIALOGUE_BOTTOM_MARGIN` | `40` | Margin from bottom of available height (px) |
| `DIALOGUE_LINE_SPACING` | `1.2` | Line spacing multiplier |
| `DIALOGUE_BOX_BOTTOM_INSET` | `20` | Inset from WINDOW_HEIGHT for box bottom edge (px) |
| `DIALOGUE_SHADOW_OFFSET` | `1` | Text shadow offset in pixels |
| `DIALOGUE_ARROW_X_INSET` | `10` | Inset for continue arrow from right margin (px) |

#### §D — Extra constants in `src/ui/inventory_constants.py`

The following 4 constants were added to `inventory_constants.py` in commit 06ee7f4 (extracted from inline values in `inventory.py`):

| Constant | Value | Purpose |
|----------|-------|---------|
| `INV_DRAG_HIGHLIGHT_BORDER` | `3` | Border width for drag-selected slot (px) |
| `INV_DRAG_BORDER_RADIUS_BASE` | `12` | Base border radius for drag highlight (before scale) |
| `INV_STAT_NAME_OFFSET_Y` | `16` | Item name label Y-offset in the stats panel (px) |
| `INV_PLACEHOLDER_SIZE` | `32` | Fallback surface size for missing assets (px) |

#### §E — Extra constants in `src/ui/speech_bubble_constants.py`

Beyond the 2 colors from the original spec (F-QUAL-02-C), 6 additional layout constants were extracted in commit 06ee7f4:

| Constant | Value | Purpose |
|----------|-------|---------|
| `BUBBLE_MAX_WIDTH_PX` | `352` | Max bubble width in pixels |
| `BUBBLE_ARROW_INSET` | `4` | Inset for arrow within bubble tail (px) |
| `BUBBLE_NAME_PLATE_PADDING_X` | `16` | Horizontal padding for speaker name plate (px) |
| `BUBBLE_NAME_PLATE_H` | `32` | Height of speaker name plate (px) |
| `BUBBLE_NAME_PLATE_EDGE_W` | `16` | Width of edge slice for 9-slice name plate |
| `BUBBLE_LINES_PER_PAGE` | `4` | Max lines of text shown per bubble page |
| `BUBBLE_NAME_PLATE_MIN_W` | `96` | Minimum width of name plate |
| `BUBBLE_NAME_PLATE_MIN_H` | `64` | Minimum height of name plate tile |

#### §F — Extra constants in `src/engine/engine_constants.py`

Beyond the 2 placeholder colors from the original spec (F-QUAL-02-A), 4 additional engine-level constants were extracted in commit 06ee7f4:

| Constant | Value | Purpose |
|----------|-------|---------|
| `SPRITESHEET_FALLBACK_SIZE` | `(32, 32)` | Fallback surface dimensions when image load fails |
| `SPRITESHEET_FALLBACK_FRAME_COUNT` | `16` | Fallback frame count when image load fails |
| `GRASS_MAX_DEPTH` | `1` | Map layer depth threshold for grass-eligible tiles |
| `TILED_PROJECT_PATH` | `"assets/tiled/game.tiled-project"` | Tiled project file path (relative to workspace root) |

