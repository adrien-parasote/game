> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Spec — Phase 1.5 : Refactoring `interaction.py` [Implementation]

> Document Type: Implementation  
> **Version :** 1.0 — 2026-05-07  
> **Statut :** Draft  
> **Covers :** F5 (`spatial_utils.py`), F6 (`collision_checker.py`)  
> **Réf. Roadmap :** [`docs/strategic/MASTER_ROADMAP.md#phase-15`](../strategic/MASTER_ROADMAP.md#phase-15)  

---

## Objectif

`src/engine/interaction.py` passe de **474 LOC à < 400 LOC** sans aucun changement comportemental.  
Critère de sortie : `python3 -m pytest` → ≥ 170 tests passent. `wc -l src/engine/interaction.py` → < 400.

---

## 1. Contexte et Dépendances

`InteractionManager` gère toute la logique spatiale du gameplay : emotes de proximité, interactions avec les objets, NPCs, pickups, téléporteurs, collision pour les entités.

**Contrainte critique :** `is_collidable(px_center, py_center, requester)` est assignée comme callback :
```python
# game.py L156
self.player.collision_func = self.interaction_manager.is_collidable
# game.py L399
npc.collision_func = self.interaction_manager.is_collidable
```
→ `is_collidable` **doit rester** comme méthode publique sur `InteractionManager`. Elle ne peut pas être déplacée sans casser ce contrat.

---

## 2. Fichiers à créer

### 2.1 `src/engine/spatial_utils.py` (F5)

**Responsabilité :** Fonctions géométriques pures pour les calculs de direction et d'orientation.  
**LOC estimé :** ~70 LOC  
**Pattern :** Fonctions module-level pures (pas de classe). Zéro dépendance sur `self` ou `game`.

```python
# Interface à implémenter
import pygame

def get_facing_vector(state: str) -> pygame.math.Vector2:
    """Retourne un vecteur unitaire basé sur la direction du joueur.
    Extrait de InteractionManager._get_player_facing_vector() (L264-L275).
    state : 'up' | 'down' | 'left' | 'right' | autre -> Vector2(0,0)"""

def facing_toward(
    player_pos: pygame.math.Vector2,
    facing: str,
    obj_pos: pygame.math.Vector2,
) -> bool:
    """Retourne True si le joueur regarde vers obj_pos depuis player_pos.
    Extrait de InteractionManager._facing_toward() (L277-L286).
    Pure function : pas d'effet de bord, pas d'état."""

def verify_orientation(obj, p_state: str, p_pos: pygame.math.Vector2) -> bool:
    """Vérifie si le joueur est orienté correctement pour interagir avec obj.
    Extrait de InteractionManager._verify_orientation() (L288-L320).
    Accède à : obj.direction_str (str), obj.pos (Vector2), obj.sub_type (str), obj.is_on (bool).
    Pure function relative à son état d'entrée."""
```

**Comportement exact à préserver :**

`get_facing_vector(state)` :
- `"down"` → `Vector2(0, 1)` ; `"up"` → `Vector2(0, -1)` ; `"left"` → `Vector2(-1, 0)` ; `"right"` → `Vector2(1, 0)` ; autre → `Vector2(0, 0)`

`facing_toward(player_pos, facing, obj_pos)` :
- Calcule `dx = obj_pos.x - player_pos.x`, `dy = obj_pos.y - player_pos.y`
- Axe dominant = horizontal si `abs(dx) >= abs(dy)`, sinon vertical
- Horizontal : `True` si `(facing == "right" and dx > 0) or (facing == "left" and dx < 0)`
- Vertical : `True` si `(facing == "down" and dy > 0) or (facing == "up" and dy < 0)`

`verify_orientation(obj, p_state, p_pos)` :
- Lit `o_dir = getattr(obj, "direction_str", "down")`, `o_pos = obj.pos`
- Alignement : `x_aligned = abs(p_pos.x - o_pos.x) < 20`, `y_aligned = abs(p_pos.y - o_pos.y) < 20`
- 4 cas standard : player à l'avant de l'objet, facing opposé, aligné
- Relaxation doors (`obj.sub_type == "door" and getattr(obj, "is_on", False)`) : 4 cas supplémentaires (closing from back)
- Retourne `False` par défaut

---

### 2.2 `src/engine/collision_checker.py` (F6)

**Responsabilité :** Logique de collision multi-couches (map tiles + obstacles dynamiques + NPCs + joueur).  
**LOC estimé :** ~45 LOC  
**Pattern :** `CollisionChecker(game: Any)` — context injection.

```python
from typing import Any

class CollisionChecker:
    def __init__(self, game: Any) -> None:
        self.game = game

    def check(self, px_center: float, py_center: float, requester=None) -> bool:
        """Vérifie si la position (px_center, py_center) est un obstacle.
        Extrait du corps de InteractionManager.is_collidable() (L364-L390).
        Séquence des 4 checks : tiles → obstacles → NPCs → player."""
```

**Séquence des 4 checks (EXACTE — ne pas réordonner) :**
1. **Map tiles** : `wx, wy = self.game.layout.to_world(px_center, py_center)` → `self.game.map_manager.is_collidable(int(wx), int(wy))`
2. **Obstacles dynamiques** : Itère `self.game.obstacles_group`, skip si `obj == requester`, `collidepoint(px_center, py_center)`
3. **NPCs** : Itère `self.game.npcs`, skip si `npc == requester`, `collidepoint(px_center, py_center)`
4. **Player** : Si `self.game.player != requester` → `collidepoint(px_center, py_center)`

**Instanciation dans `InteractionManager.__init__` :**
```python
from src.engine.collision_checker import CollisionChecker
self._collision_checker = CollisionChecker(game)
```

---

## 3. Modifications de `interaction.py`

### 3.1 Méthodes supprimées (extraites dans les nouveaux modules)

| Méthode | LOC | Destination |
|---------|-----|------------|
| `_get_player_facing_vector` | 12 | `spatial_utils.get_facing_vector` |
| `_facing_toward` | 10 | `spatial_utils.facing_toward` |
| `_verify_orientation` | 33 | `spatial_utils.verify_orientation` |
| Corps de `is_collidable` | 22 | `CollisionChecker.check` |
| **Total retiré** | **77 LOC** | — |

### 3.2 Méthodes modifiées dans `InteractionManager`

**`is_collidable` — thin wrapper (5 LOC) :**
```python
def is_collidable(self, px_center: float, py_center: float, requester=None) -> bool:
    """Public API preserved for collision_func callbacks. Delegates to CollisionChecker."""
    return self._collision_checker.check(px_center, py_center, requester)
```
→ Signature identique. `player.collision_func = self.interaction_manager.is_collidable` reste valide.

**`_check_chest_auto_close` et `_close_chest` — utilisation de `spatial_utils.verify_orientation` :**
```python
# Avant (L340) :
wrong_orientation = not self._verify_orientation(chest, self.game.player.current_state, player_pos)
# Après :
from src.engine.spatial_utils import verify_orientation
wrong_orientation = not verify_orientation(chest, self.game.player.current_state, player_pos)
```

**Tous les appels à `self._facing_toward(...)` :**
```python
# Avant :
self._facing_toward(p_pos, p_state, obj.pos)
# Après :
facing_toward(p_pos, p_state, obj.pos)
```

**Tous les appels à `self._verify_orientation(...)` :**
```python
# Avant :
self._verify_orientation(obj, p_state, p_pos)
# Après :
verify_orientation(obj, p_state, p_pos)
```

**Tous les appels à `self._get_player_facing_vector()` :**
```python
# Avant (L149) :
dir_vector = self._get_player_facing_vector()
# Après :
dir_vector = get_facing_vector(self.game.player.current_state)
```

### 3.3 Import block ajouté

```python
from src.engine.spatial_utils import facing_toward, verify_orientation, get_facing_vector
from src.engine.collision_checker import CollisionChecker
```

### 3.4 LOC cible après extraction

```
interaction.py actuel :    474 LOC
Retiré (corps méthodes) : -77 LOC
Wrappers + imports :       +5 LOC
interaction.py final :    ~402 LOC

Hmm — encore légèrement > 400.
```

> [!IMPORTANT]
> L'extraction exacte donne ~402 LOC à cause des imports et wrappers ajoutés. Pour atteindre < 400, vérifier les lignes blanches redondantes et les commentaires non essentiels dans le fichier après extraction. Si toujours > 400, inliner `_check_chest_auto_close` et `_close_chest` (40 LOC) dans `update()` — économie de 2 lignes de définition de méthode = 400 LOC exact.
>
> **Stratégie conservatrice :** Après extraction, compter exactement avec `wc -l`. Si 400 < LOC < 405, supprimer les lignes blanches doubles et les commentaires redondants dans les méthodes extractées pour descendre à < 400. Ne pas changer la logique.

---

## 4. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|-----------|
| 1 | `_facing_toward`, `_verify_orientation`, `_get_player_facing_vector` ne sont appelées que depuis `interaction.py` | Low | `grep -rn "_facing_toward\|_verify_orientation\|_get_player_facing_vector" src/ tests/` avant suppression |
| 2 | `verify_orientation` accède uniquement à `obj.direction_str`, `obj.pos`, `obj.sub_type`, `obj.is_on` — pas d'autres attributs | Low | Relire L288-L320 ligne par ligne |
| 3 | `is_collidable` est le seul point d'entrée public de collision pour les entités mobiles | Medium | `grep -rn "is_collidable\|collision_func"` pour vérifier exhaustivité |
| 4 | L'ordre des 4 checks dans `CollisionChecker.check` est identique à l'original | High — l'ordre affecte les performances et les priorités | Copier le corps exact de L364-L390 sans réordonner |
| 5 | Les tests `test_interaction_is_collidable` (L512-L525) mockent `game.map_manager.is_collidable` — ce mock reste valide via `CollisionChecker.check` | Low | Exécuter les tests après extraction |

---

## 5. Anti-Patterns (DO NOT)

| ❌ Ne pas faire | ✅ Faire à la place | Pourquoi |
|----------------|--------------------|---------| 
| Déplacer `is_collidable` hors de `InteractionManager` | Garder `is_collidable` comme méthode publique, thin wrapper | `collision_func` callback assigné dans game.py — le déplacer casse ce contrat |
| Passer `self` à `spatial_utils` functions | Extraire les paramètres avant l'appel : `facing_toward(p_pos, p_state, obj.pos)` | Les fonctions pures ne doivent pas recevoir d'objet avec état |
| Ajouter des imports conditionnels dans `spatial_utils.py` | Importer `pygame` directement (pas de `TYPE_CHECKING`) | Module de fonctions pures, pas d'architecture spéciale |
| Créer une classe dans `spatial_utils.py` | Fonctions module-level uniquement | Géométrie pure = pas d'état = pas de classe |
| Changer la logique de `verify_orientation` (threshold 20px, door relaxation) | Copier exactement L288-L320 | Ces valeurs sont calibrées par gameplay testing |
| Réordonner les 4 checks dans `CollisionChecker.check` | Ordre : tiles → obstacles → NPCs → player | Performance optimization implicite (fail-fast sur tiles) |
| Tester `spatial_utils` via `InteractionManager` | Tester les fonctions directement avec des Vector2 et mock objects | Les fonctions pures sont 100% testables sans pygame display |

---

## 6. Test Case Specifications

**Préfixes TC :** `SU-` (spatial_utils), `CC-` (collision_checker)

### Unit Tests — `spatial_utils.py`

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-SU-01 | `get_facing_vector("down")` | `"down"` | `Vector2(0, 1)` |
| TC-SU-02 | `get_facing_vector("up")` | `"up"` | `Vector2(0, -1)` |
| TC-SU-03 | `get_facing_vector("left")` | `"left"` | `Vector2(-1, 0)` |
| TC-SU-04 | `get_facing_vector("right")` | `"right"` | `Vector2(1, 0)` |
| TC-SU-05 | `get_facing_vector` état inconnu | `"idle"` | `Vector2(0, 0)` |
| TC-SU-06 | `facing_toward` horizontal droit | `pos=(0,0)`, `facing="right"`, `obj=(10,0)` | `True` |
| TC-SU-07 | `facing_toward` horizontal gauche | `pos=(10,0)`, `facing="left"`, `obj=(0,0)` | `True` |
| TC-SU-08 | `facing_toward` vertical bas | `pos=(0,0)`, `facing="down"`, `obj=(0,10)` | `True` |
| TC-SU-09 | `facing_toward` direction opposée | `pos=(0,0)`, `facing="left"`, `obj=(10,0)` | `False` |
| TC-SU-10 | `verify_orientation` standard (up/down) | obj.direction_str="up", p_state="down", p_pos.y < o_pos.y, x_aligned | `True` |
| TC-SU-11 | `verify_orientation` hors alignement | x_aligned=False | `False` |
| TC-SU-12 | `verify_orientation` door relaxation | door.is_on=True, p_state=o_dir, back side | `True` |
| TC-SU-13 | `verify_orientation` default false | Aucun cas matching | `False` |

### Unit Tests — `collision_checker.py`

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-CC-01 | Tile collidable | `map_manager.is_collidable` retourne True | `True` |
| TC-CC-02 | Obstacle bloque | Tile libre, obstacle à la position | `True` |
| TC-CC-03 | Obstacle skippé si requester | Obstacle == requester | `False` (obstacle ignoré) |
| TC-CC-04 | NPC bloque | Tile libre, NPC à la position | `True` |
| TC-CC-05 | NPC skippé si requester | NPC == requester | Pas de blocage |
| TC-CC-06 | Player bloque NPC | Player != requester, player.rect.collidepoint = True | `True` |
| TC-CC-07 | Tout libre | Rien ne bloque | `False` |

### Integration Tests

| ID | Description | Attendu |
|----|-------------|---------|
| IT-CC-01 | `InteractionManager.is_collidable` délègue à `CollisionChecker.check` | `_collision_checker.check` appelé avec mêmes args |
| IT-SU-01 | `_check_chest_auto_close` utilise `spatial_utils.verify_orientation` | `verify_orientation` appelé (pas `self._verify_orientation`) |
| IT-SU-02 | Tests `test_interaction_is_collidable` existants passent après refactoring | 170 tests passent sans modification des tests |

### Index canon (format spec_precheck)

| ID | Ref interne | Type |
|----|-------------|------|
| TC-001 | TC-SU-01 | unit |
| TC-002 | TC-SU-02 | unit |
| TC-003 | TC-SU-03 | unit |
| TC-004 | TC-SU-04 | unit |
| TC-005 | TC-SU-05 | unit |
| TC-006 | TC-SU-06 | unit |
| TC-007 | TC-SU-07 | unit |
| TC-008 | TC-SU-08 | unit |
| TC-009 | TC-SU-09 | unit |
| TC-010 | TC-SU-10 | unit |
| TC-011 | TC-SU-11 | unit |
| TC-012 | TC-SU-12 | unit |
| TC-013 | TC-SU-13 | unit |
| TC-014 | TC-CC-01 | unit |
| TC-015 | TC-CC-02 | unit |
| TC-016 | TC-CC-03 | unit |
| TC-017 | TC-CC-04 | unit |
| TC-018 | TC-CC-05 | unit |
| TC-019 | TC-CC-06 | unit |
| TC-020 | TC-CC-07 | unit |
| IT-001 | IT-CC-01 | integration |
| IT-002 | IT-SU-01 | integration |
| IT-003 | IT-SU-02 | integration |

---

## 7. Error Handling Matrix

| Failure | Détection | Réponse | Fallback |
|---------|-----------|---------|---------|
| `game.layout` None lors de `CollisionChecker.check` | AttributeError | Propagé (ne pas swallow) — indique init incorrecte de `Game` | Aucun — c'est un bug d'initialisation |
| `obj.direction_str` absent dans `verify_orientation` | `getattr(obj, "direction_str", "down")` | Utilise `"down"` par défaut | Comportement safe — pas de crash |
| `obj.pos` None dans `verify_orientation` | Caller doit vérifier avant appel | Pas de guard dans la fonction pure | Crasherait avec AttributeError — documenté comme precondition |

---

## 8. Deep Links

- **Source `_get_player_facing_vector`** : [`src/engine/interaction.py#L264-L275`](../../src/engine/interaction.py#L264)
- **Source `_facing_toward`** : [`src/engine/interaction.py#L277-L286`](../../src/engine/interaction.py#L277)
- **Source `_verify_orientation`** : [`src/engine/interaction.py#L288-L320`](../../src/engine/interaction.py#L288)
- **Source `is_collidable`** : [`src/engine/interaction.py#L364-L390`](../../src/engine/interaction.py#L364)
- **Appel collision_func** : [`src/engine/game.py#L156`](../../src/engine/game.py#L156)
- **Pattern `game: Any`** : [`src/engine/interaction.py#L1-L25`](../../src/engine/interaction.py#L1)
- **Tests existants is_collidable** : [`tests/engine/test_interaction.py#L512-L525`](../../tests/engine/test_interaction.py#L512)
- **Spec game refactoring** : [`docs/specs/phase-1.5-game-refactoring.md`](./phase-1.5-game-refactoring.md#L1)
- **Spec chest refactoring** : [`docs/specs/phase-1.5-chest-refactoring.md`](./phase-1.5-chest-refactoring.md#L1)

### Linked Test Functions

| Test ID | Fonction test | Fichier |
|---------|--------------|---------|
| IT-CC-01 | `test_interaction_is_collidable` | `../../tests/engine/test_interaction.py` |
| IT-SU-02 | `test_interaction_is_collidable` | `../../tests/engine/test_interaction.py` |
