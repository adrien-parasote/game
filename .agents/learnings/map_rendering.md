## 🗺️ Map & Rendering

### ~~L-MAP-001~~ · 2026-04-28 · U · Major Rework → **SUPERSEDED by L-MAP-006 · 2026-05-14**
**Semantic name-based layer ordering**

⚠️ **Archived — this pattern became an anti-pattern.** Sorting by name prefix worked until the `order` Tiled property was introduced. Using the name as a proxy for Z-order couples naming conventions to rendering logic and breaks silently when names change.

```python
# ❌ Superseded — name-based sort
layer_order = sorted(raw_order, key=lambda lid: self.layer_names.get(lid, ""))

# ✅ Use the explicit 'order' property instead (see L-MAP-006)
layer_order = sorted(raw_order, key=lambda lid: order_values.get(lid, 0))
```

**Original Evidence:** Background (`00-layer`) disappeared due to group nesting. `tests/test_map.py` confirmed fix.
**Superseded Evidence:** Name-based depth derivation caused invisible objects bug (2026-05-14 session).

---

### L-REND-001 · 2026-04-28 · U · Perfect
**Additive light overlays applied after darkness**

Apply `BLEND_ADD` light sources after the global darkness surface. Applying before causes darkness to dim the light source.

---

### A-MAP-001 · 2026-04-28 · U · Major Rework
**Index-based layer priority** → See L-MAP-001 (same root cause).

---


### L-REND-002 · 2026-05-01 · U · Minor Rework
**Corner-fade approach for shaped surface bottoms**

Using `effective_t = t * (1 + dist * k)` to make edges fade faster than the center also dims the center column at the bottom, creating a spike/triangle shape instead of an oval.

```python
# ❌ Couples center and edge: center spikes because effective_t > 1 at edges
effective_t = t * (1.0 + dist_x * 0.9)
v_fade = max(0.0, 1.0 - effective_t) ** 0.35

# ✅ Keep v_fade independent, add a separate corner multiplier in the bottom zone only
v_fade = (1.0 - t) ** 0.6  # unchanged for all x
if t > 0.65:
    bp = (t - 0.65) / 0.35
    cf = max(0.0, 1.0 - bp * abs(x - cx) / half_w * 1.8)  # 1.0 at center, fades at edges
else:
    cf = 1.0
alpha = master_alpha * v_fade * h_fade * cf
```

**Rule:** Never modify a per-row decay function based on per-pixel horizontal distance. Add a separate multiplier that's always 1.0 at the center column.
**Evidence:** User screenshot showed spike; corner_fade approach restored trapezoid shape with oval bottom.

---

---

### L-REND-003 · 2026-05-01 · U · Minor Rework
**Continuous cosine blending for cyclic state transitions**

Hard `if brightness < threshold: moon else: sun` switches create visible discontinuities ("tic") at state transitions like dawn/dusk.

```python
# ❌ Binary switch — 42px jump at 18h
if brightness < 0.15:
    return moon_slant   # e.g., +14px
else:
    return sun_slant    # e.g., -28px at 18h

# ✅ Two continuous cosine waves blended by brightness
sun_slant  = max_slant * cos(2π * (hour - 6) / 24)
moon_slant = max_slant * 0.5 * cos(2π * (hour - 18) / 24)
slant = sun_slant * brightness + moon_slant * (1 - brightness)
```

**Rule:** For any cyclic parameter that transitions between two modes (day/night, seasons, tides), model each mode as an independent continuous function and blend by the existing continuous transition weight.
**Evidence:** Slant continuity test — max jump < 5px across 48 half-hour samples vs. 42px jump with if/else.

---

---

### L-MAP-002 · 2026-05-13 · U · Major Rework
**Tiled exact wangid array order**

Tiled's terrain auto-painter relies on an exact order for `wangid` values when generating Mixed Wang Sets.

```python
# ❌ Shifted by 1
wangid = f"{nw},{n},{ne},{e},{se},{s},{sw},{w}"

# ✅ Exact Tiled Order
wangid = f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
```

**Anti-pattern:** Assuming a standard directional array (e.g., TopLeft first) for Tiled properties without checking the exact API order.
**Evidence:** Terrain painter failed (left checkerboard gaps) because bitmasks shifted by 1 index didn't map to valid tiles. Reordering to `Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft` fixed it perfectly.

---

### L-MAP-003 · 2026-05-13 · U · Minor Rework
**Visual artifact debugging (transparent tiles vs missing IDs)**

When an auto-generated tile appears as a flat, dark grey block in Tiled, it's easy to assume Tiled rejected the tile and placed a fallback background. 

**Anti-pattern:** Spending time debugging TSX Wang ID mappings when an autotile has a visual artifact in Tiled.
**Rule:** Check the output PNG for transparency first. Tiled's default map background is a dark grey grid. If a crop coordinate is wrong and extracts a transparent section, it looks identical to Tiled "missing" the tile. 
**Evidence:** A script was cropping `(2,0)` instead of `(4,0)` for an RPG Maker XP inner corner, producing a fully transparent 32x32 tile. Tiled successfully placed the tile, but it was invisible.

---

### L-MAP-004 · 2026-05-13 · U · Perfect
**Cache Evasion for Dynamic Tile Overlays**

When introducing dynamic visual elements (like animated autotiles) into a heavily cached static system (tilemaps), attempting to rebuild or invalidate the global static cache kills performance.

```python
# ❌ Draw animated tiles into the global static layer cache
# Requires invalidating and rebuilding the entire 3200x3200 surface every 150ms.
def get_layer_surface(self): ...

# ✅ Explicitly skip dynamic elements during static bake, leaving a transparent hole
if tile.frames is not None:
    continue # Skip animated tiles
    
# Then yield dynamic tiles in a separate pass for RenderManager
for tile in get_visible_animated_chunks():
    screen.blit(anim_manager.get_current_frame(tile.id), pos)
```

**Rule:** Always decouple dynamic elements from static pre-render pipelines by applying "Cache Evasion" — explicitly skip rendering the dynamic element into the cache, and composite it dynamically on top of the static cache during the render loop.
**Evidence:** Animated autotiles integrated flawlessly into the Tiled parser while maintaining constant 60 FPS without invalidating the static layer cache.

---

### L-MAP-005 · 2026-05-14 · U · Minor Rework
**Per-tile property overrides of layer properties**

When parsing map layers, default rendering pass behavior based on the layer's overall property (e.g., depth) must explicitly account for individual tiles that override that property.

**Anti-pattern:** Assuming that if a layer's default depth is `0`, all tiles within it can be safely baked into the background cache.
**Rule:** When optimizing layers by their collective properties, always compute the `layer_max_property` (e.g., `layer_max_depths`) to know if the layer contains exceptions. If an exception exists, use a per-tile check during the render pass to exclude those tiles from the default layer batch and yield them for the correct pass.
**Evidence:** Tiles with `depth=2` on a background layer `0` were incorrectly drawn behind the player until `MapManager` implemented `layer_max_depths` and explicitly skipped `depth > player.depth` tiles during background surface baking, delegating them to the foreground iterator.

---

### L-MAP-006 · 2026-05-14 · U · Major Rework
**Two-axis layer rendering model: `order` (Z bucket) ≠ `depth` (occlusion)**

A tile map rendering system has two independent axes that must never be conflated:

| Axis | Property | Source | Purpose |
|------|----------|--------|---------|
| **Layer Z bucket** | `order` (int) | Tiled layer custom property | Which render pass draws this layer (background=0..1, foreground=2+) |
| **Tile occlusion depth** | `depth` (int) | Tile custom property in TSX | Whether a sprite is drawn under/same/above the tile |

```python
# ❌ Conflated — uses name prefix for both layer order AND depth
self.layer_depths[layer_id] = int(layer_name[:2])  # "02" → 2 — means BOTH order AND depth

# ✅ Separated: layer_depths = order value, tile.depth = occlusion only
order_values = map_data.get("layer_order_values", {})  # from Tiled 'order' property
self.layer_depths = {lid: order_values.get(lid, 0) for lid in self.layer_order}
# tile.depth is read per-tile from TSX only for occlusion logic
```

**Rule:**
1. Store layer render Z in `layer_order_values` (from Tiled `order` property)
2. Store tile occlusion in `tile.depth` (from TSX tile properties)
3. Never derive layer Z from tile depth or vice versa
4. In `get_visible_chunks(min_depth)`: skip per-tile depth filter for layers where `layer_order_val > min_depth` — ALL tiles in a foreground-order layer belong in the foreground pass

**Evidence:** Objects with `depth=2` placed on tiles in a `order=2` layer were invisible. The conflation caused `layer_depths[order=2 layer] = 2` which looked correct, but `layer_max_depths` seeded from it masked tiles that had `tile.depth=0`, making them fall through both background and foreground passes. 3 files changed, 2 regression tests added, 21 tests green. commit `1f4e4ae`.

---

### A-MAP-002 · 2026-05-14 · U · Major Rework
**Seeding derived metrics from conflated source values causes silent invisible tiles**

`layer_max_depths[layer_id]` was seeded with `max_d = self.layer_depths.get(layer_id, 0)` — using the layer's Z-order value as a floor for per-tile depth. When a tile in an order=2 layer had `depth=0`:
- `layer_max_depths` was 2 (from order seed)
- `draw_background` excluded it: `order=2 > player.depth=1` → not in background ✅
- `draw_foreground` yielded the layer: `layer_max_depths=2 > 1` → layer included ✅
- But per-tile filter: `depth=0 <= 1` → **tile skipped** ❌
→ Tile rendered nowhere. Object above it also invisible.

```python
# ❌ Seeds max_d from layer Z-order — mixes two axes
max_d = self.layer_depths.get(layer_id, 0)  # order value, not tile depth!
for tid in layer_tiles:
    d = tile.depth
    if d > max_d: max_d = d  # now max_d = max(order, tile_depths) — semantically wrong

# ✅ Start from 0 — layer_max_depths = purely per-tile maximum
max_d = 0
for tid in layer_tiles:
    d = tile.depth
    if d > max_d: max_d = d
```

**Rule:** Derived aggregate metrics (`layer_max_depths`) must only aggregate the values they describe (per-tile depths). Never seed them with a value from a different semantic axis (layer order).
**Evidence:** Invisible tile bug traced to this seed. Fix: 1 line change + 2 regression tests. commit `1f4e4ae`.

---

### L-SPRITE-001 · 2026-05-14 · U · Major Rework
**Spritesheet dimensions are the authoritative source for frame height — not Tiled properties**

`sprite_height` declared in Tiled is a grid layout hint for map editors. It is NOT the actual pixel height of each animation frame. The spritesheet file itself defines the real frame height via `sheet_h // (end_row + 1)`.

```python
# ❌ Bug introduced in commit 73c8f8c — Tiled value used directly
# Breaks when sheet rows don't align with Tiled's declared height
real_frame_h = self.sprite_height  # Tiled says 32 → slices 172px sheet into 5 rows of 32px ❌

# ✅ Authoritative: sheet geometry defines the frame height
sheet_h = self.spritesheet.sheet.get_height()
real_frame_h = sheet_h // (end_row + 1)  # 172 // 4 = 43px ✅
self.sprite_height = real_frame_h  # update BEFORE _setup_physics reads it
```

**Concrete case that triggered the bug:**

| Entity | Sheet dimensions | end_row | Tiled `height` | Real frame_h | Regression |
|--------|-----------------|---------|----------------|--------------|------------|
| Torch | 64×128 | 3 | 32px | 128//4=32px ✅ | None (coincidental match) |
| Chest (01-iron-chests.png) | 128×172 | 3 | 32px | 172//4=**43px** | Misaligned + off-center |
| Lever (03-levers.png) | 32×128 | 1 | 32px | 128//2=**64px** | Misaligned + off-center |

**Why the torch didn't catch the regression:** Tiled's declared 32px and `128//4=32px` coincidentally matched. The regression was invisible for the torch, masking the bug.

**Centering impact:** `_setup_physics` computes `dummy_rect.midbottom` from `self.sprite_height`. If `sprite_height` is wrong at that point, the entity's logical position is misaligned. `sprite_height` MUST be updated from the sheet BEFORE `_setup_physics` runs.

**Rule:**
1. Always compute `real_frame_h = sheet_h // (end_row + 1)` when a valid spritesheet is loaded.
2. Immediately update `self.sprite_height = real_frame_h` so that `_setup_physics` uses the correct height.
3. Treat Tiled's `height` property as a fallback only when no spritesheet is available (e.g., sign triggers).

**Evidence:** Visual centering regression on chests and levers after commit `73c8f8c`. Restored by reverting to sheet-based calculation. 768/768 tests green after fix + test corrections.

---

### L-REND-004 · 2026-05-14 · U · Major Rework
**RenderManager draw_scene() : pivot point player.depth-1 pour éviter l'occlusion des entités interactives**

Une régression dans `RenderManager.draw_scene()` rendait les objets interactifs (coffres, leviers, NPCs) avec `depth=1` invisibles car occultés par les tuiles foreground `depth=2`.

| Pass | Split (avant) | Split (après — correct) | Contenu |
|------|--------------|--------------------------|---------|
| Pass 2 | `max_depth=player.depth` (1) | `max_depth=player.depth-1` (0) | Uniquement les sprites ground-level (pickups) |
| Pass 3 | `draw_foreground()` depth=2 | inchangé | Tuiles foreground (murs) |
| Pass 3b | `min_depth=2` | `min_depth=player.depth` (1) | Joueur, NPCs, coffres, leviers, torches |

```python
# ❌ Pivot trop haut — coffres/NPCs (depth=1) dessinés AVANT les murs (depth=2)
render_manager.draw_background(max_depth=player.depth)   # depth <= 1 → inclut coffres

# ✅ Pivot à player.depth-1 — coffres/NPCs dessinés APRÈS les murs
render_manager.draw_background(max_depth=player.depth - 1)  # depth <= 0 → sol uniquement
render_manager.draw_foreground()                             # murs (depth=2)
render_manager.draw_entities(min_depth=player.depth)         # coffres, NPCs, joueur (depth >= 1)
```

**Anti-pattern :** Dessiner les entités interactibles (coffres, NPCs) dans le background pass si elles partagent un depth égal ou inférieur aux murs qu'elles chevauchent. La "couche interactable" doit presque toujours être rendue après la "couche géométrie statique".

**Evidence :** Coffres et leviers invisibles contre les murs dans `99-debug_room.tmj`. TC-04 dans `tests/engine/test_bug_depth2_sprite_invisible.py` corrigé. Vérification visuelle confirmée.

---

### L-MAP-007 · 2026-05-17 · U · Major Rework
**Le `depth` d'un tile encode son rôle physique — pas seulement son rendu**

La propriété `depth` d'un tile a deux significations distinctes qui doivent toutes deux être respectées :

| `depth` | Rôle rendu | Rôle physique |
|---------|-----------|---------------|
| 0 | Sol/fond — rendu derrière le joueur | **Sol** — définit si le joueur peut se trouver ici (`is_walkable`) |
| ≥1 | Décor/mur — rendu devant le joueur | **Décor visuel** — n'affecte PAS `is_walkable`, peut affecter `get_direction_flags` |

```python
# ❌ is_walkable AND de tous les layers → décors depth=2 bloquent le sol
def is_walkable(self, x, y):
    return all(tile.walkable for tile in tiles_at(x, y))  # bloque le pont

# ❌ topmost tile wins (sans filtre depth) → tuile décorative la plus haute gagne
def is_walkable(self, x, y):
    return tiles_at(x, y)[-1].walkable  # rebord pont (depth=2) > sol (depth=0)

# ✅ Seuls les tiles depth=0 participent à la walkabilité
def is_walkable(self, x, y):
    for tile in reversed_layers(x, y):
        if tile.depth == 0:  # sol uniquement
            return tile.walkable
    return False
```

**Architecture résultante — deux fonctions complémentaires :**
```
is_walkable(x, y)         → depth=0 uniquement   "Puis-je me trouver ici ?"
get_direction_flags(x, y) → TOUS les depths       "Par où puis-je sortir ?"
```

Un tile `depth=2` avec `direction={up,left,right}` contraint les sorties via `get_direction_flags` (garde-corps, rebord de pont directionnel) sans bloquer la walkabilité.

**Root cause de la confusion :** La carte de debug contenait un pont avec :
- Layer 0 : sol pierre `walkable=True, depth=0` ← sol franchissable
- Layer 1 : rebords visuels `walkable=False, depth=2` ← décor affiché devant le joueur

Les deux fixes successifs (AND-all-layers → topmost-wins) échouaient car ils ne modélisaient pas le rôle physique de `depth`.

**Evidence :** 7 tests de régression (`test_is_walkable_*` + `test_depth1_tile_*`) — tous verts. Validation manuelle sur le pont de la debug room. ADR `BUG-WALK-001-002-is-walkable-depth-semantics.md`. commit `2fbf06c`.

---

### A-MAP-003 · 2026-05-17 · U · Major Rework
**is_walkable sur tous les layers sans filtre depth — 2 itérations pour converger**

Deux implémentations successives de `is_walkable` ont échoué avant de trouver la bonne sémantique :

```python
# ❌ Itération 1 — AND de tous les layers
# Un seul tile non-walkable dans N'IMPORTE quel layer → bloque
return all(tile.walkable for tile in all_tiles_at(x, y))
# Fail : ravin non-walkable bloque même avec pont walkable au-dessus

# ❌ Itération 2 — Topmost tile wins (sans filtre depth)
# La tuile sur le layer le plus haut gagne
for layer in reversed(layer_order):
    tile = get_tile(layer, x, y)
    if tile:
        return tile.walkable  # rebord de pont (depth=2) masque le sol
# Fail : décor depth=2 walkable=False sur le layer le plus haut → bloque

# ✅ Itération 3 — depth=0 only, topmost depth=0 wins
for layer in reversed(layer_order):
    tile = get_tile(layer, x, y)
    if tile and tile.depth == 0:  # ignorer les décors depth≥1
        return tile.walkable
return False
```

**Anti-pattern :** Traiter `is_walkable` comme une propriété aggregée de tous les layers, sans tenir compte de la sémantique physique de `depth`. Le `depth` n'est pas un tri de rendu — c'est une classification de rôle.

**Fix pour les futures specs de walkabilité :**
> « `is_walkable` ne doit consulter que les tiles `depth=0`. Les tiles `depth≥1` sont des décors visuels qui s'affichent devant le joueur mais n'appartiennent pas au sol. Seul le sol (`depth=0`) définit si le joueur peut se trouver sur une case. »

**Signe d'alerte :** Si une correction de `is_walkable` nécessite plus d'une itération, vérifier que le modèle mental du `depth` est correct — la cause est presque toujours une confusion entre rendu et physique.

**Evidence :** 2 itérations de fix (BUG-WALK-001, BUG-WALK-002) nécessaires. Human enforcement : le user a dû tester en jeu pour révéler l'insuffisance du fix 1. commit `2fbf06c`.

---


### L-MAP-008 · 2026-05-17 · U · Bug Fix
**Le filtre `depth≤1` s'applique à TOUTES les requêtes spatiales "qu'est-ce qui est sous le joueur"**

`get_terrain_material_at()` avait le même bug structurel qu'`is_walkable` (A-MAP-003) : elle retournait le tile le plus haut sans filtrer par `depth`. Un toit `depth=2, walkable=True` écrasait le matériau de la planche `depth=1` en-dessous, forçant un son de "toit" au lieu de "bois".

**Règle générale :** Toute fonction qui répond à « qu'est-ce qui est sous les pieds du joueur ? » doit ignorer les tiles avec `depth > 1`.

```python
# ❌ topmost tile wins (sans filtre depth) → toit depth=2 écrase planche depth=1
for layer in reversed(layer_order):
    tile = get_tile(layer, x, y)
    if tile and tile.properties.get("material"):
        return tile.properties["material"]  # retourne "roof" au lieu de "wood"

# ✅ Seulement les tiles depth≤1 (sol et plancher)
for layer in reversed(layer_order):
    tile = get_tile(layer, x, y)
    if tile and tile.depth <= 1 and tile.properties.get("material"):
        return tile.properties["material"]  # retourne "wood" ✓
```

**Fonctions soumises à cette règle :**
| Fonction | Sémantique | Filtre depth |
|----------|------------|--------------|
| `is_walkable(x, y)` | « Puis-je me trouver ici ? » | `depth == 0` seulement |
| `get_terrain_material_at(x, y)` | « Sur quoi est-ce que je marche ? » | `depth <= 1` |
| `get_direction_flags(x, y)` | « Par où puis-je sortir ? » | **TOUS** les depths |

**Evidence :** BUG-SFX-001 — son de pas "roof" joué sur une planche. Fix 1 ligne + 3 tests. 825/825 verts. commit suivant.

---

### A-MAP-004 · 2026-05-17 · U · Bug Fix
**Assumer que "topmost tile" = "tile sous le joueur" ignore la sémantique du depth**

Le tile le plus haut dans la pile des layers n'est PAS nécessairement le tile sur lequel le joueur marche. Un toit `depth=2` est physiquement AU-DESSUS du joueur, pas sous lui.

**Check rapide avant d'écrire une query spatiale :**
> « Est-ce que la fonction répond à une question du point de vue du joueur (physique) ou du rendu (visuel) ? »
> - Physique (is_walkable, material, son) → filtrer `depth ≤ N` selon le rôle
> - Visuel (rendu foreground, occlusion) → tous les depths

**Evidence :** Même anti-pattern déclenché 3 fois : `is_walkable` (BUG-WALK-001), `is_walkable` (BUG-WALK-002), `get_terrain_material_at` (BUG-SFX-001).

---

*Last updated: 2026-05-17 — L-MAP-008 (depth filter for all "under the player" queries), A-MAP-004 (topmost ≠ underfoot).*

---

### A-SPRITE-002 · 2026-05-17 · U · Minor Rework
**Grille spritesheet hardcodée `load_grid(cols, rows)` dans le code NPC — frames coupées silencieusement**

`NPC.__init__` hardcodait `sheet.load_grid(4, 4)` pour toutes les spritesheets. Une sheet non-standard (`05-guards.png` : 64×384px) produit des frames 16×96px (64/4=16) au lieu de 32×96px (64/2=32) → moitié du sprite coupée sans erreur ni warning.

```python
# ❌ Hardcode → toute sheet non-4×4 donne des frames coupées
self.frames = sheet.load_grid(4, 4)
# offsets animation: {"down":0, "left":4, "right":8, "up":12} — hardcodés aussi

# ✅ Configurable depuis les props Tiled — default 4/4 rétrocompat
self.frames = sheet.load_grid(sheet_cols, sheet_rows)
self.frames_per_dir = sheet_cols
fpd = self.frames_per_dir
row_offsets = {"down": 0, "left": fpd, "right": fpd * 2, "up": fpd * 3}
```

**Règle — NPC avec spritesheet :**
1. `sheet_cols` / `sheet_rows` doivent être passables depuis la config (props Tiled)
2. `frames_per_dir = sheet_cols` — offsets d'animation dynamiques, jamais hardcodés
3. Pour chaque NPC utilisant une sheet non-default, le `.tmj` DOIT spécifier `sheet_cols` + `sheet_rows`

**Règle spec :** La spec NPC DOIT documenter la formule `(sheet_cols × sheet_rows = total_frames)` et les offsets par direction. Un bug de frame silencieux est garanti si la sheet s'écarte du layout par défaut sans que le code le sache.

**Evidence :** `05-guards.png` (64×384px, 2×4) → frames coupées à 16px. Fix : `sheet_cols=2, sheet_rows=4` dans props Tiled obj 15 & 18. `frames_per_dir=2` → offsets `0,2,4,6`. commit `9fac11b`. 830/830 tests verts.

---

*Last updated: 2026-05-17 — A-SPRITE-002 (NPC spritesheet grid hardcoded → silent cropped frames).*

---

### L-REND-005 · 2026-05-22 · U · Perfect
**Composite SRCALPHA swap-and-restore pour l'occlusion partielle sprite**

Pour rendre seulement la zone d'un sprite qui chevauche un tile occludant en semi-transparent (au lieu d'appliquer un alpha global), le pattern **composite swap-and-restore** produit un premier pass parfait :

```python
# _apply_partial_occlusion() — pattern
saved_images = {}
for sprite in sprites:
    intersecting = [
        (screen_rect.clip(tile_rect), tile_depth)
        for tile_rect, tile_depth in occluding_rects
        if tile_depth > sprite.depth and screen_rect.colliderect(tile_rect)
    ]
    if not intersecting:
        continue

    # 1. Build SRCALPHA composite (same size as sprite.image)
    composite = pygame.Surface(sprite.image.get_size(), pygame.SRCALPHA)
    composite.blit(sprite.image, (0, 0))  # full opaque copy

    # 2. Apply alpha only to the intersecting zones
    alpha_surf = pygame.Surface(sprite.image.get_size(), pygame.SRCALPHA)
    alpha_surf.blit(sprite.image, (0, 0))
    alpha_surf.set_alpha(Settings.OCCLUSION_ALPHA)
    for clip_rect, _ in intersecting:
        local_rect = clip_rect.move(-screen_rect.left, -screen_rect.top)
        if local_rect.width > 0 and local_rect.height > 0:
            composite.fill((0, 0, 0, 0), local_rect)          # ← reset zone
            composite.blit(alpha_surf, local_rect, local_rect)  # ← alpha blit

    # 3. Swap and save
    saved_images[sprite] = sprite.image
    sprite.image = composite

# After custom_draw — restore
for sprite, original in saved_images.items():
    sprite.image = original
```

**Pourquoi ça marche :**
- `fill((0,0,0,0), local_rect)` avant le blit alpha est **obligatoire** — sinon le blit additionne les canaux alpha au lieu de remplacer.
- `alpha_surf.set_alpha(OCCLUSION_ALPHA)` sur une surface SRCALPHA définit l'alpha global de la surface utilisée comme source, pas du composite.
- Le swap-and-restore préserve les frames partagées de la spritesheet — `set_alpha()` direct les contaminerait.
- Fonctionne sur tous les sprites génériquement (player + NPCs) — aucun traitement special-case.

**Préconditions spec pour que ça marche :**
- `visual_rect` calculé avec `bottomright=sprite.rect.bottomright` (comme `custom_draw`)
- Guard `tile_depth > sprite_depth` strict (égalité = pas d'occlusion)
- Guard `width > 0 and height > 0` sur `clip_rect` (évite les blits 0-pixel)
- Walk guard en amont — ne pas appeler sur un player déjà transparent

**Evidence :** 19/19 tests (UT-001..011, IT-001..004) — premier pass. 971/971 suite complète. Zéro intervention humaine. commit `d3db6bf`.
