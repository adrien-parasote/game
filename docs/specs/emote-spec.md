> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification - Emote System [Implementation]

> Document Type: Implementation

This document specifies the AS-IS technical implementation of the player emote system, covering the emote manager, animated sprites, and trigger conditions.

## 1. Goal Description

Provide visual feedback to the player through animated emote bubbles that appear above the player character in response to proximity events, failed interactions, and inventory overflow. The system uses a sprite-sheet based animation with a rise-and-fade lifecycle.

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `EmoteManager` | `src/entities/emote.py` | 59 | Asset loading, trigger dispatch, sprite group management |
| `EmoteSprite` | `src/entities/emote_sprite.py` | 45 | Animated sprite with rise-and-fade lifecycle |

## 3. EmoteManager

### 3.1. Initialization

- **Asset path**: `assets/images/sprites/04-emotes.png`
- **Grid**: 5 columns × 8 rows (loaded via `SpriteSheet.load_grid(5, 8)`)
- **Storage**: Frames stored as a flat list indexed `[col * 8 + row]`

### 3.2. Emote Type Mapping

| Emote Name | Column Index | Trigger |
|------------|-------------|---------|
| `love` | 0 | Reserved for future NPC affinity |
| `bored` | 1 | Reserved for NPC idle state |
| `interact` | 2 | Player within 48px of interactive object/NPC |
| `question` | 3 | Failed interaction (no target, wrong side) |
| `frustration` | 4 | Inventory full on pickup attempt |

### 3.3. Trigger API

```python
def trigger(self, emote_name: str, entity) -> None
```

**Behavior**:
1. Look up column index from emote name
2. Extract 8 frames for that column: `frames[col*8 : col*8 + 8]`
3. Clear the `emote_group` (replacement policy — only 1 active emote per entity)
4. Create `EmoteSprite` with frames and entity reference
5. Add to `emote_group` for rendering
6. Play SFX: `03-emote.ogg` via `AudioManager.play_sfx()`

### 3.4. Rendering

- Emotes are rendered in `RenderManager` **after** the HUD layer (Pass 6)
- Camera offset is applied manually from `CameraGroup.offset`
- This ensures emotes are always visible on top of all game elements

## 4. EmoteSprite

### 4.1. Animation Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Duration | 0.6 seconds | Hardcoded |
| Frame count | 8 | Spritesheet rows per emote column |
| Frame interval | `0.6 / 8 = 0.075s` | Calculated |
| Rise distance | 15 pixels | Linear interpolation upward |
| Start position | `entity.rect.top` (X centered) | Entity's visual top |

### 4.2. Lifecycle

```
SPAWN → ANIMATE (0.6s) → SELF-DESTRUCT
  │         │
  │         ├─ frame_index increments every 75ms
  │         ├─ position.y decreases by (15 * progress) px
  │         └─ follows entity.rect.centerx
  │
  └─ kills itself from all groups on completion
```

### 4.3. Follow Logic

During its entire lifetime, the emote sprite:
- **X**: Pinned to `entity.rect.centerx` (follows horizontal movement)
- **Y**: `entity.rect.top - rise_offset` where `rise_offset = 15 * (elapsed / duration)`

This ensures the emote stays correctly positioned even if the player moves during the animation.

### 4.4. `update(dt)` Implementation

```python
def update(self, dt):
    self._elapsed += dt
    if self._elapsed >= self._duration:
        self.kill()
        return
    
    progress = self._elapsed / self._duration
    frame_idx = min(int(progress * len(self._frames)), len(self._frames) - 1)
    self.image = self._frames[frame_idx]
    
    rise = int(self._rise_px * progress)
    self.rect.midbottom = (self._entity.rect.centerx, self._entity.rect.top - rise)
```

## 5. Cooldown System

Emote triggering is rate-limited by the `InteractionManager`:
- **Proximity emotes** (`interact`): 1.5s cooldown between triggers
- **Fail feedback** (`question`): No cooldown (immediate feedback)
- **Inventory full** (`frustration`): No cooldown

The cooldown prevents sprite stacking when the player stands near multiple interactive objects.

## 6. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| 1 | Emotes have a fixed 8-frame duration. | Low | Spritesheet uses a 5x8 grid. |
| 2 | Emote is always shown above the entity. | Low | Fixed -15px offset applied. |
| 3 | Only one emote can be active per entity. | Medium | Group is emptied before spawn. |

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Stack multiple emotes | Use replacement policy (`empty()` group first) | Visual clutter and sprite leak |
| Create emote every frame in proximity | Gate with 1.5s cooldown timer | Frame-by-frame spam creates dozens of sprites |
| Render emotes before HUD | Render after HUD (Pass 6) | Ensures visibility over dialogue/inventory |
| Use `pygame.Sprite` groups for particles | Reserve sprites for emotes only | Emotes need group membership for camera offset |
| Hardcode frame positions | Use column-based indexing from spritesheet grid | Supports adding new emote types via new columns |

## 7. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-001 | EmoteManager.trigger | `"interact"`, entity | EmoteSprite added to group | Invalid emote name |
| TC-002 | EmoteSprite.update | dt=0.3 (half duration) | Frame index ~4, risen ~7px | dt=0 |
| TC-003 | EmoteSprite.update | dt=0.7 (past duration) | Sprite killed from group | Exactly 0.6s |
| TC-004 | Replacement | Trigger twice rapidly | Only 1 sprite in group | Same entity, different emote |
| TC-005 | EmoteManager init | Empty args | Group is initialized | Missing assets |

### Integration Tests
| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| IT-001 | Proximity trigger | Player at 40px from object | `interact` emote triggered after cooldown |
| IT-002 | Failed interaction | Player presses E with no target | `question` emote triggered |
| IT-003 | EmoteManager column | Trigger `'frustration'` | Column 4 frames are loaded |
| IT-004 | Emote chaining | Trigger A then B rapidly | Emote A killed immediately, B starts |
| IT-005 | Pickup full inventory | `_check_pickup_interactions` with full inv | `frustration` emote triggered, no dialogue |

### Linked Test Functions
| Test ID | Test Function | File |
|---------|---------------|------|
| IT-003 | `test_emote_manager_spritesheet_error` | `../../tests/entities/test_entities.py:L363` |
| IT-004 | `test_emote_manager_chaining` | `../../tests/entities/test_entities.py:L394` |
| IT-005 | `test_handle_interaction_pickup_partial` | `../../tests/engine/test_interaction.py:L141` |

## 8. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing spritesheet | `FileNotFoundError` | Log error | Use blue fallback surfaces |
| Invalid emote name | KeyError in column map | Log warning | No emote triggered |
| Entity without rect | `AttributeError` | Log error | Skip emote creation |
| SFX play failure | `pygame.error` | Log warning | Silent emote (visual only) |

## 9. Deep Links
- **`EmoteManager`**: [emote.py L1](../../src/entities/emote.py#L1)
- **`EmoteSprite`**: [emote_sprite.py L1](../../src/entities/emote_sprite.py#L1)
- **Trigger from InteractionManager**: [interaction.py L1](../../src/engine/interaction.py#L1)
- **Rendering (Pass 6)**: [render_manager.py L1](../../src/engine/render_manager.py#L1)
- **Emote section in engine-core**: [engine-core.md §S](../../docs/specs/engine-core.md#L1)

