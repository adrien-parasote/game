[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Game Flow & Save System

> Document Type: Implementation
**Document type:** Implementation  
**Date:** 2026-05-02  
**Status:** ✅ Ready for BUILD  
**ADRs:** ADR-001, ADR-002, ADR-003  
**Blueprint:** `docs/strategic/game_vision.md`

---

## Assumptions

| # | Assumption | Risk |
|---|---|---|
| A1 | `Item` is a pure Python data structure — serializable via `.__dict__` | LOW — confirmed by `inventory_system.py` |
| A2 | `TimeSystem._total_minutes` is the only internal state to save | LOW — all properties are derived |
| A3 | `WorldState._state` is a `dict[str, dict]` of JSON-native types | LOW — confirmed by `world_state.py` |
| A4 | `Game.__init__` always loads a map at startup — this behavior is modified: `Game.__init__` no longer loads a map if called in "shell" mode | MEDIUM — requires a `skip_map_load` flag |
| A5 | Menu assets have a black background → `colorkey=(0,0,0)` for the logo only | LOW — confirmed during assets session |

---

## 1. Asset Dimensions (measured)

| Asset | File | Total Dimensions | Per State |
|---|---|---|---|
| Logo | `00-title_logo.png` | 903×241 | — (black background, colorkey) |
| Background | `01-menu_background.png` | 1024×1024 | — (scaled to 1280×720) |
| Buttons | `02-menu_buttons.png` | 1024×182 | **341×182** (3 states: idle/hover/pressed) |
| Panel | `03-panel_background.png` | 1024×1024 | — (scaled to target size) |
| Save Slot | `04-save_slot.png` | 1024×1024 | **1024×512** (2 states: idle=top, hover=bottom) |

---

## 2. Modules to Create

### 2.1 `src/engine/save_manager.py` [NEW]

**Responsibility:** Serialization/deserialization of save slots.

```
SAVES_DIR = "saves/"
MAX_SLOTS = 3
SCHEMA_VERSION = "0.4.0"
SLOT_FILENAME = "slot_{n}.json"   # n = 1, 2, 3
```

**Public Interface:**

```python
class SaveManager:
    def list_slots(self) -> list[SlotInfo | None]
        # Returns a list of 3 elements. None = empty slot.
        # SlotInfo = dataclass { slot_id, saved_at, playtime_seconds, location, map_name, map_display_name }

    def save(self, slot_id: int, game: Game) -> None
        # slot_id: 1..3. Serializes game state → saves/slot_{id}.json

    def load(self, slot_id: int) -> SaveData | None
        # Returns SaveData or None if slot is empty/corrupt

    def delete(self, slot_id: int) -> None
        # Deletes saves/slot_{id}.json

    def slot_exists(self, slot_id: int) -> bool
```

**JSON Structure (ADR-002):**

```json
{
  "version": "0.4.0",
  "saved_at": "2026-05-02T14:30:00",
  "playtime_seconds": 3600,
  "player": {
    "map_name": "01-castle_hall.tmj",
    "x": 320.0,
    "y": 480.0,
    "facing": "down",
    "level": 1,
    "hp": 100,
    "max_hp": 100,
    "gold": 0
  },
  "time_system": {
    "total_minutes": 7200.0
  },
  "inventory": {
    "slots": [
      {"id": "sword_iron", "quantity": 1},
      null
    ],
    "equipment": {
      "HEAD": null,
      "LEFT_HAND": {"id": "sword_iron", "quantity": 1},
      "RIGHT_HAND": null,
      "UPPER_BODY": null,
      "LOWER_BODY": null,
      "SHOES": null,
      "BAG": null,
      "BELT": null
    }
  },
  "world_state": {
    "castle_hall_chest_01": {"is_on": true}
  }
}
```

**`Inventory` Serialization:**
- `slots`: list of 28 elements. Each slot = `{"id": str, "quantity": int}` or `null`
- `equipment`: dict slot_name → `{"id": str, "quantity": int}` or `null`
- Fields `name`, `description`, `icon`, `stack_max` are **omitted** → reconstructed from `propertytypes.json` during load via `Inventory.create_item(id, quantity)`

**Deserialization:**
- Validate `version` — if major mismatch, log WARNING and return None
- `Inventory.slots[i] = inventory.create_item(d["id"], d["quantity"])` if not null
- `TimeSystem._total_minutes = data["time_system"]["total_minutes"]`
- `WorldState._state = data["world_state"]`

---

### 2.2 `src/ui/title_screen.py` [MODIFIED]

**Responsibility:** Rendering and navigation of the main menu.

**Layout on 1280×720 screen:**

```
┌────────────────────────────────────────────────┐  720px
│  [01-menu_background.png — 1280×720, fullscreen]  │
│  [TITLE TEXT (Cormorant, 90pt, cyan) — y=80, centered]│
│                                                   │
│           [Menu items x=1055, y_start=360]        │
│           New Game, Load Game, Options, Quit      │
└────────────────────────────────────────────────┘ 1280px
```

**Title Rendering (dynamic text):**
- Font: `assets/fonts/cormorant-garamond-regular.ttf`, size 90pt
- Color: `(150, 255, 220)` — light cyan/turquoise
- Halo glow: `(0, 180, 150)` — intense cyan (rendered via `_blit_halo_text`)
- Position: centered x=640, y=80
- No image assets for the title (removed: `00-title_logo_main_title.png`, `00-title_logo_separator.png`, `00-title_logo_subtitle.png`, `00-title_logo_moon.png`, `00-title_logo_gear.png`)

**Animated Halos on the Background (`BACKGROUND_LIGHTS`):**
- **33 positions** calibrated via `scripts/calibration/calibrate_halos.py` (FIRE mode)
- 3 radius tiers: `45` (lanterns), `28` (windows), `18` (small windows)
- Halos pre-generated at init: distinct black surface per radius, quadratic gradient `(255, 120, 20)`, `BLEND_RGB_ADD`
- **Resolution Independence**: logical space coordinates 1280×720; `_light_scale_x / _light_scale_y` derived from `screen.get_size()`
- Scintillation: `sin(t*0.4 + i*1.1) * 0.06 + sin(t*0.9 + i*2.3) * 0.04`, base 0.92 — candle style
- `HALO_DEBUG = False` flag: enable to draw calibration crosses (red=fire, cyan=mushroom)

**Bioluminescent Mushroom Halos (`MUSHROOM_LIGHTS`):**
- **25 positions** calibrated via `scripts/calibration/calibrate_halos.py` (MUSHROOM mode, press M key)
- Format: `(x, y, radius, (R, G, B))` — color per mushroom
- Cyan color: `(70, 220, 200)` for turquoise mushrooms; red `(220, 80, 60)` also supported
- Tiers: r=22 (large), r=16 (medium), r=11 (small)
- Halos pre-generated at init per unique `(color_key, radius)` pair — `_mushroom_halos` dict
- Slow breathing effect: `sin(t*0.15 + i*1.3) * 0.10 + sin(t*0.37 + i*2.1) * 0.06`, base 0.84 — bioluminescent style

**Calibration workflow (dual-mode):**
```bash
python3 scripts/calibration/calibrate_halos.py
# FIRE mode (default): click on lanterns/windows
# Press M: switch to MUSHROOM mode → click on mushrooms
# Shift+Click = medium, Ctrl+Click = small
# S = save both lists
python3 scripts/calibration/apply_calibration.py  # inject BACKGROUND_LIGHTS + MUSHROOM_LIGHTS
```

**Menu Item Rendering:**
- Idle: "engraved in stone" effect (text + shadow + highlights via `_blit_engraved`)
- Hover: cyan halo `_blit_halo_text` color `(150, 255, 220)` / glow `(0, 180, 150)`

**TitleScreen State Machine:**
```
MAIN_MENU → (click Load Game)     → LOAD_MENU  (overlay panel + slots)
MAIN_MENU → (click Options)       → OPTIONS    (overlay panel + stub)
MAIN_MENU → (click Quit)          → QUIT       (pygame.quit + sys.exit)
LOAD_MENU → (click slot)          → returns GameEvent.LOAD_GAME(slot_id)
LOAD_MENU → (ESC or back button)  → MAIN_MENU
```

**Public Interface:**
```python
class TitleScreen:
    def __init__(self, screen: pygame.Surface, save_manager: SaveManager)
    def handle_event(self, event: pygame.Event) -> GameEvent | None
    def update(self, dt: float) -> None  # increments _light_time
    def draw(self) -> None
```

**Constants (in `title_screen_constants.py`):**
- `BACKGROUND_LIGHTS`: 33 tuples `(x, y, radius)` in logical space 1280×720
- `BG_LIGHT_COLOR = (255, 120, 20)` — amber/fire color
- `MUSHROOM_LIGHTS`: 25 tuples `(x, y, radius, color)`
- `TITLE_TXT_COLOR = (150, 255, 220)`
- `TITLE_GLOW_COLOR = (0, 180, 150)`

---

### 2.3 `src/ui/pause_screen.py` [NEW]

**Responsibility:** Rendering and handling of the pause menu in-game.

**Interface:**

```python
class PauseScreen:
    def __init__(self, screen: pygame.Surface, save_manager: SaveManager)
    def handle_event(self, event: pygame.Event) -> GameEvent | None
    def draw(self) -> None
```

**State Machine:**
```
PAUSED → (click Resume)    → returns GameEvent.RESUME
PAUSED → (click Save)      → SAVE_MENU  (overlay panel + slots)
PAUSED → (click Main Menu) → CONFIRM    (confirmation dialog)
PAUSED → (click Quit)      → returns GameEvent.QUIT
SAVE_MENU → (ESC or back)  → PAUSED
CONFIRM → (Yes)            → returns GameEvent.MAIN_MENU
CONFIRM → (No)             → PAUSED
```

**Visual style:**
- Transparent gray background overlaid on the game: `(0, 0, 0, 150)` with `pygame.SRCALPHA`
- Central Panel `03-panel_background.png` scaled to `500×600` centered at `(390, 60)`
- Cormorant font for items (Resume, Save Game, Return to Title, Quit) with identical rendering to the Title Screen

---

### 2.4 `src/engine/game_state_manager.py` [NEW]

**Responsibility:** Orchestration of screens, high-level game state transitions, and event processing.

**State Transitions:**

```
[MAIN_MENU]  ◄──────────────────────────────┐ (GameEvent.MAIN_MENU)
     │                                      │
     ├──(GameEvent.NEW_GAME)                │
     │      ▼                               │
     │   [PLAYING] ──────────────────────┐  │
     │       ▲  │                        │  │
     │       │  └──(K_ESCAPE)            │  │
     │       │      ▼                    │  │
     │       │   [PAUSED] ───────────────┼──┘
     │       │       │                   │
     │       │       └──(GameEvent.QUIT)─┼──┐
     │       │                           │  │
     │       └──(GameEvent.RESUME)       │  │
     │                                   │  │
     └──(GameEvent.LOAD_GAME)            │  │
             ▼                           │  │
         Loads slot                      │  │
             │                           ▼  ▼
             └───────────────────────► [EXIT] (pygame.quit)
```

**Public Interface:**

```python
class GameStateManager:
    def __init__(self, screen: pygame.Surface)
    def run(self) -> None  # Infinite event loop, handles dt
```

**Implementation Details:**
- Manages an instance of `SaveManager`.
- Instantiates `TitleScreen` and `PauseScreen` lazily or holds them in cache.
- Instantiates `Game` on transition `NEW_GAME` or `LOAD_GAME`.
- Cleanly exits on `GameEvent.QUIT`.

---

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|---|---|---|
| Load the entire JSON file just to display slot metadata in the menu | Only read root-level metadata in `_read_slot_info` | Optimizes save slot menu loading times |
| Overwrite the existing save file directly on write | Write to a temporary `.tmp` file and then rename | Prevents save file corruption if the game crashes mid-save |
| Handle slot clicks directly inside the `SaveSlotUI` component | Delegate collision detection and click handling to the parent overlay (`PauseScreen` / `TitleScreen`) | The parent overlay must emit the appropriate `GameEvent` transitions |
| Capture screenshots with the Pause menu UI visible | Capture the screenshot immediately before opening the Pause menu or render the game scene offscreen | The thumbnail must reflect in-game play, not overlay menus |
| Apply the hover glow using a simple opaque solid color | Render using the `pygame.BLEND_RGBA_ADD` flag | Guarantees a glowing/luminous effect consistent with the visual direction |

---

## 4. Test Case Specifications

### Unit Tests Required

| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| UT-GSM-01 | `GameStateManager` | Transition `NEW_GAME` | Instantiates `Game` and sets state to `PLAYING` | Existing game in progress is garbage collected |
| UT-GSM-02 | `GameStateManager` | Transition `LOAD_GAME(1)` | Calls `SaveManager.load(1)` and loads state | Slot file corrupted (remains in menu, logs warning) |
| UT-GSM-03 | `GameStateManager` | Event `K_ESCAPE` in `PLAYING` | Switches state to `PAUSED` | `InputHandler` is active (intercepts cleanly) |
| UT-TS-01 | `TitleScreen` | Click on "Options" | Switches state to `OPTIONS` | Clicks outside options bounds are ignored |
| UT-TS-02 | `TitleScreen` | Input event hover | `_hovered_item` is updated correctly | Mouse is completely off screen |
| UT-SM-01 | `SaveManager` | `save(1, game)` | Creates file `saves/slot_1.json` with correct schemas | Write permissions missing on target folder |
| UT-SM-02 | `SaveManager` | `load(1)` (valid) | Returns `SaveData` matching the JSON state | Schema version mismatch |
| UT-SM-03 | `SaveManager` | `load(1)` (missing) | Returns `None` | File empty or partially corrupted |

### Integration Tests Required

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-FLOW-01 | Main Menu to Playing | Instantiate `GameStateManager` | Game starts, loads maps, enters game loop | Clean pygame exit |
| IT-FLOW-02 | Play, Pause, Save, Load | Start game, play 2 seconds, pause, save to Slot 1, restart, load Slot 1 | Playtime is ~2s, player is at correct saved coordinates | Remove `saves/slot_1.json` |

---

## 5. Traceability Matrix

### Test Mappings

- **UT-GSM-01** ──► `tests/engine/test_game_state_manager.py:test_new_game_starts_playing`
- **UT-GSM-02** ──► `tests/engine/test_game_state_manager.py:test_load_game_restores_state`
- **UT-GSM-03** ──► `tests/engine/test_game_state_manager.py:test_escape_key_pauses_game`
- **UT-TS-01**  ──► `tests/ui/test_title_screen.py:test_options_clicked`
- **UT-TS-02**  ──► `tests/ui/test_title_screen.py:test_hover_updates_state`
- **UT-SM-01**  ──► `tests/engine/test_save_manager.py:test_save_serialization`
- **UT-SM-02**  ──► `tests/engine/test_save_manager.py:test_load_deserialization`
- **UT-SM-03**  ──► `tests/engine/test_save_manager.py:test_load_empty_slot`
- **IT-FLOW-01** ──► `tests/engine/test_game_state_manager.py:test_main_menu_to_game_flow`
- **IT-FLOW-02** ──► `tests/engine/test_save_manager.py:test_full_save_load_cycle`
