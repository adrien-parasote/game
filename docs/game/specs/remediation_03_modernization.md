# Spec — Steps 8 à 11 : Modernisation Python 3.12

> Document Type: Implementation
> **Covers:** @override, Type aliases, ADR-008 FRect, pathlib.Path ✅
> **Référence blueprint:** [`best_practices_remediation_blueprint.md`](../strategic/best_practices_remediation_blueprint.md#plan-dimplémentation--10-steps)
> **Guide best practices:** [`pygame_ce_python_312_best_practices.md`](./pygame_ce_python_312_best_practices.md#section-4-typing)
> **Statut:** DONE — Steps 8-11 implémentés et vérifiés (pyright: 0 errors, pytest: 1094/1094)

---

## Contexte

Quatre améliorations de faible sévérité pour moderniser la codebase vers Python 3.12 :

1. **`@override`** : Absence de décorateur sur les méthodes héritées empêche Pyright de détecter les ruptures de signature parent.
2. **Alias de type `type`** : Annotations complexes dupliquées dans `render_manager.py` sans alias nommés.
3. **ADR-008 FRect** : Décision documentée de ne pas migrer (Vector2+Rect fonctionne). Crée une trace pour les décisions futures.
4. **`pathlib.Path`** : Migration de 55 `os.path.join` vers `pathlib.Path` — 28 fichiers (`src/config.py`, `src/engine/`, `src/entities/`, `src/ui/`, `src/map/tmj_parser.py`). Seul `src/main.py:6` (bootstrap `sys.path`) conserve `os`.

---

## Constraints

| Tier | Exemples |
|---|---|
| **Always do** | `@override` uniquement sur les méthodes qui surchargent réellement une méthode parent définie (pas sur les méthodes abstraites implémentées). Alias de type `type` en haut du fichier, après les imports. |
| **Ask first** | Ajouter `@override` sur une méthode si la méthode parent n'est pas clairement identifiable. |
| **Never do** | Modifier la logique des méthodes décorées avec `@override`. `@override` est un décorateur d'annotation pure — aucun comportement runtime. Ne pas toucher aux méthodes qui n'overrident pas une méthode parent (ex: méthodes spécifiques à la sous-classe). |

---

## Cross-Spec Contracts

### Produces
| Identifiant | Format | Consommateurs |
|---|---|---|
| `docs/ADRs/ADR-008-frect.md` | Markdown | Référence future pour décision FRect |

### Consumes
N/A — modifications purement locales.

### Public Interface
N/A.

### External Invocations
N/A.

### Tracked Concepts
| Concept | Statut | Mentionné dans |
|---|---|---|
| `FRect` | Décision documentée (ADR-008) : non migré en Phase 1 | `camera-rendering.md`, `entities-system.md` |

---

## Step 8 — `@override` sur les méthodes héritées

### Inventaire complet

| Classe | Méthode | Fichier | Parent | Ligne approx. |
|---|---|---|---|---|
| `Player` | `update(dt)` | `src/entities/player.py` | `BaseEntity` | ~150 |
| `CameraGroup` | `add(*sprites)` | `src/entities/groups.py` | `pygame.sprite.Group` | ~68 |
| `CameraGroup` | `remove(*sprites)` | `src/entities/groups.py` | `pygame.sprite.Group` | ~72 |
| `NPC` | `update(dt)` | `src/entities/npc.py` | `BaseEntity` | À vérifier |

### Implémentation

**Import à ajouter (Python 3.12 stdlib — zéro dépendance) :**
```python
from typing import override
```

**Pattern :**
```python
class Player(BaseEntity):
    @override
    def update(self, dt: float) -> None:
        ...  # corps existant inchangé

class CameraGroup(pygame.sprite.Group):
    @override
    def add(self, *sprites: pygame.sprite.Sprite) -> None:
        ...  # corps existant inchangé
```

**Règle :** Ne modifier QUE la ligne d'import et la ligne de déclaration de méthode. Zéro changement au corps des méthodes.

**Vérification Pyright :** Avec `@override` et `typeCheckingMode: basic`, Pyright lèvera une erreur si la signature diffère de celle du parent — c'est l'objectif.

### Fichiers modifiés

- `src/entities/player.py`
- `src/entities/groups.py`
- `src/entities/npc.py`

---

## Step 9 — Alias de type `type` pour signatures complexes

### Inventaire des signatures à aliaser

Annotations complexes identifiées dans `render_manager.py` :

```python
# Actuellement inline (dupliquées ou non lisibles) :
list[tuple[pygame.Surface, tuple[int, int]]]   # liste de blits
list[tuple[pygame.Rect, int]]                   # rects occludants
```

### Implémentation

**En haut de `src/engine/render_manager.py`, après les imports :**
```python
# Python 3.12 type aliases
type BlitSequence = list[tuple[pygame.Surface, tuple[int, int]]]
type OccludingRect = list[tuple[pygame.Rect, int]]
```

**Utilisation dans les signatures de méthodes :**
```python
def _collect_blit_items(self) -> BlitSequence:
    ...

def _get_occluding_rects(self) -> OccludingRect:
    ...
```

**Règle :** Uniquement pour les types qui apparaissent ≥2 fois dans le fichier ou dont la lisibilité bénéficie clairement d'un nom. Pas d'alias pour les types simples déjà lisibles (`str`, `int`, `float`, `pygame.Surface`).

### Fichiers modifiés

- `src/engine/render_manager.py`

---

## Step 10 — ADR-008 : Décision FRect

### Document à créer : `docs/ADRs/ADR-008-frect-migration.md`

```markdown
# ADR-008 — Migration vers pygame.FRect : Décision de Non-Migration (Phase 1)

**Date :** 2026-05-26
**Status :** ✅ Accepted — Migration différée

## Contexte

Le guide de référence `pygame_ce_python_312_best_practices.md §2.2` recommande l'utilisation
de `pygame.FRect` pour les entités mobiles afin d'éliminer le jitter sub-pixel.

Le projet utilise actuellement `pygame.Rect` (entier) pour les hitboxes et positions de rendu,
combiné avec `pygame.math.Vector2` pour les positions sub-pixel (`pos`, `target_pos`).

## Analyse coût/bénéfice

**Bénéfice :**
- Supprimerait le double-stockage `Vector2 pos` + `Rect` dans `BaseEntity`
- Éliminerait les arrondis manuels `int(self.pos.x)`, `int(self.pos.y)`
- Conformité totale avec le guide de référence §2.2

**Coût :**
- Impact sur `base.py`, `player.py`, `npc.py`, `groups.py`, `collision_checker.py`
- Potentiel de régression sur la détection de collisions (FRect vs Rect en collision check)
- Effort estimé : >4h + 2h de tests de régression collision

**Jitter actuel :** Non observé. Le système `Vector2 pos` + `Rect` arrondi fonctionne
correctement. Aucun rapport de jitter en gameplay.

## Décision

**Ne pas migrer vers FRect en Phase 1.**

Le double-système est fonctionnel. Le bénéfice (simplification du code) ne justifie pas
le risque de régression sur les collisions et l'effort de migration.

## Conditions de révision

Reconsidérer si :
1. Du jitter sub-pixel est observé en distribution (écrans haute résolution)
2. La migration vers FRect est proposée dans une release dédiée avec test suite de collision complète
3. pygame-ce fournit un guide de migration officiel FRect

## Fichiers non modifiés

- `src/entities/base.py`
- `src/entities/player.py`
- `src/entities/groups.py`
- `src/engine/collision_checker.py`
```

---

## Step 11 (Optionnel) — Migration `os.path.join` → `pathlib.Path`

> **⚠️ Step optionnel.** Ne bloque pas les Steps 1-10. Décider séparément.

### Inventaire

~60 occurrences de `os.path.join` dans `src/`. Les concentrations majeures :

| Module | Occurrences approx. | Criticité |
|---|---|---|
| `src/engine/asset_manager.py` | ~5 | High — chemin de tous les assets |
| `src/engine/save_manager.py` | ~8 | High — chemins de sauvegarde |
| `src/ui/hud.py` | 2 | Low |
| `src/map/tmj_parser.py` | ~10 | Medium |
| Autres UI modules | ~15 | Low |

### Pattern de migration

```python
# AVANT
import os
path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "HUD", "00-clock.png")
path = os.path.normpath(path)

# APRÈS
from pathlib import Path
path = Path(__file__).parent / ".." / ".." / "assets" / "images" / "HUD" / "00-clock.png"
path = path.resolve()  # équivalent de normpath mais absolu
```

### Règle d'implémentation

1. Migrer **fichier par fichier**, pas en masse.
2. Vérifier que les fonctions appelantes acceptent `Path` ou `str` (pygame-ce accepte les deux).
3. `Path.resolve()` remplace `os.path.normpath()` + `os.path.abspath()`.
4. `Path(__file__).parent` remplace `os.path.dirname(__file__)`.
5. Les tests existants doivent passer sans modification.

### Vérification

```bash
grep -rn "os.path.join" src/  # → 0 après migration complète
grep -rn "import os" src/     # → uniquement les fichiers qui utilisent os.environ, os.path.exists, etc.
```

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | `@override` sur une méthode abstraite implémentée | Décorer avec `@override` une méthode qui implémente `@abstractmethod` | `@override` = remplace une méthode **concrète** du parent. Vérifier [`entities-system.md`](./entities-system.md#base-entity) pour la hiérarchie |
| 2 | Alias de type pour des types simples | `type Name = str` ou `type Count = int` | Aliaser uniquement les types composites : ≥2 niveaux d'imbrication ou longueur > 40 chars |
| 3 | `type Alias = ...` au milieu du fichier | Déclarer un alias après des `def` ou `class` | Les alias vont après les imports, avant le premier `def` ou `class` |
| 4 | Modifier le corps d'une méthode en ajoutant `@override` | Combiner l'ajout de `@override` avec un refactor du corps | `@override` est purement un décorateur d'annotation. Zéro modification de corps |
| 5 | `pathlib.Path` mixé avec `str` sans conversion | `pygame.image.load(Path("assets/img.png"))` si l'API attend `str` | Toujours vérifier l'API cible. Utiliser `str(path)` si nécessaire au site d'appel |
| 6 | ADR-008 sans conditions de révision | "Ne pas migrer FRect" sans définir quand revoir la décision | Documenter les 3 conditions de révision dans [`ADR-008`](../ADRs/ADR-008-frect-migration.md#conditions-de-révision) |
| 7 | Migration pathlib sur des fichiers partagés sans tests | Migrer `asset_manager.py` sans vérifier que les tests existants couvrent les chemins | Lancer les tests après chaque fichier migré. Vérifier couverture via [`verification-loop`](./../agents/skills/verification-loop/SKILL.md) |



---

## Test Case Specifications

### Unit Tests — @override

**TC-001** : `Player.update(dt=0.016)` s'exécute sans erreur avec `@override` ajouté
```python
# Arrange: player instance valide
# Act: player.update(0.016)
# Assert: no TypeError, no AttributeError
```

**TC-002** : `CameraGroup.add(sprite)` s'exécute sans erreur avec `@override`
```python
# Assert: sprite in group after add()
```

**TC-003** : `CameraGroup.remove(sprite)` s'exécute sans erreur avec `@override`
```python
# Assert: sprite not in group after remove()
```

**TC-004** : Vérification statique — `@override` présent sur les 4 méthodes ciblées
```bash
grep -n "@override" src/entities/player.py src/entities/groups.py src/entities/npc.py
# → 4 résultats
```

### Unit Tests — Type Aliases

**TC-005** : `render_manager.py` importe correctement ses propres alias (pas d'ImportError)
```python
from src.engine.render_manager import RenderManager  # import clean
```

**TC-006** : Vérification statique — `type BlitSequence` présent dans `render_manager.py`
```bash
grep "^type " src/engine/render_manager.py  # → ≥1 résultat
```

### Unit Tests — pathlib (si Step 11 exécuté)

**TC-007** : `AssetManager.get_image(path)` retourne la même surface avant et après migration
```python
# Assert: surface.get_size() identique avant/après migration
```

**TC-008** : `SaveManager._saves_dir` est un chemin valide après migration
```python
# Assert: Path(sm._saves_dir).exists() (après création)
```

**TC-009** : Vérification statique
```bash
grep -rn "os.path.join" src/  # → 0 (si migration complète)
```

### Integration Tests

**IT-001** : Partie complète — joueur se déplace, NPC bouge, sprites ajoutés/supprimés → aucune régression de comportement

**IT-002** : Pyright avec `@override` → 0 erreurs supplémentaires (les overrides sont corrects)

---

## Error Handling Matrix

| Error | Fallback | Logging |
|---|---|---|
| Pyright `reportGeneralTypeIssues` sur `@override` — signature incompatible avec le parent | Corriger la signature pour matcher le parent — erreur Pyright visible bloque le commit | `pyright src/` dans le pipeline CI |
| `type` alias non résolu — Python < 3.12 utilisé | `SyntaxError` au parsing. Vérifier `python --version` = 3.12+ | Message clair: "type statement requires Python 3.12+" |
| `Path` vs `str` incompatibilité — API pygame-ce attend `str` | `str(path)` au site d'appel — ne pas modifier l'API réceptrice | `TypeError` capturé en test TC-003 |
| ADR-008 non créé — Step 10 ignoré | Aucun impact runtime — purement documentaire | N/A |


---

## Bundling & Native-Module Audit

- **BM1:** N/A
- **BM2:** N/A
- **BM3:** N/A
- **BM4:** N/A — pas de renommage de constantes dans cette spec

---

## File Tree

```
src/
├── entities/
│   ├── player.py                    [MODIFY] — @override sur update()
│   ├── groups.py                    [MODIFY] — @override sur add() et remove()
│   └── npc.py                       [MODIFY] — @override sur update()
└── engine/
    └── render_manager.py            [MODIFY] — alias de type BlitSequence, OccludingRect

docs/
└── ADRs/
    └── ADR-008-frect-migration.md   [NEW] — décision de non-migration FRect

# Step 11 optionnel — mêmes fichiers + suppression os.path.join
```

---

## Assumptions

| Assumption | Risque | Validation |
|---|---|---|
| `BaseEntity.update(dt)` a la même signature que `Player.update(dt)` | Low | Vérifier `base.py` signature avant `@override` |
| `pygame.sprite.Group.add/remove` acceptent `*sprites` (même signature) | Low | Vérifié dans la doc pygame-ce |
| `type` statement est disponible (Python 3.12+) | Low | `python --version` = 3.12 dans venv |
| Step 11 (pathlib) ne casse pas les chemins relatifs existants | Medium — `Path.resolve()` rend absolus les chemins relatifs | Vérifier chaque chemin avant migration |
