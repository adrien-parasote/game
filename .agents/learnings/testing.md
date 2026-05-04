## 🧪 Testing

### A-TEST-005 · 2026-05-04 · U · Minor Rework
**Process-wide teardowns in unit tests**

Unpatched calls to `pygame.quit()` or `sys.exit()` during a unit test will secretly tear down the Pygame module (including the font module) for the entire testing process. This causes seemingly unrelated tests to fail randomly.

```python
# ❌ tears down Pygame for all subsequent tests
def test_global_events():
    events = [pygame.event.Event(pygame.QUIT)]
    game._process_global_events(events)

# ✅ patch process-wide teardowns
def test_global_events():
    events = [pygame.event.Event(pygame.QUIT)]
    with patch("sys.exit"), patch("pygame.quit"):
        game._process_global_events(events)
```

**Rule:** Never trigger process-wide teardowns (`sys.exit()`, `pygame.quit()`) in unit tests without explicitly patching them.
**Evidence:** 17 UI tests failed with `pygame.error: Invalid font (font module quit since font created)` directly after a global event handler test successfully ran unpatched. Fixed by adding `patch("pygame.quit")`.

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

---

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

---

### L-TEST-003 · 2026-04-28 · U · Minor Rework
**Centralized headless initialization in `conftest.py`**

Scattered `pygame.init()` + `SDL_VIDEODRIVER=dummy` calls across test files cause drift and environment-dependent failures.

✅ Put all global fixtures (headless driver, mock asset loader) in `tests/conftest.py`. Organize test files by domain (`test_engine.py`, `test_ui.py`, `test_map.py`…).

**Evidence:** 11 files → 6 domain modules, 100% pass rate after consolidation.

---

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

---

### L-TRACE-001 · 2026-05-04 · U · Perfect
**Marker-based spec↔test traceability with `@pytest.mark.tc`**

Decorating test functions with `@pytest.mark.tc("TC-ID")` enables automated traceability between specs and tests. Combined with a source-scanning report script (no subprocess needed — just regex over test files), this produces a coverage matrix with zero runtime overhead.

**Pattern to reproduce:**
```python
# 1. Register marker in pyproject.toml
[tool.pytest.ini_options]
markers = ["tc(id): Spec traceability"]

# 2. Decorate tests
@pytest.mark.tc("TC-LT-01")
def test_load_valid_json(self): ...

# 3. Report script scans source for decorators + specs for TC tables
# Cross-references → covered/missing/orphan
```

**Key design decisions:**
- Source scanning (`grep @pytest.mark.tc`) over `pytest --collect-only` — faster, no subprocess, no SDL init required.
- Domain-prefixed TC IDs (`CHEST-U-01`, `INT-I-03`) — prevents cross-spec collisions without verbose namespacing.
- Multiple markers on one function allowed when one test covers multiple TCs.

**Evidence:** 115 TC IDs across 14 specs, 90 functions decorated, 100% alignment. `scripts/tc_report.py` — 179 lines. commit `0916c6d`.

---

---

### A-TRACE-001 · 2026-05-04 · U · Minor Rework
**TC IDs must be globally unique from the start**

Generic prefixes like `TC-U-01`, `TC-I-01`, `TC-T-01` collided across 3 specs (chest-ui, interactive-objects, engine-core). Required renaming 161 IDs in 6 files.

**Rule:** When creating a new spec with Test Case Specifications, always use a domain-specific prefix:

| Spec domain | Prefix |
|-------------|--------|
| Chest UI | `CHEST-` |
| Interactive objects | `INT-` |
| Engine core | `CORE-` |
| Game flow | `GF-` |
| World system | `WS-` |
| Lighting | `LT-` |
| Loot table | `TC-LT-` |
| NPC | `TC-N-` |

**Evidence:** 16 collisions found, 161 IDs renamed. commit `0916c6d`.

---

*Last optimized: 2026-05-04 — L-TRACE-001, A-TRACE-001 from spec↔test traceability session.*

---

---

### L-TRACE-002 · 2026-05-04 · U · Perfect
**Linked test functions table requires exact backtick-only names**

The `tc_report.py` regex pattern extracts TC IDs from specs using:
```
| TC-ID | `test_func_name` | `../../path` |
```

If the function name column contains extra text after the backtick-delimited name (e.g. `` `test_on_escape` (PLAYING→PAUSED) ``), the regex fails to match and reports the marker as ORPHAN even though the ID exists in the spec.

**Rule:** In `### Linked Test Functions` tables, the function column must contain **only** the function name in backticks, nothing else. Descriptions go in a comment column or separate prose.

**Evidence:** `GF-029` and `GF-030` reported as ORPHAN until the table entry was reduced to just `` `test_on_escape` ``. commit: in-session fix.

---

---

### A-TRACE-002 · 2026-05-04 · U · Minor Rework
**`pyproject.toml` marker registration can be silently lost**

The `@pytest.mark.tc` decorator requires `[tool.pytest.ini_options] markers = [...]` registration in `pyproject.toml`. This file can be accidentally emptied (e.g. by an overwrite tool call with empty content), causing all marks to generate `PytestUnknownMarkWarning` silently — tests still pass but markers are no longer registered.

**Rule:** After any HARDEN commit, verify `pyproject.toml` still contains the markers section. Add this to the doc-update drift detection checklist.

**Evidence:** `pyproject.toml` was emptied mid-session. Detected during doc-update drift check. Fixed by restoring the 4-line marker definition.

---

*Last optimized: 2026-05-04 — L-TRACE-002, A-TRACE-002 from traceability HARDEN session.*

---

---

### L-STATIC-001 · 2026-05-04 · U · Minor Rework
**`assert x is not None` raises `AssertionError`, not `RuntimeError` — update test expectations**

When a guard pattern changes from `raise RuntimeError(...)` to `assert x is not None`, any test expecting `RuntimeError` will fail with a confusing `AssertionError` instead.

```python
# ❌ Old guard pattern — RuntimeError
if self.font is None:
    raise RuntimeError("Font not set")

# ✅ New assert guard — raises AssertionError
assert self.font is not None

# Test must match the actual exception type:
# ❌ with self.assertRaises(RuntimeError): ...
# ✅ with self.assertRaises(AssertionError): ...
```

**Rule:** When converting `raise RuntimeError` to `assert`, run `grep -r "assertRaises(RuntimeError)"` in the test suite and update all matching tests.

**Evidence:** `test_speech_bubble.py::TestSpeechBubbleFontGuard::test_raises_when_font_not_set` failed 1 test after `draw()` guard was migrated to `assert self.font is not None`.

---

---

### L-STATIC-002 · 2026-05-04 · U · Minor Rework
**Stub/Dummy classes need explicit `str | None` type annotations for Pyright strict mode**

Mock/stub classes that initialize attributes to `None` and later assign string values must use explicit type annotations. Without them, Pyright infers `None` type and blocks any heterogeneous assignment.

```python
# ❌ Pyright infers type as None — string assignment flagged
class DummySprite:
    def __init__(self):
        self.target_map = None      # inferred: None
        self.target_spawn_id = None # inferred: None

sprite.target_map = "next_map.tmj"  # ERROR: cannot assign str to None

# ✅ Explicit union allows heterogeneous assignment
class DummySprite:
    def __init__(self):
        self.target_map: str | None = None
        self.target_spawn_id: str | None = None
```

**Rule:** All stub/dummy/test helper classes in strict Pyright projects must declare every attribute with an explicit type annotation in `__init__`, even when the initial value is `None`.

**Evidence:** 4 `reportAttributeAccessIssue` errors in `tests/engine/test_interaction.py` resolved by annotating `DummySprite` attributes.

---

*Last optimized: 2026-05-04 — L-STATIC-001, L-STATIC-002 from Pyright hardening HARDEN session.*

---

---
