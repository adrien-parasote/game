# Strategic Blueprint — Render Pipeline Optimization

> **Project:** The Heir's Awakening
> **Stage:** 🎯 STRATEGY
> **Date:** 2026-06-11
> **Scope:** render_manager.py + lighting.py + map_manager (render pipeline complet)

---

## 1. Contexte

Le moteur de rendu actuel est fonctionnel et contient déjà des optimisations (culling viewport, WorldSurface pré-rendu, `fblits()`, cache dirty-flag P-004). Cependant, certains points du pipeline créent des allocations par frame ou des calculs non-cachés qui limiteront les performances à mesure que le contenu du jeu grandit (familiars, ennemis, festivals).

**But :** Rendre le pipeline robuste pour le contenu actuel *et* le contenu futur, sans changer la logique de jeu.

---

## 2. Métriques de Succès

| Métrique | Valeur cible | Timeline |
|---|---|---|
| FPS stable en jeu | ≥ 60 FPS avec contenu actuel | Fin de ce sprint |
| FPS sous charge (futur) | ≥ 60 FPS avec 2× entités actuelles | Headroom mesuré |
| Allocations par frame | 0 `pygame.Surface()` alloués sur le hot-path | Validé par profiler |
| Régression de tests | 0 test rouge non expliqué | À chaque commit |
| Taille render_manager.py | ≤ 600 LOC (vs 871 actuels) | Après refactor |

---

## 3. Contraintes

| Dimension | Contrainte |
|---|---|
| **Interface game.py** | Libre — game.py peut être modifié si nécessaire |
| **Tests** | Les tests cassés par un refactor d'interface sont réécrits dans le même commit |
| **Commits** | Atomiques par fix — chaque fix est indépendant et revertible |
| **Jouabilité** | Le jeu peut être cassé temporairement entre deux commits |
| **Profiling** | Benchmark avant/après obligatoire pour valider chaque optimisation |
| **Périmètre** | render_manager.py + lighting.py + map_manager (pas d'autres fichiers source) |

---

## 4. Problèmes Identifiés et Priorités

### P-HIGH : Allocations per-frame sur le hot-path

| Problème | Fichier | Ligne | Impact estimé |
|---|---|---|---|
| `lighting_manager.create_overlay()` sans cache | render_manager.py | 601 | Fort — appelé chaque frame, crée une Surface SRCALPHA |
| `_build_wading_composite()` crée `pygame.Surface(SRCALPHA)` par sprite | render_manager.py | 764 | Moyen — N sprites par frame |
| Animated tile cache : boucle O(tiles × layers) pour résolution layer membership | render_manager.py | 554-561 | Moyen — croît avec le contenu |

### P-MEDIUM : Logique sous-optimale

| Problème | Fichier | Impact |
|---|---|---|
| `_apply_grass_wading_to_images` itère tous les sprites même si aucun n'est sur de l'herbe | render_manager.py | Faible actuellement, croît avec entités |
| `get_window_positions()` appelé chaque frame (Q : est-ce cachable ?) | render_manager.py | À mesurer |

### P-LOW : Structure

| Problème | Impact |
|---|---|
| render_manager.py à 871 LOC (800 abs. max selon coding standards) | Maintenabilité |
| Méthodes > 50 lignes (ex: `draw_scene`, `_apply_partial_occlusion`) | Lisibilité |

---

## 5. Architecture Direction

### Approche : Fix incrémental, du plus impactant au moins impactant

**Ne pas réécrire** le render manager — le code est bien structuré. **Cibler les hotspots** dans l'ordre de leur impact mesuré.

#### Ordre d'intervention proposé

```
1. [MESURE] Profiler baseline (avant tout changement)
      ↓
2. [FIX] Lighting overlay cache dirty-flag
   → Ne recréer la Surface que si night_alpha ou active_torches changent
      ↓
3. [FIX] Wading composite pool + early-exit
   → Early-exit si aucun sprite n'est sur de l'herbe
   → Pool de surfaces SRCALPHA réutilisées par taille
      ↓
4. [FIX] Animated tile → layer membership pre-computed (dict statique)
   → Précalculé à load-time dans map_manager, plus de boucle O(N×L) par frame
      ↓
5. [MESURE] Profiler après chaque fix — valider le gain
      ↓
6. [REFACTOR] Split render_manager.py si > 600 LOC après les fixes
```

#### Ce qui reste INCHANGÉ

- API `draw_scene()`, `draw_background()`, `draw_foreground()` — contrat stable
- Architecture générale passes 1/2/3 (background → entities → foreground)
- Système de Y-sort (`custom_draw`)
- Cache P-004 (occlusion dirty-flag) — déjà optimal

---

## 6. Exclusions & Boundaries

| Hors périmètre | Raison |
|---|---|
| GPU shaders / GLSL | Nécessite `pygame.opengl` — rupture d'API complète |
| Réécriture de la boucle de jeu principale | Hors scope, risque élevé |
| Systèmes game logic (interaction, inventory, save) | Pas de lien avec le rendu |
| Co-op / multithreading | v2.0, pas v1.0 |
| Migration vers Godot | Décision stratégique séparée |

---

## 7. Risques

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Cache lighting invalide visuellement (tiles lumineuses qui restent allumées) | Moyen | Visible | Dirty-flag strict sur `night_alpha` + liste `active_torches` hashable |
| Wading pool : mauvaise surface réutilisée (artefact visuel) | Faible | Visible | Tests unitaires sur `_build_wading_composite` |
| Animated tile layer mapping cassé (tiles sur mauvaise layer) | Faible | Fort | Tests de régression sur `draw_background` + comparaison visuelle |
| Découpage render_manager.py casse des imports | Moyen | Bloquant | `rg "import.*render_manager"` avant split |

---

## 8. Assumptions Audit (Behavior #2)

| Assumption | Risk | Status |
|---|---|---|
| `create_overlay()` dans lighting.py alloue une Surface chaque frame | High | **ASSUMED** — à confirmer par profiler (step 1) |
| `get_window_positions()` est coûteux | Low | **ASSUMED** — à mesurer |
| Le cache P-004 fonctionne correctement en production | Medium | **VERIFIED** — code visible + tests existants |
| 0 allocation Surface en hot-path est atteignable sans casser les features | Medium | **ASSUMED** — pool pattern standard, risque faible |
| Les tests existants couvrent suffisamment le render pipeline pour détecter des régressions | Medium | **ASSUMED** — à vérifier en SPEC (TDD Gate) |

> **HIGH-risk assumptions non résolues :** 1 (`create_overlay` allocation)
> **Résolution :** Profiler en step 1 — ne pas entrer en SPEC sans ce profil.

---

## Deliverables de ce Sprint

- [ ] `docs/research/render_pipeline_profiler_baseline.md` — mesures avant
- [ ] `game/docs/specs/render-pipeline-optimization.md` — spec technique
- [ ] Fixes atomiques (1 commit par fix) avec profiler avant/après
- [ ] `docs/research/render_pipeline_profiler_after.md` — mesures après
