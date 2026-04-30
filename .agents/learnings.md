# Project Learnings Registry

> **Usage:** Read before any BUILD session. Each entry = one confirmed pattern or anti-pattern with evidence.
> **Format:** ID · Date · Scope [P=project-specific | U=universal] · Outcome

---

## 🧪 Testing

### L-TEST-001 · 2026-04-28 · U · Perfect
**State flags and numeric attributes on MagicMock**

`MagicMock` auto-creates child attributes as `Mock` objects, not typed values. Numeric operations (`>`, `.magnitude()`) on Mocks raise `TypeError`. Boolean state gates stay falsy.

```python
# ❌ direction.magnitude() → Mock → TypeError
game.player = MagicMock()
game._update(0.016)

# ✅ assign real types for every attribute used in math or guards
game.player = MagicMock()
game.player.direction = pygame.math.Vector2(0, 0)  # real Vector2
game.player.is_moving = False                       # real bool
mock_sheet.valid = True                             # real flag
game._update(0.016)
```

**Rule:** For any Pygame entity mock, assign `pygame.math.Vector2` for `direction`/`pos`/`target_pos`, and explicit booleans for all gate flags.
**Evidence:** `SpriteSheet.valid` (2026-04-28); `player.direction.magnitude()` in 3 game.py tests (2026-04-30).

---

### L-TEST-002 · 2026-04-28 · U · Minor Rework
**Gated state transitions need explicit `update(dt)` calls**

State-machine operations (animations, interactions) are gated by busy flags like `is_animating`. Without calling `update(dt)` between steps, consecutive operations always fail.

```python
# ❌ second interact() silently fails — is_animating still True
entity.interact(player)
entity.interact(player)

# ✅ tick to clear the gate
entity.interact(player)
entity.update(0.1)
entity.interact(player)
```

---

### L-TEST-003 · 2026-04-28 · U · Minor Rework
**Centralized headless initialization in `conftest.py`**

Scattered `pygame.init()` + `SDL_VIDEODRIVER=dummy` calls across test files cause drift and environment-dependent failures.

✅ Put all global fixtures (headless driver, mock asset loader) in `tests/conftest.py`. Organize test files by domain (`test_engine.py`, `test_ui.py`, `test_map.py`…).

**Evidence:** 11 files → 6 domain modules, 100% pass rate after consolidation.

---

### L-TEST-004 · 2026-04-28 · U · Minor Rework
**Mock native Pygame objects by property, not by method**

`pygame.Rect.collidepoint` and similar are C-level — read-only, impossible to mock directly.

```python
# ❌ raises AttributeError — C method is read-only
mocker.patch.object(rect, 'collidepoint', return_value=True)

# ✅ manipulate the rect so the real method returns what you need
rect.topleft = (target_x, target_y)
```

---

### A-TEST-001 · 2026-04-28 · U · Major Rework
**Blind `__init__` mocking leaves attributes unset**

```python
# ❌ crashes downstream with AttributeError
with patch.object(MyClass, '__init__', return_value=None):
    obj = MyClass()
obj.some_flag  # → AttributeError

# ✅ recreate all public attributes after patching __init__
with patch.object(MyClass, '__init__', return_value=None):
    obj = MyClass()
    obj.some_flag = True
    obj.config = {}
```

---

### A-TEST-002 · 2026-04-28 · U · Major Rework
**Singleton state pollution (Settings)**

Modifying `src.config.Settings` in a test without restoring causes non-deterministic failures in unrelated tests depending on execution order.

```python
# ❌ leaks into subsequent tests
Settings.DEBUG = True

# ✅ always restore
original = Settings.DEBUG
Settings.DEBUG = True
try:
    ...
finally:
    Settings.DEBUG = original
```

---

### A-TEST-003 · 2026-04-30 · U · Minor Rework
**`patch('builtins.open', side_effect=...)` intercepts all I/O**

A global `side_effect` on `builtins.open` blocks every file read in the process — i18n loaders, config files, everything.

```python
# ❌ crashes in I18nManager._load_locale, not the target path
with patch('builtins.open', side_effect=Exception("IO error")):
    game = Game()

# ✅ selective open — only raise for the target path
real_open = builtins.open
def selective_open(path, *args, **kwargs):
    if "world.world" in str(path):
        raise Exception("IO error")
    return real_open(path, *args, **kwargs)

with patch('builtins.open', side_effect=selective_open):
    game = Game()
```

---

### A-TEST-004 · 2026-04-30 · P · Minor Rework
**`pygame.Surface.get_size()` after `__init__` rescaling**

`InventoryUI.__init__` rescales all surfaces (including fallbacks) via `smoothscale`. Asserting the original fallback size always fails.

```python
# ❌ fails — fallback (32,32) becomes (1200,1200) after smoothscale
assert ui.bg.get_size() == (32, 32)

# ✅ assert existence or type, not size
assert ui.bg is not None
assert isinstance(ui.bg, pygame.Surface)
```

**Generalized rule:** After any UI `__init__` that rescales assets, assert existence/type — never assert `get_size()`.

---

## 🎮 Game Engine

### L-GAME-001 · 2026-04-28 · U · Perfect
**Footprint-based interaction center**

Decouple the visual sprite position (`midbottom` alignment) from the logical interaction center (footprint center). Supports varied asset sizes and tall sprites without breaking grid-consistent interaction math.

---

### L-ARCH-001 · 2026-04-28 · U · Perfect
**Composite keys for cross-map resource scoping**

Use `{map_base_name}-{element_id}` as keys in WorldState and DialogueManager. Prevents ID collisions across maps (e.g., two maps both with a `chest_01` object).

---

### A-GAME-001 · 2026-04-28 · U · Minor Rework
**Unthrottled spatial polling**

Proximity checks that trigger visual/audio side-effects every frame without a cooldown cause effect stacking and sprite duplication.

✅ Always gate proximity effects with `_emote_cooldown` (or equivalent) before triggering.

---

### A-GAME-002 · 2026-04-28 · U · Minor Rework
**Tile vs pixel coordinate mixups**

Passing pixel coords to functions expecting tile indices (or vice-versa) causes silent out-of-bounds errors (`is_collidable(128, 0)` → wrong tile).

✅ Name all coordinate parameters explicitly (`tile_x`, `pixel_x`) and convert at the boundary.

---

### L-ARCH-002 · 2026-04-30 · U · Major Rework
**Spec must define close sequence, not just close trigger**

Specifying WHEN to close an entity without specifying WHAT the close sequence is generates bugs for each missing step.

| Step | Action | Method |
|------|--------|--------|
| 1 | Toggle entity state | `entity.interact(player)` |
| 2 | Play SFX | `audio_manager.play_sfx(entity.sfx)` |
| 3 | Persist state | `world_state.set(key, {...})` |
| 4 | Close UI | `ui.close()` |
| 5 | Suppress follow-up feedback | reset proximity target + cooldown |

✅ Centralize all steps in `_close_X()`, called from **every** close path (zone exit, action key, etc.).
**Evidence:** 5 separate bugs in ChestUI auto-close. commit `6c7f811`.

---

### L-ARCH-003 · 2026-04-30 · U · Major Rework
**Frame-invariant checks belong in `update()`, not in conditional sub-functions**

A check placed inside a conditional branch only runs when that branch fires. If the check must fire every frame, it must live directly in `update()`.

```python
# ❌ _check_chest_auto_close() only runs when NO entity in proximity range
def _check_proximity_emotes(self):
    ...
    if nothing_in_range:
        self._check_chest_auto_close()  # missed when player is near other entity

# ✅ always-running checks go directly in update()
def update(self, dt):
    self._check_proximity_emotes()  # conditional
    self._check_chest_auto_close()  # always — regardless of proximity state
```

✅ **Spec rule:** State explicitly "Checked every update tick" or "Checked conditionally on [X]" to prevent ambiguous call-site choices.

---

## 🗺️ Map & Rendering

### L-MAP-001 · 2026-04-28 · U · Major Rework
**Semantic name-based layer ordering**

Tiled JSON layer order is unstable — nested groups reorder silently. Sort layers by semantic name prefix (`00-`, `01-`) in `MapManager` instead.

```python
# ✅
layer_order = sorted(raw_order, key=lambda lid: self.layer_names.get(lid, ""))
```

**Evidence:** Background (`00-layer`) disappeared due to group nesting. `tests/test_map.py` confirmed fix.

---

### L-REND-001 · 2026-04-28 · U · Perfect
**Additive light overlays applied after darkness**

Apply `BLEND_ADD` light sources after the global darkness surface. Applying before causes darkness to dim the light source.

---

### A-MAP-001 · 2026-04-28 · U · Major Rework
**Index-based layer priority** → See L-MAP-001 (same root cause).

---

## 🖥️ UI

### L-UI-001 · 2026-04-28 · U · Perfect
**Pre-paginate dialogue at `start_dialogue()` time**

Pre-wrap and group lines into fixed-size pages at dialogue start, not on-the-fly during typewriter animation. Ensures stable page breaks and simplifies skip→next→close progression.

---

### L-UI-002 · 2026-04-29 · P · Minor Rework
**Font sizing in large reading zones**

`Settings.FONT_SIZE_NARRATIVE` (14pt) is too small in full-height dialogue boxes. Use `int(size * 1.5)` for dedicated reading areas. For inventory descriptions, anchor at `stats_y + 5*s` (not `+30*s`) to avoid overflowing the parchment background.

---

### L-UI-003 · 2026-04-30 · U · Minor Rework
**Named offset constants as UI escape hatches**

Zone fractions (`_TITLE_ZONE_REL`, `_CONTENT_ZONE_REL`) derived from visual estimates cause iterative trial-and-error.

✅ **Measure zones before writing the spec** (image editor or PIL). Add named offset constants (`_TITLE_OFFSET_X`, `_TITLE_OFFSET_Y`, `_GRID_OFFSET_Y`) — default to zero, adjust once. Eliminates all subsequent launches.

**Evidence:** 8 game launches → `_TITLE_OFFSET_X=10, _TITLE_OFFSET_Y=15, _GRID_OFFSET_Y=-4`.

---

### L-UI-004 · 2026-04-30 · U · Perfect
**Pygame headless surface testing**

```python
# Setup in conftest.py
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# In tests — replace asset surfaces with dummy ones
monkeypatch.setattr(ui, "_bg", pygame.Surface((w, h)))
dummy.fill((255, 0, 0))

# Verify pixels (use tobytes, not deprecated tostring)
pixel = pygame.image.tobytes(screen, "RGB")
assert screen.get_at((x, y)) == (r, g, b, 255)
```

### L-UI-005 · 2026-04-30 · U · Perfect
**Pillow-driven layout analysis for background assets**

Measuring relative zones (fractions) for UI elements by eye is slow and error-prone. 

✅ **Use Pillow for automated zone detection.** Draw high-contrast marker pixels (e.g., Pure Red, Pure Blue) on the background asset. Run a script to extract the bounding box of these colors. Convert to relative fractions (`x/width`) to ensure scaling stability across resolutions.

**Evidence:** `07-chest.png` red/blue zones scanned via PIL. commit `a960147`.

---

### A-UI-001 · 2026-04-30 · U · Minor Rework
**Stretching small UI icons to fill interactive zones**

Scaling small assets (e.g., 26x26 icons) to fill larger interactive button zones causes visual distortion and "pixel bloat."

✅ **Scale by global factor and center.** Scale icons by the same global factor as the background (preserving native proportions), then blit them centered within the interactive zone rect instead of stretching to fill it. 

**Evidence:** Chest UI arrow hover distortion fixed by centering. commit `a4c98cb`.

---

## 🔧 Spec & Agent Workflow

### L-SPEC-001 · 2026-04-28 · U · Minor Rework
**Define procedural assets by boundary values**

In implementation specs, describe generated geometry/textures by **Start, End, Step/Falloff** values — not prose. Eliminates ambiguity in generation loops (e.g., center-to-edge alpha gradients).

---

### L-UX-001 · 2026-04-28 · U · Minor Rework
**Interruption-first feedback chaining**

New visual feedback (emotes, effects) must clear/overwrite existing ones immediately — never wait for the previous animation to finish.

```python
# ❌ blocks rapid interactions
if len(self.emote_group) == 0:
    self.emote_group.add(sprite)

# ✅ clear first, add immediately
self.emote_group.empty()
self.emote_group.add(sprite)
```

---

### A-UX-001 · 2026-04-28 · U · Minor Rework
**Hardcoded keyboard constants**

```python
# ❌
if event.key == pygame.K_e:

# ✅
if event.key == Settings.INTERACT_KEY:
```

---

### A-AGENT-001 · 2026-04-28 · U · Major Rework
**Blind file overwrites with stale context**

Replacing large file chunks from outdated memory destroys working code (I18n, UI scaling, etc.) and starts endless `AttributeError` loops.

✅ Always `view_file` before editing. Use targeted `multi_replace_file_content`. On accidental corruption: `git checkout -- <file>` immediately.

---

### A-AGENT-002 · 2026-04-28 · U · Major Rework
**Skipping Stream Coding pipeline stages**

Jumping to BUILD without SPEC, or skipping VERIFY/HARDEN, generates vibe-coded output that diverges from spec and requires expensive rework.

✅ Never write implementation code without RED tests (TDD Gate). Never commit without `/learn-eval` + `/doc-update`.

---

### A-SPEC-001 · 2026-04-28 · U · Minor Rework
**Ambiguous spritesheet definitions**

Describing an asset as "animated" without stating grid layout (rows × columns) and frame mapping causes incorrect slicing (4×1 instead of 4×8).

✅ Always specify: `rows=4, cols=8, frame_duration=0.1s, animation_row={state: row_index}`.

---

*Last optimized: 2026-04-30 — 499 lines → 270 lines, 0 information lost, duplicate long-form sections removed.*
