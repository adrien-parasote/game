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

## Learning: Mock Dependency Drift

**Date:** 2026-05-03
**Spec:** Performance Optimization Plan
**Outcome:** Minor Rework
**Project:** Python Pygame Engine

### What happened
Added `layer_depths` caching to `MapManager` and used it in `RenderManager`. The implementation code was perfect, but the unit tests for `RenderManager` failed because `game.map_manager` was a `MagicMock` and `layer_depths` evaluated to a mock object instead of a dict, causing a `TypeError` on comparison.

### Root cause
Adding a new property to a core dependency (`MapManager`) without simultaneously updating the test mocks in dependent classes (`test_render_manager.py`).

### Anti-pattern (what to avoid)
❌ **Don't**: Add properties to a class without updating the `MagicMock` setups in the test files of other classes that depend on it.

✅ **Do Instead**: When adding a property to Class A, search the test suite for `MagicMock()` setups of Class A and explicitly assign the new property to the mock.

### Evidence
- Test failure in `test_render_manager_draw_background`: `TypeError: \'<=\' not supported between instances of \'MagicMock\' and \'int\'`

### Scope
- [x] Universal (applies across projects)

---

### L-ARCH-005 · 2026-05-03 · U · Perfect
**Extract Mixins to preserve test mock boundaries**

The `ChestUI` monolithic class (923 lines) needed splitting to comply with the <400 line rule. However, doing so via structural delegation (`self.transfer_manager._transfer()`) would break dozens of existing tests in `test_chest.py` that mock internal `ui._transfer_...` and `ui._draw_...` methods directly.

**Pattern (what to reproduce)**
When refactoring monolithic classes that are heavily mocked in existing unit tests, use **Composition via Mixins** instead of Component Delegation to satisfy file-size constraints without triggering massive test rewrites.

By extracting the logic into Mixin classes (`ChestTransferMixin`, `ChestLayoutMixin`, `ChestDrawMixin`) and having `ChestUI` inherit from them, the namespace remained identical. All 471 tests in the suite passed immediately without needing to update mock targets.

**Evidence:**
- `src/ui/chest.py` successfully split into 5 domain-specific files (`chest.py`, `chest_layout.py`, `chest_transfer.py`, `chest_draw.py`, `chest_constants.py`).
- The entire `pytest tests/ui/test_chest.py` suite (87 tests) passed with 0 functional changes to the tests themselves.

---

### L-ARCH-006 · 2026-05-03 · U · Minor Rework
**Private Constants Exporting with Wildcard Imports**

When extracting UI configuration into a dedicated `_constants.py` file, we encountered 31 `NameError` test failures in the Python test suite. 

**Anti-pattern (what to avoid)**
Using `from module_constants import *` will **not** import any constants prefixed with an underscore (e.g. `_ASSET_DIR`, `_FONT_PATH`), as Python treats them as private to the module. If these variables are needed in the consumer file, they will be undefined.

**Pattern (what to reproduce)**
When extracting private constants, you must either:
1. Rename the constants to remove the underscore (making them public).
2. Explicitly import the underscored variables alongside the wildcard import:
   `from module_constants import *`
   `from module_constants import _PRIVATE_VAR`
3. Define `__all__` in the constants file.

We chose option 2 to make the usage explicit.

**Evidence:**
- Extracted constants from 5 UI files into `_constants.py` files.
- `test_game.py` failed with `NameError: name '_MENU_ITEM_KEYS' is not defined`.
- Fixed by adding explicit imports for underscored variables, bringing the test suite back to 100% pass rate.

---

### L-PERF-001 · 2026-05-03 · U · Perfect
**Profiling-Driven Non-Optimization**

**Pattern (what to reproduce)**
Always run `profile_game.py` or equivalent profiling tools as the absolute first step of any optimization task. If the active frame time is < 50% of the frame budget (e.g. <8ms for a 16.6ms frame at 60fps), STOP. Declare the system performant and exit the optimization workflow. Do not implement architectural "optimizations" (like caching or pre-rendering) if there is no measurable bottleneck, as this only adds premature complexity.

**Evidence:**
- Executed `@[/performance-optimization]`.
- `profile_results.txt` showed `6.355s` spent idling in `Clock.tick()` out of `10.828s` total for 600 frames. Active frame time was 7.45ms.
- Exited the workflow without touching code, saving time and preventing divergence.
