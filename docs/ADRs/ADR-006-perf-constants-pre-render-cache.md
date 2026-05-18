# ADR-006 — Pre-render Cache Pattern for Static UI Surfaces

**Date:** 2026-05-07  
**Status:** ✅ Accepted — Implemented (commit `perf-constants`)

---

## Context

The game engine suffered from three categories of technical debt that impacted runtime performance and code maintainability:

1. **Per-frame Surface Allocations**: `_blit_halo_text()` (shared between `pause_screen.py`, `save_menu.py`, `title_screen_draw.py`) allocated a new `pygame.Surface` and executed a `gaussian_blur()` at 60 FPS during hover states. `chest_draw._draw_title()` instantiated a `Font` object on every single draw frame. `hud.draw()` instantiated `I18nManager()` per frame.
2. **Orphaned Magic Numbers**: 40+ RGB tuples, pixel offsets, font sizes, and engraving colors were hardcoded directly within five non-constants UI files (`save_menu.py`, `pause_screen.py`, `chest_draw.py`, `dialogue.py`, `lighting.py`), violating the established `_constants.py` architecture.
3. **A French Comment** in `game_state_manager.py:133` violating the all-English codebase policy.

## Decision

**Pre-render Cache Pattern**: Compute static text surfaces once during `__init__` (or within a `refresh()` method for dynamic data-bound text), store them in a `dict[key → Surface]`, and invalidate them only when the underlying source data changes. This pattern was already successfully used in `title_screen.py` (line 168).

**No New Abstractions**: Do not introduce any new wrapper classes. Extend existing `_constants.py` files or create dedicated constants files (e.g. `save_menu_constants.py`).

| Optimization | Before | After |
|---|---|---|
| Surface allocations in `_blit_halo_text` per frame | 2 allocations + 1 gaussian_blur per hovered item | 0 (pre-rendered at init/refresh) |
| Font object instantiated in `_draw_title()` | 1 instantiation per frame (60×/sec) | 0 (cached in mixin init) |
| `I18nManager()` instantiation in `draw()` | 1 instantiation per frame | 0 (cached in `__init__`) |
| Magic values hardcoded in UI modules | 40+ | 0 (centralized in constants) |

## Rejected Alternatives

| Alternative | Reason for Rejection |
|---|---|
| NumPy vectorization of `_create_beam_surface()` | Out of scope; requires a separate dedicated design spec |
| Introducing a new UI library abstraction layer | Unnecessary overhead; expanding existing patterns is fully sufficient |
| Modifying the global asset pipeline | Out of scope; this is a pure code refactor |

## Consequences

**Positive:**
- Zero `pygame.Surface` allocations in draw hot paths (pause menu, save menu, HUD).
- Fully completed `_constants.py` architecture: all UI modules now have a dedicated constants file.
- Clean refactoring: zero changes to observable in-game behavior.

**Constraints / Negatives:**
- Pre-rendered surfaces must be explicitly invalidated and rebuilt when source data changes (e.g. `SaveMenuOverlay.refresh()` reconstructs `_cached_title_surfs`).
- Adopt the `_rendered_idle` / `_rendered_hover` pattern: maintain two separate surface lists, with `draw()` indexing them based on hover state.

## Modified Files

| File | Changes |
|---------|-----------|
| `src/ui/pause_screen.py` | `_make_engraved_surface()` + `_make_halo_surface()` pre-rendered at `__init__` |
| `src/ui/save_menu.py` | `_cached_title_surfs` pre-rendered at `refresh()` |
| `src/ui/chest_draw.py` | Font cached in the mixin `__init__` |
| `src/ui/hud.py` | Cached `self._i18n = I18nManager()` in `__init__` |
| `src/ui/save_menu_constants.py` | *(New file)* 15 centralized constants |
| `src/ui/pause_screen_constants.py` | +12 new constants |
| `src/engine/lighting_constants.py` | Defined `BEAM_COLOR_MOON` and `BEAM_COLOR_SUN` |
| `src/ui/dialogue_constants.py` | Mapped `DIALOGUE_SHADOW_COLOR` and `DIALOGUE_TEXT_COLOR` |
| `src/ui/chest_constants.py` | Centralized `CHEST_TITLE_TEXT`, `CHEST_TEXT_COLOR`, and `CHEST_SLOT_FALLBACK_COLOR` |
| `src/engine/game_state_manager.py` | Translated the French comment at line 133 to English |

## References

- Learning `L-UI-011` — Pre-render cache pattern (`.agents/learnings/ui.md`).
- Learning `L-UI-012` — Constants-first refactor order (`.agents/learnings/ui.md`).
- Original Strategic Spec: `docs/strategic/perf-constants-audit-strategy.md` *(archived — this ADR represents its canonical form)*.
