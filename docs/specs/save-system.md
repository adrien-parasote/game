[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

> Document Type: Implementation
# Save System & Save Menu UI

This document specifies the save system, the Save Slots user interface, and the game's thumbnail (screenshot) capture system.

## 1. Core Architecture

The system is composed of 3 major components:
1. **`SaveManager`**: Extended to support the serialization of thumbnails, player level, and active playtime.
2. **`SaveSlotUI`**: A reusable visual component designed to render an individual save slot on screen.
3. **`SaveMenuOverlay`**: An overlay menu manager (utilized by `PauseScreen` and `TitleScreen`) that displays 3 `SaveSlotUI` components.

### 1.1 SaveManager & SlotInfo

The `SaveManager` must read root metadata extremely fast to populate the UI (without parsing large nested objects like `world_state` or `inventory`).

Extended `SlotInfo` properties:
- `slot_id: int`
- `saved_at: str` (ISO 8601 format)
- `playtime_seconds: float`
- `map_name: str`
- `player_name: str` (fallback: "Hero")
- `level: int`

**Thumbnail Management**:
- During a save sequence, a squared player-centered screenshot crop (e.g., 120x120 pixels) must be saved to disk at `saves/slot_{id}_thumb.png`.
- `SaveManager` exposes `save_thumbnail(slot_id, surface)` and `load_thumbnail(slot_id) -> pygame.Surface | None`.

### 1.2 Save Slot Rendering

The slot utilizes the background image asset `assets/images/menu/03-save_slot.png` (427x200 pixels).
- **Thumbnail**: Rendered on the left side of the slot. The available coordinate window is approximately between X=40 and X=160.
- **Hover State**: When a slot is hovered by the mouse, an additive orange glow/halo (soft blurred circle or sprite) must be rendered over the 4 frame corner gems:
  - Top-Left: `(26, 27)`
  - Top-Right: `(413, 27)`
  - Bottom-Left: `(26, 170)`
  - Bottom-Right: `(414, 171)`

### 1.3 Back Button

The `SaveMenuOverlay` includes a "Back" button positioned at the bottom left of the overlay panel.
- **Icon Asset**: `assets/images/menu/01-menu_back_cursor.png` (28x25 pixels).
- **Label**: Text "Back" (parsed via I18n key `menu.back`) rendered using the `Cormorant Garamond` font.
- **Rendering States**:
  - **Idle**: Renders with an engraved ("engraved") stone effect.
  - **Hover**: Renders with an intense cyan halo (`(150, 255, 220)` with glow `(0, 180, 150)`).
- **Interaction**: Clicking this button closes the overlay and returns the game to the previous state.

## Assumptions

| Assumption | Risk Level | Implication | Validation |
|------------|------------|-------------|------------|
| Screenshot cropping | Low | Player is always centered on screen | If camera shifts, crop might be slightly off. Validate manually. |
| Hover performance | Low | Additive blending (RGBA_ADD) of 4 small halos per slot | 12 small blits per frame is negligible. |
| Fallback fonts | Medium | Cormorant Garamond is available for menu UI | Ensure the font exists in `assets/fonts/` |

## 2. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load the entire JSON file just to display slot metadata in the menu | Only read root-level metadata in `_read_slot_info` | Optimizes save slot menu loading times |
| Overwrite the existing save file directly on write | Write to a temporary `.tmp` file and then rename | Prevents save file corruption if the game crashes mid-save |
| Handle slot clicks directly inside the `SaveSlotUI` component | Delegate collision detection and click handling to the parent overlay (`PauseScreen` / `TitleScreen`) | The parent overlay must emit the appropriate `GameEvent` transitions |
| Capture screenshots with the Pause menu UI visible | Capture the screenshot immediately before opening the Pause menu or render the game scene offscreen | The thumbnail must reflect in-game play, not overlay menus |
| Apply the hover glow using a simple opaque solid color | Render using the `pygame.BLEND_RGBA_ADD` flag | Guarantees a glowing/luminous effect consistent with the visual direction |

## 3. Test Case Specifications

### Unit Tests Required

| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| SAVE-U-001 | SaveManager | `save_thumbnail(1, valid_surf)` | Creates `saves/slot_1_thumb.png` | The `saves/` folder does not exist |
| SAVE-U-002 | SaveManager | `load_thumbnail(1)` (file exists) | Returns the `pygame.Surface` | Corrupt or unreadable thumbnail file |
| SAVE-U-003 | SaveManager | `_read_slot_info` | Returns fully populated `SlotInfo` including `level` | `level` or `player_name` properties missing from old save files |
| SAVE-U-004 | SaveMenuOverlay | `update(dt)` with mouse hovered over Slot 2 | `_hovered_slot == 1` | Mouse cursor is outside the menu panel boundaries |
| SAVE-U-005 | SaveSlotUI | Rendering with `info=None` | Renders placeholder text: "Slot X — Empty" | Slot without thumbnail file (renders fallback icon) |
| SAVE-U-006 | SaveSlotUI | `draw(surface, rect, 1, None, None, False)` | Draws empty slot state without crashing | — |
| SAVE-U-007 | SaveSlotUI | `draw(surface, rect, 1, info, thumb, True)` | Draws active save state with thumbnail and gem halos | Non-squared thumbnail dimension fallbacks |
| SAVE-U-008 | SaveMenuOverlay | `__init__` + `refresh()` | Populates `_slots_info[0].map_name` correctly | SlotInfo is None for empty slots |
| SAVE-U-009 | SaveMenuOverlay | `get_clicked_slot(event)` | Returns the index of the clicked slot | Click outside save slot bounding boxes returns `None` |
| SAVE-U-010 | SaveMenuOverlay | `update(dt)` + `draw()` | `_hovered_slot` is updated, and `screen.blit` is called | — |
| SAVE-U-011 | SaveMenuOverlay | `is_back_clicked(event)` | Returns `True` if clicking the Back button | Clicking outside back button bounds returns `False` |

### Integration Tests Required

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| SAVE-I-001 | Save & Load Cycle | Player inside the `spawn` map at Level 2 | Save JSON contains `level=2` and the thumbnail file exists | Delete generated `saves/slot_X` files |
| SAVE-I-002 | Click "Save" in Pause Screen | Open Pause Screen, click "Save" | The `SAVE_MENU` overlay is displayed and all 3 save slots render | Close the Pause menu |
| SAVE-I-003 | Hover over Slot | `SaveMenuOverlay` active | Additive glow halos draw call is executed on `TitleScreen` | Close the overlay |

## 4. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| Corrupted JSON file | `json.JSONDecodeError` raised in `_read_slot_info` | Return `None` (interpreted as empty slot) | Prevent menu crashes | ERROR | None |
| Screenshot save failure | `pygame.error` raised during `save_thumbnail` | Ignore thumbnail serialization | The save slot will render without a thumbnail | WARN | None |
| Missing thumbnail image | File not found during `load_thumbnail` | Return `None` | Render slot with a default gray fallback icon | WARN | None |

## 5. Deep Links
- **`SaveManager` class**: [save_manager.py L36](../../src/engine/save_manager.py#L36)
- **`PauseScreen` overlay**: [pause_screen.py L14](../../src/ui/pause_screen.py#L14)
- **`TitleScreen` load overlay**: [title_screen.py L287](../../src/ui/title_screen.py#L287)
- **`GameStateManager` Events**: [game_state_manager.py L108](../../src/engine/game_state_manager.py#L108)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| SAVE-U-001 | `test_save_thumbnail_creates_file` | `../../tests/engine/test_save_manager.py` |
| SAVE-U-002 | `test_load_thumbnail_returns_surface` | `../../tests/engine/test_save_manager.py` |
| SAVE-U-003 | `test_list_slots_reflects_saved` | `../../tests/engine/test_save_manager.py` |
| SAVE-U-004 | `test_title_screen_update` | `../../tests/ui/test_title_screen.py` |
| SAVE-U-005 | `test_title_screen_draw_load_menu` | `../../tests/ui/test_title_screen.py` |
| SAVE-U-006 | `test_save_slot_ui_draw_empty` | `../../tests/ui/test_save_menu.py:L24` |
| SAVE-U-007 | `test_save_slot_ui_draw_filled` | `../../tests/ui/test_save_menu.py:L35` |
| SAVE-U-008 | `test_save_menu_overlay_init` | `../../tests/ui/test_save_menu.py:L48` |
| SAVE-U-009 | `test_save_menu_overlay_get_clicked_slot` | `../../tests/ui/test_save_menu.py:L57` |
| SAVE-U-010 | `test_save_menu_overlay_update_and_draw` | `../../tests/ui/test_save_menu.py:L73` |
| SAVE-U-011 | `test_save_menu_overlay_back_clicked` | `../../tests/ui/test_save_menu.py` |
| SAVE-I-001 | `test_save_creates_file` | `../../tests/engine/test_save_manager.py` |
| SAVE-I-002 | `test_pause_screen_handle_event_click_sauvegarder` | `../../tests/ui/test_pause_screen.py` |
| SAVE-I-003 | `test_title_screen_update` | `../../tests/ui/test_title_screen.py` |
