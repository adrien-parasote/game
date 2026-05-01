# Technical Spec — Chest UI System [Implementation]

**Type:** Implementation Document  
**Version:** 1.1  
**Status:** Implemented — 2026-04-30 (doc-update sync)

---

## 1. Context & Problem

The RPG engine has a fully functional `InteractiveEntity` with `sub_type='chest'`, including animation and state persistence. However, when the player opens a chest, **nothing is displayed** beyond the sprite animation. There is no interface to see or interact with the chest's contents.

### Deliverables

1. **`ChestUI`** — a new UI module (`src/ui/chest.py`) that overlays `07-chest.png` at the top of the screen when a chest is open, renders the chest name in the red title zone, and renders a slot grid in the green content zone.
2. **Interaction changes** — `InteractionManager` opens `ChestUI` on chest activation and closes it automatically when the player exits the interaction zone. The emote (!) is restored for **closed** chests.
3. **Game loop integration** — `Game` instantiates `ChestUI`, draws it, and pauses world update (but not interaction detection) while it is open.

---

## 2. Assumptions

| ID | Assumption | Risk |
|----|-----------|------|
| A-01 | `07-chest.png` is in `assets/images/HUD/` (confirmed by find command) | LOW |
| A-02 | `03-inventory_slot.png` (55x58) is reused for chest slots | LOW |
| A-03 | Chest contents are data-driven via `data/loot_table.json` and `LootTable` class | LOW |
| A-04 | The slot grid for the chest is 7 columns x 2 rows (14 slots), matching the green zone aspect ratio | MEDIUM — to validate visually |
| A-05 | `ChestUI` is a non-blocking overlay: world physics, NPCs, and teleports are paused while it is open (same as `InventoryUI`) | LOW |
| A-06 | Chest closing is triggered by: (a) player exiting interaction zone (auto-close), or (b) player pressing E again on open chest (action key close). Both paths go through `_close_chest()`. | LOW — revised 2026-04-30 |
| A-07 | The existing emote suppression in `_check_proximity_emotes` silences `!` for both open and closed chests — this must change: suppress only for **open** chests | LOW |

---

## 3. Asset Contract

| Asset | Path | Native Size | Usage |
|-------|------|-------------|-------|
| Chest background | `assets/images/HUD/07-chest.png` | ~1200x325px (estimated) | Main overlay frame |
| Slot frame | `assets/images/ui/03-inventory_slot.png` | 55x58px | Repeated for each content slot |
| Noble font | `Settings.FONT_NOBLE` / `Settings.FONT_SIZE_NOBLE` | 18pt | Chest name label |
| Tech font | `Settings.FONT_TECH` / `Settings.FONT_SIZE_TECH` | 12pt | Quantity labels in slots |
| Loot Table | `assets/data/loot_table.json` | JSON | Source of truth for chest contents |
| Property Types | `assets/data/propertytypes.json` | JSON | Metadata for item validation |

---

## 4. Layout Specification

### 4.1 Image Zones (relative to image pixel dimensions)

The image `07-chest.png` has two colored zones used as layout guides:

| Zone | Color | Relative Position (left%, top%, right%, bottom%) | Purpose |
|------|-------|--------------------------------------------------|---------|
| Title | RED | `(0.29, 0.02, 0.71, 0.23)` | Chest name, centered |
| Content | GREEN | `(0.11, 0.27, 0.89, 0.93)` | Slot grid |

Named constants in `src/ui/chest.py`:
```python
_TITLE_ZONE_REL   = (0.29, 0.02, 0.71, 0.23)
_CONTENT_ZONE_REL = (0.11, 0.27, 0.89, 0.93)
_SLOT_COLS = 10
_SLOT_ROWS = 2
```

### 4.2 Screen Position

- **Placement:** `midtop=(Settings.WINDOW_WIDTH // 2, 10)` — centered horizontally, 10px from top.
- **Scale:** The image is scaled to `_TARGET_WIDTH = 900px` while preserving aspect ratio.

### 4.3 Slot Grid

- **Layout:** 10 columns x 2 rows = 20 slots (validated visually — Assumption A-04 resolved).
- **Size per slot:** Mirrors `InventoryUI` scale: `slot_size = int(55 * (1200 / 1344))`.
- **Step:** `step = int(72 * (1200 / 1344))` — consistent spacing.
- **Centering:** `origin = content_rect.center - (grid_w // 2, grid_h // 2) + (0, _GRID_OFFSET_Y)`.
- **Rendering:** Each slot: `screen.blit(slot_img, slot_img.get_rect(center=(cx, cy)))`.

### 4.4 Title Zone

- **Content:** Hardcoded string `"coffre"` for v1 (name system redesigned later).
- **Font:** `noble_font` — color `(60, 40, 30)` (dark parchment brown, same as `InventoryUI`).
- **Alignment:** `surf.get_rect(center=title_rect.center)`.

---

## 5. Behavioral Specification

### 5.1 Open Sequence

```
Player presses E near closed chest (is_on=False)
  → InteractionManager._check_object_interactions()
    → obj.interact()          # toggles is_on to True
    → obj.sfx played
    → obj._world_state_key saved
    → if obj.sub_type == 'chest' and obj.is_on == True:
        game.chest_ui.open(obj, game.player)   # ← 2 args: entity + player
        self._open_chest_entity = obj
  → return True
```

### 5.2 Close Sequence (Auto, zone-exit or action key)

```
InteractionManager.update(dt)
  → _check_proximity_emotes() runs normally
  → _check_chest_auto_close()      ← called EVERY tick from update(), NOT inside _check_proximity_emotes
        if _open_chest_entity is None → return
        if game has no chest_ui attr → return
        if not game.chest_ui.is_open → return
        recompute: is player still in valid interaction zone?
          YES (in range AND correct orientation) → do nothing
          NO  → _close_chest(chest, chest_ui)
                  chest.interact(player)               # toggle animation is_on=False
                  audio_manager.play_sfx(chest.sfx)   # if sfx set
                  world_state.set(key, {is_on: False}) # persist
                  chest_ui.close()                     # hide overlay
                  _open_chest_entity = None
                  _last_proximity_target = chest        # suppress ! emote
                  _emote_cooldown = 1.0

Action key (E) on open chest:
  → _check_object_interactions()
    → obj.is_on == True → interact() (toggle to False)
    → chest_ui.close() if open
    → _open_chest_entity = None
    → _last_proximity_target = obj, _emote_cooldown = 1.0
```

### 5.3 Emote Logic Change

**Before (incorrect):**
```python
if obj.is_on and obj.sub_type in ["chest", "door"]:
    continue
```

**After (correct):**
```python
if obj.is_on and obj.sub_type == "chest":
    continue   # open chest: suppress emote
if obj.is_on and obj.sub_type == "door":
    continue   # open door: suppress emote
# closed chest: falls through → emote fires normally
```

### 5.4 Game Loop Integration

| State | `_update` behavior | `_draw_scene` behavior |
|-------|--------------------|------------------------|
| `chest_ui.is_open = False` | Normal game loop | Normal draw |
| `chest_ui.is_open = True` | `emote_group.update()` + `interaction_manager.update(dt)` only | Full scene draw + `chest_ui.draw(screen)` at end |

**Draw order in `_draw_scene`:**
1. Background tiles
2. Sprites
3. Foreground tiles
4. Night overlay
5. HUD (hidden when inventory open)
6. Emotes
7. Dialogue
8. InventoryUI (if open)
9. **ChestUI (if open) ← NEW**

### 5.5 Input Restrictions

- **Inventory Toggle Block:** Pressing the inventory key (default 'I') while `ChestUI.is_open` is `True` results in NO action. The inventory cannot be opened while a chest is active.
- **Auto-closing:** The inventory UI closes automatically if a chest is opened (handled by `elif` priority in `_update`).

---

## 6. Module: `src/ui/chest.py`

### Class: `ChestUI`

**Public interface:**
```python
class ChestUI:
    is_open: bool
    _chest_entity: Any
    _player: Any

    def __init__(self) -> None
    def open(entity, player) -> None        # 2 args: chest entity + player
    def close() -> None
    def draw(screen: pygame.Surface) -> None
    def update_hover(mouse_pos: tuple[int, int]) -> None
    def handle_event(event: pygame.event.Event) -> None
```

**Private methods:**
```python
    def _load_background(self) -> pygame.Surface | None
    def _load_inv_background(self) -> pygame.Surface | None
    def _load_slot_image(self) -> pygame.Surface | None
    def _load_cursor(self, path: str) -> pygame.Surface | None
    def _load_and_scale_arrow(self, path: str, scale: float) -> pygame.Surface | None
    def _get_item_icon(self, icon_filename: str, slot_size: int) -> pygame.Surface | None
    def _compute_layout(self) -> None
    def _compute_inv_layout(self, slot_size, step, screen_w, screen_h, arrow_scale) -> None
    def _capacity(self) -> int
    def _can_scroll_left(self) -> bool
    def _can_scroll_right(self) -> bool
    def _scroll_right(self) -> None
    def _scroll_left(self) -> None
    def _current_page_slots(self) -> list
    def _draw_title(self, screen: pygame.Surface) -> None
    def _draw_slots(self, screen: pygame.Surface) -> None
    def _draw_arrow_hovers(self, screen: pygame.Surface) -> None
    def _draw_inv_slots(self, screen: pygame.Surface) -> None
    def _draw_inv_arrows(self, screen: pygame.Surface) -> None
    def _draw_cursor(self, screen: pygame.Surface) -> None
```

**Constraints:**
- File < 700 lines (dual-panel implementation, v1.1+).
- All methods < 50 lines.
- No state mutation after `_compute_layout()` except `is_open`, `_chest_entity`, `_player`, hover state, and `_inv_offset`.
- No assets loaded in `draw()`.

---

## 7. Changes to Existing Modules

### `src/engine/interaction.py`

| Change | Method | Description |
|--------|--------|-------------|
| Add attribute | `__init__` | `self._open_chest_entity = None` |
| Split suppress conditions | `_check_proximity_emotes` | Separate `chest` and `door` conditions (see §5.3) |
| Add chest_ui.open call | `_check_object_interactions` | After interact(), if chest + is_on=True → open ChestUI |
| Add method | New: `_check_chest_auto_close` | Zone-exit detection (see §5.2) |
| Add method | New: `_close_chest(chest, chest_ui)` | Centralized close sequence: interact + sfx + world_state + UI close + emote suppression |
| Call auto-close | `update()` directly | `_check_chest_auto_close()` is called every tick from `update()`, NOT from `_check_proximity_emotes` |
| Close on action key | `_check_object_interactions` (chest toggle OFF branch) | `chest_ui.close()` + `_emote_cooldown = 1.0` when player re-presses E on open chest |

**Estimated file size after:** ~305 lines (target: <400). ✅

### `src/engine/game.py`

| Change | Location | Description |
|--------|----------|-------------|
| Import | Top | `from src.ui.chest import ChestUI` |
| Attribute | `__init__` | `self.chest_ui = ChestUI()` after `inventory_ui` |
| Draw | `_draw_scene` | `if self.chest_ui.is_open: self.chest_ui.draw(self.screen)` after inventory draw |
| Update | `_update` | `elif self.chest_ui.is_open:` branch — only emote + interaction_manager run |

---

## 8. Anti-Patterns (DO NOT)

| Anti-pattern | Do Instead | Why |
|---|---|---|
| Inline zone fractions as `(0.29, 0.02, ...)` in method | Named module constants `_TITLE_ZONE_REL` | One change point if asset changes |
| Scale `slot_img` inside `draw()` | Scale once in `_compute_layout()` | Per-frame scale = frame drops |
| Call `pygame.image.load()` in `draw()` | Load in `__init__`, cache as attribute | Disk I/O per frame is unacceptable |
| Close chest only on zone exit | Also support E key on open chest via `_close_chest()` | Both paths must share the same full close sequence — never close with only `chest_ui.close()` |
| Inventory and chest open simultaneously | `elif chest_ui.is_open` after inventory check | Two overlapping UIs break Z-order |
| Render item names in slots | Visual-only slots in v1 | Item system not yet designed |
| Suppress `!` emote for closed chests | Suppress only for `is_on=True` | Player must see emote to know chest is interactable |
| Crash on missing asset | Guard `draw()` with `if self._bg is None: return` | Headless tests must not crash |
| Direct `game.chest_ui` access in `_check_chest_auto_close` | `getattr(self.game, 'chest_ui', None)` | MagicMock with `spec=[]` raises `AttributeError` |
| Draw chest UI before inventory | Draw last (after inventory) | Z-order: chest behind inventory |

---

## 9. Test Case Specifications

### Unit Tests — `tests/test_chest_ui.py`

| Test ID | Component | Input | Expected Output | Edge Case |
|---------|-----------|-------|-----------------|-----------|
| TC-U-01 | `ChestUI.__init__` | Normal init | `is_open=False`, `_chest_entity=None` | — |
| TC-U-02 | `ChestUI.open` | Valid entity | `is_open=True`, `_chest_entity=entity` | — |
| TC-U-03 | `ChestUI.close` | After open | `is_open=False`, `_chest_entity=None` | Call on already-closed UI |
| TC-U-04 | `ChestUI.draw` | `is_open=False` | No `blit` calls | — |
| TC-U-05 | `ChestUI.draw` | `is_open=True`, valid bg | `screen.blit` called | — |
| TC-U-06 | `ChestUI.draw` | `is_open=True`, `_bg=None` | No `blit` calls | Asset error path |
| TC-U-07 | `ChestUI._draw_title` | Called when open | `noble_font.render("coffre", ...)` called | — |
| TC-U-08 | `ChestUI._draw_slots` | `slot_size=0` | No `blit` calls | Zero div guard |
| TC-U-09 | `ChestUI._draw_slots` | `slot_img=None` | Falls back to `pygame.draw.rect` | Missing asset |
| TC-U-10 | `_load_background` | `pygame.error` raised | Returns `None` | File not found |
| TC-U-11 | `_load_slot_image` | `FileNotFoundError` raised | Returns `None` | Headless / missing |

### Integration Tests — `tests/test_interaction.py`

| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| TC-I-01 | Chest open via E | Player in range, E pressed, chest is_on=True | `game.chest_ui.open` called once with entity |
| TC-I-02 | Auto-close: out of range | `_open_chest_entity` set, player at (500,500) | `game.chest_ui.close()` called |
| TC-I-03 | Auto-close: in range | `_open_chest_entity` set, player in valid zone | `close()` NOT called |
| TC-I-04 | Auto-close: no entity | `_open_chest_entity=None` | No error, no close |
| TC-I-05 | Auto-close: no chest_ui attr | `game = MagicMock(spec=[])` | No `AttributeError` |
| TC-I-06 | Auto-close: already closed | `chest_ui.is_open=False` | `_open_chest_entity → None` |
| TC-I-07 | Emote: closed chest | Chest `is_on=False`, player in range | `playerEmote('interact')` called |
| TC-I-08 | Emote: open chest | Chest `is_on=True`, player in range | Emote suppressed |
| TC-I-09 | Pickup proximity emote | Pickup in range, player facing | `playerEmote('question')` called |
| TC-I-10 | NPC proximity emote | NPC in range, player facing | `playerEmote('interact')` called |
| TC-I-11 | Skip: player moving | `player.is_moving=True`, E pressed | No interaction triggered |
| TC-I-12 | Skip: cooldown active | `_interaction_cooldown=0.3`, E pressed | No interaction triggered |

**Coverage target:** ≥80% per file.

---

## 10. Error Handling Matrix

| Error | Detection | Response | Fallback |
|-------|-----------|----------|----------|
| `07-chest.png` missing | `pygame.error` / `FileNotFoundError` in `_load_background` | `logging.error(...)`, return `None` | `draw()` guards: `if self._bg is None: return` |
| `03-inventory_slot.png` missing | Same in `_load_slot_image` | `logging.warning(...)`, return `None` | `_draw_slots` falls back to `pygame.draw.rect` wireframe |
| `chest_ui` missing on `game` | `getattr(self.game, 'chest_ui', None)` | Return early silently | Interaction system stable |
| `slot_size == 0` | Guard at top of `_draw_slots` | Return early | No blit / no div by zero |
| Font load failure | Delegated to `AssetManager.get_font()` | Fallback font returned | Already handled |

---

## 11. Deep Links

| Reference | Location |
|-----------|----------|
| InventoryUI (pattern to follow) | [inventory.py](../src/ui/inventory.py) |
| InteractionManager `_check_proximity_emotes` | [interaction.py L56](../src/engine/interaction.py#L56) |
| Game `_draw_scene` | [game.py L509](../src/engine/game.py#L509) |
| Game `_update` | [game.py L588](../src/engine/game.py#L588) |
| Interactive objects spec — Emote Suppression | [interactive-objects.md §2 L68](./interactive-objects.md#L68) |
| Asset: chest background | `assets/images/HUD/07-chest.png` |
| Asset: slot frame | `assets/images/ui/03-inventory_slot.png` |

---

## 12. Spec Gate Self-Assessment

| # | Check | Status |
|---|-------|--------|
| 1 | Actionable | ✅ |
| 2 | Current | ✅ |
| 3 | Single Source | ✅ |
| 4 | Decision, Not Wish | ✅ |
| 5 | Prompt-Ready | ✅ |
| 6 | No Future State | ✅ |
| 7 | No Fluff | ✅ |
| 8 | Assumptions Table (7 entries, risk-rated) | ✅ |
| 9 | External API Contract — N/A | N/A |
| 10 | Type: Implementation | ✅ |
| 11 | Anti-patterns in impl doc (10 entries) | ✅ |
| 12 | Test Cases in impl doc (11+12) | ✅ |
| 13 | Error Handling in impl doc (5 entries) | ✅ |
| 14 | Deep Links — all exact | ✅ |
| 15 | No Duplicates | ✅ |

**AI Coder Score: 9/10**  
Residual ambiguity: exact pixel fractions for the image zones (Assumption A-04). These are visual estimates requiring one calibration pass after first render.
