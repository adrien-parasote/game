# Strategic Blueprint — Pygame-CE / Python 3.12 Best Practices Remediation

> **Type:** Strategic Technical Remediation Plan
> **Reference:** `docs/specs/pygame_ce_python_312_best_practices.md`
> **Source Audit:** `pygame_ce_best_practices_audit.md` (2026-05-26)
> **Status:** Strategy validated — pending SPEC

---

## Problem Solved

8 technical violations documented in the pygame-ce / Python 3.12 reference guide.
Impacts gameplay stability (unclamped DT), performance (font.render in drawing loops),
portability (save paths), and maintainability (disabled Pyright, missing @override).

## Measurable Success

| Metric | Target |
|---|---|
| DT clamped everywhere | `grep "min(raw_dt"` → 2 hits (game.py, game_state_manager.py) |
| 0 `font.render` in draw() | `grep -n "font.render" src/ui/hud.py` → 0 in `draw()` |
| Saves via `get_pref_path` | `grep "get_pref_path" src/engine/save_manager.py` → 1 hit |
| Pyright `basic` → 0 errors | `pyright src/ --outputjson \| jq .summary.errorCount` = 0 |
| UI images via AssetManager | `grep -rn "pygame.image.load" src/ui/` → 0 |
| `@override` on inherited methods | `grep "@override" src/entities/player.py` → 1+ |
| Green tests | `pytest` → 0 failures |

---

## Architectural Decisions

### AD-1: TextCache — Inline Dict, No Shared Class
**Decision:** Pre-rendered dict in each component, using the same pattern as `title_screen.py:168` and `PauseScreen._make_engraved_surface()`.
**Rationale:** Conforms to ADR-006 §"No New Abstractions". The most complex component (inventory_draw) needs invalidation by mutation events, not by timers.
**Excluded:** A global `TextCache` class in `src/engine/`.

### AD-2: FRect — ADR Only, No Code Migration
**Decision:** Write ADR-008 documenting the decision NOT to migrate in Phase 1. The dual `Vector2+Rect` system is functional. Migration planned only if visible jitter occurs post-distribution.
**Excluded:** Any code changes in `base.py`, `player.py`, `groups.py`.

### AD-3: Pyright — `basic` Mode, Not `strict` (Unachievable without Pygame Stubs)
**Decision:** `"typeCheckingMode": "basic"`. `strict` is permanently excluded for this project.
**Measured Data:** `strict` generates 3,289 errors, of which 1,353 (`reportUnknownMemberType` + `reportUnknownVariableType`) stem from the lack of complete Pyright stubs for pygame-ce. These errors are **unresolvable without third-party stubs**.
**Real Fix:** Switch to `basic` + remove `reportOptional*` suppressions one by one. The 14 real `reportOptionalMemberAccess` errors will then become visible and fixable.

### AD-4: `pathlib.Path` — Distinct Optional Step, Not an Exclusion
**Revision:** The initial exclusion was lazy ("outside reference document"). `pathlib.Path` is the Python 3.12 standard.
**Decision:** This is not a violation of the reference guide, but it is a legitimate improvement. Categorized as **Optional Step 11** (mechanical refactoring of ~60 occurrences). Handled separately from violation fixes as it does not address a specific anti-pattern identified in the audit.

---

## Implementation Plan — 10 Steps

| Step | Description | Severity | Effort | Files |
|---|---|---|---|---|
| **1** | DT Clamp in all loops | 🔴 | 15 min | `game.py`, `game_state_manager.py` |
| **2** | HUD Text Cache (semi-static text) | 🔴 | 1h | `hud.py` |
| **3** | Inventory Text Cache (dynamic text) | 🔴 | 1h | `inventory_draw.py` |
| **4** | Chest Text Cache | 🔴 | 30 min | `chest_draw.py` |
| **5** | `pygame.system.get_pref_path` saves | 🟡 | 1h | `save_manager.py` |
| **6** | Centralize UI images in AssetManager | 🟡 | 2h | 8 `ui/` files |
| **7** | Pyright `basic` mode + remove Optional suppressions | 🟡 | 1-2h | `pyrightconfig.json` |
| **8** | `@override` on inherited methods | 🟢 | 30 min | `player.py`, `groups.py`, `npc.py` |
| **9** | `type` Type Aliases | 🟢 | 30 min | `render_manager.py` |
| **10** | ADR-008 FRect — evaluation and decision | 🟢 | 30 min | `docs/ADRs/ADR-008-frect.md` |
| **11** _(optional)_ | `os.path.join` → `pathlib.Path` migration | 🟢 | 2-3h | ~60 occurrences in `src/` |

**Total Estimated Effort: 9-12h**

---

## Scope — What We Do NOT Do (and Why)

| Exclusion | Precise Reason |
|---|---|
| `FRect` migration (code) | Vector2+Rect is functional. No visible jitter. Cost > immediate benefit. ADR-008 documents the decision. |
| Pyright `strict` | **Unachievable**: 1,353/3,289 errors are structurally unresolvable without complete Pyright stubs for pygame-ce. Target: `basic` only. |
| `src/map/` | No violations identified in the audit. Zero loop `font.render`, zero image loads outside AssetManager, zero unclamped DT. |
| `src/graphics/spritesheet.py` | `pygame.image.load` on line 26 is **legitimate**: loaded at entity init, not in the drawing loop. Already mocked in tests. |
| `AssetManager` internal refactoring | `AssetManager` does not change. Phase 2-C modifies the 8 UI files that *bypass* it — AssetManager itself is not refactored. |

> **Note:** `pathlib.Path` is no longer an exclusion — it is a distinct **Optional Step 11**. See the implementation plan.

---

## Open Gaps (to Resolve Before SPEC)

| # | Gap | Owner |
|---|---|---|
| **G1** | Inventory TextCache invalidation pattern (HP/GOLD/LVL setters ?) | Code + You |
| **G2** | Return type of `pygame.system.get_pref_path` in pygame-ce 2.4+ | Research |
| **G3** | `AssetManager.get_image` calls `convert_alpha` — headless crash in tests? | Code |
| **G4** | Acceptable budget for Pyright `basic` corrections? | You |

---

## Integrated Learnings

- **L-UI-011** → Pre-render cache pattern for static text (PauseScreen, SaveMenu)
- **ADR-006** → No New Abstractions — inline dict preferred over new class
- **L-UI-012** → Order: constants → source → tests
- **A-UI-002** → grep before any asset mv/rm

---

## Gap Resolution

| # | Gap | Resolution | Source |
|---|---|---|---|
| **G1** | Inventory TextCache invalidation (HP/GOLD/LVL) | `hp`, `gold`, and `level` are simple public attributes. Mutations happen only at init + inside `_apply_save_data()`. Pattern: pre-render at `InventoryUI` `__init__` + call `refresh_stats()` after `_apply_save_data()`. Identical to `SaveMenuOverlay.refresh()` (ADR-006). | Code inspection |
| **G2** | `pygame.system.get_pref_path` return type | Returns `str` in Python 3. No `bytes` handling necessary. | Web search pygame-ce docs |
| **G3** | `AssetManager.convert_alpha()` headless | `conftest.py` creates a real `pygame.HIDDEN` display. `.convert_alpha()` works. Risk-free centralization. | Code inspection |
| **G4** | Pyright `basic` budget | Type corrections **only in files modified by other Steps**. No corrections in untouched files. | Scope decision |

---

*Created: 2026-05-26 | Gaps Resolved: 2026-05-26 | Next Step: SPEC*
