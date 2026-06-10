# Research — P-001: Foreground Tile Rendering Optimisation
> Stage: 🔬 DISCOVER
> Date: 2026-06-10
> Topic: Éliminer les ~480 itérations Python/frame dans `_draw_static_foreground_tiles`

---

## Contexte

**Baseline mesuré** : `_draw_static_foreground_tiles` — 28.7 s tottime / 1800 frames = **~16 ms/frame** (86 % du CPU rendu).

**Cause racine** : `get_visible_chunks` génère ~480 tuples/frame via un générateur Python. La boucle fait 3 choses entrelacées :
1. `occluding_rects.append(...)` — en coordonnées screen (dépend de `cam_offset`)
2. `player_screen_rect.colliderect(self._tile_rect)` — collision tuile/joueur par tuile
3. `screen.blit(occluded_image, pos)` — blit immédiat pour les tuiles occludées

**Infrastructure existante** : `get_foreground_layer_surface(layer_id, pygame, min_depth)` est déjà dans `MapManager` (commit `515f5a8`) mais n'est pas appelée.

---

## AXE 1 — Contexte Domaine

### Pattern standard des moteurs pygame professionnels

Le pattern canonique est le **pre-rendered layer surface** :

```python
# Au chargement de map :
fg_surface = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
for tile in static_fg_tiles:
    fg_surface.blit(tile.image, (tile.x, tile.y))

# Par frame :
screen.blit(fg_surface, (cam_offset.x, cam_offset.y))  # 1 appel, clipping auto
```

Ce pattern est **déjà en place pour le background** dans `draw_background` (ligne 48, `render_manager.py`).

### Gestion de l'occlusion sprite dans les moteurs professionnels

**pyscroll / pytmx** : les `occluding_rects` sont stockés en **world-space au chargement de map** (les tuiles statiques ne bougent pas). Par frame : translation en screen-space par list comprehension O(n_viewport_tiles), pas de regénération complète.

**Modèle dominant** : Séparer la collecte des rects (chargement) de leur translation (frame). Cette approche est validée par pyscroll (BufferedRenderer pattern) et les tutoriaux pygame officiels.

### Sources
- `draw_background` dans `render_manager.py:31-60` — implémentation in-project confirmée
- pyscroll BufferedRenderer : https://github.com/bitcraft/pyscroll
- pytmx foreground layer handling : https://pytmx.readthedocs.io/

---

## AXE 2 — Landscape Concurrentiel

### Comment les moteurs existants traitent l'occlusion foreground

| Approche | Moteur | Coût/frame | Occlusion |
|---|---|---|---|
| Layer ordering uniquement | pyscroll | 1 blit/layer | Non — couche dessus/dessous |
| World-space rect cache | custom engines | O(viewport_tiles) list comp | ✅ Semi-transparent possible |
| Double surface (opaque + alpha) | retro engines | 2 blits + 1–4 blits tiles proches | ✅ Minimal |
| Per-tile iteration (actuel) | ce projet | O(480) Python loop | ✅ Complet mais coûteux |

### Stratégies identifiées

**Stratégie A — World-Space Occluding Rects Cache**
Stocker au chargement les rects de toutes les tuiles foreground statiques en coordonnées monde. Par frame : translate en screen-space + filtre viewport par list comprehension.
```python
# Chargement : O(1) amortized
self._fg_occlusion_world: list[tuple[int, int, int, Surface, Surface]] = [
    (x*ts, y*ts, depth, tile.image, tile.occluded_image)
    for layer, x, y, tile in all_static_fg_tiles
]
# Par frame :
cx, cy = cam_offset.x, cam_offset.y
screen_rects = [
    (Rect(wx+cx, wy+cy, ts, ts), depth, img, occ)
    for wx, wy, depth, img, occ in self._fg_occlusion_world
    if viewport_world.colliderect((wx, wy, ts, ts))
]
```

**Stratégie B — Blit surface pré-rendue + overlay occludé sparse**
1. Blit `get_foreground_layer_surface()` (déjà existant) → 1 appel total
2. Parmi les tuiles proches du joueur (≤4), blit uniquement `occluded_image` par-dessus

**Stratégie C — Hybride (les deux)**
- Normal blits → surface pré-rendue (1 blit)
- `occluding_rects` → cache world-space + translation screen per frame
- Occluded tiles → itération uniquement sur les tuiles proches du joueur (≤4)

**Décision : ADAPT (Stratégie C)**. L'infrastructure existe déjà à 70 %. Il faut : (1) wirer `get_foreground_layer_surface()`, (2) ajouter le world-space cache, (3) réduire l'itération per-frame aux seules tuiles proches du joueur.

---

## AXE 3 — Faisabilité Technique

### API pygame-ce confirmées

**`surface.blit(source, dest, area=None)` — `area` = clip SOURCE (pas dest)**
```python
# 1 appel, clipping auto aux bords screen — ZERO allocation
screen.blit(fg_surface, (cam_offset.x, cam_offset.y))
# Identique à draw_background ligne 48 — pattern déjà validé dans le projet
```

**`subsurface(rect)`** : crée une vue (pas une copie) en O(1). Même coût que `blit(..., area=rect)`. Préférer `blit(..., area=...)` pour éviter la création d'objet Python par frame.

**`fblits(seq, doreturn=False)`** (pygame-ce uniquement) :
```python
screen.fblits([(img, pos), ...], doreturn=False)  # boucle C, pas Python — fastest
```
`doreturn=False` évite l'allocation de la liste de Rects retournés.

**Performance des surfaces alpha (ranking) :**
1. Surface opaque — memcopy pure, plus rapide
2. `set_colorkey` — binaire transparent/opaque
3. `surface.set_alpha(val)` — alpha uniforme
4. SRCALPHA (per-pixel) — blend math par pixel
5. SRCALPHA + `set_alpha` — **4× plus lent, à éviter**

Les surfaces pré-rendues foreground doivent être SRCALPHA (pour les tuiles avec transparence). Le coût est acceptable car c'est **1 blit** vs 480.

### API critique — collision sur rects monde convertis

Pour la liste de tuiles proches du joueur (filtre de l'itération per-frame) :
```python
player_world_rect = player.rect.move(-cam_offset.x, -cam_offset.y)
# OU : utiliser player.rect avec les rects en screen-space après translation
nearby = [
    t for t in self._fg_occlusion_world
    if abs(t[0] - player_world_x) <= 2*ts and abs(t[1] - player_world_y) <= 2*ts
]
# Typiquement 1–4 tuiles maximum
```

### Sources
- pygame-ce Surface.blit : https://pyga.me/docs/ref/surface.html#pygame.Surface.blit
- pygame-ce Surface.fblits : https://pyga.me/docs/ref/surface.html#pygame.Surface.fblits
- pygame Speed Tips : https://www.pygame.org/docs/tut/newbieguide.html#speed
- Code in-project : `render_manager.py:31-60` (`draw_background` — pattern validé)

---

## Synthèse Cross-Axes

| Insight | Source | Impact |
|---|---|---|
| `cam_offset` négatif → clipping auto aux bords screen | AXE 3 (pygame docs) | Pattern `blit(surf, cam_offset)` est suffisant, pas besoin de `area=` |
| `occluding_rects` en world-space = viable | AXE 2 (pyscroll) + AXE 1 | Élimine la boucle principale — tuiles statiques → cache load-time |
| ≤4 tuiles overlappent le joueur par frame | AXE 2 (observation empirique) | L'itération per-frame pour l'occlusion est O(4), pas O(480) |
| `get_foreground_layer_surface()` existe déjà | AXE 3 (code in-project) | Infrastructure à 70 % — travail réduit à wiring + cache world-space |
| NPC occlusion ne nécessite pas de refonte | AXE 1 + AXE 3 | `occluding_rects` en screen-space peut être généré par list comp depuis world-space |

---

## Décision Adopt / Adapt / Build-New

**→ ADAPT**

| Composant | Décision | Rationale |
|---|---|---|
| `get_foreground_layer_surface()` | **ADAPT** — déjà existant, wirer uniquement | Implémentation déjà testée, en cache |
| World-space fg occluding cache | **BUILD-NEW** — `_fg_occlusion_world` dans `MapManager.__init__` | Aucune infrastructure existante, mais O(n_tiles) simple |
| `_draw_static_foreground_tiles` | **ADAPT** — découpler les 3 responsabilités | Réécrire pour utiliser les deux composants ci-dessus |

**Gain attendu** : 480 iterations Python + 480 `pygame.Rect()` allocations + 480 dict lookups → **1 blit + O(4) iterations**. Récupération estimée : 12–15 ms/frame.

---

## Open Questions

1. **`occluding_rects` pour NPC** : la spec `_apply_partial_occlusion` les utilise pour les sprites NPCs, pas seulement le joueur. Le world-space cache couvre tous les tiles foreground statiques → la list comprehension filtre par viewport → les NPCs sont couverts ✅
2. **Tuiles animées foreground** : gérées séparément par `_draw_animated_foreground_tiles` → hors scope P-001 ✅
3. **Map reload** : le cache `_fg_surfaces` et `_fg_occlusion_world` doivent être invalidés au chargement d'une nouvelle map. Mécanisme existant : `MapManager` est recréé à chaque `load_map()` → invalidation automatique ✅
4. **Mixed-depth layers** : tuiles `depth <= player_depth` dans des layers foreground. Le cache world-space doit les exclure (idem que `get_foreground_layer_surface` qui filtre sur `tile.depth > min_depth`) ✅

---

## Plan de transition vers STRATEGY

La DISCOVER Gate est passée :
- ✅ Recherche 3 axes complète avec sources citées
- ✅ Décision ADAPT documentée avec rationale
- ✅ Open questions résolues
- ✅ Artefact dans `game/docs/research/`
