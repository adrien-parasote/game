# Technical Spec: Engine & Test Optimization

> Document Type: Implementation


This document specifies the technical implementation of performance and structural optimizations.

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Recalculate text wrapping every frame | Pre-calculate lines during pagination | Performance waste on static text |
| Use `SysFont` for core UI | Use loaded TTF files | Consistency across platforms |
| Keep interaction logic in `Game` | Delegate to `InteractionManager` | `Game.py` is becoming a "God Object" |
| Have 30+ tiny test files | Group by logical component | Reduces test suite noise and overhead |
| Ignore coverage for UI modules | Implement edge-case tests for HUD/Dialogue | Critical user-facing components need verification |

## Component: DialogueManager Optimization

### Logic: Pre-calculated Wrapping
- **Trigger**: `start_dialogue` or `advance` (when changing page).
- **Process**:
    1. During `_paginate`, calculate the full list of lines for each page.
    2. Store as `self._pages: list[list[str]]`.
    3. In `draw`, only determine which *characters* of the current lines to show based on `_page_char_index`.
    4. **Optimization**: Pre-render each line's shadow and main text if possible, though blitting characters for typewriter effect might still require standard blits.

### Unit Tests Required
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-DLG-01 | Pagination | Very long text | Correct number of pages | Empty string, single word |
| TC-DLG-02 | Typewriter | `dt` updates | `displayed_text` matches index | Speed=0, extreme `dt` |
| TC-DLG-03 | Advancing | Skip input | Page complete immediately | Last page closes |

## Component: InteractionManager Extraction

### Logic: Spatial Hash (Optional but Recommended)
- Instead of iterating through all interactives/NPCs, maintain a spatial grid or simply optimized group checks.
- Extract `_handle_interactions`, `_facing_toward`, and `_is_collidable` from `Game` into `InteractionManager`.

### Integration Tests Required
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-INT-01 | Spatial Interaction | Spawn NPC at (X,Y) | Player at (X,Y-32) facing DOWN triggers | Clear groups |
| IT-INT-02 | Chain Interaction | Object A triggers Object B | Object B state toggles | Clear WorldState |

## Component: RenderManager Extraction

### Logic: Scene Rendering Decoupling
- Extract all rendering hooks (`_draw_background`, `_draw_foreground`, `_draw_hud`, `_draw_scene`) from `game.py` into a new `RenderManager` class.
- The `RenderManager` initializes with a reference to `Game` to access the `map_manager`, `visible_sprites`, `lighting_manager`, etc.
- In `game.py`, replace the `_draw_scene()` definition with `self.render_manager.draw_scene()`.

## Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging |
|------------|-----------|----------|----------|---------|
| Font Missing | `pygame.font.SysFont` returns None | Use default system font | `pygame.font.Font(None, size)` | ERROR |
| Missing Map Asset | `os.path.exists` fails | Log error, stay on current map | Return to spawn point | CRITICAL |
| Invalid Target ID | `find_entity` returns None | Log warning, ignore interaction | No-op | WARN |

## Deep Links
- **`engine-core.md`**: [engine-core.md L1](./engine-core.md#L1)
- **`RenderManager`**: [render_manager.py L1](../../src/engine/render_manager.py#L1)
- **`InteractionManager`**: [interaction.py L1](../../src/engine/interaction.py#L1)
- **`DialogueManager`**: [dialogue.py L1](../../src/ui/dialogue.py#L1)
- **`Game._draw_scene`**: [game.py L509](../../src/engine/game.py#L509)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-DLG-01 | `test_dialogue_pagination` | `tests/ui/test_inventory.py:L238` |
| IT-INT-01 | `test_handle_interaction_npc` | `tests/engine/test_interaction.py:L169` |
| IT-INT-02 | `test_interaction_toggle_entity_by_id` | `tests/engine/test_interaction.py:L513` |