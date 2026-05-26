# Spec — Steps 5 à 7 : Saves Path + AssetManager UI + Pyright

> Document Type: Implementation
> **Covers:** Save-Path, AssetManager-UI, Pyright-basic
> **Référence blueprint:** [`best_practices_remediation_blueprint.md`](./strategic/best_practices_remediation_blueprint.md#plan-dimplémentation--10-steps)
> **Guide best practices:** [`pygame_ce_python_312_best_practices.md`](./pygame_ce_python_312_best_practices.md#section-3-save-system)
> **Statut:** SPEC — prêt pour BUILD

---

## Contexte

Trois violations de moyenne sévérité :

1. **Save path relatif** : `SAVES_DIR = "saves"` dans `save_manager.py` — fragile en distribution (macOS .app bundle, Windows UAC). Doit utiliser `pygame.system.get_pref_path()`.
2. **Images UI chargées hors `AssetManager`** : 8 fichiers UI utilisent `pygame.image.load(path).convert_alpha()` directement, bypassing le cache partagé.
3. **Pyright quasi-désactivé** : `pyrightconfig.json` supprime 7 catégories d'erreurs dont 5 ne cachent rien et 2 cachent 14 vraies erreurs corrigeables.

---

## Constraints

| Tier | Exemples |
|---|---|
| **Always do** | Initialiser `pygame.system` avant `get_pref_path`. Créer le répertoire si absent. Passer par `AssetManager.get_image()` pour tout `pygame.image.load` dans `src/ui/`. |
| **Ask first** | Modifier la signature publique de `SaveManager.__init__`. Changer `SAVES_DIR` globalement (impact sur saves existantes). |
| **Never do** | Supprimer `reportAttributeAccessIssue: none` (irréductible sans stubs pygame-ce). Modifier `AssetManager` lui-même. Toucher `src/engine/save_manager.py` au-delà de `SAVES_DIR`. |

---

## Cross-Spec Contracts

### Produces
| Path / Identifiant | Format | Schema | Consommateurs |
|---|---|---|---|
| Répertoire saves | Filesystem, path `str` | `save-system.md § "Format de sauvegarde"` | `SaveManager.list_slots()`, `SaveManager.load()`, `SaveManager.save()` |

### Consumes
| Identifiant | Format | Défini dans | Producteur |
|---|---|---|---|
| `AssetManager.get_image(path)` | `pygame.Surface` (convert_alpha'd) | `engine-core.md § "AssetManager"` | `AssetManager` singleton |
| `pygame.system.get_pref_path(org, app)` | `str` (chemin absolu OS-specific) | pygame-ce docs | pygame-ce stdlib |

### Public Interface
N/A — pas de changement d'API publique. `SaveManager.__init__(saves_dir)` garde la même signature (override via paramètre optionnel).

### External Invocations
| Type | Invoqué | Défini dans |
|---|---|---|
| `pygame.system.get_pref_path("adrien", "game")` | Retourne le répertoire de préférences OS | pygame-ce API — retourne `str` |

### Tracked Concepts
| Concept | Statut | Mentionné dans |
|---|---|---|
| `SAVES_DIR` | Migré vers `get_pref_path` à l'init | `save-system.md § "Répertoire"` |
| `AssetManager` singleton | Consommé, non modifié | `engine-core.md § "AssetManager"` |

---

## Step 5 — `pygame.system.get_pref_path` pour les saves

### Fichier modifié : `src/engine/save_manager.py`

**Avant (L12) :**
```python
SAVES_DIR = "saves"
```

**Après :**
```python
import pygame.system
import os
import shutil

def _get_saves_dir() -> str:
    """Return the OS-appropriate saves directory path.

    Uses pygame.system.get_pref_path() for cross-OS compatibility:
    - macOS: ~/Library/Application Support/adrien/game/
    - Windows: %APPDATA%/adrien/game/
    - Linux: ~/.local/share/adrien/game/

    Falls back to "./saves" if pygame not initialized (e.g. test context).
    
    Migration logic: If legacy "./saves" exists and the new directory is empty,
    moves all saves to the new directory and renames "./saves" to "./saves_migrated".
    """
    try:
        path = pygame.system.get_pref_path("adrien", "game")
        
        # MIGRATION: Preserve user data from legacy paths
        legacy_path = "./saves"
        if os.path.exists(legacy_path) and os.path.isdir(legacy_path):
            # Check if new path is empty
            if not os.path.exists(path) or not os.listdir(path):
                os.makedirs(path, exist_ok=True)
                for item in os.listdir(legacy_path):
                    s = os.path.join(legacy_path, item)
                    d = os.path.join(path, item)
                    if os.path.isdir(s): shutil.copytree(s, d)
                    else: shutil.copy2(s, d)
                # Safe rename to avoid crashing if destination already exists
                migrated_path = legacy_path + "_migrated"
                if not os.path.exists(migrated_path):
                    os.rename(legacy_path, migrated_path)
                else:
                    counter = 1
                    while os.path.exists(f"{migrated_path}_{counter}"):
                        counter += 1
                    os.rename(legacy_path, f"{migrated_path}_{counter}")
                
        return path
    except Exception:
        return "saves"  # fallback pour tests headless

SAVES_DIR = _get_saves_dir()
```

**Règle :** `pygame.init()` doit avoir été appelé avant `_get_saves_dir()`. Dans l'ordre d'init actuel (`game.py:__init__` → `pygame.init()` → `SaveManager()`), c'est garanti.

**Tests existants :** `SaveManager` accepte `saves_dir` en paramètre (`__init__(self, saves_dir: str = SAVES_DIR)`). Les tests passent leur propre répertoire temporaire → non impactés par ce changement.

### Vérification post-implémentation

```bash
python3 -c "
import pygame
pygame.init()
import pygame.system
print(pygame.system.get_pref_path('adrien', 'game'))
"
# → doit afficher un chemin absolu dans ~/Library/Application Support/ (macOS)
```

---

## Step 6 — Centraliser les chargements d'images dans `AssetManager`

### Inventaire complet des violations

| Fichier | Lignes | Image chargée |
|---|---|---|
| `src/ui/inventory.py` | 144, 210 | Images d'inventaire (backgrounds, slots) |
| `src/ui/chest_draw.py` | 216, 227, 238, 246, 258, 277 | Images du coffre |
| `src/ui/chest_layout.py` | 96 | Image de survol du slot |
| `src/ui/hud.py` | 46 | Images d'HUD (clock, season icons) |
| `src/ui/title_screen.py` | 83, 94 | Backgrounds écran titre |
| `src/ui/pause_screen.py` | 76, 87 | Backgrounds écran pause |
| `src/ui/dialogue.py` | 66, 75 | Bubbles dialogue |
| `src/ui/speech_bubble.py` | Variable | Ressources speech bubble |
| `src/ui/save_slot.py` | Variable | Icônes slot de sauvegarde |
| `src/ui/save_menu.py` | Variable | Background menu save |

### Pattern de migration

**Avant :**
```python
# Dans __init__ d'un module UI
img = pygame.image.load(path).convert_alpha()
```

**Après :**
```python
from src.engine.asset_manager import AssetManager

# Dans __init__
am = AssetManager()
img = am.get_image(path)
```

**Règle :** `AssetManager` est un singleton — `AssetManager()` retourne toujours la même instance. `.get_image(path)` appelle `.convert_alpha()` en interne (vérifié `asset_manager.py:44`). Aucune double conversion.

**⚠️ Précaution :** Avant chaque migration, vérifier que le chemin passé à `pygame.image.load(path)` est identique au chemin que recevrait `am.get_image(path)`. `AssetManager.get_image` peut avoir un format de chemin différent (relatif vs absolu). Vérifier `asset_manager.py` avant de migrer.

### Fichiers modifiés

Chacun des 8 fichiers listés ci-dessus — **uniquement les lignes `pygame.image.load`**. Aucun autre changement.

---

## Step 7 — Pyright mode `basic` + suppression des suppressions fantômes

### Données mesurées

| Config | Erreurs |
|---|---|
| Config actuelle (7 suppressions) | 0 erreurs (Pyright muet) |
| Mode `basic` sans aucune suppression | 158 erreurs |
| Mode `basic` + `reportAttributeAccessIssue: none` seulement | **14 erreurs** |

### Config cible : `pyrightconfig.json`

```json
{
  "pythonVersion": "3.12",
  "pythonPlatform": "Darwin",
  "extraPaths": ["."],
  "exclude": [
    "**/__pycache__",
    ".venv",
    "venv",
    "tests",
    ".agents",
    "scripts",
    "build",
    "dist"
  ],
  "typeCheckingMode": "basic",
  "reportMissingModuleSource": "none",
  "reportMissingImports": "warning",
  "reportAttributeAccessIssue": "none"
}
```

**Suppressions retirées (étaient fantômes — 0 erreur supplémentaire) :**
- `reportGeneralTypeIssues` (était `"none"`)
- `reportOptionalSubscript` (était `"none"`)
- `reportOptionalCall` (était `"none"`)
- `reportOptionalIterable` (était `"none"`)

**Suppression conservée (irréductible sans stubs pygame-ce) :**
- `reportAttributeAccessIssue: none` — 144 erreurs de type `.blit`, `.pos`, `.rect` sur objects pygame

**Correction supplémentaire :** `"pythonVersion": "3.13"` → `"3.12"` (le projet tourne en 3.12)

### 14 Erreurs réelles à corriger

| Fichier | Nb | Type | Correction |
|---|---|---|---|
| `src/engine/lighting.py` | 4 | `reportOptionalOperand` — opérations `/`, `*`, `+`, `-` sur valeur potentiellement `None` | Ajouter guard `if value is None: return` ou assertion |
| `src/map/tmj_parser.py` | 2 | Type `str | None` passé à `int()` | `int(value)` → `int(value) if value is not None else default` |
| `src/ui/dialogue.py` | 3 | `reportOptionalMemberAccess` — `.render()` et `.get_linesize()` sur `font: Font | None` | Guard `if self._font is None: return` en début de méthode |
| `src/ui/save_menu.py` | 3 | `reportOptionalMemberAccess` — attrs sur `SaveData | None` | Guard `if slot_data is None: return` |
| `src/ui/speech_bubble.py` | 1 | `reportOptionalMemberAccess` — `.render()` sur font `None` | Guard `if self._font is None: return` |

**Correction type :**
```python
# AVANT — lighting.py:150
result = value / divisor  # value peut être None

# APRÈS
if value is None:
    logging.warning("lighting: expected float, got None")
    return
result = value / divisor
```

### Vérification post-Step 7

```bash
source venv/bin/activate && pyright src/
# → 0 errors, N warnings (informatifs)
```

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | `pygame.image.load().convert_alpha()` inline dans `__init__` UI | `img = pygame.image.load(path).convert_alpha()` dans 8 modules UI | `am = AssetManager(); img = am.get_image(path)` — conforme [`engine-core.md`](./engine-core.md#assetmanager) |
| 2 | Supprimer toutes les règles Pyright sans mesurer | 7 suppressions actives, 5 ne cachaient rien | Supprimer uniquement les suppressions vérifiées comme fantômes. Garder `reportAttributeAccessIssue: none` |
| 3 | Supprimer `reportAttributeAccessIssue` | Supprime 144 erreurs pygame-ce irréductibles | Ne JAMAIS retirer cette suppression sans stubs pygame-ce |
| 4 | `get_pref_path` avant `pygame.init()` | `SaveManager()` instancié avant le premier `pygame.init()` | Toujours initialiser pygame avant `SaveManager`. Vérifier l'ordre dans [`engine-core.md`](./engine-core.md#init-sequence) |
| 5 | Chemin absolus hardcodés pour les saves | `SAVES_DIR = "/Users/user/game/saves"` | Uniquement `pygame.system.get_pref_path(org, app)` comme source du chemin |
| 6 | Modifier `AssetManager.get_image()` pour adapter les chemins UI | Changer le format de chemin dans `AssetManager` pour accommoder les modules UI | Adapter le chemin dans le site d'appel UI, pas dans `AssetManager` |
| 7 | `"pythonVersion": "3.13"` dans pyrightconfig.json | Faux positifs 3.13 sur un projet 3.12 | Toujours aligner `pythonVersion` avec la version réelle du venv |



---

## Test Case Specifications

### Unit Tests — Save Path

**TC-SAVE-001** : `SaveManager()` initialisé avec `pygame.init()` actif → `self._saves_dir` est un chemin absolu (ne commence pas par `"saves"`)
```python
# Arrange: pygame.init() appelé (conftest.py)
# Act: sm = SaveManager()
# Assert: os.path.isabs(sm._saves_dir) == True
```

**TC-SAVE-002** : `SaveManager()` initialisé sans pygame → `self._saves_dir == "saves"` (fallback)
```python
# Arrange: patch pygame.system.get_pref_path → raise Exception
# Act: sm = SaveManager()
# Assert: sm._saves_dir == "saves"
```

**TC-SAVE-003** : Tests existants passent sans modification — le paramètre `saves_dir` override reste fonctionnel
```python
# Arrange: SaveManager(saves_dir="/tmp/test_saves")
# Assert: sm._saves_dir == "/tmp/test_saves"
```

**TC-SAVE-004** : `_get_saves_dir()` retourne un `str` (pas `bytes`) sur pygame-ce
```python
# Assert: isinstance(result, str)
```

### Unit Tests — AssetManager UI

**TC-ASSET-001** : Après migration, aucun fichier `src/ui/` ne contient `pygame.image.load`
```python
# Vérification statique :
# grep -rn "pygame.image.load" src/ui/ → 0 résultats
```

**TC-ASSET-002** : `AssetManager.get_image(path)` appelé 3× avec le même path → `pygame.image.load` appelé 1× (cache hit)
```python
# Arrange: mock pygame.image.load
# Act: am.get_image(path) × 3
# Assert: load.call_count == 1
```

**TC-ASSET-003** : Les tests de modules UI (chest, inventory, pause_screen) passent après migration — pas de régression sur les surfaces

### Unit Tests — Pyright

**TC-PYRIGHT-001** : `pyright src/` avec la nouvelle config → 0 errors
```bash
pyright src/ | grep "0 errors"
```

**TC-PYRIGHT-002** : `lighting.py` — opération sur valeur `None` → levée de warning logging, pas de crash
```python
# Arrange: mettre la valeur None dans le contexte lighting
# Assert: logging.warning appelé, pas d'exception
```

**TC-PYRIGHT-003** : `dialogue.py` — `_font is None` → `draw()` retourne sans blit
```python
# Arrange: dialogue._font = None
# Act: dialogue.draw(screen)
# Assert: screen.blit not called, no AttributeError
```

**TC-PYRIGHT-004** : `save_menu.py` — `slot_data is None` → rendu slot vide sans crash
```python
# Arrange: slot_data = None
# Assert: no AttributeError on None.map_display_name
```

### Integration Tests

**TC-IT-SAVE-001** : Cycle save → quit → load sur chemin `get_pref_path` → données identiques avant/après

**TC-IT-ASSET-001** : Démarrage du jeu complet, ouverture inventaire + coffre + écran titre → aucune `pygame.error` sur image manquante

---

## Error Handling Matrix

| Erreur | Cause | Comportement |
|---|---|---|
| `pygame.system.get_pref_path` lève exception | pygame non initialisé | Fallback vers `"saves"` + log warning |
| Répertoire `get_pref_path` non créable (permissions) | Permissions OS restreintes | `OSError` remontée par `SaveManager.save()` — message user-friendly "Impossible de sauvegarder" |
| `AssetManager.get_image(path)` — fichier manquant | Asset supprimé/renommé | `AssetManager` retourne surface fallback + log error (comportement existant non modifié) |
| Chemin UI incompatible avec `AssetManager` | Format chemin différent | `FileNotFoundError` visible à la migration — corriger le chemin dans le site d'appel |
| `lighting.py` — `None` dans opération arithmétique | Valeur non initialisée | Guard + `logging.warning` + `return` |
| `dialogue.py` — font `None` | Chargement font échoué | Guard `if self._font is None: return` |

---

## Bundling & Native-Module Audit

- **BM1:** N/A — projet Python pur
- **BM2:** N/A
- **BM3:** N/A — aucun module natif introduit
- **BM4:** N/A — aucune constante renommée. Vérifier que `SAVES_DIR` n'est pas importé directement ailleurs : `grep -rn "from src.engine.save_manager import SAVES_DIR" src/`

---

## File Tree

```
src/
├── engine/
│   └── save_manager.py              [MODIFY] — SAVES_DIR via _get_saves_dir()
└── ui/
    ├── inventory.py                 [MODIFY] — pygame.image.load → AssetManager
    ├── chest_draw.py                [MODIFY] — pygame.image.load → AssetManager
    ├── chest_layout.py              [MODIFY] — pygame.image.load → AssetManager
    ├── hud.py                       [MODIFY] — pygame.image.load → AssetManager
    ├── title_screen.py              [MODIFY] — pygame.image.load → AssetManager
    ├── pause_screen.py              [MODIFY] — pygame.image.load → AssetManager
    ├── dialogue.py                  [MODIFY] — pygame.image.load → AssetManager + guard font None
    ├── speech_bubble.py             [MODIFY] — pygame.image.load → AssetManager + guard font None
    ├── save_slot.py                 [MODIFY] — pygame.image.load → AssetManager
    └── save_menu.py                 [MODIFY] — pygame.image.load → AssetManager + guard SlotInfo None

pyrightconfig.json                   [MODIFY] — typeCheckingMode basic, python 3.12, 5 suppressions retirées
```

---

## Assumptions

| Assumption | Risque | Validation |
|---|---|---|
| `AssetManager.get_image()` accepte les mêmes chemins que `pygame.image.load()` dans les modules UI | Medium — les chemins peuvent être relatifs vs absolus | Vérifier `asset_manager.py:get_image()` pour le format attendu avant de migrer chaque fichier |
| `pygame.system.get_pref_path` est disponible dans pygame-ce 2.x | Low — API stable depuis pygame 2.0 | `import pygame.system; hasattr(pygame.system, 'get_pref_path')` |
| Les 14 erreurs Pyright sont toutes corrigeables par guard `is None` | Low — toutes catégorisées `reportOptionalMemberAccess` / `reportOptionalOperand` | Données mesurées sur la codebase réelle |
| Les saves existantes dans ./saves/ seront inaccessibles après migration vers `get_pref_path` | High — **breaking change pour les parties en cours** | **MIGRATION OBLIGATOIRE** implémentée dans `_get_saves_dir`. Le répertoire legacy est copié vers pref_path puis renommé `saves_migrated`. |
