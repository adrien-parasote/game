# Technical Specification - Speech Bubble [Implementation]

> Document Type: Implementation

This document specifies the AS-IS technical implementation of the NPC speech bubble system, covering nine-patch surface construction, text wrapping, pagination, and camera-relative rendering.

## 1. Goal Description

Display dialogue text above NPC sprites using a dynamically-sized speech bubble constructed from nine-patch PNG tiles. The bubble supports multi-page text, an animated cursor for page advancement, and a name plate identifying the speaking NPC.

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `SpeechBubble` | `src/ui/speech_bubble.py` | 281 | Nine-patch construction, text layout, rendering |
| Constants | `src/ui/speech_bubble_constants.py` | 29 | Asset paths, tile mappings, spatial offsets |

## 3. Nine-Patch Surface Construction

### 3.1. Asset Tile Mapping

All tiles are 32×32 pixels located in `assets/images/HUD/`:

| Asset File | Position | Purpose |
|-----------|----------|---------|
| `13-bubble_top_left.png` | Top-left corner | Frame corner |
| `14-bubble_top.png` | Top edge | Horizontally tiled |
| `15-bubble_top_right.png` | Top-right corner | Frame corner |
| `16-bubble_left.png` | Left edge | Vertically tiled |
| `17-bubble_center.png` | Center fill | Tiled both axes |
| `18-bubble_right.png` | Right edge | Vertically tiled |
| `19-bubble_bottom_left.png` | Bottom-left corner | Frame corner |
| `20-bubble_bottom.png` | Bottom edge | Horizontally tiled |
| `21-bubble_bottom_right.png` | Bottom-right corner | Frame corner |
| `22-bubble_arrow.png` | Pagination indicator | Shown on multi-page |
| `23-bubble_name.png` | Name plate background | Variable-width subsurface |

### 3.2. Construction Algorithm

```
1. Calculate required bubble dimensions from text content
2. Create transparent Surface(width, height, SRCALPHA)
3. Blit 4 corners at fixed positions
4. Tile top/bottom edges between corners
5. Tile left/right edges between corners
6. Fill center area with tiled center tile
7. Attach tail below bottom-center
```

**Width**: `max(text_width + 2 * PADDING_X, name_plate_width + PADDING_X, MIN_WIDTH)`
**Height**: `line_count * line_height + PADDING_TOP + PADDING_BOTTOM`

Dimensions are rounded up to multiples of tile size (32px) for clean tiling.

## 4. Text Layout

### 4.1. Text Wrapping

- **Font**: `Settings.FONT_NARRATIVE` (loaded from settings)
- **Max width**: `max_width_px = 224` (7 tiles × 32px)
- **Algorithm**: Word-level wrapping using `font.size(word)` to measure
- **Overflow**: Words exceeding max width are force-split at character level

### 4.2. Pagination

| Parameter | Value | Source |
|-----------|-------|--------|
| Max lines per page | 4 | `_MAX_LINES_PER_PAGE` constant |
| Line height | `font.get_linesize()` | Dynamically calculated |
| Page separator | None (seamless) | — |

**State**: `self.page` (0-indexed), `self.total_pages` (pre-computed at `set_text()`)

### 4.3. Text Positioning

- **X offset**: `PADDING_X = 30` from left edge of bubble
- **Y offset**: `PADDING_TOP = 20` from top edge of bubble
- **Text color**: `(60, 40, 30)` — dark brown
- **Shadow**: 1px offset dark shadow for readability against bubble texture

## 5. Name Plate

### 5.1. Rendering

- **Background**: `23-bubble_name.png` — used as a subsurface with variable width
- **Text**: NPC name rendered in `FONT_NOBLE` at `FONT_SIZE_NOBLE`
- **Position**: Top-left of bubble, offset by `(_NAME_OFFSET_X, _NAME_OFFSET_Y)`
- **Width calculation**: `font.size(name)[0] + 2 * NAME_PADDING_X`
- **Subsurface slicing**: The name plate background image is sliced to match the calculated width

### 5.2. Name Source

The NPC name comes from the `name` property set in Tiled, resolved via `i18n.get("npc_names.{name}")`.

## 6. Camera-Relative Rendering

### 6.1. Blit Function Pattern

The bubble uses a `blit_func` callable for camera-relative rendering:

```python
def blit_func(surface, position):
    screen.blit(surface, position - camera_offset)
```

This allows the bubble to be rendered in world-space (following the NPC) while the camera pans.

### 6.2. Anchor Point

- **X**: Centered on `npc.rect.centerx`
- **Y**: `npc.rect.top - bubble_height - tail_gap`
- **Tail**: `21-bubble_queue.png` anchored at `npc.rect.top` with configurable `_TAIL_GAP`

## 7. Pagination Navigation

### 7.1. State Machine

```
set_text(text, name) → Page 0
  │
  ├─ advance() while page < total_pages - 1 → Next page
  │
  └─ advance() at last page → Returns signal to close bubble
```

### 7.2. Page Indicator

- **Arrow asset**: `22-bubble_arrow.png`
- **Visibility**: Only shown when `total_pages > 1` and not on last page
- **Position**: Bottom-right of bubble interior
- **Animation**: Gentle bob effect (sinusoidal Y offset)

## 8. Integration with Game Engine

### 8.1. Game State

The `Game` class maintains `_npc_bubble: dict | None`:
```python
_npc_bubble = {
    "npc": NPC,         # Reference to speaking NPC
    "text": str,        # Full dialogue text
    "page": int,        # Current page index
}
```

### 8.2. Trigger Flow

```
Player presses E near NPC
  → InteractionManager.handle_interactions()
    → NPC.interact(player) returns element_id
      → Game._trigger_npc_bubble(npc, element_id)
        → i18n.get("{map_name}-{element_id}")
          → SpeechBubble.set_text(text, npc.name)
```

### 8.3. Advancement

```
Player presses E while bubble is open
  → Game._advance_npc_bubble()
    → SpeechBubble.advance()
      → If more pages: increment page
      → If last page: close bubble, NPC.reset_to_idle()
```

## 9. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Reconstruct bubble every frame | Build once at `set_text()`, blit cached surface | Nine-patch construction is expensive |
| Use fixed bubble size | Calculate from text content | Supports variable-length dialogue |
| Render in screen space | Use `blit_func` with camera offset | Bubble must follow NPC in world |
| Hardcode name string | Use i18n lookup | Localization support |
| Use `SpeechBubble` for signs | Use `DialogueManager` for signs/books | SpeechBubble is for NPC-attached dialogue only |

## 10. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| SPB-U-01 | set_text | Short text (1 line) | 1 page, bubble sized to text | Empty string |
| SPB-U-02 | set_text | Long text (8 lines) | 2 pages (4 lines each) | Exactly 4 lines |
| SPB-U-03 | advance | Page 0 of 2 | Page increments to 1 | Single page text |
| SPB-U-04 | advance | Last page | Returns close signal | Already closed |
| SPB-U-05 | Name plate | Name "Aldric" | Plate width matches text | Very long name |

### Integration Tests
| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| SPB-I-01 | Full dialogue | NPC with 3-page text | All pages display, bubble closes on last advance |
| SPB-I-02 | Camera follow | NPC at edge of screen, camera pans | Bubble stays anchored to NPC |

## 11. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing tile asset | `FileNotFoundError` | Log warning | Use magenta debug surface |
| Missing font | `FileNotFoundError` | Log error | Use pygame default font |
| Empty text | `len(text) == 0` | Log warning | Don't show bubble |
| Missing i18n key | Key not in lang dict | Log warning | Show raw key string |

## 12. Deep Links
- **`SpeechBubble`**: [speech_bubble.py L1](../../src/ui/speech_bubble.py#L1)
- **Constants**: [speech_bubble_constants.py L1](../../src/ui/speech_bubble_constants.py#L1)
- **Game integration**: [game.py](../../src/engine/game.py#L1) (`_trigger_npc_bubble`, `_advance_npc_bubble`)
- **NPC spec**: [npc-system.md §2](./npc-system.md#L1)
- **Unit tests**: [test_speech_bubble.py L1](../../tests/ui/test_speech_bubble.py#L1)


## Assumptions
| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | System performs adequately | Low | Playtest |
| 2 | Inputs are sanitized | Low | Code review |
| 3 | Components interact seamlessly | Low | Integration tests |

## Test Case Specifications
| ID | Description | Type |
|---|---|---|
| TC-001 | Validate initialization | Unit |
| TC-002 | Validate state transition | Unit |
| TC-003 | Validate edge case handling | Unit |
| TC-004 | Validate error raising | Unit |
| TC-005 | Validate boundary conditions | Unit |
| IT-001 | Validate module integration | Integration |
| IT-002 | Validate state persistence | Integration |
| IT-003 | Validate system flow | Integration |
