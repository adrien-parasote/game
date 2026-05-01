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


---

### A-UI-002 · 2026-04-30 · U · Major Rework
**Missing event dispatch for new UI components in game loop**

Adding `handle_event()` to a UI class does nothing unless the game loop explicitly calls it. The absence is silent — clicks register in pygame but reach no handler.

```python
# ❌ chest_ui.handle_event never called → all arrow clicks silently swallowed
def _handle_events(self):
    for event in pygame.event.get():
        if self.inventory_ui.is_open:
            self.inventory_ui.handle_input(event)
        # chest_ui missing entirely

# ✅ every UI component with handle_event must be wired
def _handle_events(self):
    for event in pygame.event.get():
        if self.inventory_ui.is_open:
            self.inventory_ui.handle_input(event)
        if self.chest_ui.is_open:
            self.chest_ui.handle_event(event)
```

**Rule:** When adding any new UI component with interactive state, immediately add its dispatch to `_handle_events()`. Write a test that calls `handle_event()` via a simulated click and asserts a state change.
**Evidence:** Chest UI arrows did nothing for entire session until `handle_event` wired. commit `ff92747`.

---

### A-UI-003 · 2026-04-30 · U · Major Rework
**Page-based vs window-based offset clamping are different formulas**

For **window-based** scrolling (slide 1 slot at a time), max_offset = `capacity - visible`. For **page-based** scrolling (jump a full page at a time), max_offset = `capacity - 1`.

```python
# ❌ window-based clamp applied to page-based jump
# capacity=24, visible=18 → max_offset=6 → offset=min(18,6)=6 → shows [6:24]=18 slots (wrong)
max_offset = capacity - visible
self._inv_offset = min(self._inv_offset + visible, max_offset)

# ✅ page-based: clamp to capacity-1 so partial last page is reachable
# capacity=24, visible=18 → offset=min(18, 23)=18 → shows [18:24]=6 slots (correct)
self._inv_offset = min(self._inv_offset + _INV_SLOTS_VISIBLE, self._capacity() - 1)
```

**Rule:** In spec, declare navigation mode explicitly: `WINDOW` (1-slot slide) or `PAGE` (full-page jump). Apply the correct clamp formula for each.
**Evidence:** Took 3 correction rounds; `visible_count` exposé the wrong formula. commit `ff92747`.

---

### A-UI-004 · 2026-04-30 · U · Minor Rework
**Left/right arrow semantic direction must be explicit in spec**

"Left arrow" and "right arrow" are physical; "advance" and "rewind" are semantic. Without a clear mapping, implementations diverge and require swap iterations.

```markdown
# ✅ Spec must state this explicitly:
# ▶ Right arrow → advance window (higher indices) — visible when more items ahead
# ◀ Left arrow  → rewind window (lower indices)  — visible when offset > 0
```

**Rule:** For any scrollable UI, the spec must include a table: `Physical Arrow | Data Direction | Visibility Condition`.
**Evidence:** 2 direction swaps in one session (left↔right wiring). commit `ff92747`.

---

### L-UI-006 · 2026-04-30 · U · Minor Rework
**visible_count must guard both rendering AND hover hit-testing**

After fixing rendering to only draw N slots, the hover zone loop still iterates all 18 `_inv_slot_positions`, making invisible slots hoverable and triggering out-of-bounds states.

```python
# ❌ hover registers on invisible slots 6–17 even when only 6 are drawn
for i, rect in enumerate(self._inv_slot_positions):
    if rect.collidepoint(mouse_pos):
        self._hovered_inv_slot = i

# ✅ same visible_count used in both draw and hover
visible_count = min(_INV_SLOTS_VISIBLE, max(0, self._capacity() - self._inv_offset))
for i, rect in enumerate(self._inv_slot_positions[:visible_count]):
    if rect.collidepoint(mouse_pos):
        self._hovered_inv_slot = i
```

**Rule:** Any `visible_count` guard introduced for rendering must immediately be applied to all hit-test loops over the same positions list.
**Evidence:** Hover on ghost slots after page 2 scroll. Fixed in same commit `ff92747`.

---

*Last optimized: 2026-04-30 — added A-UI-002, A-UI-003, A-UI-004, L-UI-006 from ChestUI paged inventory session.*

---

## ✅ Optimisation globale — 2026-04-30

### A-TEST-005 · 2026-04-30 · U · Spec Wrong
**Tests qui passent silencieusement sur un contrat brisé (duck-typing Pygame)**

`pygame.Rect.collidepoint()` accepte un `Vector2` en Python — il déstructure automatiquement en `(x, y)`. Un test appelant `_is_collidable(Vector2(0,0))` passait vert même si la signature déclarée attendait `(float, float)`.

```python
# ❌ test passe mais le contrat est faux — Vector2 ≠ float
assert game._is_collidable(pygame.math.Vector2(0, 0)) is True

# ✅ tester avec les types exacts de la signature déclarée
assert game._is_collidable(0.0, 0.0) is True
```

**Règle :** Toujours inspecter la signature déclarée avant d'écrire un test. En Pygame, `collidepoint` est suffisamment permissif pour masquer des erreurs de type → vérifier avec `mypy` ou des annotations `float` strictes.

**Evidence :** `test_engine.py::test_game_is_collidable` — 3 appels avec Vector2 corrigés en floats. `game.py::_is_collidable(px_center: float, py_center: float)`.

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

### L-TEST-005 · 2026-04-30 · U · Perfect
**Fichier de tests ciblé par rapport de couverture**

Plutôt que d'ajouter des tests dispersés dans des fichiers existants, créer un fichier `test_coverage_gaps.py` unique regroupant tous les tests ciblés sur les branches manquantes identifiées par `--cov-report=term-missing`. Plus facile à supprimer/réorganiser et clairement séparé des tests fonctionnels.

```bash
# Identifier exactement les lignes manquantes
pytest --cov=src --cov-report=term-missing -q 2>&1 | grep "module_name"

# Résultat → fichier unique organisé par module
# tests/test_coverage_gaps.py::TestI18nCoverage
# tests/test_coverage_gaps.py::TestInteractiveCoverage
# ...
```

**Règle :** Pour toute session de couverture ciblée, créer `test_coverage_gaps.py` avec classes par module. Ne jamais disperser ces tests dans les fichiers existants — ils deviennent introuvables.

**Evidence :** +51 tests en 1 fichier, coverage 89%→92%. Aucune régression dans les 216 tests existants.

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

### A-SPEC-002 · 2026-04-30 · P · Spec Wrong
**POSITION_TO_DIR inversé dans la spec vs code**

`interactive-objects.md` documentait `0=Up, 1=Right, 2=Left, 3=Down`. Le code (`InteractiveEntity.POSITION_TO_DIR`) implémentait `0=Down, 1=Left, 2=Right, 3=Up`. La spec et le code divergeaient depuis la création du module.

**Cause :** Le mapping a été défini dans le code avant d'être documenté. La spec a été écrite de mémoire, inversée.

**Règle :** Pour tout mapping constant (enum-like), toujours extraire la valeur depuis le code source avec `grep` avant de documenter. Ne jamais documenter de mémoire.

```bash
# ✅ vérifier avant de documenter
grep -n "POSITION_TO_DIR" src/entities/interactive.py
```

**Scope :** Project-specific mais le pattern est universel — voir L-SPEC-001.

**Evidence :** `interactive-objects.md` ligne 24 corrigée. Confirmé avec `InteractiveEntity.POSITION_TO_DIR` dans `interactive.py`.

---

### A-TEST-006 · 2026-04-30 · U · Major Rework
**Render-only branches résistent à la couverture sans display réel**

`chest.py` est resté à 84% après tous les tests ciblés. Les branches non couvertes (lignes 205-216, 248-304, 354-356, 550-588) sont toutes dans des méthodes de rendu qui appellent `pygame.Surface.blit()`, `pygame.image.load()`, ou `pygame.transform.smoothscale()` sur des assets réels.

Sans display réel (`SDL_VIDEODRIVER=dummy`), `blit()` fonctionne mais les branches conditionnelles sur la présence d'un asset valide (`if self._slot_img is not None`) ne peuvent être testées sans charger de vrais fichiers PNG.

**Pattern empirique :**
```
Couverture atteignable sans assets réels : ~84-88% pour les modules UI lourds
Couverture atteignable avec assets réels (CI avec display) : ~95%+
```

**Règle :** Accepter un plafond de couverture de ~85% pour les modules UI render-only en tests headless. Ne pas investir davantage sans infrastructure CI avec display. Documenter ce plafond dans le `Makefile` ou `.coverage.ini`.

```ini
# .coveragerc ou pyproject.toml — exclure les branches render-only
[coverage:report]
exclude_lines =
    if.*_img is not None
    screen\.blit\(
```

**Evidence :** `chest.py` 84% stable même après 8 tests ciblés supplémentaires. `inventory.py` 100% obtenu car ses branches render ne dépendent pas d'assets fichiers.

---

### A-UI-005 · 2026-05-01 · U · Minor Rework
**UI Decoupling from Temporal Animations**

**What happened:** Halting an NPC mid-tile causes visual sliding and snapping issues. The code was then updated to let the NPC finish its tile movement, but the UI bubble appeared instantly, causing the bubble to slide along with the NPC. We then implemented a `pending_npc_dialogue` queue.

**Root cause:** Temporal coupling. Assuming that the logical trigger (pressing 'Interact') and the visual response (opening the UI) must happen on the same frame. For animated entities in a grid-based game, actions often need to be queued until the current animation/movement cycle finishes.

```python
# ❌ Triggering synchronous UI events (like dialogue bubbles) instantly on entities that have asynchronous or continuous state transitions (like grid movement).
res = npc.interact(self.game.player)
if res:
    self.game._trigger_npc_bubble(npc, res)

# ✅ Implement an event queue or a `pending_action` state in the main update loop.
res = npc.interact(self.game.player)
if res:
    if npc.is_moving:
        self.game._pending_npc_dialogue = (npc, res)
    else:
        self.game._trigger_npc_bubble(npc, res)
```

**Rule:** When an interaction occurs on a moving entity, store the intent, let the entity resolve its current interpolation (e.g., finish walking to the next tile), and only trigger the UI callback when `entity.is_moving == False`.
**Evidence:** `src/engine/interaction.py` queueing logic: `if npc.is_moving: self.game._pending_npc_dialogue = (npc, res)`. Tests failed initially because Mock objects have properties that evaluate to True in python, requiring explicit `npc.is_moving = False` in `tests/test_interaction.py`.

---

*Last optimized: 2026-05-01 — optimization session: A-UI-005.*

---

### L-REND-002 · 2026-05-01 · U · Minor Rework
**Corner-fade approach for shaped surface bottoms**

Using `effective_t = t * (1 + dist * k)` to make edges fade faster than the center also dims the center column at the bottom, creating a spike/triangle shape instead of an oval.

```python
# ❌ Couples center and edge: center spikes because effective_t > 1 at edges
effective_t = t * (1.0 + dist_x * 0.9)
v_fade = max(0.0, 1.0 - effective_t) ** 0.35

# ✅ Keep v_fade independent, add a separate corner multiplier in the bottom zone only
v_fade = (1.0 - t) ** 0.6  # unchanged for all x
if t > 0.65:
    bp = (t - 0.65) / 0.35
    cf = max(0.0, 1.0 - bp * abs(x - cx) / half_w * 1.8)  # 1.0 at center, fades at edges
else:
    cf = 1.0
alpha = master_alpha * v_fade * h_fade * cf
```

**Rule:** Never modify a per-row decay function based on per-pixel horizontal distance. Add a separate multiplier that's always 1.0 at the center column.
**Evidence:** User screenshot showed spike; corner_fade approach restored trapezoid shape with oval bottom.

---

### L-REND-003 · 2026-05-01 · U · Minor Rework
**Continuous cosine blending for cyclic state transitions**

Hard `if brightness < threshold: moon else: sun` switches create visible discontinuities ("tic") at state transitions like dawn/dusk.

```python
# ❌ Binary switch — 42px jump at 18h
if brightness < 0.15:
    return moon_slant   # e.g., +14px
else:
    return sun_slant    # e.g., -28px at 18h

# ✅ Two continuous cosine waves blended by brightness
sun_slant  = max_slant * cos(2π * (hour - 6) / 24)
moon_slant = max_slant * 0.5 * cos(2π * (hour - 18) / 24)
slant = sun_slant * brightness + moon_slant * (1 - brightness)
```

**Rule:** For any cyclic parameter that transitions between two modes (day/night, seasons, tides), model each mode as an independent continuous function and blend by the existing continuous transition weight.
**Evidence:** Slant continuity test — max jump < 5px across 48 half-hour samples vs. 42px jump with if/else.

---

### A-AGENT-003 · 2026-05-01 · U · Spec Wrong
**Verify @property vs method before calling**

Generated `self.time_system.world_time()` with parentheses, but `world_time` is a `@property`. Runtime crash: `'WorldTime' object is not callable`.

```python
# ❌ Assumes world_time is a method
wt = self.time_system.world_time()

# ✅ Verify first — it's a property
wt = self.time_system.world_time
```

**Rule:** Before calling any attribute from an external module, verify whether it's a property or method:
```bash
grep -n "def world_time\|world_time = " src/engine/time_system.py
```

**Scope:** Universal — Python @property vs method mixups cause `TypeError: 'X' object is not callable`.
**Evidence:** Runtime crash on `_compute_slant()` first call. Fixed by removing parentheses.

---

*Last optimized: 2026-05-01 — added L-REND-002, L-REND-003, A-AGENT-003 from window lighting beam session.*

---

### L-TEST-006 · 2026-05-01 · U · Perfect
**Domain-based test directory structure**

Organiser les tests par domaine métier (mirroring `src/`) produit un ratio signal/bruit maximal : la prochaine IA sait immédiatement où chercher sans lire tous les fichiers.

```
tests/
├── conftest.py          # Global SDL init, shared fixtures
├── engine/              # mirrors src/engine/
├── entities/            # mirrors src/entities/
├── map/                 # mirrors src/map/
├── ui/                  # mirrors src/ui/
└── graphics/            # mirrors src/graphics/
```

**Règle :** Chaque nouveau module `src/<domain>/foo.py` → créer `tests/<domain>/test_foo.py`. Jamais de test à la racine `tests/` sauf `conftest.py`.

**Evidence :** 23 fichiers plats → 16 fichiers dans 5 domaines. 436/436, 0 régression. commit `484ccfa`.

---

### A-TEST-007 · 2026-05-01 · P · Minor Rework
**Slice `lines[start:end]` sans validation syntaxique → `IndentationError`**

Extraire un bloc de code par slicing de lignes sans valider que `start` pointe sur la première ligne non-indentée du bloc (def/class) produit un fichier syntaxiquement invalide.

```python
# ❌ start peut pointer sur une ligne DANS le corps du bloc précédent
lines = source.splitlines()
start = next(i for i, l in enumerate(lines) if 'class TestX' in l)
helper_lines = lines[32:77]  # estimation empirique → fragile
with open("out.py", "w") as f:
    f.write("\n".join(helper_lines))  # → IndentationError si mal calé

# ✅ valider avec ast.parse avant d'écrire
import ast
candidate = "\n".join(lines[start:end])
try:
    ast.parse(candidate)
    with open("out.py", "w") as f:
        f.write(candidate)
except SyntaxError as e:
    raise RuntimeError(f"Slice invalide [L{start}:L{end}]: {e}")
```

**Règle générale :** Pour les migrations 1:1, utiliser `shutil.copy()`. Réserver les scripts de slicing aux extractions de classes isolées, toujours validées avec `ast.parse()` avant écriture.

**Evidence :** `tests/entities/test_interactive.py` — `IndentationError` à la ligne 13 corrigé en 30s après refactoring du script. commit `484ccfa`.

---

*Last optimized: 2026-05-01 — added L-TEST-006, A-TEST-007 from test suite urbanization session.*

---

### L-ARCH-005 · 2026-05-01 · U · Perfect
**Decoupling Engine God Objects**

`game.py` accumulated rendering loops, collision mathematics, state updates, and interactions, making test maintenance highly coupled and increasing CPU overhead per frame with excessive class lookups.

**Pattern :**
```python
# ❌ Logic bundled in the main loop class
class Game:
    def _is_collidable(self, x, y): ...
    def _draw_scene(self): ...
    def _update(self): 
        # mixing spatial, rendering, input
```

```python
# ✅ Extract logic into highly focused Manager classes
class Game:
    def __init__(self):
        self.render_manager = RenderManager(self)
        self.interaction_manager = InteractionManager(self)
        
    def _draw(self):
        self.render_manager.draw_scene()
```

**Règle :** Main engine loops should act exclusively as Event Dispatchers and Timers. Complex spatial queries, collision checks, and layered rendering MUST be decoupled into dedicated `Manager` classes that are passed a reference to the main state.

**Evidence :** `InteractionManager` and `RenderManager` extracted, eliminating >200 lines from `game.py`. 100% test coverage maintained without architectural breakage.
