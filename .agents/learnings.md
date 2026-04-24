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


## ❌ Anti-patterns to Avoid

### 1. Hardcoded UI Interaction Keys
**ID:** A-UX-001
**Context:** Use `Settings` for all keys (e.g., `Settings.INTERACT_KEY`) instead of `pygame.K_e`.
**Why:** Prevents breaking the unified input system when porting or allowing customization.
