# Blueprint Stratégique — Remédiation Best Practices Pygame-CE / Python 3.12

> **Type :** Plan stratégique de remédiation technique
> **Référence :** `docs/specs/pygame_ce_python_312_best_practices.md`
> **Audit source :** `pygame_ce_best_practices_audit.md` (2026-05-26)
> **Statut :** Stratégie validée — en attente de SPEC

---

## Problème résolu

8 violations techniques documentées dans le guide de référence pygame-ce / Python 3.12.
Impacte la stabilité du gameplay (DT non clampé), les performances (font.render en boucle),
la portabilité (chemins saves) et la maintenabilité (Pyright désactivé, @override absent).

## Succès mesurable

| Métrique | Cible |
|---|---|
| DT clampé partout | `grep "min(raw_dt"` → 2 hits (game.py, game_state_manager.py) |
| 0 `font.render` dans draw() | `grep -n "font.render" src/ui/hud.py` → 0 dans `draw()` |
| saves via `get_pref_path` | `grep "get_pref_path" src/engine/save_manager.py` → 1 hit |
| Pyright `basic` → 0 erreurs | `pyright src/ --outputjson \| jq .summary.errorCount` = 0 |
| Images UI via AssetManager | `grep -rn "pygame.image.load" src/ui/` → 0 |
| `@override` sur méthodes héritées | `grep "@override" src/entities/player.py` → 1+ |
| Tests verts | `pytest` → 0 failures |

---

## Décisions architecturales

### DA-1 : TextCache — dict inline, pas de classe partagée
**Décision :** Pré-rendu dict dans chaque composant, pattern identique à `title_screen.py:168` et `PauseScreen._make_engraved_surface()`.
**Rationale :** Conforme ADR-006 §"No New Abstractions". Le composant le plus complexe (inventory_draw) a besoin d'invalidation par event de mutation, pas par timer.
**Exclu :** Classe `TextCache` globale dans `src/engine/`.

### DA-2 : FRect — ADR uniquement, pas de migration code
**Décision :** Rédiger ADR-008 documentant la décision de ne PAS migrer en Phase 1. Le double-système `Vector2+Rect` est fonctionnel. Migration planifiée si jitter visible post-distribution.
**Exclu :** Tout changement de code sur `base.py`, `player.py`, `groups.py`.

### DA-3 : Pyright — mode `basic`, pas `strict` (inaccessible sans stubs pygame)
**Décision :** `"typeCheckingMode": "basic"`. `strict` est exclu définitivement pour ce projet.
**Données mesurées :** `strict` génère 3 289 erreurs dont 1 353 (`reportUnknownMemberType` + `reportUnknownVariableType`) viennent de l'absence de stubs Pyright complets pour pygame-ce. Ces erreurs sont **irréductibles sans stubs tiers**.
**Vrai fix :** Passer à `basic` + supprimer les suppressions `reportOptional*` une par une. Les 14 erreurs `reportOptionalMemberAccess` réelles seront alors visibles et corrigeables.

### DA-4 : `pathlib.Path` — Step optionnel distinct, pas une exclusion
**Révision :** L'exclusion initiale était paresseuse ("hors document de référence"). `pathlib.Path` est le standard Python 3.12.
**Décision :** Ce n'est pas une violation du guide de référence, mais c'est une amélioration légitime. Classé **Step 11 optionnel** (refactoring mécanique ~60 occurrences). Traité séparément des corrections de violations car il ne répond pas à un anti-pattern identifié dans l'audit.

---

## Plan d'implémentation — 10 Steps

| Step | Description | Sévérité | Effort | Fichiers |
|---|---|---|---|---|
| **1** | DT Clamp dans toutes les boucles | 🔴 | 15 min | `game.py`, `game_state_manager.py` |
| **2** | Text Cache HUD (textes semi-statiques) | 🔴 | 1h | `hud.py` |
| **3** | Text Cache Inventory (textes dynamiques) | 🔴 | 1h | `inventory_draw.py` |
| **4** | Text Cache Chest | 🔴 | 30 min | `chest_draw.py` |
| **5** | `pygame.system.get_pref_path` saves | 🟡 | 1h | `save_manager.py` |
| **6** | Centraliser images UI dans AssetManager | 🟡 | 2h | 8 fichiers `ui/` |
| **7** | Pyright mode `basic` + suppr. suppressions Optional | 🟡 | 1-2h | `pyrightconfig.json` |
| **8** | `@override` sur méthodes héritées | 🟢 | 30 min | `player.py`, `groups.py`, `npc.py` |
| **9** | Alias de type `type` | 🟢 | 30 min | `render_manager.py` |
| **10** | ADR-008 FRect — évaluation et décision | 🟢 | 30 min | `docs/ADRs/ADR-008-frect.md` |
| **11** _(optionnel)_ | Migration `os.path.join` → `pathlib.Path` | 🟢 | 2-3h | ~60 occurrences dans `src/` |

**Effort total estimé : 9-12h**

---

## Scope — Ce qu'on ne fait PAS (et pourquoi)

| Exclusion | Raison précise |
|---|---|
| Migration `FRect` (code) | Vector2+Rect est fonctionnel. Pas de jitter visible. Coût > bénéfice immédiat. ADR-008 documente la décision. |
| Pyright `strict` | **Inaccessible** : 1 353/3 289 erreurs sont structurellement irréductibles sans stubs Pyright complets pour pygame-ce. Cible : `basic` uniquement. |
| `src/map/` | Aucune violation identifiée dans l'audit. Zéro `font.render` en boucle, zéro chargement image hors AssetManager, zéro DT non clampé. |
| `src/graphics/spritesheet.py` | `pygame.image.load` à la ligne 26 est **légitime** : chargement à l'init de l'entité, pas dans la boucle de dessin. Déjà mocké dans les tests. |
| Refactoring interne `AssetManager` | `AssetManager` ne change pas. P2-C modifie les 8 fichiers UI qui le *contournent* — AssetManager lui-même n'est pas refactorisé. |

> **Note :** `pathlib.Path` n'est plus une exclusion — c'est un **Step 11 optionnel** distinct. Voir plan d'implémentation.

---

## Gaps ouverts (à résoudre avant SPEC)

| # | Gap | Owner |
|---|---|---|
| **G1** | Pattern d'invalidation TextCache inventory (HP/GOLD/LVL setters ?) | Code + toi |
| **G2** | Type de retour de `pygame.system.get_pref_path` dans pygame-ce 2.4+ | Research |
| **G3** | `AssetManager.get_image` appelle `convert_alpha` — crash headless en tests ? | Code |
| **G4** | Budget corrections Pyright `basic` acceptable ? | Toi |

---

## Learnings intégrés

- **L-UI-011** → Pre-render cache pattern pour textes statiques (PauseScreen, SaveMenu)
- **ADR-006** → No New Abstractions — dict inline preferred over new class
- **L-UI-012** → Ordre : constants → source → tests
- **A-UI-002** → grep avant tout mv/rm d'asset

---

## Résolution des Gaps

| # | Gap | Résolution | Source |
|---|---|---|---|
| **G1** | Invalidation TextCache inventory (HP/GOLD/LVL) | `hp`, `gold`, `level` sont des attributs publics simples. Mutations uniquement à l'init + dans `_apply_save_data()`. Pattern : pre-render au `__init__` de `InventoryUI` + méthode `refresh_stats()` appelée après `_apply_save_data()`. Identique à `SaveMenuOverlay.refresh()` (ADR-006). | Code inspection |
| **G2** | Type retour `pygame.system.get_pref_path` | Retourne `str` en Python 3. Aucune gestion de `bytes` nécessaire. | Web search docs pygame-ce |
| **G3** | `AssetManager.convert_alpha()` headless | `conftest.py` crée un vrai display `pygame.HIDDEN`. `.convert_alpha()` fonctionne. Centralisation sans risque. | Code inspection |
| **G4** | Budget Pyright `basic` | Corrections de types **uniquement dans les fichiers modifiés par les autres Steps**. Pas de correction dans les fichiers non touchés. | Décision de scope |

---

*Créé : 2026-05-26 | Gaps résolus : 2026-05-26 | Prochaine étape : SPEC*
