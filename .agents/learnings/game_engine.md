## 🎮 Game Engine

### L-GAME-001 · 2026-04-28 · U · Perfect
**Footprint-based interaction center**

Decouple the visual sprite position (`midbottom` alignment) from the logical interaction center (footprint center). Supports varied asset sizes and tall sprites without breaking grid-consistent interaction math.

---

### A-EVENT-002 · 2026-05-03 · P · Minor Rework
**`pygame.event.post()` re-queues events handled by the orchestrator**

`GameStateManager._handle_playing()` re-posts filtered events via `pygame.event.post()` so `Game._handle_events()` can consume them. If BOTH layers handle the same key (e.g., `TOGGLE_FULLSCREEN_KEY`), the key triggers twice per press — double-toggling fullscreen.

```python
# ❌ Orchestrator handles K_p AND re-posts it to Game which also handles K_p
filtered = [e for e in events if not (e.type == KEYDOWN and e.key == K_ESCAPE)]
for event in filtered:
    pygame.event.post(event)  # K_p survives the filter
# Then Game._handle_events() sees K_p and calls toggle_fullscreen() again

# ✅ Remove the duplicate handler from Game._handle_events()
# The orchestrator (_process_global_events) owns all cross-state keys.
# Game._handle_events() only handles gameplay-local keys (interact, inventory...).
```

**Règle :** Keys handled in the orchestrator's `_process_global_events()` MUST be removed from `Game._handle_events()`. If `pygame.event.post()` is used, the inner game handler is a secondary consumer — it will see every non-filtered event.

**Evidence:** `K_p` toggled fullscreen twice per press. Fixed by removing handler from `Game._handle_events()`. commit `ca94c9c`.

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

### A-ARCH-003 · 2026-05-01 · U · Minor Rework
**Rendering loop disconnected from dynamic properties**

When an object's state (e.g., `is_on`) transitions from an event-driven boolean to a dynamically computed property (e.g., based on `TimeSystem.brightness`), the rendering state (e.g., sprite index) must be actively synchronized in the `update()` loop.

```python
# ❌ Rendering sprite column only updates on explicit interaction
def interact(self):
    self.is_on = not self.is_on
    self._update_col_index()  # OK for manual, but misses auto-toggles

# ✅ Polling dynamic state in the update loop
def update(self, dt):
    if getattr(self, 'day_night_driven', False):
        self._update_col_index()  # Sync visual state with computed property
```

**Rule:** When replacing static state variables with dynamically computed properties, ensure the `update()` loop polls and synchronizes any visual or layout properties that depend on them.
**Evidence:** Day/night torches computed `is_on=False` correctly at dawn, but rendered the "ON" sprite because `col_index` was only updated during `interact()`.

---



### A-ARCH-001 · 2026-04-30 · U · Minor Rework
**Disk I/O dans une méthode appelée à chaque ouverture de panneau**

`ChestUI._compute_layout()` appelait `_load_slot_image()` (chargement disque + `convert_alpha()`) à chaque ouverture de coffre. L'image était déjà disponible en attribut depuis `__init__`.

```python
# ❌ I/O disque à chaque open() — spike CPU visible
self._slot_img = pygame.transform.smoothscale(
    self._load_slot_image(),   # charge depuis disque
    (slot_size, slot_size)
)

# ✅ scale depuis l'attribut déjà en mémoire — zéro I/O
self._slot_img = pygame.transform.smoothscale(self._slot_img, (slot_size, slot_size))
```

**Règle :** Toute méthode `_compute_layout()` / `_rebuild_layout()` ne doit jamais déclencher d'I/O disque. Les assets sont chargés UNE FOIS dans `__init__`. La spec doit explicitement mentionner « No disk I/O in `draw()` or `_compute_layout()` ».

**Evidence :** `chest.py::_compute_layout` ligne 350 — `_load_slot_image()` remplacé par `self._slot_img`.

---

---

### A-ARCH-002 · 2026-04-30 · U · Spec Wrong
**Singleton réinstancié à chaque appel — leurre de performance**

`_trigger_dialogue()` dans `game.py` appelait `I18nManager()` (constructeur) à chaque dialogue déclenché. Le singleton `__new__` retourne la même instance, mais le pattern visuel `SomeManager()` dans une méthode d'update/event signal une intention de réinstanciation.

```python
# ❌ pattern trompeur — semble créer une nouvelle instance
msg = I18nManager().get(f"dialogues.{full_key}")

# ✅ utiliser l'attribut de classe — intention claire
msg = self.i18n.get(f"dialogues.{full_key}")
```

**Règle :** Les singletons ne doivent jamais être appelés par leur constructeur dans des méthodes chaudes. Toujours stocker la référence singleton comme attribut d'instance (`self.i18n = I18nManager()`) dans `__init__` et utiliser `self.i18n` partout.

**Scope :** Universal — s'applique à tout singleton (AudioManager, Settings, etc.).

**Evidence :** `game.py::_trigger_dialogue` ligne 402.

---

---

### L-ARCH-004 · 2026-04-30 · U · Perfect
**Dispatcher thin + helpers privés pour les méthodes > 50L**

`_spawn_entities()` (93L) et `_check_proximity_emotes()` (68L) ont été décomposées en dispatcher léger + helpers privés focalisés, sans changer le comportement observable.

**Pattern :**
```python
# ❌ 90 lignes de if/elif avec logique imbriquée
def _spawn_entities(self, entities):
    for ent in entities:
        if type == "interactive":
            # 40 lignes...
        elif type == "teleport":
            # 15 lignes...

# ✅ dispatcher 20L + helpers 20-30L chacun
def _spawn_entities(self, entities):
    for ent in entities:
        if type == "interactive": self._spawn_interactive(ent, props, map_name)
        elif type == "teleport":  self._spawn_teleport(ent, props)

def _spawn_interactive(self, ent, props, map_name): ...  # 30L
def _spawn_teleport(self, ent, props): ...               # 12L
```

**Règle :** Toute méthode >40L qui contient un `if/elif` de dispatch doit être décomposée. Le dispatcher ne doit faire que router — aucune logique métier.

**Evidence :** `game.py` (-70L sur `_spawn_entities`), `interaction.py` (-55L sur `_check_proximity_emotes`), `inventory.py` (-60L sur `draw`). Zéro régression.

---

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

---

### L-PERF-001 · 2026-05-03 · U · Perfect
**Profiling-Driven Non-Optimization**

**Pattern (what to reproduce)**
Always run `profile_game.py` or equivalent profiling tools as the absolute first step of any optimization task. If the active frame time is < 50% of the frame budget (e.g. <8ms for a 16.6ms frame at 60fps), STOP. Declare the system performant and exit the optimization workflow. Do not implement architectural "optimizations" (like caching or pre-rendering) if there is no measurable bottleneck, as this only adds premature complexity.

**Evidence:**
- Executed `@[/performance-optimization]`.
- `profile_results.txt` showed `6.355s` spent idling in `Clock.tick()` out of `10.828s` total for 600 frames. Active frame time was 7.45ms.
- Exited the workflow without touching code, saving time and preventing divergence.

---

---

### L-ARCH-007 · 2026-05-04 · U · Perfect
**Break TYPE_CHECKING cycles with `Any` for same-layer mutual imports**

When two modules in the same layer mutually import each other, a `TYPE_CHECKING` guard delays the circular import to type-checking time — but architectural cycle detectors (sentrux) still flag it. For same-layer dependencies used only as a runtime attribute bag (not for type narrowing), type with `Any`.

```python
# ❌ Cycle still detected by sentrux at architecture level
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.engine.game import Game

class InteractionManager:
    def __init__(self, game: "Game"): ...

# ✅ Zero cycle: same layer, attribute access, no narrowing needed
from typing import Any

class InteractionManager:
    def __init__(self, game: Any): ...
```

**Rule:** Use `Any` for same-layer circular refs where the type annotation provides no functional value. Reserve `TYPE_CHECKING` for cross-layer deps where type correctness adds real IDE value.

**Evidence:** `sentrux check` flagged `game.py ↔ interaction.py` as 1 cycle. After `Any` refactor: 0 cycles.

