> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Dialogue System [Implementation]

> Document Type: Implementation
> Source: `src/ui/dialogue.py` (306 LOC), `src/ui/dialogue_constants.py` (19 LOC)

This document specifies the AS-IS implementation of the `DialogueManager` responsible for rendering dialogue boxes with typewriter animation, pagination, and shadow text effects.

## 1. Goal Description

Display dialogue text in a styled box at the screen bottom, with typewriter reveal animation, automatic pagination based on font metrics, and optional speaker title. Support advance-on-click (skip typing → next page → close).

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `DialogueManager` | `src/ui/dialogue.py` | 306 | Text wrapping, typewriter, rendering |
| Constants | `src/ui/dialogue_constants.py` | 19 | Layout offsets, colors |

### Dependencies
- `src.config.Settings` — `WINDOW_WIDTH`, `WINDOW_HEIGHT`, `TEXT_SPEED`, font paths
- `src.engine.asset_manager.AssetManager` — font loading
- `pygame` — rendering, font metrics

## 3. Constants

| Constant | Value | File | Purpose |
|----------|-------|------|---------|
| `DIALOGUE_CONTENT_MARGIN_X` | *(from constants)* | `dialogue_constants.py` | Horizontal padding inside dialogue box |
| `DIALOGUE_MSG_Y_OFFSET_PLAIN` | *(from constants)* | `dialogue_constants.py` | Y offset for text when no title |
| `DIALOGUE_MSG_Y_OFFSET_TITLED` | *(from constants)* | `dialogue_constants.py` | Y offset for text when title is present |
| `DIALOGUE_ARROW_Y_OFFSET` | *(from constants)* | `dialogue_constants.py` | Y position of the "next page" arrow |
| `DIALOGUE_SHADOW_COLOR` | *(from constants)* | `dialogue_constants.py` | Drop shadow color for text |
| `DIALOGUE_TEXT_COLOR` | *(from constants)* | `dialogue_constants.py` | Main text color |

## 4. State Machine

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

| State | `is_active` | `_is_page_complete` | Behavior |
|-------|-------------|---------------------|----------|
| INACTIVE | `False` | — | No rendering |
| TYPING | `True` | `False` | Typewriter reveal, advance() skips to end |
| PAGE_COMPLETE | `True` | `True` | Shows arrow, advance() goes to next page or closes |

## 5. Interfaces

### 5.1. `start_dialogue(text: str, title: str = "") -> None`

**Behavior**:
1. If `text` is empty → set `is_active = False`, return
2. Store `message`, `title`
3. Set `is_active = True`, reset page/char indices
4. Call `_paginate(text)` to compute pages and pre-render surfaces
5. If pagination produces 0 pages → set `is_active = False`

### 5.2. `advance() -> None`

Three-stage progression:
1. **If TYPING**: Skip to end of current page (set `_page_char_index` to full length)
2. **If PAGE_COMPLETE + more pages**: Advance to next page, reset to TYPING
3. **If PAGE_COMPLETE + last page**: Close dialogue, clear all state

### 5.3. `update(dt: float) -> None`

**Typewriter animation**:
- `_page_char_index += typewriter_speed * dt`
- `typewriter_speed = 1.0 / Settings.TEXT_SPEED` (chars per second)
- `displayed_text = page_text[:int(_page_char_index)]`
- When `_page_char_index >= len(page_text)` → `_is_page_complete = True`

### 5.4. `draw(screen) -> None`

Rendering layers:
1. **Dialogue box**: `05-textbox.png` scaled to `0.5×`, positioned `midbottom` at `(W/2, H-20)`
2. **Title** (if present): Shadow + main text at `(box.x + margin, box.y + plain_offset)`
3. **Message text**:
   - If page complete → blit pre-rendered `_page_surfaces[current_page]`
   - If typing → hybrid render: full lines from pre-rendered surface (strip blit), partial line rendered dynamically
4. **Next arrow**: `06-cursor.png` at box right edge when page is complete

## 6. Pagination Algorithm (`_paginate`)

**Input**: Full dialogue text string.

**Algorithm**:
1. Calculate `max_w = box_width - 2 * content_margin_x`
2. Calculate `available_h = box_height - message_y_offset - 40`
3. Calculate `max_lines = floor(available_h / (font_linesize * 1.2))`
4. **Word-wrap**: Split text by spaces, accumulate words per line while `font.size(line) <= max_w`
5. **Paginate**: Group wrapped lines into chunks of `max_lines`
6. **Pre-render**: For each page, create a transparent Surface with shadow + main text for each line

**Line spacing**: `1.2 × font.get_linesize()`

**Edge case**: Words exceeding `max_w` are placed on their own line without breaking. This is acceptable for authored game dialogue where word length is controlled by content designers.

## 7. Typewriter Rendering (Optimized Hybrid)

During typing, the draw method uses a hybrid approach:
- **Complete lines**: Blit horizontal strips from the pre-rendered page surface (zero font.render() calls)
- **Partial line** (currently typing): Render only the visible substring dynamically with shadow

This avoids per-frame `font.render()` for already-revealed lines.

## 8. Assets

| Asset | Path | Usage |
|-------|------|-------|
| Dialogue box | `assets/images/hud/05-textbox.png` | Background, scaled to 50% |
| Next arrow | `assets/images/hud/06-cursor.png` | Page-complete indicator |
| Title font | Settings.FONT_NOBLE at `1.5× FONT_SIZE_NOBLE` | Speaker name |
| Message font | Settings.FONT_NARRATIVE at `1.5× FONT_SIZE_NARRATIVE` | Dialogue text |

## 9. Wiring

| Caller | Method | Context |
|--------|--------|---------|
| `InteractionManager` | `start_dialogue(text, title)` | NPC/object interaction |
| `InputHandler` | `advance()` | On action key press |
| `Game._update()` | `update(dt)` | Every frame while active |
| `RenderManager` | `draw(screen)` | UI layer rendering |

## 10. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `font.render()` for every visible line per frame | Use pre-rendered page surfaces | Performance (306→0 render calls) |
| Split text by characters for wrapping | Split by words (space-separated) | Word boundaries look correct |
| Skip shadow pass | Always render shadow at `+1,+1` offset | Visual depth consistency |
| Assume fixed line count | Calculate from font metrics + box height | Adapts to font size changes |
| Modify `_pages` or `_page_surfaces` outside `_paginate()` | Always call `start_dialogue()` which re-paginates | Keeps pages/surfaces in sync |

## 11. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing textbox asset | `os.path.exists()` | No load | `dialogue_box = None`, draw() no-ops |
| Missing arrow asset | `os.path.exists()` | No load | `next_arrow = None`, arrow not drawn |
| Font load failure | Caught in `_load_assets` | Log ERROR | Bare `except` (⚠️ tech debt) |
| Empty text | Check in `start_dialogue` | `is_active = False` | No dialogue shown |

## 12. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| UT-DLG-01 | `start_dialogue` | Short text, no title | 1 page, TYPING state |
| UT-DLG-02 | `start_dialogue` | Long text exceeding box | Multiple pages created |
| UT-DLG-03 | `start_dialogue` | Empty string | `is_active = False` |
| UT-DLG-04 | `advance` | During TYPING | Skips to page complete |
| UT-DLG-05 | `advance` | PAGE_COMPLETE, more pages | Advances to next page |
| UT-DLG-06 | `advance` | PAGE_COMPLETE, last page | Closes dialogue |
| UT-DLG-07 | `update` | dt=0.5, speed=20 chars/s | 10 characters revealed |
| UT-DLG-08 | `_paginate` | Text with 10 words | Correct line wrapping |

### Integration Tests
| Test ID | Flow | Verification |
|---------|------|--------------|
| IT-DLG-01 | NPC interaction → dialogue → advance through | All pages display, closes cleanly |
| IT-DLG-02 | Rapid advance clicks | No crash, skips correctly |

## 13. Deep Links
- **DialogueManager**: [dialogue.py:18](../../src/ui/dialogue.py#L18)
- **Constants**: [dialogue_constants.py](../../src/ui/dialogue_constants.py#L1)
- **Caller (InteractionManager)**: [interaction.py](../../src/engine/interaction.py#L1)

## 14. Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| 1 | Scale factor 0.5 is permanent | Low | Tied to HUD design |
| 2 | Line spacing 1.2× is visually correct | Low | Playtested |
| 3 | `TEXT_SPEED` is delay per char (seconds) | Medium | Verify Settings docs |
| 4 | Box position `midbottom (W/2, H-20)` is final | Low | Standard RPG layout |
