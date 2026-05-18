# ~~Strategic Blueprint — Performance & Constants Hardening~~

> ⚠️ **ARCHIVED — 2026-05-15**  
> The content of this document has been promoted to **[ADR-006](../ADRs/ADR-006-perf-constants-pre-render-cache.md)** (validated architectural decision).  
> Kept for historical traceability only. **Reference ADR-006 instead.**

> ✅ **This document is COMPLETED.** All described implementations were completed in the 2026-05-07 session.  
> Kept for historical reference. Do not re-implement.

# Strategic Blueprint — Performance & Constants Hardening

## Q1. What exact problem are you solving?

The game engine has three categories of technical debt that degrade runtime
performance and code maintainability:

1. **Per-frame Surface allocations** — `_blit_halo_text()` (shared across
   `pause_screen.py`, `save_menu.py`, `title_screen_draw.py`) allocates
   `pygame.Surface` + runs `gaussian_blur()` at 60 FPS during hover states.
   `chest_draw._draw_title()` instantiates a Font object every draw frame.
   `hud.draw()` constructs `I18nManager()` every frame.

2. **Orphaned magic values** — 40+ RGB tuples, pixel sizes, font sizes, and
   engraving colors are hardcoded inline in 5 non-constants files
   (`save_menu.py`, `pause_screen.py`, `chest_draw.py`, `dialogue.py`,
   `lighting.py`), violating the established `_constants.py` architecture.

3. **One French comment** — `# Sauvegarder button` in
   `game_state_manager.py:133` violates the all-English comment policy.

## Q2. Success Metrics

| Metric | Before | After |
|---|---|---|
| Surface allocs in `_blit_halo_text` per frame | 2 allocs + 1 gaussian_blur per hovered item | 0 (all pre-rendered at init/hover-change) |
| Font object created in `_draw_title()` | 1 per frame (60×/s) | 0 (cached in mixin init) |
| `I18nManager()` constructed in `draw()` | 1 per frame | 0 (cached in `__init__`) |
| Inline magic values in non-constants files | 40+ | 0 |
| French words in source comments | 1 | 0 |
| Regressions in 647 tests | — | 0 |

## Q3. Why is this the right approach?

The project already enforces the `_constants.py` architecture (confirmed in
CODEMAPS/architecture.md: "100% localized to English," "all UI modules have
dedicated `_constants.py`"). This change **completes** the existing pattern
rather than introducing a new one. Risk of regression is minimal: all
changes are pure refactors (rename, move to constant, pre-render cache).

## Q4. Core Architecture Decision

**Pre-render cache pattern**: static text surfaces computed once at
`__init__` (or `refresh()` for data-dependent text), stored as `dict[key →
Surface]`, invalidated only when source data changes. This is already used
in `title_screen.py` (line 168: "Pre-render idle menu label surfaces").

No new abstractions. No new classes. Extend existing `_constants.py` files
or create one new file (`save_menu_constants.py`).

## Q5. Tech Stack Rationale

Pure Python/Pygame-CE. No new dependencies. All changes are:
- Move literals → constants
- `self._cache[key] = surface` pattern (already used in `AssetManager`)
- One `import` line addition per migrated file

## Q6. Feature List (implementation order)

| # | Feature ID | Description | Files |
|---|---|---|---|
| 1 | P-FR-01 | Fix French comment | `game_state_manager.py:133` |
| 2 | P-CONST-01a | Add `BEAM_COLOR_MOON/SUN` to `lighting_constants.py`, use in `lighting.py` | 2 files |
| 3 | P-CONST-01b | Add `DIALOGUE_SHADOW_COLOR/TEXT_COLOR` to `dialogue_constants.py`, use in `dialogue.py` | 2 files |
| 4 | P-CONST-01c | Add `CHEST_TITLE_TEXT`, `CHEST_TEXT_COLOR`, `CHEST_SLOT_FALLBACK_COLOR` to `chest_constants.py`, use in `chest_draw.py` | 2 files |
| 5 | P-CONST-01d | Extend `pause_screen_constants.py` with 12 new constants, update `pause_screen.py` | 2 files |
| 6 | P-CONST-01e | Create `save_menu_constants.py` (15 constants), update `save_menu.py` | 1 new + 1 modified |
| 7 | P-PERF-01a | Cache `I18nManager` in `hud.py.__init__` | 1 file |
| 8 | P-PERF-01b | Cache font in `chest_draw._draw_title` (move to mixin init) | 1 file |
| 9 | P-PERF-01c | Pre-render halo/engraved button surfaces in `pause_screen.py` | 1 file |
| 10 | P-PERF-01d | Pre-render title + slot texts in `save_menu.py` | 1 file |

## Q7. What we are NOT building

- No NumPy vectorization of `_create_beam_surface()` (separate spec needed)
- No asset pipeline changes or new file formats
- No new UI components or features
- No changes to `title_screen.py` (halo already pre-rendered at line 168)
- No changes to test assertions (refactor only, observable behavior unchanged)
