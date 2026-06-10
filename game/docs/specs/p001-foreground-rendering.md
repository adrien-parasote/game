# Technical Specification — P-001: Foreground Rendering Optimization [Implementation]

> Document type: Implementation
> **Source Files:** `src/engine/render_manager.py`, `src/map/manager.py`
> **Covers:** P-001 (foreground tile pre-rendering + world-space occluding rect cache)
> **Research:** `./research/p001-foreground-rendering.md`
> **Related specs:** `./camera-rendering.md`, `./performance-system.md`

---

## 1. Context & Objective

### 1.1 Baseline Problem

`_draw_static_foreground_tiles` in `render_manager.py:62` coûte **~16 ms/frame** (28.7 s / 1800 frames).
La boucle `get_visible_chunks` génère ~480 tuples Python/frame et effectue 3 opérations entrelacées :

| Opération | Coût | Peut être pré-calculé ? |
|---|---|---|
| Blit des tuiles normales via `fblits` | ~400 iterations | ✅ OUI — surface pré-rendue |
| Build `occluding_rects` en screen-space | ~480 iterations + 480 `pygame.Rect()` alloc | ✅ OUI — cache world-space + list comp |
| Blit tuiles occludées (player overlap) | ~1–4 blit par frame | ✅ OUI — filtre ≤4 tiles proches joueur |

**Objectif :** remplacer 480 iterations Python + 480 Rect allocs par **1 blit + O(N_fg_world) operations** (viable car la map est capée à 200x200 maximum, limitant N_fg_world).

### 1.2 Architecture Direction (from STRATEGY)

Découplage en 3 fonctions privées sous `_draw_static_foreground_tiles` (orchestrateur inchangé côté appelant) :

```
draw_foreground()                         ← signature inchangée
└── _draw_static_foreground_tiles()       ← refactored (toujours private)
    ├── _blit_foreground_surface()        ← NEW: blit surface pré-rendue
    ├── _build_screen_occluding_rects()   ← NEW: list comp depuis world-space
    └── _blit_occluded_tiles_near_player()← NEW: ≤4 tiles player-overlap
```

Nouvelle donnée dans `MapManager` (peuplée au `__init__`) :
```python
_fg_occlusion_world: list[tuple[int, int, int, pygame.Surface, pygame.Surface | None]]
# (world_x, world_y, depth, image, occluded_image)
```

---

## 2. MapManager Changes

### 2.1 `_build_fg_occlusion_world()` — nouvelle méthode privée

**Signature :**
```python
def _build_fg_occlusion_world(self) -> None:
```

**Appelée une fois** à la fin de `__init__`, après que `self.layers`, `self.tiles`, `self.layer_depths`, `self.layer_max_depths`, `self.layer_order` et `self.layout` sont peuplés.

**Logique exacte :**
```python
def _build_fg_occlusion_world(self) -> None:
    """Pre-build world-space list of all static foreground tiles.
    Used by RenderManager to avoid per-frame iteration over get_visible_chunks.
    Includes all tiles with depth > 0 that may act as occluders.
    """
    result: list[tuple[int, int, int, pygame.Surface, pygame.Surface | None]] = []
    ts = self.layout.tile_size
    for layer_id in self.layer_order:
        layer_max = self.layer_max_depths.get(layer_id, 0)
        # Skip layers that contain only background tiles (max depth <= 0 means no fg tiles)
        # player_depth is not available here — we store ALL depth > 0 tiles;
        # RenderManager filters by player_depth at runtime.
        if layer_max <= 0:
            continue
        layer_data = self.layers[layer_id]
        for y, row in enumerate(layer_data):
            for x, tile_id in enumerate(row):
                if tile_id == 0:
                    continue
                tile = self.tiles.get(tile_id)
                if tile is None or tile.frames:
                    continue  # skip animated tiles (handled separately)
                if tile.depth <= 0:
                    continue  # skip background depth tiles
                result.append((
                    x * ts,
                    y * ts,
                    tile.depth,
                    tile.image,
                    tile.occluded_image,  # may be None for some tiles
                ))
    self._fg_occlusion_world = result
```

**Constraint :** Ne pas appeler `get_visible_chunks` ici — itérer directement sur `self.layers` (pleine map, pas viewport).

### 2.2 `__init__` — ajout de l'attribut + appel build

Dans `MapManager.__init__`, après la ligne qui peuple `self.layer_max_depths` :

```python
# P-001: world-space fg occlusion cache — built once at load, invalidated on map reload
# via MapManager recreation in load_map()
self._fg_occlusion_world: list[tuple[int, int, int, pygame.Surface, pygame.Surface | None]] = []
self._build_fg_occlusion_world()
```

**Position dans `__init__` :** après `self.layer_max_depths` et `self.tiles` sont peuplés, avant le `return`.

### 2.3 `get_foreground_layer_surface()` — déjà implémenté

Méthode existante (commit `515f5a8`) — aucun changement requis.
Signature confirmée : `get_foreground_layer_surface(layer_id: int, pygame_module, min_depth: int) -> pygame.Surface | None`

---

## 3. RenderManager Changes

### 3.0 `__init__` — initialisation

Ajouter l'initialisation de `_tile_rect` dans `RenderManager.__init__` pour éviter les allocations `pygame.Rect` per-frame :
```python
self._tile_rect = pygame.Rect(0, 0, self.game.tile_size, self.game.tile_size)
```

### 3.1 `_draw_static_foreground_tiles()` — refactoring complet

**Signature inchangée** (contrat public respecté) :
```python
def _draw_static_foreground_tiles(
    self,
    cam_offset: pygame.Vector2,
    walk_active: bool,
    player_screen_rect: pygame.Rect,
    player_depth: int,
    occluding_rects: OccludingRect,
) -> BlitSequence:
```

**Nouvelle implémentation :**
```python
def _draw_static_foreground_tiles(
    self,
    cam_offset: pygame.Vector2,
    walk_active: bool,
    player_screen_rect: pygame.Rect,
    player_depth: int,
    occluding_rects: OccludingRect,
) -> BlitSequence:
    """Process static foreground tiles using pre-rendered surface + world-space cache.

    Optimized pipeline:
    1. Blit pre-rendered foreground layers.
    2. Viewport-cull the world-space cache into a frame-level cache: self._frame_visible_fg_tiles.
    3. Translate coordinates and build screen-space occluding_rects.
    4. Sparse blit occluded images near the player.
    """
    self._blit_foreground_surface(cam_offset, player_depth)

    # Viewport-cull and depth-filter the entire cache once per frame
    cx, cy = cam_offset.x, cam_offset.y
    tile_size = self.game.tile_size
    vp = self._viewport_world

    self._frame_visible_fg_tiles = [
        (wx, wy, depth, img, occ_img)
        for wx, wy, depth, img, occ_img in self.game.map_manager._fg_occlusion_world
        if depth > player_depth
        and wx + tile_size > vp.left and wx < vp.right
        and wy + tile_size > vp.top and wy < vp.bottom
    ]

    self._build_screen_occluding_rects(cam_offset, player_depth, occluding_rects)
    if not walk_active:
        self._blit_occluded_tiles_near_player(
            cam_offset, player_screen_rect, player_depth
        )

    self._frame_visible_fg_tiles = []
    return []  # normal blits handled internally — BlitSequence contract preserved
```

### 3.2 `_blit_foreground_surface()` — nouvelle méthode privée

```python
def _blit_foreground_surface(
    self,
    cam_offset: pygame.Vector2,
    player_depth: int,
) -> None:
    """Blit pre-rendered foreground layer surfaces using a single blit call per layer.

    Mirrors draw_background() pattern (render_manager.py:44-48).
    get_foreground_layer_surface() returns a cached SRCALPHA surface of the full map;
    blitting with cam_offset provides automatic viewport clipping at screen boundaries.
    """
    for layer_id in self.game.map_manager.layer_order:
        surface = self.game.map_manager.get_foreground_layer_surface(
            layer_id, pygame, player_depth
        )
        if surface:
            self.game.screen.blit(surface, (cam_offset.x, cam_offset.y))
```

**Invariant :** `get_foreground_layer_surface` retourne `None` si le layer n'a pas de tuiles foreground — le guard `if surface:` préserve ce comportement.

### 3.3 `_build_screen_occluding_rects()` — nouvelle méthode privée

```python
def _build_screen_occluding_rects(
    self,
    cam_offset: pygame.Vector2,
    player_depth: int,
    occluding_rects: OccludingRect,
) -> None:
    """Translate world-space fg occlusion cache to screen-space occluding_rects.

    Uses the pre-filtered self._frame_visible_fg_tiles if present (optimized path).
    Otherwise falls back to iterating over the full map cache (compatibility path).
    """
    cx, cy = cam_offset.x, cam_offset.y
    tile_size = self.game.tile_size
    vp = self._viewport_world

    visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
    if visible_tiles is not None:
        # Optimized path (pre-filtered by depth and viewport)
        for wx, wy, depth, img, _occ in visible_tiles:
            occluding_rects.append((
                pygame.Rect(wx + cx, wy + cy, tile_size, tile_size),
                depth,
                img,
            ))
    else:
        # Fallback path for unit tests calling this method directly
        for wx, wy, depth, img, _occ in self.game.map_manager._fg_occlusion_world:
            if depth <= player_depth:
                continue
            if wx + tile_size <= vp.left or wx >= vp.right:
                continue
            if wy + tile_size <= vp.top or wy >= vp.bottom:
                continue
            occluding_rects.append((
                pygame.Rect(wx + cx, wy + cy, tile_size, tile_size),
                depth,
                img,
            ))
```

**Invariant :** `occluding_rects` est la même liste mutée in-place que dans la version précédente — `_apply_partial_occlusion` reçoit le même type et le même contrat.

### 3.4 `_blit_occluded_tiles_near_player()` — nouvelle méthode privée

```python
def _blit_occluded_tiles_near_player(
    self,
    cam_offset: pygame.Vector2,
    player_screen_rect: pygame.Rect,
    player_depth: int,
) -> None:
    """Blit occluded_image for tiles immediately adjacent to the player.

    Uses the pre-filtered self._frame_visible_fg_tiles if present (optimized path).
    Otherwise falls back to iterating over the full map cache (compatibility path).
    """
    cx, cy = cam_offset.x, cam_offset.y
    tile_size = self.game.tile_size
    screen = self.game.screen
    vp = self._viewport_world

    visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
    if visible_tiles is not None:
        # Optimized path (pre-filtered by depth and viewport)
        for wx, wy, depth, img, occ_img in visible_tiles:
            self._tile_rect.x = wx + cx
            self._tile_rect.y = wy + cy
            if player_screen_rect.colliderect(self._tile_rect):
                screen.blit(occ_img if occ_img is not None else img, (self._tile_rect.x, self._tile_rect.y))
    else:
        # Fallback path for unit tests calling this method directly
        for wx, wy, depth, img, occ_img in self.game.map_manager._fg_occlusion_world:
            if depth <= player_depth:
                continue
            if wx + tile_size <= vp.left or wx >= vp.right:
                continue
            if wy + tile_size <= vp.top or wy >= vp.bottom:
                continue
            self._tile_rect.topleft = (wx + cx, wy + cy)
            if player_screen_rect.colliderect(self._tile_rect):
                screen.blit(occ_img if occ_img is not None else img, self._tile_rect.topleft)
```

**Invariant :** La surface pré-rendue a déjà blité la version opaque de cette tuile. Ce blit par-dessus écrase uniquement le(s) pixel(s) de la zone de collision → résultat visuel identique à l'original.

---

## 4. Constraints

| Tier | Exemples |
|------|----------|
| **Always do** | Lancer `pytest tests/engine/test_render_manager.py tests/engine/test_render_manager_coverage.py` après chaque modification. Maintenir la taille de la map ≤ 200x200 tuiles pour éviter une surconsommation mémoire (SRCALPHA ~160MB max) et des lenteurs CPU O(N_fg_world). Vérifier syntaxe avec `py_compile` avant commit. |
| **Ask first** | Modifier la signature de `_draw_static_foreground_tiles`. Modifier `get_visible_chunks`. Ajouter une dépendance à un module externe. |
| **Never do** | Dépasser la taille de map de 200x200 sans refactoriser en chunks. Supprimer `occluding_rects` de la signature ou du comportement. Modifier `_draw_animated_foreground_tiles`. Toucher des fichiers hors de `render_manager.py` et `manager.py`. |

---

## 5. Cross-Spec Contracts

### Produces

| Identifier | Format | Schema | Consumers |
|---|---|---|---|
| `MapManager._fg_occlusion_world` | `list[tuple[int, int, int, Surface, Surface\|None]]` | Ce spec § 2.1 | `RenderManager._build_screen_occluding_rects`, `_blit_occluded_tiles_near_player` |

### Consumes

| Identifier | Format | Schema | Producer |
|---|---|---|---|
| `MapManager.get_foreground_layer_surface(layer_id, pygame, min_depth)` | `Surface \| None` | `performance-system.md § 8.3` | `map/manager.py` commit `515f5a8` |
| `OccludingRect` type alias | `list[tuple[Rect, int, Surface\|None]]` | `render_manager.py:8` | `render_manager.py` |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Method | `_draw_static_foreground_tiles(cam_offset, walk_active, player_screen_rect, player_depth, occluding_rects)` | Ce spec § 3.1 — signature inchangée |
| Attribute | `MapManager._fg_occlusion_world` | Ce spec § 2.1 |

### External Invocations

| Type | Invoqué | Défini dans |
|---|---|---|
| Method | `_apply_partial_occlusion(occluding_rects, ...)` | `camera-rendering.md` § occlusion pipeline |
| Method | `get_foreground_layer_surface(layer_id, pygame, player_depth)` | `performance-system.md § 8.3` |

### Tracked Concepts

| Concept | Statut | Mentionné dans |
|---|---|---|
| `occluding_rects` | Produit par `_draw_static_foreground_tiles`, consommé par `_apply_partial_occlusion` | `camera-rendering.md`, `pixel-perfect-occlusion.md` |
| Foreground layer surface cache | Étendu (build world-space cache ajouté) | `performance-system.md § 8.3` |

---

## 6. Anti-Patterns

| ❌ Don't | ✅ Do Instead | Pourquoi |
|---|---|---|
| Appeler `get_visible_chunks(min_depth=...)` dans `_draw_static_foreground_tiles` | Utiliser `_fg_occlusion_world` + list comp | La boucle generator Python est le bottleneck à éliminer |
| Allouer `pygame.Rect()` dans `_build_screen_occluding_rects` par list comp | Allouer dans la compréhension (chaque rect est unique, pas de reuse possible ici) | Les rects screen sont différents à chaque frame — allocation nécessaire mais limitée à n_viewport_fg_tiles |
| Itérer `_fg_occlusion_world` entier dans `_blit_occluded_tiles_near_player` sans guard `depth > player_depth` | Toujours filtrer `depth <= player_depth` en premier | Évite les colliderect() inutiles sur les tuiles background |
| Créer une surface SRCALPHA per-frame pour les tiles occludées | Blit directement `occ_img` sur l'écran | `occ_img` est déjà une Surface pré-alphée — pas de création de surface per-frame |
| Retourner une `BlitSequence` non vide de `_draw_static_foreground_tiles` | Retourner `[]` et gérer les blits en interne | `draw_foreground` appelle `fblits(normal_blits)` sur le retour — `fblits([])` est un no-op safe |
| Appeler `_build_fg_occlusion_world()` per-frame | Appeler une fois dans `MapManager.__init__()` | Les tuiles statiques ne bougent pas. La map est recréée à chaque `load_map()` → invalidation automatique |
| Modifier `_draw_animated_foreground_tiles` | Ne pas toucher | Hors scope P-001 — les tuiles animées gèrent leur propre `occluding_rects` |

---

## 7. Error Handling Matrix

| Erreur | Response | Fallback | Classification |
|---|---|---|---|
| `tile.occluded_image is None` | Utiliser `tile.image` | `occ_img if occ_img is not None else img` — CITED: pattern déjà présent `render_manager.py:97` | VERIFIED |
| `get_foreground_layer_surface()` retourne `None` | Guard `if surface:` — layer ignoré | Aucune tuile blitée pour ce layer (correct si layer 100% background) | VERIFIED — même guard dans `draw_background:47` |
| `_fg_occlusion_world` vide (map sans fg tiles) | Boucle no-op — `[]` retourné | `occluding_rects` reste vide → `_apply_partial_occlusion` reçoit `[]` (déjà géré) | VERIFIED |
| `MapManager.tiles.get(tile_id)` retourne `None` | Guard `if tile is None: continue` dans `_build_fg_occlusion_world` | Tuile ignorée dans le cache | VERIFIED — même pattern dans `get_visible_chunks:237-238` |
| Surface fg > mémoire / chute FPS CPU | Empêché par la contrainte de taille de map ≤ 200x200 (~160 MB max par layer) | N/A | VERIFIED (mathématiquement) |

---

## 8. Test Case Specifications

### 8.1 Unit Tests — `MapManager._build_fg_occlusion_world`

| Test ID | Fonction | Description | Assertion |
|---|---|---|---|
| TC-001 | `test_fg_occlusion_world_populated_on_init` | MapManager avec fg tiles peuple `_fg_occlusion_world` | `len(mm._fg_occlusion_world) > 0` |
| TC-002 | `test_fg_occlusion_world_excludes_background_depth` | Tuiles `depth=0` absentes du cache | Aucune entrée avec `depth <= 0` |
| TC-003 | `test_fg_occlusion_world_excludes_animated_tiles` | Tuiles avec `frames` absentes du cache | Aucune entrée correspondant à un tile animé |
| TC-004 | `test_fg_occlusion_world_world_coords` | Coordonnées en pixels monde (pas tiles) | `world_x % tile_size == 0` pour toutes les entrées |
| TC-005 | `test_fg_occlusion_world_occluded_image_none_allowed` | Tuile sans `occluded_image` incluse avec `None` | `occ_img is None` acceptable, pas de KeyError |
| TC-006 | `test_fg_occlusion_world_empty_for_bg_only_map` | Map sans fg tiles → cache vide | `mm._fg_occlusion_world == []` |

### 8.2 Unit Tests — `RenderManager` nouvelles méthodes

| Test ID | Fonction | Description | Assertion |
|---|---|---|---|
| TC-007 | `test_blit_foreground_surface_calls_blit_once_per_layer` | `_blit_foreground_surface` appelle `screen.blit` N fois (N = layers avec fg tiles) | `screen.blit.call_count == n_fg_layers` |
| TC-008 | `test_build_screen_occluding_rects_filters_by_depth` | Tuiles `depth <= player_depth` absentes de `occluding_rects` | Aucune entrée avec `depth <= player_depth` |
| TC-009 | `test_build_screen_occluding_rects_filters_by_viewport` | Tuiles hors viewport absentes | `len(occluding_rects) < len(_fg_occlusion_world)` quand viewport < map |
| TC-010 | `test_build_screen_occluding_rects_screen_coords` | Rects en coordonnées screen = world + cam_offset | `rect.x == wx + cx` pour chaque entrée |
| TC-011 | `test_blit_occluded_tiles_skips_non_colliding` | Tuile non adjacente au joueur → `screen.blit` non appelé pour elle | `screen.blit` call count = 0 si player loin |
| TC-012 | `test_blit_occluded_tiles_uses_occluded_image` | Tuile adjacente avec `occ_img` → `occ_img` blitée | `screen.blit.call_args[0][0] is occ_img` |
| TC-013 | `test_blit_occluded_tiles_fallback_to_image_if_no_occ` | Tuile sans `occ_img` → `image` blitée | Pas de `AttributeError`, `screen.blit` appelé |

### 8.3 Integration Tests — `_draw_static_foreground_tiles` contract

| Test ID | Fonction | Description | Assertion |
|---|---|---|---|
| IT-001 | `test_draw_static_foreground_tiles_returns_empty_list` | La méthode retourne `[]` | `result == []` |
| IT-002 | `test_draw_foreground_occluding_rects_populated` | `draw_foreground()` retourne `occluding_rects` non vide si fg tiles dans viewport | `len(occluding_rects) > 0` |
| IT-003 | `test_draw_foreground_walk_active_skips_occluded_blit` | Si `walk_active=True`, `_blit_occluded_tiles_near_player` non appelé | Pas de blit sur tuile adjacente au joueur pendant walk |

### 8.4 Performance Regression Test

| Test ID | Fonction | Description | Assertion |
|---|---|---|---|
| TC-014 | `test_fg_occlusion_world_build_time` | `_build_fg_occlusion_world` sur map 40×40 < 50 ms | `time.perf_counter()` delta < 0.05s |

---

## 9. Deep Links

- **`_draw_static_foreground_tiles` (avant refactoring) :** [render_manager.py:62](../../src/engine/render_manager.py#L62)
- **`draw_foreground` (orchestrateur) :** [render_manager.py:134](../../src/engine/render_manager.py#L134)
- **`draw_background` (pattern miroir) :** [render_manager.py:31](../../src/engine/render_manager.py#L31)
- **`get_foreground_layer_surface` (infra existante) :** [manager.py:91](../../src/map/manager.py#L91)
- **`get_visible_chunks` (remplacé) :** [manager.py:197](../../src/map/manager.py#L197)
- **`_apply_partial_occlusion` (consommateur de occluding_rects) :** [render_manager.py:260](../../src/engine/render_manager.py#L260)
- **Tests render_manager :** [test_render_manager.py](../../tests/engine/test_render_manager.py#L1)
- **Tests render_manager_coverage :** [test_render_manager_coverage.py](../../tests/engine/test_render_manager_coverage.py#L1)
- **Research P-001 :** [p001-foreground-rendering.md](../research/p001-foreground-rendering.md#L1)

---

## 10. Assumptions (finalisées)

| Assumption | Statut | Source Type | Preuve |
|---|---|---|---|
| `screen.blit(fg_surface, cam_offset)` clip automatiquement | VERIFIED | SHOW | `rg 'blit(surface' src/engine/render_manager.py:48` — `draw_background` en prod + docs pygame-ce |
| ≤4 tuiles fg overlappent le joueur à tout instant | ASSUMED / Low | TELL | Joueur = 32×32px, tile = 32×32px → max 4 adjacentes (géométrie) |
| `MapManager` recréé à chaque `load_map()` | VERIFIED | SHOW | `rg 'MapManager' src/engine/game.py` — instanciation dans `load_map` confirmée |
| `occluded_image` peut être `None` sur certaines tuiles | VERIFIED | SHOW | `rg 'occluded_image or' src/engine/render_manager.py:97` — guard existant en production |
| Map 200×200 = 156 MB/surface. Hard limit imposée. | VERIFIED | SHOW | `python3 -c "..."` — 6400x6400px à 4 bytes/px = ~156 MB. Viable pour RAM moderne. |
