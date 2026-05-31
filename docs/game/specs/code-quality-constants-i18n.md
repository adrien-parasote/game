# Spec: Code Quality Pass — Constants & i18n Text Cleanup

> Document Type: Implementation

**Covers:** F-QUAL-01 (French→EN translation), F-QUAL-02 (magic color constants), F-QUAL-03 (existing constant usage bugs)
**Spec version:** 1.0 | **Last updated:** 2026-05-27

---

## Assumptions

| # | Assumption | Source Type | Risk | Validation |
|---|-----------|-------------|------|------------|
| A-01 | `COLOR_TEXT_STONE` already exists in `ui_colors.py` and can be reused for `speech_bubble.py` text color | SHOW: `grep -n COLOR_TEXT_STONE src/ui/ui_colors.py` returns a match | Low | Run grep before implementing |
| A-02 | `SAVE_TITLE_COLOR` is already imported in `save_menu.py`'s import block — only the usage site at line 224 needs updating | SHOW: `grep -n SAVE_TITLE_COLOR src/ui/save_menu.py` shows import present | Low | Verify import block before editing |
| A-03 | `PANEL_W` and `PANEL_H` are already imported in `pause_screen.py` — only the two hardcoded `(480, 480)` usages need updating | SHOW: `grep -n PANEL_W src/ui/pause_screen.py` shows import present | Low | Verify import block before editing |
| A-04 | The French i18n locale file `assets/langs/fr.json` exists and is not affected — runtime text comes from it, not Python fallback strings | TELL: i18n architecture documented in `docs/specs/asset-i18n.md` | Low | JSON files are out of scope; only Python fallback strings change |
| A-05 | No test file directly imports or references the magic tuples being replaced — regressions will only appear as runtime errors | SHOW: `grep -rn "(255, 0, 255)\|(0, 0, 255)\|(60, 40, 30)" tests/` returns zero matches | Low | Full pytest run confirms zero regressions |

---

## Overview

This spec covers a targeted code-quality pass across all `src/` Python files:

1. **Translate all French text to English** — comments, docstrings, log strings, i18n fallback defaults.
2. **Move all magic color tuples to their module's `_constants.py`** — or to shared `ui_colors.py` / new `engine_constants.py`.
3. **Fix two pre-existing bugs** where existing constants are defined but not used (hardcoded tuples remain in the implementation file).

This is a **zero-logic-change** refactor: no behavior changes, no new features, no restructuring. Only text and constant references change.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run `python -m pytest tests/ -x -q` after all changes; verify zero French chars remain |
| **Ask first** | Any discovered logic change needed beyond the items listed in this spec |
| **Never do** | Rename constants that are already imported elsewhere; change any values (only names/locations); modify test files |

---

## Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `src/engine/engine_constants.py` | Python module | This spec § "engine_constants.py — new file" | `asset_manager.py`, `spritesheet.py`, `teleport.py`, `pickup.py` |
| `src/ui/ui_colors.py` (updated) | Python module | This spec § "ui_colors.py — additions" | All UI modules that fill surfaces with black/white |

### Consumes
| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `src/ui/ui_colors.py` | Python module | `docs/specs/camera-rendering.md` | Camera/rendering system |
| `src/entities/interactive_constants.py` | Python module | `docs/specs/entities-system.md` | Entities system |
| `src/ui/speech_bubble_constants.py` | Python module | `docs/specs/dialogue-system.md` | Dialogue system |
| `src/ui/save_menu_constants.py` | Python module | `docs/specs/save-system.md` | Save system |
| `src/ui/pause_screen_constants.py` | Python module | `docs/specs/game-flow-spec.md` | Game flow |
| `src/ui/title_screen_constants.py` | Python module | `docs/specs/game-flow-spec.md` | Title screen |

### Public Interface

| Type | Identifier | Documented at |
|------|------------|---------------|
| N/A | N/A — this spec changes no public API signatures | N/A |

### External Invocations

| Type | Invoked | Defined in |
|------|---------|------------|
| N/A | N/A — no external services or commands invoked | N/A |

### Tracked Concepts
| Concept | Status in this spec | Mentioned in |
|---|---|---|
| `COLOR_BLACK` / `COLOR_WHITE` | New constants in `ui_colors.py` | `camera-rendering.md`, `entities-system.md` |
| `COLOR_PLACEHOLDER_MAGENTA` | New constant in `engine_constants.py` | `entities-system.md` |
| i18n fallback strings | Translated FR→EN | `game-flow-spec.md` |

---

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
    engine_constants.py          [NEW] — placeholder colors
    asset_manager.py             [MODIFY] — use COLOR_PLACEHOLDER_MAGENTA
    save_manager.py              [MODIFY] — translate 3 FR occurrences
    game.py                      [MODIFY] — use COLOR_BLACK for fade surface
  ui/
    ui_colors.py                 [MODIFY] — add COLOR_BLACK, COLOR_WHITE
    speech_bubble_constants.py   [MODIFY] — add BUBBLE_CENTER_FILL, BUBBLE_NAME_TEXT_COLOR
    speech_bubble.py             [MODIFY] — use 3 new constants
    save_menu.py                 [MODIFY] — use SAVE_TITLE_COLOR at line 224; translate "Retour"→"Back"
    save_slot.py                 [MODIFY] — use COLOR_BLACK
    pause_screen_constants.py    [MODIFY] — translate _BUTTON_DEFAULTS
    pause_screen.py              [MODIFY] — use PANEL_W/PANEL_H; translate "Sauvegarder la partie"→"Save Game"
    title_screen_constants.py    [MODIFY] — add LABEL_MEASURE_COLOR; translate _MENU_ITEM_DEFAULTS, BACK_BTN_LABEL_DEFAULT
    title_screen_draw.py         [MODIFY] — use LABEL_MEASURE_COLOR; translate docstring
    title_screen.py              [MODIFY] — use COLOR_BLACK
    title_screen_lights.py       [MODIFY] — use COLOR_BLACK
  entities/
    interactive_constants.py     [MODIFY] — add PARTICLE_DEFAULT_COLOR
    interactive_particles.py     [MODIFY] — use PARTICLE_DEFAULT_COLOR
    interactive.py               [MODIFY] — translate French comment at line 383
    interactive_lighting.py      [MODIFY] — use COLOR_BLACK
    teleport.py                  [MODIFY] — use COLOR_PLACEHOLDER_MAGENTA
    pickup.py                    [MODIFY] — use COLOR_PLACEHOLDER_MAGENTA
  graphics/
    spritesheet.py               [MODIFY] — use COLOR_PLACEHOLDER_BLUE
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
Engine-level constants — placeholder and debug colors.
These colors appear in fallback/error rendering paths (never in production UI).
"""

# Placeholder colors for missing or fallback assets (debug-visible, non-production)
COLOR_PLACEHOLDER_MAGENTA: tuple[int, int, int] = (255, 0, 255)
COLOR_PLACEHOLDER_BLUE: tuple[int, int, int] = (0, 0, 255)
```

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
- `docs/specs/development-quality.md` — related quality spec: [development-quality.md](./development-quality.md)
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

### Extra Constant Adoption Found

| File | Before | After | Constant source |
|------|--------|-------|----------------|
| `src/ui/speech_bubble.py` line 261 | `(60, 40, 30)` | `COLOR_TEXT_STONE` | `src/ui/ui_colors.py` (existing) |
| `src/ui/pause_screen.py` line 91 | `(0, 0, 0)` | `COLOR_BLACK` | `src/ui/ui_colors.py` (new) |

### Intentional Exclusion (Proper Noun)

| File | String | Rationale |
|------|--------|-----------|
| `src/ui/title_screen.py` line 218 | `"L'Éveil de l'Héritier"` | Game's proper title — stays French by design. Marked with inline comment. |

