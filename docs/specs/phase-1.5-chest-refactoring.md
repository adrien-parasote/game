> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Spec — Phase 1.5 : Refactoring `chest.py` [Implementation]

> Document Type: Implementation  
> **Version :** 1.0 — 2026-05-07  
> **Statut :** Draft  
> **Covers :** F7 (`chest.py` + `chest_draw.py` modification)  
> **Réf. Roadmap :** [`docs/strategic/MASTER_ROADMAP.md#phase-15`](../strategic/MASTER_ROADMAP.md#phase-15)  
> **Réf. Spec existante ChestUI :** [`docs/specs/chest-ui-spec.md`](./chest-ui-spec.md#L1)

---

## Objectif

`src/ui/chest.py` passe de **420 LOC à < 400 LOC** sans aucun changement comportemental.  
Critère de sortie : `python3 -m pytest tests/ui/test_chest.py` → ≥ 52 tests passent. `wc -l src/ui/chest.py` → < 400.

---

## 1. Contexte

`ChestUI` hérite de 3 mixins (`ChestLayoutMixin`, `ChestTransferMixin`, `ChestDrawMixin`).  
Le précédent refactoring (L-ARCH-005) a splitté un monolithe 923 LOC → 5 fichiers, en préservant 471 tests.  
Ce refactoring est un ajustement mineur : déplacer 6 méthodes asset-loading de `chest.py` vers `chest_draw.py`.

**Principe de cohésion :** Les méthodes `_load_*` et `_get_item_icon` chargent des assets utilisés exclusivement par `ChestDrawMixin`. Les déplacer dans `chest_draw.py` renforce la cohésion drawing + assets.

**Contrainte L-ARCH-001 :** `_load_*` methods sont appelées dans `ChestUI.__init__` — elles doivent rester accessibles dans ce contexte (via l'héritage du mixin). `chest_draw.py` fournit ces méthodes par héritage → `ChestUI.__init__` peut continuer à appeler `self._load_background()` sans changement.

---

## 2. Déplacement des méthodes

### 2.1 Méthodes à déplacer de `chest.py` vers `chest_draw.py`

| Méthode | LOC | Lignes source | Contenu |
|---------|-----|--------------|---------|
| `_load_background` | 10 | L287-L296 | Load + scale chest bg à `_TARGET_WIDTH` |
| `_load_inv_background` | 10 | L298-L307 | Load + scale inv bg à `_INV_TARGET_WIDTH` |
| `_load_slot_image` | 7 | L309-L315 | Load slot placeholder |
| `_load_cursor` | 11 | L317-L327 | Load + scale cursor via `Settings.CURSOR_SIZE` |
| `_load_and_scale_arrow` | 9 | L329-L337 | Load + scale arrow par facteur |
| `_get_item_icon` | 21 | L339-L359 | Load, scale, cache item icon par `icon_filename@size` |
| **Total déplacé** | **68 LOC** | — | — |

### 2.2 Imports à ajouter dans `chest_draw.py`

Les méthodes déplacées ont besoin de :
```python
import logging
import os
import pygame
from src.config import Settings
from src.ui.chest_constants import (
    ASSET_CHEST_BG,
    ASSET_INV_BG,
    ASSET_SLOT_IMG,
    _TARGET_WIDTH,
    _INV_TARGET_WIDTH,
)
```

`chest_draw.py` importe déjà `logging`, `pygame`, `Settings`, et plusieurs constantes. Vérifier et ajouter uniquement les manquants : `os`, `ASSET_CHEST_BG`, `ASSET_INV_BG`, `ASSET_SLOT_IMG`, `_TARGET_WIDTH`, `_INV_TARGET_WIDTH`.

### 2.3 Imports à retirer de `chest.py`

Après déplacement, vérifier si ces constantes sont encore utilisées dans `chest.py` :
- `ASSET_CHEST_BG`, `ASSET_INV_BG`, `ASSET_SLOT_IMG` → utilisés uniquement dans `_load_*` → **retirer** de l'import de `chest.py`
- `_TARGET_WIDTH`, `_INV_TARGET_WIDTH` → idem → **retirer**
- `ASSET_POINTER`, `ASSET_POINTER_SELECT` → encore utilisés dans `__init__` (`_load_cursor(ASSET_POINTER)`) → **garder**

### 2.4 LOC cible après déplacement

```
chest.py actuel :          420 LOC
Méthodes déplacées :       -68 LOC
Imports retirés (~5 LOC) :  -5 LOC
chest.py final :           ~347 LOC  ✅ < 400

chest_draw.py actuel :     192 LOC
Méthodes ajoutées :        +68 LOC
Imports ajoutés (~4 LOC) :  +4 LOC
chest_draw.py final :      ~264 LOC  ✅ < 400
```

---

## 3. Comportement à préserver (copie exacte)

Les méthodes sont transférées **à l'identique** dans `ChestDrawMixin`. Aucun changement de logique.

### `_load_background()` → `ChestDrawMixin`
```python
def _load_background(self) -> pygame.Surface | None:
    """Load and scale the chest background image to _TARGET_WIDTH."""
    try:
        img = pygame.image.load(ASSET_CHEST_BG).convert_alpha()
        w, h = img.get_size()
        scale = _TARGET_WIDTH / w
        return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
    except Exception as e:
        logging.error(f"ChestUI background load failed: {e}")
        return None
```

### `_load_inv_background()` → `ChestDrawMixin`
```python
def _load_inv_background(self) -> pygame.Surface | None:
    """Load and scale the inventory background image to _INV_TARGET_WIDTH."""
    try:
        img = pygame.image.load(ASSET_INV_BG).convert_alpha()
        w, h = img.get_size()
        scale = _INV_TARGET_WIDTH / w
        return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
    except Exception as e:
        logging.error(f"ChestUI inventory background load failed: {e}")
        return None
```

### `_load_slot_image()` → `ChestDrawMixin`
```python
def _load_slot_image(self) -> pygame.Surface | None:
    """Load the slot placeholder image."""
    try:
        return pygame.image.load(ASSET_SLOT_IMG).convert_alpha()
    except Exception as e:
        logging.warning(f"ChestUI slot image load failed: {e}")
        return None
```

### `_load_cursor(path)` → `ChestDrawMixin`
```python
def _load_cursor(self, path: str) -> pygame.Surface | None:
    """Load and scale a cursor image."""
    try:
        img = pygame.image.load(path).convert_alpha()
        size = Settings.CURSOR_SIZE
        w, h = img.get_size()
        ratio = min(size / w, size / h)
        return pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))
    except Exception as e:
        logging.warning(f"ChestUI cursor load failed ({path}): {e}")
        return None
```

### `_load_and_scale_arrow(path, scale)` → `ChestDrawMixin`
```python
def _load_and_scale_arrow(self, path: str, scale: float) -> pygame.Surface | None:
    """Load an arrow icon and scale it by the given factor."""
    try:
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
    except Exception as e:
        logging.warning(f"ChestUI arrow hover load failed ({path}): {e}")
        return None
```

### `_get_item_icon(icon_filename, slot_size)` → `ChestDrawMixin`
```python
def _get_item_icon(self, icon_filename: str, slot_size: int) -> pygame.Surface | None:
    """Load, scale, and cache an item icon to *slot_size* px."""
    cache_key = f"{icon_filename}@{slot_size}"
    if cache_key in self._icon_cache:
        return self._icon_cache[cache_key]

    path = os.path.join("assets", "images", "icons", icon_filename)
    if not path.endswith(".png"):
        path += ".png"

    try:
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (slot_size, slot_size))
            self._icon_cache[cache_key] = img
            return img
    except Exception as e:
        logging.warning(f"ChestUI: Could not load icon {icon_filename}: {e}")

    self._icon_cache[cache_key] = None
    return None
```

> [!IMPORTANT]
> `_get_item_icon` accède à `self._icon_cache` qui est défini dans `ChestUI.__init__`. Ce dict est accessible via l'héritage mixin — aucun changement requis dans `__init__`. Ne pas déplacer `self._icon_cache: dict = {}` dans `ChestDrawMixin.__init__` (il n'y a pas de `__init__` dans les mixins de ce projet).

---

## 4. Vérification : pas de double définition

Après déplacement, s'assurer que ces méthodes n'existent plus dans `chest.py` et n'existent pas déjà dans `chest_draw.py`. Commande de vérification :
```bash
grep -n "def _load_background\|def _load_inv_background\|def _load_slot_image\|def _load_cursor\|def _load_and_scale_arrow\|def _get_item_icon" src/ui/chest.py src/ui/chest_draw.py
```
Attendu après refactoring : 0 match dans `chest.py`, 6 matches dans `chest_draw.py`.

---

## 5. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|-----------|
| 1 | `ChestUI.__init__` peut continuer à appeler `self._load_background()` sans changement (méthode fournie par `ChestDrawMixin` via héritage) | Low | L'ordre MRO Python garantit que `ChestDrawMixin` est résolu avant `ChestUI` pour les méthodes partagées |
| 2 | Les tests existants (`test_chest.py`) qui patchent `ChestUI._load_*` continuent de fonctionner (même namespace via héritage mixin) | Low — L-ARCH-005 prouvé | Exécuter `pytest tests/ui/test_chest.py` immédiatement après le déplacement |
| 3 | `_get_item_icon` n'est appelée que depuis `ChestDrawMixin._draw_slots` et `_draw_inv_slots` et `_draw_dragged_item` | Low | `grep -rn "_get_item_icon" src/ui/` |
| 4 | `ASSET_CHEST_BG`, `ASSET_INV_BG`, `ASSET_SLOT_IMG` sont définis dans `chest_constants.py` — pas dans `chest.py` | Low | Vérifier `src/ui/chest_constants.py` |
| 5 | `chest_draw.py` final (264 LOC) reste bien sous 400 LOC | Low | `wc -l src/ui/chest_draw.py` après ajout |

---

## 6. Anti-Patterns (DO NOT)

| ❌ Ne pas faire | ✅ Faire à la place | Pourquoi |
|----------------|--------------------|---------| 
| Ajouter un `__init__` dans `ChestDrawMixin` | Garder les mixins sans `__init__` | L'état (`_icon_cache`, `_bg`, etc.) est défini dans `ChestUI.__init__` — pattern existant du projet |
| Créer un 5ème mixin **ChestAssetsMixin** | Intégrer dans `ChestDrawMixin` existant | 5ème mixin pour 68 LOC = over-engineering ; drawing + assets = cohésion fonctionnelle |
| Dupliquer les méthodes (les garder dans `chest.py` ET les ajouter dans `chest_draw.py`) | Supprimer de `chest.py`, ajouter dans `chest_draw.py` | Double définition → Python MRO choisit la première, mais c'est un bug latent |
| Appeler `pygame.image.load()` dans `draw()` ou `_compute_layout()` | Garder les loads dans `__init__` uniquement (L-ARCH-001) | Disk I/O dans le render loop → frame drops |
| Modifier la logique de `_get_item_icon` (cache, path resolution) | Copie exacte de L339-L359 | Le cache `@size` est une optimisation critique |
| Importer `ASSET_CHEST_BG` etc. dans `chest.py` après suppression des `_load_*` | Retirer les imports devenus inutilisés | Imports inutilisés = confusion + lint errors |

---

## 7. Test Case Specifications

**Préfixes TC :** `CA-` (chest assets)  
Note : Les tests existants dans `tests/ui/test_chest.py` (52 tests) couvrent déjà le comportement. Ces TCs sont additionnels pour valider le refactoring.

### Unit Tests — méthodes déplacées

| ID | Description | Input | Attendu |
|----|-------------|-------|---------|
| TC-CA-01 | `_load_background` avec fichier absent | Asset absent (env test headless) | Retourne `None`, log error |
| TC-CA-02 | `_load_inv_background` avec fichier absent | Asset absent | Retourne `None`, log error |
| TC-CA-03 | `_load_slot_image` avec fichier absent | Asset absent | Retourne `None`, log warning |
| TC-CA-04 | `_load_cursor` avec fichier absent | Path invalide | Retourne `None`, log warning |
| TC-CA-05 | `_load_and_scale_arrow` avec fichier absent | Path invalide | Retourne `None`, log warning |
| TC-CA-06 | `_get_item_icon` cache hit | Même `icon@size` appelé 2x | 2ème appel retourne depuis `_icon_cache` sans I/O |
| TC-CA-07 | `_get_item_icon` fichier absent | Icon inexistant | Retourne `None`, met `None` en cache |
| TC-CA-08 | `_get_item_icon` sans extension `.png` | `"sword"` (sans .png) | Chemin `sword.png` utilisé |

### Regression Tests (exécuter les tests existants)

| ID | Description | Attendu |
|----|-------------|---------|
| IT-CA-01 | Suite complète tests/ui/test_chest.py après refactoring | ≥ 52 tests passent |
| IT-CA-02 | `ChestUI()` instanciable sans erreur | Pas d'AttributeError ou ImportError |
| IT-CA-03 | `ChestUI._load_background` accessible via `self` dans `__init__` | Méthode résolue via MRO mixin |
| IT-CA-04 | `ChestUI._get_item_icon` accessible dans `_draw_slots` (chest_draw.py) | Méthode disponible via `self` |
| IT-CA-05 | Pas de double définition de méthodes | `grep` retourne 0 matches dans `chest.py`, 6 dans `chest_draw.py` |

### Index canon (format spec_precheck)

| ID | Ref interne | Type |
|----|-------------|------|
| TC-001 | TC-CA-01 | unit |
| TC-002 | TC-CA-02 | unit |
| TC-003 | TC-CA-03 | unit |
| TC-004 | TC-CA-04 | unit |
| TC-005 | TC-CA-05 | unit |
| TC-006 | TC-CA-06 | unit |
| TC-007 | TC-CA-07 | unit |
| TC-008 | TC-CA-08 | unit |
| IT-001 | IT-CA-01 | integration |
| IT-002 | IT-CA-02 | integration |
| IT-003 | IT-CA-03 | integration |

---

## 8. Error Handling Matrix

| Failure | Détection | Réponse | Fallback |
|---------|-----------|---------|---------|
| Asset image absent (`FileNotFoundError`) | `except Exception` dans chaque `_load_*` | `logging.error/warning` | Retourne `None` — les méthodes draw vérifient `if self._bg is not None` |
| `convert_alpha()` sans display init | `pygame.error` dans `except Exception` | `logging.error` | Retourne `None` |
| Icon inexistant dans `_get_item_icon` | `os.path.exists` False | Met `None` en cache | Slot vide affiché, pas de crash |
| `_icon_cache` non initialisé | Ne peut pas arriver si `ChestUI.__init__` exécuté | N/A | Guard `hasattr(self, "_icon_cache")` optionnel si défense en profondeur requise |

---

## 9. Deep Links

- **Source méthodes à déplacer** : [`src/ui/chest.py#L287-L359`](../../src/ui/chest.py#L287)
- **Destination `ChestDrawMixin`** : [`src/ui/chest_draw.py`](../../src/ui/chest_draw.py#L1)
- **`ChestUI.__init__`** : [`src/ui/chest.py#L31-L86`](../../src/ui/chest.py#L31)
- **`ChestUI` class header (inheritance)** : [`src/ui/chest.py#L28`](../../src/ui/chest.py#L28)
- **`chest_constants.py`** : [`src/ui/chest_constants.py`](../../src/ui/chest_constants.py#L1)
- **Tests chest** : [`tests/ui/test_chest.py`](../../tests/ui/test_chest.py#L1)
- **Learning L-ARCH-005** (Mixin pattern) : `.agents/learnings/game_engine.md#L-ARCH-005`
- **Learning L-ARCH-001** (No I/O in draw) : `.agents/learnings/game_engine.md#A-ARCH-001`
- **Spec game refactoring** : [`docs/specs/phase-1.5-game-refactoring.md`](./phase-1.5-game-refactoring.md#L1)
- **Spec interaction refactoring** : [`docs/specs/phase-1.5-interaction-refactoring.md`](./phase-1.5-interaction-refactoring.md#L1)

### Linked Test Functions

| Test ID | Fonction test | Fichier |
|---------|--------------|---------|
| IT-CA-01 | (suite complète) | `../../tests/ui/test_chest.py` |
| IT-CA-02 | `test_capacity_no_player` | `../../tests/ui/test_chest.py` |
| IT-CA-06 | `test_get_chest_contents_pads_to_max` | `../../tests/ui/test_chest.py` |
