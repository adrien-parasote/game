# SPEC: Emote System Update

> Document Type: Implementation


## Goal
Improve emote responsiveness, and ensure chaining works correctly.

## Proposed Changes

- Ensure `trigger` effectively kills existing emotes to prevent overlap.

### [MODIFY] [emote_sprite.py](file:///Users/adrien.parasote/Documents/perso/game/src/entities/emote_sprite.py)
- Set default `duration` to `0.6` (configurable via `Settings`).
- Accelerate the `rise_offset` to match the shorter duration.

- In `_check_pickup_interactions`, confirm that no dialogue box is triggered when inventory is full.

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Overlap multiple emotes | Kill previous emote on new trigger | Visual clutter and confusion |
| Hardcode durations | Use `Settings` for animation speeds | Easier tuning and optimization |
| Block player for emotes | Emotes should be non-blocking overlays | Keep the game flow smooth |
| Use large sprites for emotes | Keep emotes compact (e.g. 16x16 or 24x24) | Avoid obscuring character details |
| Trigger emotes too frequently | Use a cooldown (e.g. 0.5s) | Prevent flashing and visual noise |

## Test Case Specifications

| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-EMO-01 | EmoteManager | Trigger 'frustration' | Column 4 frames are loaded |
| TC-EMO-02 | EmoteManager | Trigger A then B | Emote A is killed immediately, B starts |
| TC-EMO-03 | Interaction | Pickup with full inv | `frustration` emote triggered, no dialogue |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Sprite | Sprite index out of range | Log error | Skip emote trigger |

## Deep Links
- **`EmoteSprite` class**: [emote_sprite.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/entities/emote_sprite.py#L1)
- **Emote trigger**: [emote.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/entities/emote.py#L1)
- **Interaction (pickup full inv)**: [interaction.py L141](file:///Users/adrien.parasote/Documents/perso/game/src/engine/interaction.py#L141)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-EMO-01 | `test_emote_interruption` | `tests/engine/test_interaction.py:L41` |
| TC-EMO-02 | `test_emote_interruption` | `tests/engine/test_interaction.py:L41` |
| TC-EMO-03 | `test_handle_interaction_pickup_partial` | `tests/engine/test_interaction.py:L141` |