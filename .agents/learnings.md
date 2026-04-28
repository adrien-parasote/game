# Project Learnings Registry

This document tracks universal patterns and anti-patterns extracted from the BUILD→HARDEN cycles of this project.

## ✅ Patterns to Reproduce

### 1. Game Engine: Footprint-Based Interaction
**ID:** L-GAME-001
**Source:** [INTERACTIVE_OBJECTS.md:L79](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/INTERACTIVE_OBJECTS.md)
**Pattern:** Decouple the visual sprite position (midbottom alignment) from the logical interaction center (footprint center).
**Why:** Supports varied asset sizes and tall sprites without breaking grid-consistent interaction math.

### 2. Spec: Procedural Geometry/Textures
**ID:** L-SPEC-001
**Source:** [INTERACTIVE_OBJECTS.md:L80](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/INTERACTIVE_OBJECTS.md)
**Pattern:** In implementation specs, define procedural assets by **Boundary Values** (Start, End, Step/Falloff) rather than prose descriptions.
**Why:** Eliminates ambiguity in generation loops (e.g., center-to-edge alpha gradients).

### 3. Rendering: Additive Light Overlays
**ID:** L-REND-001
**Source:** [INTERACTIVE_OBJECTS.md:L81](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/INTERACTIVE_OBJECTS.md)
**Pattern:** Apply additive (`BLEND_ADD`) light sources AFTER applying global darkness surfaces.
**Why:** Light sources must "cut through" the darkness. Applying before the darkness would cause the source to be dimmed by the overlay.

### 4. UI: Pre-paginated Dialogue Logic
**ID:** L-UI-001
**Source:** [src/ui/dialogue.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/dialogue.py)
**Pattern:** Pre-wrap and group lines into fixed-size pages at the start of a dialogue, rather than wrapping on-the-fly during typewriter effect.
**Why:** Ensures stable page breaks and simplifies multi-stage progression logic (skip -> next -> close).

### 5. Test: State-Flag Mocking
**ID:** L-TEST-001
**Pattern:** When mocking classes that provide internal state flags (e.g., `valid`, `initialized`), always ensure the mock instance has these flags explicitly set to `True`.
**Why:** Prevents misleading `AttributeError` or logic bypasses in systems that use these flags as gates (e.g., `SpriteSheet.valid`).

### 6. Test: Gated State Transitions
**ID:** L-TEST-002
**Pattern:** For state-machine logic (animations, interactions), always include explicit `update(dt)` steps between operations in unit tests.
**Why:** Many operations (like `interact`) are gated by "busy" flags (like `is_animating`). `update` is required to clear these gates and allow consecutive operations to succeed.

### 7. Architecture: Composite Resource Scoping
**ID:** L-ARCH-001
**Pattern:** Use composite keys (`{map_base_name}-{element_id}`) for global resource lookups (Dialogue, WorldState).
**Why:** Prevents ID collisions across map boundaries and ensures resource uniqueness in a modular world.

### 8. Map: Deterministic Semantic Layering
**ID:** L-MAP-001
**Pattern:** Sort map layers primarily by name-based semantic prefixes (e.g., `00-layer`, `01-layer`) rather than Tiled's internal JSON order.
**Why:** Tiled IDs change; names are deterministic and allow background layers to be explicitly prioritized in a flattened group-recursive structure.

### 9. UX: Interruption-First Feedback Chaining
**ID:** L-UX-001
**Pattern:** Allow new visual feedback triggers (emotes, effects) to clear/overwrite existing ones immediately rather than waiting for the previous animation to complete.
**Why:** Prevents the game from feeling "stuck" or unresponsive when multiple interaction triggers occur in rapid succession.

### 10. Test: Centralized Headless Initialization
**ID:** L-TEST-003
**Pattern:** Consolidate Pygame initialization, headless environment variables (SDL_VIDEODRIVER=dummy), and global fixtures in `tests/conftest.py`.
**Why:** Reduces drift between test files, simplifies imports, and ensures a consistent environment for CI/CD.

### 11. Test: Native Object State Positioning
**ID:** L-TEST-004
**Pattern:** Instead of mocking methods on built-in types (like `pygame.Rect.collidepoint`), manipulate the object's properties (like `topleft` or `width`) to force the desired logical outcome.
**Why:** Native Pygame objects are often implemented in C and their methods are read-only, making them impossible to mock directly.


## ❌ Anti-patterns to Avoid

### 1. Hardcoded UI Interaction Keys
**ID:** A-UX-001
**Context:** Use `Settings` for all keys (e.g., `Settings.INTERACT_KEY`) instead of `pygame.K_e`.
**Why:** Prevents breaking the unified input system when porting or allowing customization.

### 2. Blind __init__ Mocking
**ID:** A-TEST-001
**Anti-pattern:** Patching `__init__` on a class without manually recreating its mandatory public attributes.
**Why:** Dependent objects will crash on `AttributeError` when trying to read configuration flags that were never initialized.

### 3. Ambiguous Spritesheet Definitions
**ID:** A-SPEC-001
**Anti-pattern:** Defining a spritesheet asset as "animated" in a spec without explicitly stating the grid layout (rows × columns) and frame mapping.
**Why:** Leads to static frames or incorrect slicing (e.g. slicing 4x1 instead of 4x8), causing "pas en mode animation" bugs.

### 4. Unthrottled Spatial Polling
**ID:** A-GAME-001
**Anti-pattern:** Running continuous proximity checks (`distance_to < range`) that trigger visual/audio side-effects without an explicit time-based cooldown.
**Why:** Causes effect stacking, sprite duplication, or frame-by-frame spam when the logic group clears the state asynchronously or conditionally.

### 5. Index-Based Layer Priority
**ID:** A-MAP-001
**Anti-pattern:** Relying on Tiled's internal JSON list order or layer IDs for rendering priority.
**Why:** Moving layers in Tiled or using nested groups unpredictably changes the rendering order, causing background layers to pop over sprites.

### 6. Over-Conservative Feedback Gates
**ID:** A-UX-002
**Anti-pattern:** Guarding a visual feedback trigger (like an emote) behind a check that requires the previous animation to finish (`if len(group) == 0`).
**Why:** Breaks input chaining and feedback responsiveness, making the UI feel sluggish.

### 7. Tile vs Pixel Coordinate Mixups
**ID:** A-GAME-002
**Anti-pattern:** Passing world pixel coordinates to functions that expect grid (tile) indices, or vice-versa, without explicit validation or conversion.
**Why:** Causes out-of-bounds errors or silent logic failures (e.g., `is_collidable` returning `True` because it treats a pixel coordinate of 128 as a tile index out of bounds).

### 8. Singleton State Pollution
**ID:** A-TEST-002
**Anti-pattern:** Modifying global configuration objects (like `src.config.Settings`) during a test without restoring the original state.
**Why:** Causes non-deterministic failures in unrelated test files depending on the execution order (State Leakage).


## Learning: Deterministic Semantic Layer Rendering
**Date:** 2026-04-28
**Spec:** Stabilization Implementation Plan
**Outcome:** Major Rework
**Project:** RPG Engine

### What happened
Relying on Tiled's internal layer order or simple overrides for specific IDs failed when the map structure used nested groups. The `00-layer` (background) disappeared because it was pushed to the end of the rendering order.

### Root cause
Tiled JSON layer list order is not a stable proxy for semantic depth when groups are involved.

### Anti-pattern (what to avoid)
❌ **Don't** rely on the Tiled list order for critical rendering priorities (like background/foreground).

### Pattern (what to reproduce)
✅ **Do Instead** use a semantic naming convention (e.g., `00-layer`, `01-layer`) and perform an explicit sort by name in the `MapManager` before rendering.

### Evidence
- `MapManager.layer_order` updated to `sorted(raw_order, key=lambda lid: self.layer_names.get(lid, ""))`.
- `tests/test_map.py` verified nested group layers are rendered in the correct numeric prefix order.

### Scope
- [x] Universal (applies to any data-driven 2D tile engine)


## Learning: Interruption-First Feedback Chaining
**Date:** 2026-04-28
**Spec:** Stabilization Implementation Plan
**Outcome:** Minor Rework
**Project:** RPG Engine

### What happened
The player's emotes were blocked if another was active, causing rapid interactions to fail silently.

### Root cause
Over-conservative safety check: `if len(self.emote_group) == 0: return`.

### Anti-pattern (what to avoid)
❌ **Don't** block visual feedback triggers (emotes, sounds, effects) based on the completion of the previous instance.

### Pattern (what to reproduce)
✅ **Do Instead** clear the existing group or overwrite the state immediately to provide instant feedback for the latest user action.

### Evidence
- Refactored `InteractionManager._check_proximity_emotes` to clear `emote_group` before adding new sprites.
- Verified in `tests/test_interaction.py`.

### Scope
- [x] Universal (applies to UI/UX responsiveness in any interactive software)


## Learning: Domain-Based Test Consolidation
**Date:** 2026-04-28
**Spec:** Stabilization Implementation Plan
**Outcome:** Minor Rework
**Project:** RPG Engine

### What happened
Moving from scattered test files to domain modules broke multiple tests due to missing local imports, stale mocks, and environment-dependent pygame initialization.

### Root cause
High coupling between test files and their specific local mock setups, combined with fragmented initialization boilerplate.

### Pattern (what to reproduce)
✅ **Do Instead** Use `conftest.py` for all global fixtures (Headless Pygame, Asset Mocking) and organize tests into semantic domains (`engine`, `map`, `ui`, `interaction`).

### Evidence
- Consolidated 11 test files into 6 domain-based modules with 100% pass rate.
- Shared fixtures moved to `tests/conftest.py`.

### Scope
- [ ] Project-specific
- [x] Universal (Testing practices)
