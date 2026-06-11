# Spec — Render Pipeline Optimization

> Document type: Implementation

> **Module:** `game/src/engine/render_manager.py`, `game/src/engine/lighting.py`, `game/src/map/manager.py`
> **Stage:** 📋 SPEC
> **Date:** 2026-06-11
> **Blueprint:** [render_pipeline_blueprint.md](../strategic/render_pipeline_blueprint.md#L1)
> **Covers:** All hotspots identified in blueprint §4
> **Related specs:** [performance-system.md](./performance-system.md#L1) · [p001-foreground-rendering.md](./p001-foreground-rendering.md#L1) · [lighting-system.md](./lighting-system.md#L1) · [map-world-system.md](./map-world-system.md#L1) · [camera-rendering.md](./camera-rendering.md#L1)

---

## Blueprint Coverage Matrix

| Hotspot ID | Description | Covered by |
|---|---|---|
| H-001 | `_build_wading_composite` alloue `Surface(SRCALPHA)` par sprite/frame | This spec § H-001 |
| H-002 | `_update_animated_tile_cache` boucle O(tiles × layers) par frame | This spec § H-002 |
| H-003 | `_apply_grass_wading_to_images` itère tous les sprites sans early-exit | This spec § H-003 |
| H-004 | `render_manager.py` à 871 LOC (800 abs. max) | This spec § H-004 |
| ~~H-CANCELLED~~ | ~~`create_overlay()` allocation par frame~~ | **Annulé** — `_overlay_cache` pré-alloué ligne 32 lighting.py, `fill()` réutilise la surface |

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Lancer les tests avant chaque commit ; profiler avant/après chaque fix ; ne toucher que les fichiers dans scope |
| **Ask first** | Changer l'interface publique de `draw_scene`, `draw_background`, `draw_foreground` ; ajouter une dépendance externe |
| **Never do** | Modifier `game.py`, `interaction.py`, ou tout fichier hors scope (render_manager, lighting, map/manager) ; supprimer un test sans le réécrire dans le même commit |

---

## Cross-Spec Contracts

### Produces

| Identifier | Format | Schema | Consumers |
|---|---|---|---|
| `RenderManager.draw_scene()` | appel synchrone | render_manager.py § `draw_scene` | `game.py` ligne ~380 |
| `RenderManager.draw_background()` | appel synchrone | render_manager.py § `draw_background` | `game.py` |
| `RenderManager.draw_foreground()` → `OccludingRect` | `list[tuple[Rect, int, Surface|None]]` | render_manager.py type alias ligne 10 | `game.py` |

### Consumes

| Identifier | Format | Producer |
|---|---|---|
| `MapManager._fg_occlusion_grid` | `dict[(col,row), (depth, img, occ_img)]` | `map/manager.py` § `_build_fg_occlusion_world` |
| `MapManager._fg_occlusion_world` | `list[tuple[wx,wy,depth,img,occ_img]]` | `map/manager.py` § `_build_fg_occlusion_world` |
| `MapManager.get_visible_animated_chunks()` | iterator `(px,py,tile_id,depth)` | `map/manager.py` ligne 361 |
| `LightingManager.create_overlay()` | `pygame.Surface` (réutilisée) | `lighting.py` ligne 74 |

### Public Interface (inchangée après les fixes)

| Method | Signature | Note |
|---|---|---|
| `draw_scene()` | `(self) -> None` | Contrat stable — ne pas modifier |
| `draw_background()` | `(self) -> None` | Contrat stable |
| `draw_foreground()` | `(self) -> OccludingRect` | Contrat stable |
| `reset_occ_cache()` | `(self) -> None` | Contrat stable |

---

## H-001 — Wading Composite Surface Reuse

### Problème

`_build_wading_composite()` (ligne 764 render_manager.py) appelle `pygame.Surface(visual_size, pygame.SRCALPHA)` à chaque invocation. Avec N sprites sur de l'herbe, cela produit N allocations par frame.

### Cause racine confirmée

```python
# render_manager.py ligne 764 — HOT PATH — alloue à chaque frame
composite = pygame.Surface(visual_size, pygame.SRCALPHA)
```

`_wading_surf` est déjà poolé (ligne 784-788), mais `composite` ne l'est pas.

### Solution spécifiée

**Pré-allouer UN composite réutilisable par taille unique (resize-on-demand), analogue au pattern `_wading_surf` existant.**

> ⚠️ **Anti-pattern — NE PAS pooler les composites par `visual_size` dans un dict partagé.**
> Le composite est assigné à `sprite.image` après création. Si deux sprites ont la même `visual_size`,
> un pool keyed par size retournerait la MÊME Surface pour les deux — le `fill()` du sprite B
> détruirait le composite du sprite A (qui est son `.image` actuel). Corruption visuelle garantie.
> Chaque composite doit être UNIQUE par sprite dans un frame donné.

#### Contrat d'implémentation

```python
# Dans __init__, ajouter :
self._wading_composite: pygame.Surface | None = None  # single reusable surface, resize-on-demand

# Dans _build_wading_composite(), remplacer l'allocation par :
if self._wading_composite is None or self._wading_composite.get_size() != visual_size:
    self._wading_composite = pygame.Surface(visual_size, pygame.SRCALPHA)

# IMPORTANT: copier la surface pour chaque sprite — le composite est assigné à sprite.image
# et doit rester intact jusqu'à la restauration post-draw.
composite = self._wading_composite.copy()
composite.fill((0, 0, 0, 0))
composite.blit(sprite.image, (0, 0))
# ... suite identique
```

**Pourquoi `copy()` est nécessaire :** `_apply_grass_wading_to_images` assigne `sprite.image = composite`.
Si on réutilisait la même surface sans copie, le `fill()` du sprite suivant
détruirait l'image du sprite précédent. La copie est ~10× plus rapide que
`pygame.Surface()` car elle évite l'initialisation SRCALPHA du constructeur.

**Note :** Si tous les sprites wading ont la même taille (cas courant),
`_wading_composite` est alloué UNE fois et copié N fois.
Si la taille change, une seule réallocation se produit (resize-on-demand).

**Invalidation lors d'un changement de carte :**

```python
def reset_render_caches(self) -> None:
    """Invalider tous les caches de rendu lors d'un changement de map.

    Appelé par game.py dans transition_map(), après _load_map().
    """
    self._wading_composite = None
    self._occ_key = None
    self._occ_composite_cache.clear()
```

**Point d'intégration obligatoire (AR-002) :**

```python
# Dans game.py, méthode transition_map(), après l'appel à _load_map() :
self.render_manager.reset_render_caches()
```

> ⚠️ `reset_occ_cache()` n'est actuellement appelé NULLE PART dans `game.py`
> ni `map_loader.py`. Les deux caches (occlusion + wading) doivent être invalidés
> via `reset_render_caches()` dans `transition_map()`. Sans cet appel, les
> composites d'occlusion de l'ancienne map persistent sur la nouvelle map.

#### Préconditions

- `_wading_composite` est un template réutilisable — chaque sprite reçoit une `copy()` unique
- Single-threaded : pas de concurrence sur `_wading_composite`
- `fill()` + `blit` sur la copie remet le composite à l'état initial — pas de leak entre frames

#### Postconditions

- 0–1 allocation `Surface()` dans `_build_wading_composite` par session (resize-on-demand)
- N appels `Surface.copy()` par frame (N = sprites sur herbe) — plus rapide que N allocations
- L'image restituée est visuellement identique à l'ancienne implémentation
- Chaque sprite possède sa propre surface composite — pas d'aliasing entre sprites

---

## H-002 — Animated Tile Layer Membership Pre-computed

### Problème

`_update_animated_tile_cache()` (lignes 548-561 render_manager.py) résout le layer d'appartenance d'une tile animée avec une boucle imbriquée O(visible_anim_tiles × N_layers) **à chaque frame**.

```python
# render_manager.py lignes 554-561 — HOT PATH — O(tiles × layers) par frame
for lid in self.game.map_manager.layer_order:
    if lid in self.game.map_manager.layers:
        layer_data = self.game.map_manager.layers[lid]
        if 0 <= row < len(layer_data) and 0 <= col < len(layer_data[row]):
            if layer_data[row][col] == tile_id:
                self._frame_anim_by_layer[lid].append(...)
                break
```

### Cause racine

Le mapping `tile_id → layer_id` est calculable **une seule fois** à l'initialisation de `MapManager` car les tiles animées sont statiquement définies dans le `.tmj`. Il n'existe actuellement aucun cache de ce mapping dans `MapManager`.

### Solution spécifiée

**Pré-calculer `_anim_tile_layer_map: dict[tuple[int,int], int]` dans `MapManager.__init__`.**

#### Contrat d'implémentation — MapManager

```python
# Dans MapManager.__init__, après _build_fg_occlusion_world() :
self._anim_tile_layer_map: dict[tuple[int, int], int] = {}
self._build_anim_tile_layer_map()

def _build_anim_tile_layer_map(self) -> None:
    """Pre-compute (col, row) -> layer_id for all animated tiles.

    Called once at init. Result is immutable — never modify per-frame.
    Anti-pattern: never call this per-frame (O(layers * W * H)).
    """
    for lid in self.layer_order:
        layer_data = self.layers.get(lid)
        if not layer_data:
            continue
        for y, row_data in enumerate(layer_data):
            for x, tile_id in enumerate(row_data):
                if tile_id == 0 or tile_id not in self.tiles:
                    continue
                if self.tiles[tile_id].frames:
                    # setdefault keeps the FIRST layer encountered, matching old 'break' logic
                    self._anim_tile_layer_map.setdefault((x, y), lid)
```

#### Contrat d'implémentation — RenderManager

```python
# Dans _update_animated_tile_cache, remplacer les lignes 554-561 par :
col = px // tile_size
row = py // tile_size
lid = self.game.map_manager._anim_tile_layer_map.get((col, row))
if lid is not None:
    self._frame_anim_by_layer[lid].append((px, py, tile_id, depth))
```

#### Préconditions

- `_anim_tile_layer_map` est construit avant le premier appel à `_update_animated_tile_cache`
- Une tile animée sur plusieurs layers (cas rare mais possible en Tiled) → seul le premier layer scanné est enregistré (comportement identique à l'ancienne boucle avec `break`)
- Le map est rechargé entièrement lors d'une transition → `_anim_tile_layer_map` est reconstruit avec le nouveau `MapManager`

#### Postconditions

- La boucle O(tiles × layers) disparaît du hot-path
- Le hot-path devient O(visible_anim_tiles) — lookups `dict.get()` O(1)
- `_frame_anim_by_layer` reste identique en contenu

---

## H-003 — Early-Exit Grass Wading

### Problème

`_apply_grass_wading_to_images()` itère `get_sorted_sprites()` complet même si aucun sprite n'est sur de l'herbe.

### Solution spécifiée

**Ajouter un early-exit si le joueur n'est pas sur de l'herbe** (le joueur est l'entité la plus susceptible de déclencher le wading ; les NPCs hors de l'herbe sont aussi ignorés).

```python
# Début de _apply_grass_wading_to_images(), avant la boucle for sprite :
# Early-exit: si le joueur n'est pas sur de l'herbe, les NPCs proches
# seront détectés individuellement dans _build_wading_composite via
# get_grass_tile_image_at() — pas de shortcut global possible.
# MAIS on peut éviter l'appel get_sorted_sprites() si map_manager
# ne possède pas de grass grid non-vide.
if not self.game.map_manager:
    return {}
if not any(
    img is not None
    for row in self.game.map_manager._grass_grid
    for img in row
):
    return {}   # Map has no grass tiles at all — skip entirely
```

**Note :** Cette optimisation est conservatrice (vérifie la map, pas la position du joueur) pour ne pas introduire de bug si un NPC est sur de l'herbe sans le joueur.

**Amélioration complémentaire :** Ajouter `_map_has_grass: bool` calculé à l'init de `MapManager` pour éviter de scanner `_grass_grid` chaque frame :

```python
# Dans MapManager.__init__, après _build_grass_grid() :
self._map_has_grass: bool = any(
    img is not None for row in self._grass_grid for img in row
)

def update_grass_state(self) -> None:
    """Doit être appelé si l'herbe est créée/détruite dynamiquement en jeu."""
    self._map_has_grass = any(
        img is not None for row in self._grass_grid for img in row
    )
```

```python
# Dans RenderManager._apply_grass_wading_to_images :
if not self.game.map_manager._map_has_grass:
    return {}
```

---

## H-004 — Split render_manager.py (871 → ≤ 600 LOC)

### Problème

871 LOC dépasse la limite absolue (800 LOC per `coding-standards.md`). H-001/H-002/H-003 ajoutent ~25 lignes de code. Le fichier atteindra ~896 LOC après implémentation.

### Règle de déclenchement

> H-004 est **obligatoire**. Le fichier dépasse déjà la limite absolue de 800 LOC (871 actuellement).
> Les fixes H-001/H-002/H-003 ajoutent du code — le fichier ne descendra pas sous 800 sans extraction.

### Stratégie de découpage

| Nouveau fichier | Contenu extrait | LOC estimés |
|---|---|---|
| `render_manager.py` | draw_scene, draw_background, draw_foreground, draw_hud | ~250 |
| `render_occlusion.py` | `_apply_partial_occlusion`, `_create_composite_occlusion_surface`, `reset_occ_cache` | ~200 |
| `render_wading.py` | `_apply_grass_wading_to_images`, `_build_wading_composite`, `_blit_grass_tile_intersections` | ~180 |

**Contrainte :** Si découpé, les méthodes extraites doivent être **importées** dans `RenderManager` via composition (helper class) ou rester des méthodes de la même classe via mixin — pas de classes indépendantes qui nécessiteraient de modifier `game.py`.

**Décision à prendre avant implémentation H-004 :** mixin ou module functions ? → **Ask first** (tiers 2).

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | **Allouer `pygame.Surface()` dans un hot-path** | `pygame.Surface(size, SRCALPHA)` dans une boucle per-frame → GC pressure à 60 FPS | Pré-allouer un template réutilisable (resize-on-demand), copier via `Surface.copy()` |
| 2 | **Mapping statique calculé dans la boucle de rendu** | Boucle O(tiles × layers) dans `_update_animated_tile_cache` à chaque frame | Pré-calculer `_anim_tile_layer_map` dans `MapManager.__init__` — données de map immuables après chargement |
| 3 | **Invalider les caches de rendu par frame** | Appeler `reset_render_caches()` dans `draw_scene()` ou à chaque update | Appeler uniquement lors d'un changement de map via `transition_map()` |
| 4 | **Modifier `sprite.image` sans restauration garantie** | Swap image sans `try/finally` ou sans `saved_images` restore | Utiliser le pattern `saved_images` existant — restauration systématique après `custom_draw` |
| 5 | **Scanner `_grass_grid` O(W×H) dans le hot-path** | `any(img for row in _grass_grid for img in row)` appelé chaque frame | Utiliser `_map_has_grass: bool` précalculé à init — O(1) |
| 6 | **Changer la signature des méthodes publiques sans approbation** | Modifier `draw_scene()`, `draw_background()`, `draw_foreground()` | Ces méthodes sont le contrat public avec `game.py` — tier 2 `Ask first` |
| 7 | **Exposer `_anim_tile_layer_map` hors de `_update_animated_tile_cache`** | Accès direct depuis un autre module | Si besoin externe, déclarer une propriété publique `anim_tile_layer_map` |
| 8 | **Pooler des composites par `visual_size` dans un dict partagé** | Deux sprites avec la même taille partagent la MÊME Surface — `fill()` du sprite B détruit le composite du sprite A | Chaque sprite reçoit sa propre copie via `Surface.copy()` — pas d'aliasing intra-frame |
| 9 | **Omettre `fill()` avant de réutiliser un composite** | Réutiliser sans reset → pixels du frame précédent persistent | `composite.fill((0,0,0,0))` puis `blit(sprite.image, (0,0))` — obligatoire dans cet ordre |

---

## Test Case Specifications

> ID mapping: `TC-RPERF-U-NNN` = unit, `TC-RPERF-I-NNN` = integration.
> Aliases: TC-001=TC-RPERF-U-001, TC-002=TC-RPERF-U-002, TC-003=TC-RPERF-U-003, TC-004=TC-RPERF-U-004, TC-005=TC-RPERF-U-005, IT-001=TC-RPERF-I-001, IT-002=TC-RPERF-I-002, IT-003=TC-RPERF-I-003

### H-001 — Wading Composite Reuse

| ID | Type | Description | Given | When | Then |
|---|---|---|---|---|---|
| TC-RPERF-U-001 | Unit | Template réalloué seulement si taille change | sprite 32×48 sur herbe | `_build_wading_composite` appelé 2× avec même size | `_wading_composite` alloué 1× ; resize-on-demand |
| TC-RPERF-U-002 | Unit | Chaque sprite reçoit sa propre copie | 2 sprites 32×48 tous deux sur herbe | `_build_wading_composite` appelé pour chaque | `id(composite_A) != id(composite_B)` — pas d'aliasing |
| TC-RPERF-U-003 | Unit | `fill()` précède le blit sur la copie | sprite avec image rouge | composite copié frame suivante | Aucun pixel du frame précédent visible (composite entièrement opaque en zone non-herbe) |
| TC-RPERF-U-004 | Unit | `reset_render_caches()` invalide le template | `_wading_composite` non-None | `reset_render_caches()` appelé | `_wading_composite is None` et `_occ_composite_cache == {}` |
| TC-RPERF-U-005 | Unit | Template inchangé si sprite hors herbe | sprite hors herbe | `_build_wading_composite` retourne None | `_wading_composite` inchangé (pas de réallocation) |
| TC-RPERF-I-001 | Integration | Résultat visuel identique avant/après optimisation | scène avec herbe et sprite dessus | `draw_scene()` appelé 3 frames | `composite.get_at((cx,cy))` identique avec et sans optimisation |
| TC-RPERF-I-002 | Integration | `reset_render_caches()` appelé à la transition de map | transition map A → map B | `draw_scene()` appelé sur map B | Pas d'artefact visuel de map A dans le wading |
| TC-RPERF-I-004 | Integration | 2 sprites même taille sur herbe dans le même frame | 2 sprites 32×48 marchant sur herbe | `draw_scene()` appelé | Les DEUX sprites affichent le wading correctement — pas de corruption visuelle |

### H-002 — Animated Tile Layer Map

| ID | Type | Description | Given | When | Then |
|---|---|---|---|---|---|
| TC-RPERF-U-006 | Unit | `_build_anim_tile_layer_map` popule le dict | map avec tile animée (id=1001) en layer 7, col=2, row=3 | `MapManager.__init__` | `_anim_tile_layer_map[(2,3)] == 7` |
| TC-RPERF-U-007 | Unit | Tile non-animée absente du map | map avec tile statique (id=50) | `MapManager.__init__` | `(x,y)` de la tile statique absent de `_anim_tile_layer_map` |
| TC-RPERF-U-008 | Unit | `_update_animated_tile_cache` utilise le map | `_anim_tile_layer_map[(2,3)] == 7` | `_update_animated_tile_cache` appelé | `_frame_anim_by_layer[7]` contient la tile à (64, 96) |
| TC-RPERF-U-009 | Unit | Tile animée inconnue ignorée sans crash | `_anim_tile_layer_map` vide, tile animée visible | `_update_animated_tile_cache` appelé | `_frame_anim_by_layer` reste vide — pas d'exception |
| TC-RPERF-U-010 | Unit | Résultat identique à l'ancienne boucle | map avec 3 tiles animées sur layers différents | Ancienne impl vs nouvelle impl | `_frame_anim_by_layer` identique dans les deux cas |
| TC-RPERF-I-003 | Integration | Tiles animées visibles avec le nouveau hot-path | map avec tile animée, anim_map_manager mock | `draw_background()` appelé | `fblits` appelé avec les tiles animées attendues |

### H-003 — Early-Exit Grass

| ID | Type | Description | Given | When | Then |
|---|---|---|---|---|---|
| TC-RPERF-U-011 | Unit | Early-exit si map sans herbe | `_map_has_grass = False` | `_apply_grass_wading_to_images()` | Retourne `{}` sans appeler `get_sorted_sprites` |
| TC-RPERF-U-012 | Unit | Pas d'early-exit si map avec herbe | `_map_has_grass = True` | `_apply_grass_wading_to_images()` | `get_sorted_sprites()` appelé normalement |
| TC-RPERF-U-013 | Unit | `_map_has_grass` calculé à init | map avec au moins 1 tile grass | `MapManager.__init__` | `_map_has_grass == True` |
| TC-RPERF-U-014 | Unit | `_map_has_grass` False si aucune grass | map sans tile material=grass | `MapManager.__init__` | `_map_has_grass == False` |

### H-004 — Split (obligatoire)

| ID | Type | Description |
|---|---|---|
| TC-RPERF-U-015 | Unit | `from src.engine.render_manager import RenderManager` fonctionne sans changer les imports de `game.py` |
| TC-RPERF-U-016 | Unit | Tous les tests existants de `test_render_manager.py` passent sans modification de leur import |

---

## Error Handling Matrix

| Situation | Error | Response | Fallback | Classification |
|---|---|---|---|---|
| `MapManager` est `None` dans `_apply_grass_wading_to_images` | `AttributeError` si accès direct | Early-return `{}` avant tout accès | Rendu continue sans wading | VERIFIED — guard ligne 833, [render_manager.py#L833](../../../src/engine/render_manager.py#L833) |
| `_anim_tile_layer_map[(col,row)]` absent | Lookup miss | `dict.get()` → `None`, tile ignorée | Tile animée non assignée à un layer (invisible dans bg/fg) | ASSUMED (Low) — comportement dict standard |
| Wading composite : taille sprite change en cours de jeu | Aucune — resize-on-demand | `_wading_composite` réalloué une seule fois pour la nouvelle taille | N/A | ASSUMED (Low) — resize-on-demand pattern |
| `reset_render_caches()` appelé avec caches vides | Aucune | `None` assignment + `dict.clear()` no-ops | N/A | CITED — Python standard |
| `_build_anim_tile_layer_map` : layer data absent | KeyError si accès direct | `self.layers.get(lid)` → `None`, `continue` | Layer ignoré sans crash | VERIFIED — guard dans spec §H-002 |
| Surface composite réutilisée avec `fill()` oublié | Pixels frame précédent visibles | `fill((0,0,0,0))` obligatoire avant `blit` | N/A — pas de fallback : test TC-RPERF-U-003 détecte la régression | VERIFIED — test case spec §H-001 |
| `_occ_composite_cache` retourne composites stales après transition de map | Occlusion visuelle de l'ancienne map sur la nouvelle | `reset_render_caches()` appelé dans `transition_map()` — invalidation complète | N/A — pas de fallback : test TC-RPERF-I-002 détecte | VERIFIED — spec §H-001 point d'intégration |

---

## Bundling & Native-Module Audit

- BM1: N/A — projet Python pur, pas de bundler JS
- BM2: N/A — pas de CLIENT/SERVER split
- BM3: N/A — aucun module natif introduit
- BM4: N/A — aucun rename de constante dans ce spec

---

## Assumptions

| Assumption | Risk | Source Type | Evidence |
|---|---|---|---|
| `create_overlay()` n'alloue pas de Surface par frame | High | SHOW — verified via `grep` | `grep '_overlay_cache' game/src/engine/lighting.py` → ligne 32 : `self._overlay_cache = pygame.Surface(screen_size, pygame.SRCALPHA)` (init seulement), ligne 88 : `self._overlay_cache.fill(...)` (réutilisation) |
| `get_window_positions()` est déjà mis en cache | Medium | SHOW — verified via `grep` | `grep '_window_cache' game/src/map/manager.py` → lignes 53,403,413,433 : cache initialisé à `None`, testé avant calcul, assigné après |
| Un sprite a une `visual_size` stable pendant une session | Medium | TELL — convention pygame | Les sprites pygame-ce ne changent pas de `image.get_size()` dynamiquement dans ce codebase (pas de resize animé) |
| `_anim_tile_layer_map` ne nécessite pas d'invalidation partielle | Medium | TELL — architecture Tiled | Les tiles animées sont définies dans le `.tmj` et ne sont pas modifiées dynamiquement en jeu |
| Le split H-004 ne nécessite pas de changer les imports de `game.py` | Medium | SHOW — verified via `rg` | `rg 'render_manager' game/src/engine/game.py` → import `from src.engine.render_manager import RenderManager` — interface publique seulement |

---

## Invariant — `_occ_composite_cache` Key Contract (AR-003)

> **Invariant :** `occluding_rects` contient UNIQUEMENT des tiles statiques de foreground
> issues de `_fg_occlusion_grid`. Aucune entité dynamique ne contribue à cette liste.
> Le cache key `(cam_x, cam_y, len(occluding_rects))` est valide car les positions des tiles
> sont fixes en world space et leur nombre est stable pour un viewport donné.
>
> Si une entité dynamique est ajoutée à `occluding_rects` à l'avenir, le cache key
> devra inclure un hash des positions/identités des entités dynamiques.

---

## File Tree (fichiers modifiés)

```
game/src/
├── engine/
│   ├── game.py                    [MODIFY] — appel reset_render_caches() dans transition_map()
│   ├── render_manager.py          [MODIFY] — H-001 composite reuse, H-002 lookup, H-003 early-exit, reset_render_caches()
│   ├── render_occlusion.py        [NEW — H-004]
│   └── render_wading.py           [NEW — H-004]
└── map/
    └── manager.py                 [MODIFY] — H-002 _build_anim_tile_layer_map, H-003 _map_has_grass

game/tests/engine/
├── test_render_manager.py         [MODIFY] — ajouter TC-RPERF-U-001..U-005, I-001, I-002, I-004
├── test_render_manager_coverage.py [MODIFY — H-004]
└── test_render_perf.py            [NEW] — TC-RPERF-U-006..U-016
game/tests/map/
└── test_map_manager_perf.py       [NEW] — TC-RPERF-U-006, U-007, U-013, U-014
```
