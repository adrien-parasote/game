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

## Learning: Object Orientation vs Player Facing Direction
**Date:** 2026-04-24
**Spec:** docs/specs/INTERACTIVE_OBJECTS.md
**Outcome:** Major Rework
**Project:** Python Pygame RPG

### What happened
The player's interaction with directional objects (like chests opening to the right or left) failed because the orientation logic interpreted the object's `direction` as the required player facing direction, rather than the object's physical front side.

### Root cause
Implicit assumption that interaction direction properties describe the actor's state rather than the target's state.

### Anti-pattern (what to avoid)
❌ **Don't** treat an object's directional property (e.g., `direction='left'`) as the required player facing direction.
✅ **Do Instead** treat it as the physical orientation of the object (its front side). If an object faces left, the player must stand on its left side (`player.x < obj.x`) and face the opposite direction (`player.facing = 'right'`).

### Evidence
- Bug fix in `InteractionManager._verify_orientation` required reversing player `p_state` and verifying orthogonal positioning (`x_aligned`/`y_aligned`) against the object's physical side.

### Scope
- [x] Universal (applies across top-down 2D grid/pixel-based games)

## Learning: Pygame Surface Mocking for Blit Operations
**Date:** 2026-04-28
**Spec:** docs/specs/INTERACTIVE_OBJECTS.md (Test Hardening Cycle)
**Outcome:** Minor Rework
**Project:** Python Pygame RPG

### What happened
While writing tests for `InventoryUI` and `DialogueManager`, `TypeError: argument 1 must be pygame.surface.Surface, not MagicMock` occurred during `screen.blit()` calls. The tests mocked `pygame.font.render` and `asset_manager.get_image` with standard `MagicMock` objects.

### Root cause
Pygame's `blit` function has strict C-level type checking and does not accept Python `MagicMock` objects. It requires an actual `pygame.Surface`.

### Pattern (what to reproduce)
✅ **Do Instead:** When mocking any Pygame function that returns an image or text to be drawn, explicitly set its return value to a dummy `pygame.Surface`.
```python
# Correct Mocking Pattern for Pygame UI Tests
mock_font = MagicMock()
mock_font.render.return_value = pygame.Surface((10, 10))
mock_asset_manager.get_image.return_value = pygame.Surface((32, 32))
```

### Evidence
- Fix applied in `test_ui_extended.py` to `ui.font.render.return_value` replacing default MagicMocks with `pygame.Surface((10, 10))`.

### Scope
- [X] Project-specific (Pygame UI/Testing)
- [ ] Universal

## Learning: Entity Initialization Signature Verification
**Date:** 2026-04-28
**Spec:** Test Hardening Cycle
**Outcome:** Minor Rework
**Project:** Python Pygame RPG

### What happened
Tests for `NPC` and `InteractiveEntity` failed with `TypeError` during instantiation because the tests passed a dictionary instead of a tuple for `pos`, missed required arguments like `sprite_sheet`, and used incorrect kwarg names (`sound_effect` instead of `sfx`).

### Root cause
Test scaffolding was written based on generalized assumptions of entity data structures rather than inspecting the explicit `__init__` signatures of the target classes.

### Anti-pattern (what to avoid)
❌ **Don't:** Write test instantiations blindly based on JSON data structures without verifying the target class constructor.

### Pattern (what to reproduce)
✅ **Do Instead:** Before writing tests for a class, verify its `__init__` signature (e.g. by viewing the file or running a grep) and copy the exact parameter list into the test file as a reference.

### Evidence
- `InteractiveEntity` in `test_entities_extended.py` required explicit positional and keyword arguments matching its `def __init__(self, pos: tuple, groups: list[pygame.sprite.Group], ...)` signature.

### Scope
- [ ] Project-specific
- [X] Universal (Testing practices)

## Learning: Guard Clauses and Hidden UI State in Tests
**Date:** 2026-04-28
**Spec:** Test Hardening Cycle
**Outcome:** Minor Rework
**Project:** Python Pygame RPG

### What happened
Initial attempts to test `InventoryUI.draw()` resulted in 0% coverage increase for that method despite calling it in tests.

### Root cause
The `InventoryUI` class contains a guard clause `if not self.is_open: return`. Because `is_open` defaults to `False`, the test immediately returned without executing any drawing logic.

### Anti-pattern (what to avoid)
❌ **Don't:** Call update/draw methods in UI tests without explicitly initializing the component's visibility/active state flags.

### Evidence
- Coverage increased only after setting `ui.is_open = True` before calling `ui.draw(screen)` in `test_ui_extended.py`.

### Scope
- [X] Project-specific (UI Architecture)
- [ ] Universal

## Learning: Hardcoded Mock Lengths for Data-Driven Assets
**Date:** 2026-04-28
**Spec:** docs/specs/engine-core.md
**Outcome:** Minor Rework
**Project:** Python Pygame RPG

### What happened
After updating the emotes spritesheet from 4 columns to 5 columns in the engine logic, `test_emotes.py` failed with `IndexError: list index out of range`.

### Root cause
The unit test hardcoded the mock grid size to exactly 32 frames (`[pygame.Surface] * 32`), tightly coupling the test to the previous implementation detail of exactly 4 columns.

### Anti-pattern (what to avoid)
❌ **Don't** hardcode exact sequence lengths in mock returns for data-driven assets (like grid structures) unless the test specifically validates that exact length constraint.
✅ **Do Instead** either dynamically calculate the mock size based on the tested variables, use an oversized mock (e.g., `* 100`) if the exact length is irrelevant, or remember to explicitly update associated mocks when changing spec constraints (like grid dimensions).

### Evidence
- `tests/test_emotes.py::test_emote_manager_trigger` failed when the new extraction logic requested `index + i * 5` (which accessed indices > 31) because the mock returned a fixed list of 32 items.

### Scope
- [ ] Project-specific
- [X] Universal (Testing practices)

## Learning: State Mutation Requires Test Mock Updates

**Date:** 2026-04-28
**Spec:** Stabilization Implementation Plan
**Outcome:** Minor Rework
**Project:** RPG Engine

### What happened
We added `layer_order` as a required field in the `MapManager` state. The actual engine logic was updated correctly, but a legacy unit test (`test_map_manager_viewport_culling`) failed because its mocked data payload lacked the new `layer_order` field, causing the logic to return an empty array.

### Root cause
The spec explicitly stated what to change in the business logic but did not explicitly specify that test mock payloads must be updated to reflect the newly mutated state expectations.

### Anti-pattern (what to avoid)
❌ Changing state requirements in business logic without explicitly specifying the test mocks that need to be updated.

### Evidence
- `test_map_manager_viewport_culling` failed with `AssertionError: assert 0 == 4` because `layer_order` was empty in the mocked `map_result`.

### Scope
- [ ] Project-specific
- [x] Universal
