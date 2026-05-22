# Spec Technique — Occlusion Partielle des Sprites [Implementation]

> Document Type: Implementation
> Covers: F1, F2, F3, F4, F5 (partial-occlusion-blueprint.md Q6)
> Créé: 2026-05-22
> ADR: docs/ADRs/ADR-007-partial-occlusion-surface-composite.md

---

## 1. Problème & Objectif

**Comportement actuel (incorrect) :**
Quand un sprite (NPC ou player) passe derrière un tile foreground (`depth > player.depth`),
`draw_scene()` applique `sprite.image.set_alpha(OCCLUSION_ALPHA)` globalement — tout le sprite
devient semi-transparent, même la partie qui n'est pas derrière le tile.

**Comportement cible :**
Seule la zone du sprite qui intersecte physiquement un tile occludant est rendue en alpha.
Le reste reste opaque. La logique est générique : player + NPCs + toute entité du pass 3b.

### Schéma visuel

```
Sprite NPC 32×48px        Tile occludant 32×32px (à y=Sy+16)
┌──────────┐              ┌──────────┐
│          │  tête opaque │          │
│  TÊTE    │              │          │
├──────────┼──────────────┤  TILE    │
│  PIEDS   │ ← alpha ici  │ depth>1  │
└──────────┘              └──────────┘
```

La surface composite finale :
- Zone **hors intersection** : pixels originaux (opaque)
- Zone **dans l'intersection** : pixels originaux avec alpha = OCCLUSION_ALPHA

---

## 2. Composants modifiés

| Module | Fichier | Modification |
|--------|---------|-------------|
| `RenderManager` | `src/engine/render_manager.py` | `draw_foreground()` → retourne `list[pygame.Rect]` ; `draw_scene()` → logique occlusion partielle générique |
| `CameraGroup` | `src/entities/groups.py` | **Inchangé** — reste générique |

**Suppression :**
- Le bloc `is_occluded / player.image.set_alpha() / restore` dans `draw_scene()` disparaît
- Remplacé par la logique générique de blit partiel

---

## 3. Spec : `draw_foreground()` — Collecte des rects occludants (F1)

### 3.1 Signature

```python
def draw_foreground(self) -> list[tuple[pygame.Rect, int]]:
```

**Retourne** : liste de tuples contenant les screen-space rects et leur profondeur pour les tiles actifs avec `depth > player.depth`.
Liste vide si aucun tile occludant visible. Évalue à `False` si vide (rétrocompat partielle).

### 3.2 Collecte des rects — boucle principale modifiée

La méthode collecte les rects occludants pour **deux sources**.
Voici le corps complet de la boucle principale (Source A) avec les lignes ajoutées et supprimées :

```python
occluding_rects = []  # ← NOUVEAU (remplace player_occluded = False)

for px, py, tile_id, depth in self.game.map_manager.get_visible_chunks(
    self._viewport_world, min_depth=player_depth
):
    tile_data = tiles[tile_id]
    screen_pos = (px + cam_offset.x, py + cam_offset.y)

    # ← NOUVEAU : collecter le rect pour TOUS les tiles depth > player,
    #   pas seulement ceux qui chevauchent le player.
    #   Les NPCs peuvent être derrière un tile que le player ne touche pas.
    if depth > player_depth:
        occluding_rects.append((
            pygame.Rect(screen_pos, (self.game.tile_size, self.game.tile_size)),
            depth
        ))

    # Logique de rendu des tiles — INCHANGÉE
    if not walk_active and depth > player_depth:
        self._tile_rect.topleft = screen_pos
        if player_screen_rect.colliderect(self._tile_rect):
            screen.blit(tile_data.occluded_image or tile_data.image, screen_pos)
            # ← SUPPRIMÉ : player_occluded = True (l'ancien bool n'existe plus)
        else:
            normal_blits.append((tile_data.image, screen_pos))
    else:
        normal_blits.append((tile_data.image, screen_pos))
```

**Lignes à supprimer de l'ancien code :**
- L65 : `player_occluded = False` → remplacer par `occluding_rects = []`
- L99 : `player_occluded = True` → supprimer (plus de bool)
- L120 : `return player_occluded` → remplacer par `return occluding_rects`

#### Source B — Tiles animés

Après les tiles statiques, scanner `get_visible_animated_chunks(self._viewport_world)` :

```python
for px, py, tile_id, depth in self.game.map_manager.get_visible_animated_chunks(
    self._viewport_world
):
    if depth > player_depth:
        screen_pos = (px + cam_offset.x, py + cam_offset.y)
        occluding_rects.append((pygame.Rect(screen_pos, (self.game.tile_size, self.game.tile_size)), depth))
```

> **Note :** Aujourd'hui aucun tile animé n'a `depth > 1`. Cette branche est inerte
> mais sera activée automatiquement quand des tiles animés foreground seront créés.

### 3.3 Valeur de retour

```python
return occluding_rects  # list[tuple[pygame.Rect, int]], screen-space coords & depth
```

Le booléen `player_occluded` (ancienne valeur de retour) est **supprimé**.

---

## 4. Spec : `draw_scene()` — Blit partiel générique (F2, F3, F4)

### 4.1 Pipeline modifié

```
Avant :
    is_occluded = draw_foreground()           # → bool
    if is_occluded: player.image.set_alpha()  # alpha global player uniquement
    custom_draw(min_depth=player.depth)
    if is_occluded: restore player alpha

Après :
    occluding_rects = draw_foreground()       # → list[tuple[pygame.Rect, int]]
    # Occlusion partielle (swap-and-restore)
    saved_images = {}
    if not walk_active:
        saved_images = _apply_partial_occlusion(occluding_rects)

    custom_draw(min_depth=player.depth)       # rendu trié en profondeur avec les composites

    # Restauration immédiate après le rendu
    for sprite, original_image in saved_images.items():
        sprite.image = original_image
```

### 4.2 `_apply_partial_occlusion(occluding_rects)`

Méthode privée de `RenderManager`. Appelée **avant** `custom_draw(min_depth=player.depth)`.

**Principe :** Pour chaque sprite qui intersecte au moins un rect occludant, générer une surface composite temporaire où seule la zone occludée est en alpha, et remplacer temporairement `sprite.image` par celle-ci. Retourne un dictionnaire pour restaurer les images originales après le rendu.

```python
def _apply_partial_occlusion(self, occluding_rects: list[tuple[pygame.Rect, int]]) -> dict[pygame.sprite.Sprite, pygame.Surface]:
    if not occluding_rects:
        return {}

    cam_offset = self.game.visible_sprites.offset
    saved_images = {}

    player_depth = self.game.player.depth
    for sprite in self.game.visible_sprites.get_sorted_sprites():
        if not sprite.image or not sprite.rect:
            continue
        # Seuls les sprites rendus en Pass 3b (depth >= player.depth) sont concernés
        if getattr(sprite, "depth", 1) < player_depth:
            continue

        # Construire le visual_rect screen-space (même calcul que custom_draw)
        visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
        sprite_screen_rect = pygame.Rect(
            (visual_rect.left + cam_offset.x, visual_rect.top + cam_offset.y),
            visual_rect.size,
        )

        # Collecter les intersections avec les tiles occludants stricement au-dessus du sprite
        sprite_depth = getattr(sprite, "depth", 1)
        intersections = [
            sprite_screen_rect.clip(occ_rect)
            for occ_rect, tile_depth in occluding_rects
            if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
        ]
        if not intersections:
            continue  # Sprite pas occludé → skip

        # Construire la surface composite
        composite = pygame.Surface(visual_rect.size, pygame.SRCALPHA)
        composite.blit(sprite.image, (0, 0))  # copie opaque complète

        # Peindre les zones occludées en alpha
        for isect in intersections:
            # Rect.clip() peut retourner un rect de taille 0 (tiles adjacents)
            if isect.width <= 0 or isect.height <= 0:
                continue
            # isect est en screen-space → convertir en coords locales à la composite
            local_rect = pygame.Rect(
                isect.x - sprite_screen_rect.x,
                isect.y - sprite_screen_rect.y,
                isect.width,
                isect.height,
            )
            # Vider la zone cible pour éviter le blend opaque → transparent
            composite.fill((0, 0, 0, 0), local_rect)
            
            # Blit de la zone source avec alpha
            alpha_surface = pygame.Surface(local_rect.size, pygame.SRCALPHA)
            alpha_surface.blit(sprite.image, (0, 0), local_rect)
            alpha_surface.set_alpha(Settings.OCCLUSION_ALPHA)
            composite.blit(alpha_surface, local_rect.topleft)

        # Sauvegarder l'image originale et appliquer la composite temporaire
        saved_images[sprite] = sprite.image
        sprite.image = composite

    return saved_images
```

### 4.3 Contraintes d'implémentation critiques

| Contrainte | Raison |
|---|---|
| `sprite.image.get_size()` lu dynamiquement à chaque appel | Frames de taille variable à prévoir (Gap #3) |
| Surface composite `SRCALPHA` allouée par sprite occludé par frame | Taille max 32×48px — négligeable en mémoire |
| `visual_rect` calculé avec `bottomright=sprite.rect.bottomright` | Identique à `custom_draw` — cohérence obligatoire (sinon décalage visuel) |
| Remplacement temporaire avant `custom_draw` | Permet à Pygame de rendre les sprites dans l'ordre de tri de profondeur parfait |
| `cam_offset` utilisé de la même façon que dans `custom_draw` | Cohérence du repère screen-space |
| Nettoyage avec `fill((0, 0, 0, 0), local_rect)` avant le blit alpha | Indispensable : Pygame conserve la destination opaque si on ne la vide pas en premier |

### 4.4 Suppression du code player alpha global

**Ce bloc doit être supprimé de `draw_scene()`** :

```python
# ❌ SUPPRIMER — remplacé par swap-and-restore
walk_active = getattr(self.game, "_intra_walk_target", None) is not None
original_alpha = None
if not walk_active and is_occluded and self.game.player.image:
    original_alpha = self.game.player.image.get_alpha()
    if original_alpha is None:
        original_alpha = 255
    self.game.player.image.set_alpha(Settings.OCCLUSION_ALPHA)

self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

if original_alpha is not None and self.game.player.image:
    self.game.player.image.set_alpha(original_alpha)
```

**Remplacé par :**

```python
walk_active = getattr(self.game, "_intra_walk_target", None) is not None
saved_images = {}
if not walk_active:
    saved_images = self._apply_partial_occlusion(occluding_rects)

self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

# Restauration immédiate des images originales des sprites
for sprite, original_image in saved_images.items():
    sprite.image = original_image
```

### 4.5 Cas du scripted walk (`_intra_walk_target`)

Pendant un scripted walk, le player est invisible (`_player_transparent`).
`_apply_partial_occlusion` **ne doit pas être appelé** dans ce cas (UT-013 inchangé).

La garde `walk_active` reste en place :

```python
walk_active = getattr(self.game, "_intra_walk_target", None) is not None
occluding_rects = self.draw_foreground()
...
saved_images = {}
if not walk_active:
    saved_images = self._apply_partial_occlusion(occluding_rects)

self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

for sprite, original_image in saved_images.items():
    sprite.image = original_image
```

---

## 5. Contraintes

| Tier | Exemples |
|------|----------|
| **Always do** | Utiliser `sprite.image.get_size()` dynamiquement (pas de cache de taille) ; préserver le guard `walk_active` ; utiliser `pygame.Rect.clip()` pour les intersections |
| **Ask first** | Changer la signature publique de `draw_foreground()` au-delà de `list[tuple[pygame.Rect, int]]` ; toucher `CameraGroup.custom_draw()` |
| **Never do** | Appliquer `set_alpha()` directement sur `sprite.image` (mutation partagée) ; Oublier de filtrer `tile_depth > sprite_depth` |

---

## 6. Cross-Spec Contracts

### Produces

| Identifiant | Format | Consommateurs |
|---|---|---|
| `RenderManager.draw_foreground()` → `list[tuple[pygame.Rect, int]]` | Python list de tuples (pygame.Rect screen-space, depth) | `draw_scene()` de ce même module |

### Consumes

| Identifiant | Format | Producteur |
|---|---|---|
| `MapManager.get_visible_chunks(min_depth)` | Iterator[(px, py, tile_id, depth)] | `src/map/manager.py` § `get_visible_chunks` |
| `MapManager.get_visible_animated_chunks(viewport)` | Iterator[(px, py, tile_id, depth)] | `src/map/manager.py` § `get_visible_animated_chunks` |
| `CameraGroup.get_sorted_sprites()` | list[Sprite] | `src/entities/groups.py` § `get_sorted_sprites` |
| `Settings.OCCLUSION_ALPHA` | int (0–255) | `src/config.py` |

### Public Interface

| Type | Identifiant | Changement |
|---|---|---|
| Méthode Python | `RenderManager.draw_foreground() -> list[tuple[pygame.Rect, int]]` | Signature change : `bool` → `list[tuple[pygame.Rect, int]]` |
| Méthode Python (new) | `RenderManager._apply_partial_occlusion(occluding_rects)` | Nouvelle méthode privée |

### External Invocations

| Type | Invoqué | Défini dans |
|---|---|---|
| `pygame.Surface(size, SRCALPHA)` | Création surface composite | pygame-ce API |
| `pygame.Rect.clip(other)` | Intersection de rects | pygame-ce API |

### Tracked Concepts

| Concept | Statut dans cette spec | Mentionné dans |
|---|---|---|
| `player_occluded` (ancien bool) | **Supprimé** | `camera-rendering.md` § 4.3 — à mettre à jour |
| `draw_foreground()` return type | `bool` → `list[tuple[pygame.Rect, int]]` | `intra-map-teleport.md` § 4.6 L283 — à mettre à jour (`False` → `[]`) |
| `OCCLUSION_ALPHA` | Réutilisé (même valeur) | `camera-rendering.md`, `config.py` |
| `_intra_walk_target` guard | Préservé | `intra-map-teleport.md` § 4.4 |

---

## 7. Anti-Patterns (DO NOT)

| ❌ Ne pas faire | ✅ Faire à la place | Pourquoi |
|---|---|---|
| `sprite.image.set_alpha(OCCLUSION_ALPHA)` directement | Créer une surface composite SRCALPHA | `set_alpha` modifie la surface partagée entre frames — persiste et corrompt les frames suivantes |
| Cacher la taille du sprite (ex. `self._sprite_size`) | `sprite.image.get_size()` dynamiquement | Les frames peuvent avoir des tailles différentes dans le futur (Gap #3) |
| Calculer `visual_rect` différemment de `custom_draw` | Utiliser exactement `get_rect(bottomright=sprite.rect.bottomright)` | Incohérence = décalage visuel entre le sprite rendu et la zone composite |
| Appeler `_apply_partial_occlusion` pendant un scripted walk | Vérifier `walk_active` avant l'appel | Le player est invisible → redessiner sa zone produit un artefact alpha visible |
| Itérer tous les sprites pour tous les rects (O(sprites × rects)) | Filtrer d'abord par `colliderect` | Sur une map dense, ça peut être coûteux ; le filtre `colliderect` élimine 95%+ des cas |
| Retourner `bool` de `draw_foreground()` | Retourner `list[tuple[pygame.Rect, int]]` | `bool` ne suffit pas — il faut les rects et leur profondeur pour positionner l'occlusion correctement |
| Faire un second scan des tiles dans `_apply_partial_occlusion` | Réutiliser les rects collectés dans `draw_foreground()` | Double scan = work dupliqué ; les rects sont déjà calculés |
| Ignorer la profondeur (depth) dans `_apply_partial_occlusion` | Vérifier `tile_depth > sprite.depth` | Un tile ne doit pas occlure un sprite qui est à la même profondeur ou au-dessus de lui |
| Inclure la zone de l'intersection en coords monde dans `occluding_rects` | Stocker en **screen-space** (après `+ cam_offset`) | Le blit final est en screen-space ; une conversion monde→écran dans le hot path = overhead inutile |

---

## 8. Test Case Specifications

### Tests unitaires

| Test ID | Composant | Input | Résultat attendu |
|---|---|---|---|
| UT-001 | `draw_foreground()` | Aucun tile depth > 1 visible | Retourne `[]` (liste vide) |
| UT-002 | `draw_foreground()` | 1 tile depth 2 visible, overlappant player rect | Retourne liste avec 1 tuple (Rect, depth) |
| UT-003 | `draw_foreground()` | Tile animé depth 2 visible | Tuple du tile animé dans la liste |
| UT-004 | `draw_foreground()` | Tile depth 2 mais `walk_active=True` | Liste retournée (collecte inchangée), mais appelant ne passe pas à `_apply_partial_occlusion` |
| UT-005 | `_apply_partial_occlusion` | `occluding_rects=[]` | Retour immédiat, aucun blit supplémentaire |
| UT-006 | `_apply_partial_occlusion` | Sprite hors intersection de tous les rects | Sprite non retraité (skip) |
| UT-007 | `_apply_partial_occlusion` | Sprite avec intersection partielle (moitié basse) | Surface composite blittée : moitié haute opaque, moitié basse alpha |
| UT-008 | `_apply_partial_occlusion` | Sprite (depth=1) entièrement dans le rect occludant (depth=2) | Composite entier en alpha |
| UT-009 | `_apply_partial_occlusion` | Sprite avec 2 tiles occludants qui se chevauchent | Les deux intersections appliquées, zones non-chevauchantes correctes |
| UT-010 | `_apply_partial_occlusion` | Sprite (depth=2) intersectant rect occludant (depth=2) | Sprite non retraité (skip, tile_depth n'est pas strictement supérieur) |
| UT-011 | `draw_scene()` | `walk_active=True`, tiles occludants présents | `_apply_partial_occlusion` non appelé |

### Tests d'intégration

| Test ID | Flow | Setup | Vérification |
|---|---|---|---|
| IT-001 | Player sous tile depth 2 | Map mock avec tile depth 2 au-dessus du player rect | `draw_foreground()` retourne liste non vide ; `_apply_partial_occlusion` appelé |
| IT-002 | NPC semi-occludé | NPC sprite 32×48, tile occludant sur la moitié basse | Surface composite différente de l'image originale sur la zone occludée |
| IT-003 | Rétrocompat scripted walk | `_intra_walk_target` actif | `_apply_partial_occlusion` non appelé — UT-013 préservé |
| IT-004 | Anciens tests TC-OCC-001/002 | Adapter les tests existants | `draw_foreground()` retourne `list` non vide au lieu de `True` |

### Tests de non-régression (existants à adapter)

| Fonction test existante | Fichier | Adaptation requise |
|---|---|---|
| `test_render_manager_draw_foreground_occlusion` (L119-120) | `tests/engine/test_render_manager.py` | `assert is_occluded is True` → `assert isinstance(is_occluded, list) and len(is_occluded) > 0 and isinstance(is_occluded[0], tuple)` |
| `test_render_manager_draw_foreground_occlusion` (L124-125) | `tests/engine/test_render_manager.py` | `assert is_occluded is False` → `assert is_occluded == []` |
| `test_render_manager_draw_scene_occlusion` | `tests/engine/test_render_manager.py` | `patch.object(rm, 'draw_foreground', return_value=True)` → `return_value=[(pygame.Rect(0,0,32,32), 2)]` ; adapter assertions pour composite swap-and-restore |

---

## 9. Error Handling Matrix

| Erreur | Détection | Réponse | Fallback |
|---|---|---|---|
| `sprite.image` est `None` lors de `_apply_partial_occlusion` | Guard `if not sprite.image` | Skip ce sprite | Aucun blit corrompu |
| `sprite.rect` est `None` | Guard `if not sprite.rect` | Skip ce sprite | Idem |
| Intersection produit un Rect de taille 0 (`clip()` hors bounds) | `pygame.Rect.clip()` retourne Rect(0,0,0,0) | Vérifier `if isect.width > 0 and isect.height > 0` avant blit | Skip silencieux — pas d'erreur |
| `pygame.Surface()` fails (mémoire) | `pygame.error` | Non attrapé — erreur fatale attendue (hors RAM) | — |
| `get_sorted_sprites()` retourne liste vide | `for sprite in []` | Boucle vide, aucun effet | Aucun |

---

## 10. Bundling & Native-Module Audit

- **BM1** : N/A — Python pur, pas de bundler client/serveur
- **BM2** : N/A — idem
- **BM3** : N/A — aucun module natif introduit
- **BM4** : N/A — aucun renommage de constante (OCCLUSION_ALPHA reste identique)

---

## 11. Assumptions

| # | Hypothèse | Risque | Validation |
|---|---|---|---|
| 1 | `visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)` est identique dans `custom_draw` et `_apply_partial_occlusion` | Low | Code review — même formule |
| 2 | `Settings.OCCLUSION_ALPHA` est la valeur correcte pour les NPCs (même que le player) | Low | Décision design confirmée — même expérience visuelle pour tous |
| 3 | Les tiles foreground sont tous de taille `TILE_SIZE × TILE_SIZE` (32×32) | Low | Constraint du moteur — `tile_size` issu de `self.game.tile_size` |
| 4 | Max 2-3 NPCs occludés simultanément → pas de problème perf | Medium | À vérifier en jeu si map dense |
| 5 | Tiles animés avec `depth > 1` n'existent pas encore — la branche est inerte jusqu'à création | Low | Confirmé par user en STRATEGY |

---

## 12. Deep Links

- **`RenderManager`** : [render_manager.py L6](../../src/engine/render_manager.py#L6)
- **`draw_foreground()` (actuel)** : [render_manager.py L54](../../src/engine/render_manager.py#L54)
- **`draw_scene()` (actuel)** : [render_manager.py L128](../../src/engine/render_manager.py#L128)
- **`CameraGroup.custom_draw()`** : [groups.py L91](../../src/entities/groups.py#L91)
- **`CameraGroup.get_sorted_sprites()`** : [groups.py L76](../../src/entities/groups.py#L76)
- **`MapManager.get_visible_chunks()`** : [manager.py L152](../../src/map/manager.py#L152)
- **`MapManager.get_visible_animated_chunks()`** : [manager.py L202](../../src/map/manager.py#L202)
- **`Settings.OCCLUSION_ALPHA`** : [config.py L136](../../src/config.py#L136)
- **Spec rendu actuelle** : [camera-rendering.md §4.3](./camera-rendering.md#L124)
- **ADR décision** : [ADR-007](../ADRs/ADR-007-partial-occlusion-surface-composite.md#L1)
- **Blueprint stratégique** : [partial-occlusion-blueprint.md](../strategic/partial-occlusion-blueprint.md#L1)
- **Tests render** : [test_render_manager.py](../../tests/engine/test_render_manager.py#L1)
- **Tests render order** : [test_render_order.py](../../tests/engine/test_render_order.py#L1)
