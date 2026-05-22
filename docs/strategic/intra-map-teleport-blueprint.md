# Strategic Blueprint — Intra-Map Teleport + Walk Camera Transition

> Version 1.0 · 2026-05-22 · Status: STRATEGY

---

## 1. Problème exact à résoudre

**Persona :** Le joueur entre dans un château. La porte est une zone `Teleport` Tiled.  
**Problème actuel :** `target_map == _current_map_name` → `transition_map()` → `_load_map()` → toute la carte est détruite et rechargée : entités vidées, spawn repositionné, fade optionnel. Résultat : flash blanc/noir, perte de contexte, et la même carte repart de zéro.  
**Problème secondaire :** Aucun `transition_type` ne fait suivre la caméra pendant que le joueur MARCHE de la zone source à la zone destination. Le seul option fluide est `"fade"` (fondu noir), qui cache le déplacement.

**Outcome attendu :**
- Téléport intra-carte : zéro rechargement, zéro flash, entités préservées.
- `transition_type = "walk"` : le joueur se déplace automatiquement en ligne droite de A→B, la caméra suit en temps réel, le tout visible à l'écran.

---

## 2. Métriques de succès

| Critère | Mesure |
|---------|--------|
| Zéro rechargement de carte | `_load_map()` n'est pas appelé pour `target_map == _current_map_name` |
| Entités préservées | Les sprites restent dans leurs groupes après le téléport |
| Transition fluide | 60 FPS maintenus pendant le `"walk"` (profiler confirme < 8ms/frame) |
| Caméra suit le joueur | `visible_sprites.offset` mis à jour à chaque frame du walk |
| Intégration Tiled | Aucune nouvelle propriété Tiled requise (réutilise `target_map`, `target_spawn_id`, `transition_type`) |

---

## 3. Avantage architectural

Le système existant est déjà proche de la solution :
- `Teleport` stocke `target_map`, `target_spawn_id`, `transition_type` → aucune nouvelle propriété.
- `CameraGroup.calculate_offset()` suit le joueur à chaque frame → si le joueur marche vers la destination, la caméra suit naturellement.
- `_position_player()` dans `MapLoader` est déjà isolée → réutilisable sans `_load_map()`.
- `WorldState` + `_save_interactive_states()` protègent les états (A-ML-001) → pas de risque de perte.

---

## 4. Décision architecturale principale

### Q4 : Mécanisme de déplacement pour `"walk"` — Lerp vs Pathfinding vs Input simulé

Trois options :

| Option | Mécanisme | Pro | Con |
|--------|-----------|-----|-----|
| **A — Lerp direct** | Tweening pos A→B en N frames | Simple, prévisible, 0 risque collision | Ignore le système de collision (mais c'est voulu — le téléport a autorité) |
| **B — Inputs simulés** | Push `player.direction` vers la cible | Réutilise le player.input() | Difficile à terminer précisément, drift possible |
| **C — Pathfinding** | Calcul de chemin tile-by-tile | Respecte les obstacles | Complexité disproportionnée pour un couloir droit |

**DÉCISION : Option A — Lerp direct dans `game.py`.**

Rationale :
1. Un téléport de type "entrée dans un bâtiment" est toujours une trajectoire DROITE (couloir, porte).
2. Le joueur n'a pas besoin de contourner des obstacles — le téléport override la physique.
3. Lerp = 10 lignes dans `game.py`, pas de dépendances nouvelles.
4. La durée est configurable : `INTRA_WALK_SPEED = 4` tiles/seconde par défaut.
5. Cohérent avec `L-ARCH-005` : pas de Manager/Factory pour ce qui est résolvable en une fonction.

**Conséquences :**
- Pendant le walk, `player.input()` est suspendu (le mouvement est scripté).
- Les collisions ne s'appliquent pas (le téléport a autorité sur le chemin).
- La caméra suit via `calculate_offset()` normal — aucune modification de `CameraGroup`.

---

## 5. Stack technique & rationale

| Composant | Technologie | Rationale |
|-----------|-------------|-----------|
| Détection intra-carte | `interaction.py` | C'est là que `check_teleporters()` vit déjà |
| Walk controller | `game.py` méthode `intra_map_teleport()` | Pattern L-ARCH-008 : context injection `game: Any` |
| Résolution spawn | `map_loader.py` méthode `resolve_spawn_by_id()` | MapLoader possède la connaissance du spawn |
| Déplacement | Lerp direct sur `player.pos` + `player.rect` | Pas de dépendance sur player.input() |
| Caméra | `CameraGroup.calculate_offset()` existant | Aucun changement requis |
| Tiled | Propriétés existantes (`target_map`, `target_spawn_id`, `transition_type="walk"`) | Zéro nouvelle propriété |

---

## 6. Features — ordonnées par dépendance

### Feature 1 : Détection intra-carte dans `check_teleporters()`
`interaction.py` — branchement : même carte → `game.intra_map_teleport()`, carte différente → `game.transition_map()` (inchangé).

### Feature 2 : `MapLoader.resolve_spawn_by_id()` 
`map_loader.py` — lit les entités spawn depuis `self.game.map_manager` (en mémoire) pour trouver les coordonnées pixel du `target_spawn_id`.

> ⚠️ **Gap G1** : `map_manager` en mémoire expose-t-il les entités spawn ? Vérifier si `TmjParser` stocke les entités ou seulement les tiles.

### Feature 3 : `game.intra_map_teleport(target_spawn_id, transition_type)`
`game.py` — dispatcher :
- `"instant"` → appelle `_map_loader._position_player(spawn_pos)` directement.
- `"walk"` → démarre une boucle de lerp frame-by-frame.

### Feature 4 : Walk loop dans `_update_core_state()`
`game.py` — état `_intra_walk_active` : si actif, déplace `player.pos` d'un pas vers `_walk_target` chaque frame, calcule l'orientation du joueur selon la direction du walk.

### Feature 5 : Tests
- TC-01 : Téléport intra-carte `"instant"` → repositionne sans rechargement.
- TC-02 : Téléport intra-carte `"walk"` → démarre la boucle walk.
- TC-03 : Walk termine → `_intra_walk_active = False`, position = target.
- TC-04 : Téléport cross-carte → `transition_map()` appelé (régression).

---

## 7. Ce qu'on NE construit PAS

| Exclusion | Rationale |
|-----------|-----------|
| ❌ Pathfinding A* pour le walk | Disproportionné — les couloirs de téléport sont droits par design |
| ❌ Nouveau type de propriété Tiled | Les propriétés existantes suffisent |
| ❌ Modification de `CameraGroup` | `calculate_offset()` suit le joueur naturellement |
| ❌ Lerp de caméra (camera tween séparé) | Inutile si le joueur lerpe — la caméra suit |
| ❌ Animation de porte (ouvrir/fermer) | Hors scope — géré par les interactives existants |
| ❌ Multi-step waypoints | Hors scope — toujours ligne droite A→B |

---

## Gap Discovery — ✅ TOUS RÉSOLUS

| # | Gap | Décision |
|---|-----|----------|
| **G1** ✅ | `map_manager` expose-t-il les entités spawn en mémoire ? | OUI — `MapManager._entities` (ligne 16) stocke la liste complète des entités, incluant les spawn points. `resolve_spawn_by_id()` peut chercher directement dans `self.game.map_manager._entities`. |
| **G2** ✅ | Inputs pendant le walk ? | **Complètement bloqués** — ni mouvement, ni inventaire, ni interaction pendant la transition. |
| **G3** ✅ | Durée vs vitesse ? | **Vitesse fixe** = même `px/s` que le joueur normal (`Settings.PLAYER_SPEED`). Distance courte = transition rapide, longue = plus lente. Naturel et cohérent. |
| **G4** ✅ | Orientation pendant le walk ? | **Suit la direction du déplacement automatique** — si le joueur marche vers le haut, `player.current_state = "up"`. L'animation walk joue normalement. |

---

*Tous les gaps sont résolus → prêt pour SPEC.*
