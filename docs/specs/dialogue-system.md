# Technical Specification — Dialogue & Speech Bubble Systems [Implementation]

> **Document Type:** Implementation
> **Source Files:** `src/ui/dialogue.py`, `src/ui/speech_bubble.py`, `src/ui/dialogue_constants.py`, `src/ui/speech_bubble_constants.py`

This specification consolidates the implementation of the bottom Dialogue Box (DialogueManager) and the world-space NPC Speech Bubble systems.

---

## 1. Dialogue Systems Comparison

The engine supports two distinct dialogue systems based on semantic intent:

| Feature | DialogueManager (Dialogue Box) | SpeechBubble |
|---------|---------------------------------|--------------|
| **Position** | Screen space (bottom-fixed `midbottom`) | World space (anchored above NPC sprite) |
| **Speaker** | Global narrator or speaker title | Specific NPC (includes name plate) |
| **Construction** | Single-stretched texture backdrop | Dynamic nine-patch tiled surface |
| **Animation** | Sequential typewriter character reveal | Instant reveal of the current page |
| **Use Case** | Signs, books, narration, main story beats | NPC-attached conversations |

---

## 2. DialogueManager (Bottom Box)

Renders a bottom-fixed dialogue frame with progressive typewriter animation.

### 2.1 State Machine
```
INACTIVE ──start_dialogue()──→ TYPING ──(page complete)──→ PAGE_COMPLETE
                                 ↑                              │
                                 │                     advance()│
                                 │                     (more pages)
                                 └──────────────────────────────┘
                                                         │
                                                advance()│(last page)
                                                         ↓
                                                      INACTIVE
```

The `DialogueManager` uses a boolean `_is_page_complete` flag to track the conceptual states:
- **INACTIVE**: `is_active == False`
- **TYPING**: `is_active == True` and `_is_page_complete == False`
- **PAGE_COMPLETE**: `is_active == True` and `_is_page_complete == True`

### 2.2 Text wrapping & Pagination Algorithm
- **Width**: `max_w = box_width - 2 * DIALOGUE_CONTENT_MARGIN_X` (140px margins).
- **Line capacity**: `max_lines = floor(available_h / (font_linesize * 1.2))`. Adjusts dynamically (3 lines max with title, 5 lines max without).
- **Wrapping**: Words are accumulated into lines using `font.size()`. Words exceeding `max_w` sit on their own line.
- **Pre-rendering**: Pages are pre-rendered onto transparent Surfaces at startup to optimize frame rates.

### 2.3 Typewriter Hybrid Rendering
To bypass expensive `font.render()` calls per frame:
- **Complete Lines**: Blits horizontal strips directly from the pre-rendered page surface.
- **Typing Line**: Dynamically renders only the active substring.
- **Skip Action**: Pressing the interact key (E) during typing instantly fills the current page.

---

## 3. SpeechBubble (Nine-Patch NPC Bubble)

Renders dynamically sized speech bubbles above NPC sprites, constructed using a nine-patch tile system.

### 3.1 Nine-Patch Tile Set
All tiles are 32×32 pixels and loaded from `assets/images/HUD/`:

| Tile | Position | File |
|------|----------|------|
| Top-Left | Corner | `13-bubble_top_left.png` |
| Top | Edge | `14-bubble_top.png` |
| Top-Right | Corner | `15-bubble_top_right.png` |
| Left | Edge | `16-bubble_left.png` |
| Center | Fill | `17-bubble_center.png` |
| Right | Edge | `18-bubble_right.png` |
| Bottom-Left| Corner | `19-bubble_bottom_left.png` |
| Bottom | Edge | `20-bubble_bottom.png` |
| Bottom-Right| Corner | `21-bubble_bottom_right.png` |
| Arrow | Cursor | `22-bubble_arrow.png` |
| Name | Plate | `23-bubble_name.png` |

### 3.2 Nine-Patch Construction Algorithm
1. Calculate bounds based on wrapped text size:
   - `width = max(text_width + 60, name_plate_width + 30, 224)` (rounded up to 32px multiples). The `224` is the **minimum bubble surface width** (7 tiles × 32px), distinct from the text content wrap width (also 224px, see [npc-system.md §SpeechBubble](./npc-system.md)).
   - `height = line_count * line_height + 40` (rounded up to 32px multiples).
2. Create transparent Surface `(width, height, SRCALPHA)`.
3. Blit 4 corner tiles.
4. Tile edges horizontally and vertically between corners.
5. Fill the central area with center tiles.
6. Attach tail (`21-bubble_queue.png`) centered at the bottom edge.

### 3.3 Name Plate subsurface
NPC name plates use `23-bubble_name.png` sliced to a calculated width based on the localized name length:
- `width = font.size(name)[0] + 2 * NAME_PADDING_X`.
- Blitted at the top-left offset corner of the speech bubble.

### 3.4 Camera-Relative Anchor
The bubble is anchored above the NPC's head in world-space. Drawing utilizes a custom `blit_func` callback that factors in the active camera viewport offset:
- **X**: `npc.rect.centerx`.
- **Y**: `npc.rect.top - bubble_height - tail_gap`.

---

## 4. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Render typewriter text frame-by-frame | Use hybrid pre-rendered strips | Severe CPU and GPU bottlenecking |
| Construct nine-patch bubbles per-frame | Build once inside `set_text()` and cache | Nine-patch tiling loops degrade frame rates |
| Draw speech bubbles in screen coordinates | Anchor using world-space camera offsets | Speech bubbles must follow NPCs during camera pans |
| Hardcode names in dialogue buffers | Query i18n localization dictionaries | Breaks multi-language support |

---

## 5. Test Case Specifications

### 5.1 Unit Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| UT-DLG-01 | `test_dialogue_manager_pre_renders_pages` | `../../tests/ui/test_dialogue.py` |
| UT-DLG-02 | `test_dialogue_manager_advance_and_update` | `../../tests/ui/test_dialogue.py` |
| UT-DLG-03 | `test_dialogue_manager_draw` | `../../tests/ui/test_dialogue.py` |
| UT-SPB-01 | `test_max_width_not_exceeded` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-02 | `test_wrap_uses_padding_not_tile_size` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-03 | `test_bubble_bottom_anchored_above_character` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-04 | `test_multiple_pages_exist_for_long_text` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-05 | `test_arrow_drawn_for_multi_page_text` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-06 | `test_page_index_clamped` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-07 | `test_raises_when_font_not_set` | `../../tests/ui/test_speech_bubble.py` |
| UT-SPB-08 | `test_name_plate_rendered` | `../../tests/ui/test_speech_bubble.py` |

### 5.2 Integration & UI Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-DLG-01 | `test_dialogue_pagination` | `../../tests/ui/test_inventory.py` | ⚠️ Misplaced — should be moved to `test_dialogue.py` |

---

## 6. Deep Links
- **DialogueManager**: [dialogue.py L18](../../src/ui/dialogue.py#L18)
- **SpeechBubble rendering**: [speech_bubble.py L1](../../src/ui/speech_bubble.py#L1)
- **Dialogue NPC bubble triggers**: [game.py L405](../../src/engine/game.py#L405)
