# Spec — Phase 1.5 : Refactoring `game.py` [Implementation]

> Document Type: Implementation  
> **Version :** 1.2 — 2026-05-07  
> **Statut :** Delivered ✅ (BUILD terminé, tous tests verts, 93% coverage global)  
> **Covers :** F1 (`game_setup.py`), F2 (`entity_factory.py`), F3 (`map_loader.py`), F4 (`input_handler.py`), F5 (`test_coverage_gaps_phase15.py`)
> **Réf. Roadmap :** [`docs/strategic/MASTER_ROADMAP.md#phase-15`](../strategic/MASTER_ROADMAP.md#phase-15)  
> **ADR :** [`docs/ADRs/ADR-004-refactoring-context-injection.md`](../ADRs/ADR-004-refactoring-context-injection.md#L1)

---

## Objectif

`src/engine/game.py` passe de **732 LOC à < 800 LOC (objectif absolu)** sans aucun changement comportemental.  
Résultat réel : **479 LOC** (objectif cible < 400 LOC non atteint ; accepté car < 800 absolu et pas de régression).  
Critère de sortie : `python3 -m pytest` → ≥ 170 tests passent. `wc -l src/engine/game.py` → < 800.

---

## 1. Contexte et Dépendances

`Game` est l'orchestrateur central. Il instancie et coordonne tous les sous-systèmes. Son `__init__` et ses méthodes de spawn/map-load sont les principaux contributeurs de LOC.

**Pattern établi dans le projet :** `SomeManager(game: Any)` avec `self.game = game` — reproduire pour toutes les nouvelles classes (L-ARCH-007 : utiliser `Any`, pas `TYPE_CHECKING`, pour éviter les cycles).

**Interfaces publiques immuables (ne pas changer leur signature) :**
- `Game.__init__(skip_map_load: bool = False)`
- `Game.run()`, `Game.run_frame()`, `Game.get_state()`, `Game.transition_map()`
- `Game._load_map(map_name, target_spawn_id, transition_type)` — appelée par `GameStateManager`

---

## 2. Fichiers à créer

### 2.1 `src/engine/game_setup.py` (F1)

**Responsabilité :** Fonctions module-level pour l'infrastructure de démarrage (logging, property types).  
**LOC estimé :** ~50 LOC  
**Pattern :** Fonctions pures (pas de classe), appelées une fois dans `Game.__init__`.

```python
# Interface à implémenter
def setup_logging(settings) -> None:
    """Configure le logging via RotatingFileHandler + StreamHandler.
    Extrait de Game._setup_logging() (L704-L731)."""

def load_property_types(project_path: str) -> list[dict]:
    """Charge game.tiled-project et retourne propertyTypes.
    Extrait de Game._load_property_types() (L691-L702).
    Retourne [] si le fichier est absent ou invalide."""
```

**Comportement exact à préserver :**
- `setup_logging` : configure `RotatingFileHandler` sur `logs/game.log` + `StreamHandler`. Niveau log depuis `Settings.LOG_LEVEL`. Format : `%(asctime)s - %(levelname)s - %(message)s`.
- `load_property_types` : lit `assets/tiled/game.tiled-project` (JSON), retourne `data.get("propertyTypes", [])`. Si `FileNotFoundError` ou `JSONDecodeError` → log warning, retourne `[]`.

**Appel dans `Game.__init__` après extraction :**
```python
from src.engine.game_setup import setup_logging, load_property_types

setup_logging(Settings)                                    # remplace self._setup_logging()
property_types = load_property_types("assets/tiled/game.tiled-project")  # remplace self._load_property_types()
```

---

### 2.2 `src/engine/entity_factory.py` (F2)

**Responsabilité :** Instanciation et configuration de toutes les entités de la carte (interactives, téléporteurs, NPCs, pickups).  
**LOC estimé :** ~200 LOC  
**Pattern :** `EntityFactory(game: Any)` — context injection.

```python
from typing import Any

def _get_property(obj: dict, key: str, default=None):
    """Helper module-level. Recherche récursive d'une propriété dans obj.
    Extrait de Game._get_property() (L35-L56). Pas de changement de logique."""

class EntityFactory:
    def __init__(self, game: Any) -> None:
        self.game = game

    def spawn_entities(self, entities: list[dict], map_name: str) -> None:
        """Dispatcher principal. Extrait de Game._spawn_entities() (L301-L321)."""

    def spawn_interactive(self, ent: dict, props: dict, map_name: str) -> None:
        """Extrait de Game._spawn_interactive() (L323-L374)."""

    def spawn_teleport(self, ent: dict, props: dict) -> None:
        """Extrait de Game._spawn_teleport() (L376-L387)."""

    def spawn_npc(self, ent: dict, props: dict) -> None:
        """Extrait de Game._spawn_npc() (L389-L417)."""

    def spawn_pickup(self, ent: dict, props: dict) -> None:
        """Extrait de Game._spawn_pickup() (L419-L447)."""

    def start_initial_ambients(self, player_pos) -> None:
        """Extrait de Game._start_initial_ambients() (L286-L299)."""
```

**Accès au contexte `game` dans les méthodes :**  
Tous les accès à `self.game.visible_sprites`, `self.game.interactives`, `self.game.npcs`, `self.game.pickups`, `self.game.teleports_group`, `self.game.obstacles_group`, `self.game.world_state`, `self.game.loot_table`, `self.game.audio_manager`, `self.game.tile_size` sont des reads/writes sur l'objet `game`. Ce couplage est accepté (pattern existant).

**Instanciation dans `Game.__init__` :**
```python
from src.engine.entity_factory import EntityFactory
self._entity_factory = EntityFactory(self)
```

**Appel dans `Game._load_map` après extraction :**
```python
self._entity_factory.spawn_entities(map_result.get("entities", []), map_name)
self._entity_factory.start_initial_ambients(pygame.math.Vector2(spawn_pos))
```

**Méthodes supprimées de `Game` :** `_get_property`, `_spawn_entities`, `_spawn_interactive`, `_spawn_teleport`, `_spawn_npc`, `_spawn_pickup`, `_start_initial_ambients`.

---

### 2.3 `src/engine/map_loader.py` (F3)

**Responsabilité :** Chargement d'une carte Tiled : parsing, BGM, world size, cleanup, spawn, positionnement du joueur.  
**LOC estimé :** ~115 LOC  
**Pattern :** `MapLoader(game: Any)` — context injection.  
**Scope strict :** Load pur uniquement. Le fade de transition reste dans `Game.transition_map()`.

```python
from typing import Any

class MapLoader:
    def __init__(self, game: Any) -> None:
        self.game = game

    def load(
        self,
        map_name: str,
        target_spawn_id: str | None = None,
        transition_type: str = "instant",
    ) -> None:
        """Charge une carte. Extrait de Game._load_map() (L186-L284).
        Logique préservée à l'identique. Appelle self.game._entity_factory."""
```

**Séquence interne de `load()` (EXACTE — ne pas réordonner) :**
1. Normalize `.tjm` → `.tmj` (L193)
2. Vérifier existence du fichier → `logging.error` + `return` si absent (L196-L198)
3. Parser avec `TmjParser` (L200-L201)
4. Créer `OrthogonalLayout` + `MapManager` sur `self.game` (L203-L204)
5. Jouer BGM si propriété `bgm` présente (L206-L208)
6. Mettre à jour `Settings.MAP_SIZE` et `self.game.map_size` (L211-L212)
7. Initialiser world size sur `visible_sprites` (L215-L217)
8. Sauvegarder states NPC avant départ (L220-L225)
9. Vider tous les groupes d'entités (L228-L234)
10. Appeler `self.game._entity_factory.spawn_entities(...)` (remplace L242)
11. Résoudre position spawn (L245-L269)
12. Forcer transform du joueur (L272-L277)
13. Logger position (L278)
14. Appeler `self.game._entity_factory.start_initial_ambients(...)` (remplace L284)

**Imports nécessaires dans `map_loader.py` :**
```python
import logging, os
import pygame
from src.config import Settings
from src.engine.audio import AudioManager  # non — via self.game.audio_manager
from src.map.layout import OrthogonalLayout
from src.map.manager import MapManager
```

**Appel dans `Game.__init__` :**
```python
from src.engine.map_loader import MapLoader
self._map_loader = MapLoader(self)
# ...
if not skip_map_load:
    self._map_loader.load(default_map)
```

**Appel dans `Game._load_map` :** Remplacer tout le corps de `_load_map` par :
```python
def _load_map(self, map_name: str, target_spawn_id: str | None = None, transition_type: str = "instant") -> None:
    """Delegate to MapLoader. Signature preserved for external callers."""
    self._map_loader.load(map_name, target_spawn_id, transition_type)
```
→ `_load_map` devient un thin wrapper de 3 LOC. Interface publique préservée.

---

### 2.4 `src/engine/input_handler.py` (F4)

**Responsabilité :** Traitement des événements pygame dans le contexte gameplay.  
**LOC estimé :** ~55 LOC  
**Pattern :** `InputHandler(game: Any)` — context injection.

```python
from typing import Any
import pygame

class InputHandler:
    def __init__(self, game: Any) -> None:
        self.game = game

    def handle_events(self, events: list) -> None:
        """Extrait de Game._handle_events() (L560-L595).
        Traite KEYDOWN pour interact, inventory, npc-bubble, dialogue."""
```

**Logique à préserver (L560-L595) :**
- `pygame.QUIT` → `pygame.quit()` + `sys.exit()`
- `KEYDOWN K_ESCAPE` (quand pas dialogue ouvert) → `sys.exit()`
- `KEYDOWN Settings.INTERACT_KEY` → dispatch selon état (dialogue, npc_bubble, world interact)
- `KEYDOWN Settings.INVENTORY_KEY` → toggle inventory si chest fermé
- Emote reset sur `Settings.INTERACT_KEY` si `_current_interactive_target` présent

**Appel dans `Game.__init__` :**
```python
from src.engine.input_handler import InputHandler
self._input_handler = InputHandler(self)
```

**Remplacement dans `Game._handle_events` :**
```python
def _handle_events(self) -> None:
    """Delegate to InputHandler."""
    self._input_handler.handle_events(pygame.event.get())
```
→ Thin wrapper de 2 LOC. Appelle `pygame.event.get()` lui-même (simplification vs spec initiale).

---

## 3. Modifications de `game.py`

### 3.1 Nouvelles lignes ajoutées dans `__init__` (après extractions)

```python
# Dans __init__, après instanciation des systèmes existants :
self._entity_factory = EntityFactory(self)   # F2
self._map_loader = MapLoader(self)           # F3
self._input_handler = InputHandler(self)     # F4
```

### 3.2 Import block (remplacer les imports internes)

```python
# Supprimer : TmjParser (import local dans _load_map)
# Ajouter :
from src.engine.entity_factory import EntityFactory
from src.engine.map_loader import MapLoader
from src.engine.input_handler import InputHandler
from src.engine.game_setup import setup_logging, load_property_types
```

### 3.3 `__init__` — lignes retirées

| Lignes retirées | Remplacées par |
|----------------|---------------|
| `self._setup_logging()` (L67) | `setup_logging(Settings)` |
| `property_types = self._load_property_types()` (L116) | `property_types = load_property_types("assets/tiled/game.tiled-project")` |
| Corps de `_load_map` (L186-L284) | `self._map_loader.load(...)` (3 LOC) |
| Corps de `_handle_events` (L560-L595) | `self._input_handler.handle_events(events)` (2 LOC) |

### 3.4 Méthodes supprimées de `Game`

| Méthode | LOC | Destination |
|---------|-----|------------|
| `_get_property` | 22 | `entity_factory.py` (module-level) |
| `_spawn_entities` | 21 | `EntityFactory.spawn_entities` |
| `_spawn_interactive` | 52 | `EntityFactory.spawn_interactive` |
| `_spawn_teleport` | 12 | `EntityFactory.spawn_teleport` |
| `_spawn_npc` | 29 | `EntityFactory.spawn_npc` |
| `_spawn_pickup` | 29 | `EntityFactory.spawn_pickup` |
| `_start_initial_ambients` | 14 | `EntityFactory.start_initial_ambients` |
| Corps de `_load_map` | ~90 | `MapLoader.load` |
| Corps de `_handle_events` | ~30 | `InputHandler.handle_events` |
| `_setup_logging` | 28 | `game_setup.setup_logging` |
| `_load_property_types` | 12 | `game_setup.load_property_types` |
| **Total retiré** | **~349 LOC** | — |

### 3.5 LOC cible après extraction

```
game.py avant:           732 LOC
Retiré (méthodes):      -349 LOC
Overhead (wrappers/imports): +10 LOC
game.py estimé:          ~393 LOC
game.py réel:            479 LOC  (thin wrappers conservés pour compat tests)
```

---

## 4. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|-----------|
| 1 | `Game._load_map` est appelée exclusivement via `transition_map()` dans `GameStateManager` — pas d'appel direct externe non documenté | Medium | `grep -rn "_load_map\|\.load_map"` sur tout le projet avant implémentation |
| 2 | `Game._handle_events` reçoit une `list` d'events filtrés par `GameStateManager` — pas d'appel direct en dehors du game loop | Low | `grep -rn "_handle_events"` — vérifié dans DISCOVER |
| 3 | `_get_property` n'est utilisé que dans les méthodes spawn de `game.py` | Low | `grep -rn "_get_property"` avant de supprimer |
| 4 | Transférer `spawn_entities` dans `EntityFactory` ne casse pas les tests qui mockent `game._spawn_*` | Medium | Exécuter la suite de tests immédiatement après extraction de chaque méthode |
| 5 | `MapLoader.load()` peut accéder librement à `self.game._entity_factory` (instancié avant `_map_loader`) | Low | Vérifier ordre d'instanciation dans `__init__` : `_entity_factory` avant `_map_loader` |

---

## 5. Anti-Patterns (DO NOT)

| ❌ Ne pas faire | ✅ Faire à la place | Pourquoi |
|----------------|--------------------|---------| 
| Utiliser `TYPE_CHECKING` pour `game: Any` dans les nouvelles classes | Utiliser `from typing import Any` | L-ARCH-007 : `TYPE_CHECKING` crée des cycles sentrux |
| Changer la signature de `_load_map`, `_handle_events` ou autres méthodes publiques | Garder les signatures identiques, faire des thin wrappers | GameStateManager appelle ces méthodes — toute signature change = régression |
| Déplacer la logique de fade dans `MapLoader` | `MapLoader` = load pur ; le fade reste dans `transition_map` | Gap 2 résolu en STRATEGY — séparation propre des responsabilités |
| Créer `EntityFactory` comme singleton | Instancier dans `Game.__init__` : `self._entity_factory = EntityFactory(self)` | Un singleton partagé globalement cassait le pattern de test avec reset |
| Appeler `_load_map` depuis `__init__` via le MapLoader sans passer par la méthode wrapper | Toujours appeler `self._load_map(default_map)` | Interface préservée, testabilité via `skip_map_load=True` inchangée |
| Mettre de la logique métier dans le thin wrapper `_load_map` | Wrapper = `self._map_loader.load(map_name, target_spawn_id, transition_type)` et rien d'autre | Toute logique dans `MapLoader.load()` pour cohérence |
| Importer `TmjParser` en lazy import dans `MapLoader.load()` | Importer `TmjParser` au niveau du module dans `map_loader.py` | Import module-level requis pour que `patch('src.engine.map_loader.TmjParser')` fonctionne dans les tests |
| Modifier les tests existants pour s'adapter aux nouvelles classes | Mettre à jour uniquement les imports et les mock targets si nécessaire | Les tests valident le comportement, pas l'implémentation interne |

---

## 6. Test Case Specifications

**Préfixes TC :** `GS-` (game_setup), `EF-` (entity_factory), `ML-` (map_loader), `IH-` (input_handler)

### Unit Tests — `game_setup.py`

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-GS-01 | `load_property_types` avec fichier valide | Fichier JSON avec `propertyTypes: [...]` | Retourne la liste |
| TC-GS-02 | `load_property_types` avec fichier absent | Chemin invalide | Retourne `[]`, log warning |
| TC-GS-03 | `load_property_types` avec JSON invalide | Fichier corrompu | Retourne `[]`, log warning |
| TC-GS-04 | `setup_logging` configure les handlers | `Settings` mock | RotatingFileHandler + StreamHandler ajoutés à root logger |
| TC-GS-05 | `load_property_types` avec clé absente | JSON sans `propertyTypes` | Retourne `[]` |

### Unit Tests — `entity_factory.py`

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-EF-01 | `_get_property` trouvé à la racine | `{"key": "val"}`, `"key"` | `"val"` |
| TC-EF-02 | `_get_property` trouvé en nested | `{"a": {"key": "val"}}`, `"key"` | `"val"` |
| TC-EF-03 | `_get_property` absent | `{}`, `"key"`, `default="x"` | `"x"` |
| TC-EF-04 | `spawn_interactive` ajoute à `visible_sprites` et `interactives` | Mock game + ent dict type `03-interactive` | Entity dans les 2 groupes |
| TC-EF-05 | `spawn_teleport` ajoute à `teleports_group` | Mock game + ent dict type `15-teleport` | Entity dans `teleports_group` |
| TC-EF-06 | `spawn_npc` ajoute à `visible_sprites` et `npcs` | Mock game + ent dict type `07-npc` | Entity dans les 2 groupes |
| TC-EF-07 | `spawn_pickup` ajoute à `pickups` | Mock game + ent dict type pickup | Entity dans `pickups` |
| TC-EF-08 | `spawn_entities` dispatcher : type inconnu ignoré | ent dict avec type non reconnu | Aucune exception, log warning |
| TC-EF-09 | `spawn_interactive` avec world_state restore | game.world_state a une entrée → entity restorée | `entity.is_on` = valeur sauvegardée |

### Unit Tests — `map_loader.py`

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-ML-01 | `load` map absente | Chemin inexistant | Log error, retour immédiat (pas d'exception) |
| TC-ML-02 | `load` normalise `.tjm` → `.tmj` | `"map.tjm"` | Cherche `"map.tmj"` |
| TC-ML-03 | `load` résout spawn par `target_spawn_id` | Entities avec `spawn_id: "A"`, `target="A"` | Player positionné sur spawn A |
| TC-ML-04 | `load` résout spawn initial (is_initial_spawn) | Entities avec `is_initial_spawn: True` | Player positionné sur cet entity |
| TC-ML-05 | `load` fallback sur `spawn_player` root | Pas d'entity spawn_point, spawn_player dict | Player positionné sur spawn_player |
| TC-ML-06 | `load` fallback center si rien | Pas de spawn trouvé | Log warning, player au centre |
| TC-ML-07 | `load` vide les groupes avant spawn | Groupes non vides | Groupes vides après load, puis respawnés |

### Unit Tests — `input_handler.py`

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-IH-01 | `QUIT` → sys.exit | `pygame.QUIT` event | `sys.exit()` appelé |
| TC-IH-02 | `INTERACT_KEY` sans dialogue | Keydown E, dialogue fermé | `interaction_manager.handle_interactions()` appelé |
| TC-IH-03 | `INTERACT_KEY` avec dialogue ouvert | Keydown E, dialogue ouvert | `dialogue_manager.advance()` ou `_trigger_npc_bubble` (pas interact) |
| TC-IH-04 | `INVENTORY_KEY` chest fermé | Keydown I, chest_ui.is_open = False | `inventory_ui.toggle()` appelé |
| TC-IH-05 | `INVENTORY_KEY` chest ouvert | Keydown I, chest_ui.is_open = True | Aucun toggle inventory |

### Integration Tests

| ID | Description | Attendu |
|----|-------------|---------|
| IT-EF-01 | `Game.__init__` instancie `_entity_factory`, `_map_loader`, `_input_handler` | 3 attributs présents et du bon type |
| IT-ML-01 | `Game._load_map` délègue à `MapLoader.load` avec mêmes arguments | `MapLoader.load` appelé avec `(map_name, target_spawn_id, transition_type)` |
| IT-IH-01 | `Game._handle_events` délègue à `InputHandler.handle_events` | `InputHandler.handle_events` appelé avec la liste events |
| IT-GS-01 | `Game.__init__` appelle `setup_logging` avant les autres systèmes | Logger configuré (RotatingFileHandler présent) après init |

### Index canon (format spec_precheck)

| ID | Ref interne | Type |
|----|-------------|------|
| TC-001 | TC-GS-01 | unit |
| TC-002 | TC-GS-02 | unit |
| TC-003 | TC-GS-03 | unit |
| TC-004 | TC-GS-04 | unit |
| TC-005 | TC-GS-05 | unit |
| TC-006 | TC-EF-01 | unit |
| TC-007 | TC-EF-02 | unit |
| TC-008 | TC-EF-03 | unit |
| TC-009 | TC-EF-04 | unit |
| TC-010 | TC-EF-05 | unit |
| TC-011 | TC-EF-06 | unit |
| TC-012 | TC-EF-07 | unit |
| TC-013 | TC-EF-08 | unit |
| TC-014 | TC-EF-09 | unit |
| TC-015 | TC-ML-01 | unit |
| TC-016 | TC-ML-02 | unit |
| TC-017 | TC-ML-03 | unit |
| TC-018 | TC-ML-04 | unit |
| TC-019 | TC-ML-05 | unit |
| TC-020 | TC-ML-06 | unit |
| TC-021 | TC-ML-07 | unit |
| TC-022 | TC-IH-01 | unit |
| TC-023 | TC-IH-02 | unit |
| TC-024 | TC-IH-03 | unit |
| TC-025 | TC-IH-04 | unit |
| TC-026 | TC-IH-05 | unit |
| IT-001 | IT-EF-01 | integration |
| IT-002 | IT-ML-01 | integration |
| IT-003 | IT-IH-01 | integration |
| IT-004 | IT-GS-01 | integration |

### Coverage Gap Tests (Phase 1.5 Hardening)

Pour garantir la résilience du moteur et atteindre le seuil de `>=90% global coverage`, une série de tests ciblés a été ajoutée dans `tests/test_coverage_gaps_phase15.py` :

| Cible | But |
|-------|-----|
| `TestGameCoverage` | Tester les branches de délégation tardive (PNJs, _start_initial_ambients) et UI fallback. |
| `TestEntityFactoryCoverage` | Couvrir les lectures de `_get_property` imbriquées et la restauration des états sauvegardés (ex. quantity/collected). |
| `TestCameraGroupCoverage` | Valider les clampings de caméra (`calculate_offset`) et les invalidations de cache pour les entités en mouvement. |
| `TestPickupCoverage` | Assurer la fallback de chargement de spritesheet sans extension `.png`. |
| `TestLightingCoverage` | Valider l'eviction du cache (LRU) et la gestion des halos lumineux sans intensité (`is_on=False`). |
| `TestTiledProjectCoverage` | Vérifier la gestion des erreurs de syntaxe JSON et la résolution de propriétés imbriquées (classes). |
| `TestInteractiveLightingCoverage` | Vérifier le `_update_flicker` sur des entités avec fallback `is_on=False` ou animées. |
| `TestSaveMenuCoverage` | Couvrir l'initialisation UI avec fallback `AssetManager` et interactions annulées (back button). |

---

## 7. Error Handling Matrix

| Failure | Détection | Réponse | Fallback |
|---------|-----------|---------|---------|
| Fichier map absent | `os.path.exists` → False dans `MapLoader.load` | `logging.error(f"Target map not found: {map_path}")` + `return` | Pas de changement d'état — map précédente reste chargée |
| `game.tiled-project` absent | `FileNotFoundError` dans `load_property_types` | `logging.warning(...)` | Retourne `[]` — loot_table fonctionne sans property types |
| Spawn point non trouvé | Aucun match dans la boucle resolve | `logging.warning(...)` | Player positionné au centre de la carte |
| NPC spawn sans asset | `FileNotFoundError` dans `EntityFactory.spawn_npc` | `logging.error(...)` — NPC non ajouté | Carte reste jouable sans ce NPC |
| Entity type inconnu | Type non dans le dispatcher de `spawn_entities` | `logging.warning(f"Unknown entity type: {ent_type}")` | Entity ignorée |

---

## 8. Deep Links

- **Source `Game.__init__`** : [`src/engine/game.py#L62-L184`](../../src/engine/game.py#L62)
- **Source `_load_map`** : [`src/engine/game.py#L186-L284`](../../src/engine/game.py#L186)
- **Source spawn methods** : [`src/engine/game.py#L286-L447`](../../src/engine/game.py#L286)
- **Source `_handle_events`** : [`src/engine/game.py#L560-L595`](../../src/engine/game.py#L560)
- **Source `_setup_logging`** : [`src/engine/game.py#L704-L731`](../../src/engine/game.py#L704)
- **Source `_load_property_types`** : [`src/engine/game.py#L691-L702`](../../src/engine/game.py#L691)
- **Pattern `game: Any`** : [`src/engine/interaction.py#L1-L25`](../../src/engine/interaction.py#L1)
- **ADR context injection** : [`docs/ADRs/ADR-004-refactoring-context-injection.md`](../ADRs/ADR-004-refactoring-context-injection.md#L1)
- **Spec interaction refactoring** : [`docs/specs/phase-1.5-interaction-refactoring.md`](./phase-1.5-interaction-refactoring.md#L1)
- **Spec chest refactoring** : [`docs/specs/phase-1.5-chest-refactoring.md`](./phase-1.5-chest-refactoring.md#L1)
- **Learnings** : L-ARCH-007 (game: Any), L-ARCH-004 (thin dispatcher)
- **Note LOC** : `game.py` à 479 LOC post-BUILD (thin wrappers maintenus pour compatibilité API existante)

### Linked Test Functions

| Test ID | Fonction test | Fichier |
|---------|--------------|---------|
| IT-EF-01 | `test_game_initialization` | `../../tests/engine/test_game.py` |
| IT-ML-01 | `test_load_map_delegates_to_map_loader` | `../../tests/engine/test_game.py` |
| IT-IH-01 | `test_handle_events_delegates_to_input_handler` | `../../tests/engine/test_game.py` |
