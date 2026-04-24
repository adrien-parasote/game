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
