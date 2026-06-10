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

---

### A-EF-001 · 2026-05-07 · P · Major Rework (silent bug)
**Dispatcher `startswith()` avec préfixe partagé entre types Tiled → entité silencieusement perdue**

Le type Tiled `'15-npc'` et les teleports (`'15-teleport'`, `'13-teleport'`) partagent le préfixe `'15-'`. Le dispatcher `spawn_entities` testait les teleports en premier avec `ent_type_field.startswith("15-")`, ce qui absorbait silencieusement tout objet `15-npc` avant d'atteindre la branche NPC. Zéro erreur, zéro warning — le NPC était simplement absent de la map.

```python
# ❌ Téléport intercepte le NPC silencieusement
elif _get_property(props, "type") == "teleport" or ent_type_field.startswith("15-"):
    self.spawn_teleport(ent, props)  # capte "15-npc" !
elif entity_type == "npc" or ...:
    self.spawn_npc(ent, props)       # jamais atteint

# ✅ NPC en priorité, exact match '15-npc', teleport après
elif entity_type == "npc" or ent_type_field == "15-npc" or ent_type_field.startswith("07-"):
    self.spawn_npc(ent, props)
elif _get_property(props, "type") == "teleport" or ent_type_field.startswith("15-"):
    self.spawn_teleport(ent, props)
```

**Règle :** Dans tout dispatcher sur des préfixes de chaînes, vérifier d'abord que les types les plus spécifiques (match exact ou sous-type nommé) sont checkés avant les catches larges (`startswith`). Documenter l'ordre de priorité dans la spec avec un ⚠️ explicite quand deux types partagent un préfixe.

**Règle spec :** Quand la spec décrit le type Tiled d'une entité dans les test cases (`TC-EF-06 : type '07-npc'`), elle doit refléter le type exact présent dans les assets Tiled — vérifiable via `python3 -c "import json; ..."` sur le fichier `.tmj`. Un type erroné dans les TCs = bug potentiel non couvert par les tests.

**Evidence :** `entity_factory.py` dispatch corrigé. `Spawned NPC 'npc' at [174, 462]` visible dans les logs après fix. `TC-EF-06` mis à jour dans `phase-1.5-game-refactoring.md` v1.3. 661/661 tests verts.
---

### L-GE-017 · 2026-05-14 · U · Major Rework
**`LootTable.get_contents()` retournait une shallow copy → corruption de l'état global**

`get_contents()` retournait `list(self._contents)` — une shallow copy de la liste, mais les items eux-mêmes étaient partagés. Modifier un item après un tirage (ex: décrémenter `quantity`) altérait l'état global de la LootTable, rendant les tirages suivants incorrects.

```python
# ❌ Shallow copy — les dictionnaires item sont partagés
def get_contents(self) -> list[dict]:
    return list(self._contents)  # même références → mutations propagées

# ✅ Deep copy — chaque tirage est une copie indépendante
import copy

def get_contents(self) -> list[dict]:
    return copy.deepcopy(self._contents)
```

**Règle :** Toute méthode `get_X()` qui retourne une collection mutable d'objets mutable DOIT retourner une `copy.deepcopy()`. Une shallow copy est insuffisante si les callers modifient les éléments retournés.

**Détection :** Chercher les méthodes retournant `list(self._X)` ou `dict(self._X)` dans les classes qui gèrent des données de jeu — vérifier si les callers mutent les éléments.

**Evidence :** Bug visible dans la debug room : ouvrir un coffre deux fois retournait des items avec quantity=0 car le premier tirage avait muté les items partagés. Corrigé en `copy.deepcopy`. Tests confirmés : 758/758 verts après fix.

---

*Last updated: 2026-05-15 — A-EF-002 factory game propagation, A-GAME-003 direction clear on blocked move, A-ML-001 interactive state not saved before map unload.*

---

### A-EF-002 · 2026-05-15 · P · Major Rework (silent bug)
**Factory `spawn_*` doit propager `entity.game = self.game` — omission = boundary clamping silencieux**

Lors du refactoring Phase 1.5 (L-ARCH-008), `EntityFactory` a été extrait de `game.py`. La méthode `spawn_npc()` n'a pas été mise à jour pour propager `npc.game = self.game`. Résultat : `BaseEntity.start_move()` utilisait `Settings.MAP_SIZE=32` (fallback par défaut) pour calculer la boundary monde → 32×32=1024px. Le NPC ID 23 en debug room est à y=1168px (map 40 tiles = 1280px). Tous les targets y étaient clampés à 1008px (zone de murs) → walkable check échoue → NPC bloqué.

```python
# ❌ game jamais assigné → boundary = MAP_SIZE fallback
npc = NPC(...)
npc.name = ...
npc.walkable_func = self.game.interaction_manager.is_walkable

# ✅ TOUJOURS assigner game avant walkable_func
npc.game = self.game        # ← obligatoire
npc.walkable_func = self.game.interaction_manager.is_walkable
```

**Règle :** Toute méthode `spawn_*` dans une factory extraite via le pattern L-ARCH-008 DOIT contenir `entity.game = self.game` avant toute utilisation de `self.game.*` sur l'entité. La spec doit lister `game` dans les attributs requis de l'entité.

**Contrôle :** Chercher `spawn_npc\|spawn_interactive\|spawn_` dans `entity_factory.py` et vérifier que chaque méthode propage `.game`.

**Evidence :** NPC ID 23 coincé en debug room. 3 tests RED → 4 GREEN. commit `c88d996`.

---

### A-GAME-003 · 2026-05-15 · U · Minor Rework (visual bug)
**Direction non clearée après move bloqué → retry infini + "spinning" visuel**

`NPC.start_move()` setait `self.state = "idle"` quand `super().start_move()` échouait (pas `is_moving`), mais laissait `self.direction != Vector2(0,0)`. `BaseEntity.move()` détecte `direction != 0` → appelle `start_move()` de nouveau à la prochaine frame. L'IA met à jour `current_facing` à chaque cooldown → le NPC tourne sur lui-même sans se déplacer.

```python
# ❌ State corrigé mais direction laissée → retry chaque frame
if not self.is_moving:
    self.state = "idle"

# ✅ Toujours synchroniser l'état complet de mouvement
if not self.is_moving:
    self.direction = pygame.math.Vector2(0, 0)  # ← empêche le retry
    self.state = "idle"
```

**Règle générale :** Après toute transition d'état échouée dans une state machine de mouvement, TOUS les champs qui contrôlent la re-entrée doivent être réinitialisés (pas seulement le state label). Un state `idle` avec `direction != 0` est un état invalide.

**Règle spec :** Documenter dans l'Error Handling Matrix la réponse exacte à "Invalid Path/Wander" : "clear `direction`, set `state = idle`" — pas juste "cancel wander".

**Evidence :** NPC spinning visible en debug room. `test_move_does_not_retry_start_move_after_blocked` RED → GREEN. commit `c88d996`.

---

### L-ARCH-008 · 2026-05-07 · U · Major Rework
**Pattern context injection `SomeManager(game: Any)` pour les refactorings "God Object"**

Quand `game.py` dépasse 800 LOC, extraire des classes en les alimentant via `game: Any` (context injection) :

```python
# Pattern : EntityFactory, MapLoader, InputHandler, CollisionChecker
from typing import Any

class EntityFactory:
    def __init__(self, game: Any) -> None:
        self.game = game  # accès via self.game.sprites, self.game.audio_manager, etc.
```

**Règles :**
1. Utiliser `game: Any` — pas `TYPE_CHECKING` (crée des cycles, détectés par sentrux DSM)
2. Instancier dans `Game.__init__` : `self._entity_factory = EntityFactory(self)`
3. `_load_map()`, `_handle_events()` deviennent des thin wrappers (3 LOC max) — signature inchangée pour les appelants externes
4. L'ordre d'instanciation dans `__init__` est critique : `_entity_factory` avant `_map_loader` (qui l'utilise)

**Résultats Phase 1.5 :**
- `game.py` : 732 → 420 LOC
- `interaction.py` : 474 → 400 LOC
- Suite : 647 tests, tous verts

**Evidence :** [`docs/game/specs/engine-core.md`](../../docs/game/specs/engine-core.md), ADR-004.

**Scope :** Project-specific (pattern général Python)

> *Migré depuis `.agents/learnings/methodology_and_docs.md` le 2026-05-15 (audit documentation — L-DOC-005 : un learning = un seul fichier domaine).*

---


### A-ML-001 · 2026-05-15 · U · Major Rework (silent bug)
**`MapLoader` ne sauvegardait que les NPCs avant le déchargement — états interactifs silencieusement perdus**

`MapLoader.load()` appelait `_save_npc_states()` puis `_clear_groups()`. Les entités interactives (coffres, leviers, portes) n'avaient **aucune sauvegarde pre-unload** : leurs `is_on` étaient silencieusement écrasés par le clear, et elles re-spawnaient avec les valeurs par défaut Tiled à chaque téléport.

```python
# ❌ Seuls les NPCs étaient sauvegardés — les entités interactives perdaient leur état
self._save_npc_states()
self._clear_groups()   # interactives.empty() → états perdus

# ✅ Snapshot complet AVANT le clear
self._save_npc_states()
self._save_interactive_states()  # ← NEW — coffres, leviers, portes
self._clear_groups()
```

**Règle (MapLoader) :** Tout appel à `_clear_groups()` DOIT être précédé de la sauvegarde **complète** de tous les groupes qui ont un état persistable (`_world_state_key`). Pas seulement les NPCs.

**Règle (spec) :** La section "Map Loading Pipeline" dans `world-system.md` DOIT lister explicitement chaque snapshot de groupe et son ordre relatif par rapport à `_clear_groups()`. L'absence dans la spec = anti-pattern non documenté = bug potentiel à la prochaine régénération.

**Détection :** Chercher dans `MapLoader` toute méthode `_save_*` manquante pour un groupe qui expose `_world_state_key`. Vérifier que la spec liste tous les snapshots.

**Evidence :** Coffres revenant à `is_on=False` après chaque téléport en debug room. `_save_interactive_states()` ajoutée. 4 tests TC-ML-01→04 RED → GREEN. 777/777 tests verts.

---

### L-GAME-002 · 2026-05-22 · U · Perfect
**Pattern `_intra_walk_target: Vector2 | None` pour un walk scrypté avec input-block**

Quand un système nécessite de déplacer le joueur de façon scriptée (téléport intra-carte avec animation), utiliser un champ nullable `Vector2 | None` comme état de machine d'état pour intercepter le loop normal AVANT `player.input()`.

```python
# Pattern complet — spec: intra-map-teleport.md § 4.4
# 1. Champ d'état dans _init_groups()
self._intra_walk_target: pygame.math.Vector2 | None = None

# 2. Armement du walk
def _start_intra_walk(self, target: pygame.math.Vector2) -> None:
    self._intra_walk_target = target
    self.player.target_pos = pygame.math.Vector2(target)  # bypass tile-by-tile
    self.player.is_moving = True
    # G4 : facing initial basé sur le vecteur delta
    delta = target - self.player.pos
    if delta.magnitude() > 0:
        if abs(delta.x) >= abs(delta.y):
            self.player.current_state = "right" if delta.x > 0 else "left"
        else:
            self.player.current_state = "up" if delta.y < 0 else "down"

# 3. Tick — appelé à la place du path normal
def _tick_intra_walk(self, dt: float) -> None:
    if not self.player.is_moving:   # player.move() a atteint target_pos
        self._intra_walk_target = None
        self.player.direction = pygame.math.Vector2(0, 0)  # A-GAME-003
        return
    # Mise à jour facing continu (G4)
    delta = self._intra_walk_target - self.player.pos
    if delta.magnitude() > 0:
        ...  # même logique facing que _start_intra_walk

# 4. Intercept dans _update_core_state — AVANT player.input()
if self._intra_walk_target is not None:
    self._tick_intra_walk(dt)
    self.visible_sprites.update(dt)  # animations continuent
    # player.input() et check_teleporters() skippés
else:
    self.player.input()
    ...
```

**Pourquoi ça fonctionne :** `BaseEntity.move()` respecte `target_pos` arbitraire (non-tile) quand `is_moving=True` est armé directement — bypass de `start_move()` sans modifier `BaseEntity`. La détection d'arrivée est déléguée à `move()` → `is_moving = False` à convergence.

**Règles à documenter dans la spec :**
- G2 : inputs bloqués (player.input() skippé)
- G3 : vitesse = `Settings.PLAYER_SPEED` (héritée du player, aucune config supplémentaire)
- G4 : facing mis à jour chaque frame, pas seulement au démarrage
- A-GAME-003 : direction clearée à l'arrivée (sinon retry loop)
- `check_teleporters()` skippé pendant le walk (évite re-trigger mid-walk)

**Evidence :** `test_intra_map_teleport.py` — 13/13 tests GREEN à la première implémentation, 0 rework. 380/380 tests régression verts. Cycle intra-map-teleport.md → code : zéro itération de correction.

---

### L-PERF-002 · 2026-05-22 · U · Perfect
**Pattern `property setter auto-refresh` pour les caches frame-level en Python**

Quand une valeur dérivée doit être précomputée une fois par frame ET testable sans appeler `update()`, transformer l'attribut source en `@property` avec un setter qui auto-refresh le cache. Cela maintient la compatibilité descendante des tests qui injectent l'attribut directement.

```python
# Pattern F1 — _total_minutes setter refresh cache WorldTime
@_total_minutes.setter
def _total_minutes(self, value: int) -> None:
    self.__total_minutes = value
    self._compute_world_time()  # cache refresh immédiat

# Pattern F2 — _time_system setter avec guard None (init phase)
@_time_system.setter
def _time_system(self, value) -> None:
    self.__time_system = value
    if self.day_night_driven and value is not None:  # guard CRITIQUE
        self._is_on_cache = self._compute_is_on()
```

**Règle :** Le guard `value is not None` dans le setter est obligatoire quand le setter est appelé pendant `__init__` avant que les attributs consommés par `_compute_*()` soient tous initialisés.

**Règle spec :** Quand la spec dit "Ordering is critical", elle doit citer l'ordre exact des lignes d'initialisation dans `__init__` ou `_parse_*()`. Une ambiguïté d'ordre = une itération de correction assurée.

**Evidence :** F1 (`time_system.py`) → 0 rework, 13/13 tests pass. F2 (`interactive.py`) → 3 itérations sur l'init order avant stabilisation. 1086/1086 tests verts.

---

### A-PERF-001 · 2026-05-22 · U · Minor Rework
**Init `_parse_*()` : ordre des attributs quand un `@property` setter appelle une méthode**

Quand un setter appelle `_compute_X()` qui lit `self.Y`, l'attribut `Y` DOIT être assigné AVANT l'assignation déclenchant le setter. L'erreur est silencieuse à l'analyse statique mais lève `AttributeError` à l'exécution.

```python
# ❌ setter → _compute_is_on() → self.light_control non set → AttributeError
def _parse_day_night(self, day_night_driven):
    self._is_on_cache = False
    self._time_system = None   # setter fires _compute_is_on() → reads light_control!
    self.light_control = "auto" if day_night_driven else "none"

# ✅ dépendances assignées avant le setter
def _parse_day_night(self, day_night_driven):
    self._is_on_cache = False
    self.light_control = "auto" if day_night_driven else "none"  # en premier
    self._time_system = None   # setter fires _compute_is_on() → light_control ✓
```

**Règle :** Dans tout `_parse_*()`, lister les attributs dans l'ordre topologique de leurs dépendances. La spec doit expliciter : « Initialize in this order: `_cache`, `light_control`, `_time_system` ».

**Détection :** Dans `_parse_*`, chercher toutes assignations dont le RHS (via setter) appelle `self.*` — vérifier que chaque `self.*` lu est déjà assigné dans le même bloc.

**Evidence :** `interactive.py::_parse_day_night` → `AttributeError: object has no attribute 'light_control'`. 3 itérations pour isoler. 1086/1086 verts après fix.

---

### A-PERF-002 · 2026-05-22 · U · Minor Rework
**Tests d'isolation sur sous-méthodes orchestrées : contrat de cache implicite cassé**

Quand `draw_scene()` est refactoré pour pré-peupler des caches consommés par ses sous-méthodes (`draw_background`, `draw_foreground`), les tests qui appellent les sous-méthodes directement se retrouvent avec des caches vides → assertions silencieusement fausses.

```python
# ❌ cache vide — draw_scene() non appelé
rm = RenderManager(game)
rm.draw_background()   # _frame_anim_by_layer = {} → fblits jamais appelé
assert game.screen.fblits.called  # FAIL

# ✅ pré-peupler le cache manuellement
rm = RenderManager(game)
rm._frame_anim_by_layer = {layer_id: [(x, y, tile_id, depth)]}
rm.draw_background()
assert game.screen.fblits.called  # PASS
```

**Règle :** Toute méthode qui consomme un cache peuplé par son orchestrateur doit documenter ce contrat dans la spec (section « Testing Contract ») ET en commentaire dans le code : `# Cache pre-populated by draw_scene() — tests must set self._frame_anim_by_layer`.

**Evidence :** 3 tests cassés après F3 (`test_render_manager_coverage.py`, `test_render_manager.py`, `test_render_order.py`). Fix : pré-peupler les caches dans chaque test. 1086/1086 verts après.

---

### L-ARCH-009 · 2026-05-22 · U · Perfect
**Modularisation des orchestrateurs graphiques (RenderManager) pour satisfaire la limite de taille des fonctions**

Quand une méthode de rendu graphique ou d'orchestration de scène (`draw_scene`) accumule de multiples passes logiques complexes (filtrage de visibilité, calculs de wading d'herbe, occlusion, gestion de pool de surfaces, tris de profondeur), la refactoriser en sous-méthodes privées spécialisées (ex : `_render_grass_wading_for_sprite`, `_apply_partial_occlusion`) est indispensable pour respecter la règle de taille des fonctions (< 50 lignes).

**Pattern :**
- L'orchestrateur primaire ne doit contenir que la boucle principale de rendu et la délégation aux passes spécialisées.
- Chaque passe spécialisée est isolée dans une fonction pure ou privée prenant en paramètres explicites les données nécessaires (e.g. `cam_offset`, `tile_size`).
- Cette décomposition simplifie considérablement la couverture de test unitaire sur chaque passe graphique et élimine les goulots d'étranglement de complexité cognitive.

**Evidence :** Refactoring de `RenderManager.py` : la méthode `_apply_grass_wading` a été divisée en extrayant `_render_grass_wading_for_sprite` (passant de 115 lignes à deux méthodes de moins de 45 lignes chacune). 1086/1086 tests validés avec succès après modularisation, 100% de conformité aux gates d'architecture.

---

---

### L-PERF-003 · 2026-06-10 · P · Minor Rework
**Mesurer après chaque micro-optimisation isolée pour révéler le bottleneck réel suivant**

Lors d'un cycle d'optimisations multiples (P-001 à P-007), l'ordre d'exécution prévu (P-002 → P-001 → P-005 → P-003) a été réordonné après investigation. Mesurer après chaque correction individuelle a révélé que P-003 (`_update_particles`) était le 2e bottleneck réel APRÈS P-005 (`_update_flicker`), alors que le plan initial plaçait P-001 (foreground tiles) en 1er.

**Pattern :** Profiler une correction à la fois avec un run de N frames identique à la baseline. Ne jamais grouper deux corrections sans mesure intermédiaire — les gains s'annulent, se compensent ou s'amplifient de façon non linéaire.

**Evidence :** P-005 : 1.165 s → 0.313 s (−73 %, mesuré). P-003 : 5.166 s → 3.955 s (−23 %, mesuré). Sans mesures intermédiaires, ces gains individuels auraient été inobservables, et l'attribution causale aurait été impossible.

---

### A-PERF-003 · 2026-06-10 · P · Major Rework *(updated 2026-06-10 — résolu par P-001, occurrences: 1)*
**Livrer l'infrastructure de cache foreground sans décomposer d'abord les responsabilités entrelacées de la boucle cible**

`get_foreground_layer_surface()` a été ajoutée à `MapManager` (commit `515f5a8`) mais reste non wirée à `_draw_static_foreground_tiles`. La raison : la boucle `get_visible_chunks` dans `_draw_static_foreground_tiles` cumule 3 responsabilités entrelacées — (1) blit normal des tuiles → remplaçable par surface pré-rendue, (2) blit occludé (`occluded_image`) dépendant de `player_screen_rect` par frame, (3) construction de `occluding_rects` pour `_apply_partial_occlusion`. Impossible de découpler (1) sans refonte du pipeline d'occlusion.

**Anti-pattern :** Livrer une infrastructure de cache AVANT d'avoir décomposé les responsabilités entrelacées de la boucle qui doit la consommer. L'infrastructure devient inutilisable et crée de la dette (code non appelé).

**Fix pour la prochaine spec perf :** Spécifier d'abord la décomposition de la boucle (3 responsabilités → 3 fonctions distinctes), puis l'infrastructure de cache. Ordre : spec → découplage → infrastructure → wire. Ne jamais livrer l'infrastructure avant que la décomposition soit conçue et documentée.

**Résolution (P-001, 2026-06-10) :** La boucle a été décomposée en 3 méthodes distinctes dans `MapManager` (`_build_world_surface`, `_build_fg_occlusion_world`, `_get_fg_depth_tiles`) + 2 dans `RenderManager` (`_draw_world_surface`, `_draw_fg_occlusion_tiles`). La `WorldSurface` est wirée et produit le gain attendu. Voir L-PERF-004 pour le pattern positif associé.

---

### L-PERF-004 · 2026-06-10 · P · Minor Rework
**Pattern 3-fonctions pour découpler une boucle tile foreground à responsabilités entrelacées**

Quand une boucle tile foreground cumule (1) blit normal, (2) blit occludé conditionnel, (3) collecte de rects pour un pipeline aval, la transformer en WorldSurface pre-rendered exige de décomposer d'abord les 3 responsabilités en fonctions distinctes.

**Décomposition résultante :**

```python
# MapManager — BUILD TIME (1x par changement de map)
def _build_world_surface(self) -> None:
    """(1) Blit normal des tuiles foreground depth>player → Surface world-space pré-rendue."""

def _build_fg_occlusion_world(self) -> None:
    """(2) Collecte des tuiles occludant potentiellement un sprite → liste world-space."""

def _get_fg_depth_tiles(self) -> Generator[...]:
    """(3) Tuiles foreground par depth — utilisées pour les deux pipelinnes ci-dessus."""

# RenderManager — FRAME TIME
def _draw_world_surface(self, cam_offset: tuple[int, int]) -> list[Rect]:
    """Blit viewport de la WorldSurface + collecte occluding_rects depuis _fg_occlusion_world."""

def _draw_fg_occlusion_tiles(self, player_rect: Rect, player_depth: int, cam_offset: tuple) -> None:
    """Blit les tuiles d'occlusion partielle (depth <= player_depth — tiles semi-transparentes)."""
```

**Règle :** La décomposition doit être spécifiée AVANT de livrer l'infrastructure de cache (anti-pattern A-PERF-003). L'ordre correct : spec → décomposition 3 fonctions → WorldSurface → wire.

**Règle spec :** La spec doit lister les 3 responsabilités nommées et leurs fonctions cibles. Toute ambiguïté sur "quelle responsabilité appartient à quelle méthode" = 1 itération de refactoring assurée.

**Evidence :** P-001 commit `10778e9`. 17 nouveaux tests (TC-P001-001..008, TC-015..020) RED → GREEN. 91/91 tests verts. Gain attendu : −20 ms/frame (élimination boucle 480 tiles/frame).

---

### L-PERF-005 · 2026-06-10 · P · Perfect
**Dirty flag avec clé minimale `(int(cam_x), int(cam_y), len(rects))` pour les caches de composites par frame**

Pour les caches de composites graphiques invalidés quand la caméra bouge OU quand le nombre de rects occludants change, une clé à 3 entiers est suffisante et n'introduit aucune collision silencieuse :

```python
# Dans RenderManager.__init__
self._occ_key: tuple[int, int, int] | None = None
self._occ_composite_cache: dict[Any, pygame.Surface] = {}

# Méthode reset (appeler lors d'un changement de map)
def reset_occ_cache(self) -> None:
    self._occ_key = None
    self._occ_composite_cache.clear()

# Dans _apply_partial_occlusion
def _apply_partial_occlusion(self, occluding_rects: list[...], cam_offset: tuple) -> None:
    key = (int(cam_offset[0]), int(cam_offset[1]), len(occluding_rects))
    if key == self._occ_key:
        # Cache HIT — réinstaller composites sans re-itérer les sprites
        for sprite, composite in self._occ_composite_cache.items():
            sprite.image = composite
        return
    # Cache MISS — calcul complet + mise à jour cache
    ...
    self._occ_key = key
    self._occ_composite_cache = new_cache
```

**Pourquoi `len(occluding_rects)` suffit comme 3e composante :** Le nombre de rects occludants change dès que le joueur entre ou sort d'une zone de tuile foreground — précisément les frames où le composite doit être recalculé. En pratique, deux sets de rects avec le même `len` mais des positions différentes impliquent que le joueur a bougé → `cam_offset` a changé → clé différente.

**Préconditions pour que le cache soit safe :**
- `draw_scene()` restaure `sprite.image` après chaque frame (swap-and-restore, L-REND-005)
- `reset_occ_cache()` est appelé à chaque chargement de map
- La clé n'est PAS basée sur les coordonnées des sprites — ceux-ci ne font pas partie de la clé

**Règle :** Ne jamais inclure les coordonnées individuelles des `occluding_rects` dans la clé — trop coûteux à hacher. `len()` + cam_offset est le minimum suffisant pour détecter les invalididations pertinentes.

**Evidence :** P-004 commit `df93698`. 6 tests TC-P004-001..006 RED → GREEN au premier pass. 97/97 tests verts. Zéro human enforcement sur l'implémentation.

---

### L-GAME-018 · 2026-06-11 · P · Minor Rework
**Appliquer les décalages visuels de rendu uniquement au moment de l'affichage (render time) sans altérer le hitbox physique (`self.rect`)**

Lors de l'implémentation de la hauteur visuelle dans les escaliers (Option A/C), modifier le hitbox physique (`self.rect`) de l'entité brise les collisions physiques et le calcul d'alignement avec les tuiles de Pygame. Le décalage vertical doit être purement cosmétique.

**Pattern :** 
1. Stocker le décalage vertical visuel (ex: `visual_y_offset`) ou les propriétés de mouvement vertical dans l'entité (`self._vertical_move`).
2. Dans la boucle de rendu (`CameraGroup.custom_draw`), récupérer ce décalage et l'appliquer uniquement sur la position de dessin du sprite (`offset_pos` passée à `surface.blit`).
3. Laisser `self.rect` inchangé pour que la physique, les collisions et les calculs de grille restent cohérents.

**Evidence :** Implémentation du décalage visuel des escaliers dans `groups.py` et `base.py`. 22 tests unitaires et d'intégration passent avec succès sans regression de la physique de collision.

---

### L-GAME-019 · 2026-06-11 · P · Minor Rework
**Traiter les interceptions de direction diagonale dans `start_move()` avant les contrôles de contraintes de sortie**

Dans un moteur de jeu basé sur des cases (grid-based movement), l'interception de direction (par exemple, transformer un déplacement gauche/droite en diagonale sur un escalier) doit s'exécuter avant de valider si la direction demandée est autorisée par les contraintes de sortie de la tuile (ex: `get_direction_flags`).

**Pattern :**
1. Intercepter la direction d'entrée dans `start_move()`.
2. Si l'entité est sur une tuile spéciale (ex: escalier), mapper la direction d'entrée vers la direction de sortie cible (diagonale) et mettre à jour `self.direction`.
3. Effectuer ensuite la vérification par rapport aux drapeaux de direction autorisés (`allowed_directions = get_direction_flags(...)`) avec la direction mise à jour.
4. Cela évite que les contraintes de direction standard de la tuile bloquent à tort le mouvement de l'escalier.

**Evidence :** Implémentation de la logique d'interception au début de `BaseEntity.start_move()` dans `base.py` résolvant les conflits de blocage directionnel.

*Last updated: 2026-06-11 — A-PERF-003 résolu (P-001), L-PERF-004 (3-method decomposition), L-PERF-005 (dirty flag cache key), L-GAME-018 (render-time offset), L-GAME-019 (diagonal interception priority).*

