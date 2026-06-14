[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification - Camera & Rendering Pipeline [Implementation]

> Document Type: Implementation
> ADR (Partial Occlusion): [ADR-007](../ADRs/ADR-007-partial-occlusion-surface-composite.md#L1)

This document specifies the AS-IS technical implementation of the camera system, sprite rendering pipeline, Y-sorting, frustum culling, and spritesheet utility.

## 1. Goal Description

Render the game world using a multi-pass pipeline that correctly orders sprites by depth, applies camera offset to all world-space elements, optimizes performance via frustum culling and sort caching, and supports overlay systems (lighting, UI, emotes).

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `CameraGroup` | `src/entities/groups.py` | 134 | Camera offset, Y-sort, frustum culling, sprite drawing |
| `RenderManager` | `src/engine/render_manager.py` | ~560 | Multi-pass scene orchestrator — includes `_apply_partial_occlusion()`, `_apply_grass_wading_to_images()`, `_build_wading_composite()` |
| `MapManager` (extension) | `src/map/manager.py` | +~20 | New `get_grass_tile_image_at()` query — see [map-world-system.md §4.2](./map-world-system.md#L83) |
| SpriteSheet | `src/graphics/spritesheet.py` | 89 | Grid-based spritesheet extraction utility |

## 3. CameraGroup — Camera & Sprite Rendering

### 3.1. Camera Offset Calculation (`calculate_offset`)

Tracks a target sprite (player) and computes the world-to-screen offset:

```python
offset.x = half_screen_width - target.rect.centerx
offset.y = half_screen_height - target.rect.centery
```

**Clamping rules**:
| Condition | Behavior |
|-----------|----------|
| `world_width < screen_width` | Center map: `offset.x = (screen_w - world_w) // 2` |
| `world_width >= screen_width` | Clamp: `min(0, max(centered, -(world_w - screen_w)))` |
| Same logic applies for Y axis | — |

**World size**: Set via `set_world_size(width_px, height_px)` at map load.

### 3.2. Y-Sort Rendering (`get_sorted_sprites`)

Sprites are sorted to simulate depth (entities lower on screen appear in front). The sort key is:
- `sprite.sort_y` — when the attribute is defined (explicit override)
- `sprite.rect.bottom` — fallback for all standard sprites

The `sort_y` override exists for tall multi-tile entities (e.g. the drawbridge, 224px high) where `rect.bottom` would incorrectly place them after the player. Setting `sort_y = rect.top` causes the entity to sort by its **top edge**, so any sprite walking on or past the entity renders in front.

**Caching optimization**:
- Sorted result cached in `_sorted_cache`
- Cache invalidated via `_cache_dirty` flag:
  - `add()` / `remove()` → dirty
  - `mark_dirty()` → explicit invalidation
  - `custom_draw()` → checks for any sprite with `is_moving=True` → dirty

### 3.3. Frustum Culling

In `custom_draw(surface, min_depth=None, max_depth=None)`, each sprite is tested against the screen rect before blitting.

Depth filtering (refined in session 2026-05-14 to prevent entity occlusion):
- `max_depth`: skip sprites with `depth > max_depth` (Pass 2 — entities strictly in background, `max_depth=player.depth - 1`)
- `min_depth`: skip sprites with `depth < min_depth` (Pass 3b — entities at or above player depth, `min_depth=player.depth`)
- When both are `None` (default): all depths drawn (legacy behaviour)

```python
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
stair_y_offset = getattr(sprite, 'current_stair_offset', 0.0)  # stair-movement spec §1.4
offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)
screen_sprite_rect = pygame.Rect(offset_pos, visual_rect.size)
if screen_rect.colliderect(screen_sprite_rect):
    surface.blit(sprite.image, offset_pos)
```

> **Stair visual offset:** `BaseEntity` exposes `current_stair_offset: float` (see [stair-movement.md §1.4](./stair-movement.md)). This float is interpolated during stair traversal and must be applied as an additional Y-offset in **every** `blit()` call via `getattr(sprite, 'current_stair_offset', 0.0)`. The `getattr` default of `0.0` ensures normal sprites (no stair system) are unaffected. **Never read `sprite._vertical_move` directly** — that is the raw property store; `current_stair_offset` is the authoritative render value.

> **Stair clip rendering:** `BaseEntity` exposes `current_stair_clip: float` (see [stair-movement.md §1.4](./stair-movement.md)). When `current_stair_clip > 0`, the sprite's bottom pixels must be made transparent via composition — NOT by modifying `sprite.image`. The rendering path inside the frustum cull block becomes:
>
> ```python
> stair_clip = int(getattr(sprite, 'current_stair_clip', 0.0))
> if stair_clip > 0:
>     clipped_image = pygame.Surface(sprite.image.get_size(), pygame.SRCALPHA)
>     clipped_image.blit(sprite.image, (0, 0))
>     clip_rect = pygame.Rect(0, clipped_image.get_height() - stair_clip, clipped_image.get_width(), stair_clip)
>     clipped_image.fill((0, 0, 0, 0), clip_rect, special_flags=pygame.BLEND_RGBA_MIN)
>     surface.blit(clipped_image, offset_pos)
> else:
>     surface.blit(sprite.image, offset_pos)
> ```
>
> See [stair-movement.md §1.4](./stair-movement.md) for the complete rendering block including frustum culling integration. The clip amount is interpolated per-frame during stair traversal, creating a smooth depth illusion. The `getattr` default of `0.0` ensures non-stair sprites take the fast `else` path.

### 3.4. Visual Anchoring

Sprites are anchored `bottomright` of visual image to `bottomright` of logical hitbox:
- **Logical hitbox**: Always `32×32` (`TILE_SIZE`) for grid alignment
- **Visual rect**: Can be larger (e.g., `32×48` for player) — extends upward
- This prevents tall sprites from "sinking" into tiles

### 3.5. Debug Hitbox Rendering

When Settings.DEBUG is enabled, red rectangles are drawn around all sprite hitboxes:
```python
if Settings.DEBUG:
    debug_rect = sprite.rect.move(self.offset.x, self.offset.y)
    pygame.draw.rect(surface, (255, 0, 0), debug_rect, 1)
```
Wrapped in `try-except TypeError` for test compatibility with mock surfaces.

## 4. RenderManager — Multi-Pass Pipeline

### 4.1. Full Rendering Pipeline (`draw_scene`)

| Pass | Method | Content | Blending |
|------|--------|---------|----------|
| 0 | `screen.fill()` | Background color clear | — |
| 1 | `draw_background()` | Map layers with `depth <= player.depth` | Normal |
| 2 | `visible_sprites.custom_draw(max_depth=player.depth-1)` | Y-sorted background entities (strictly below player depth) | Normal |
| 3 | `draw_foreground()` | Map tiles from foreground-order layers + tiles with `depth > player.depth` from mixed layers | Normal (occluded alpha near player) |
| 3b | `visible_sprites.custom_draw(min_depth=player.depth)` | Y-sorted entities at or above player depth (includes chests, levers, player, NPCs) | Normal |
| 3c | `_apply_grass_wading_to_images()` | Pre-blit image-swap: bakes grass wading composite into `sprite.image` BEFORE `custom_draw` — only for sprites on `material=grass` tiles | Normal |
| 4a | `lighting_manager.draw_additive_window_beams()` | Window light cones | `BLEND_RGB_ADD` |
| 4b | `lighting_manager.create_overlay()` | Night darkness overlay + torch punch-through | `SRCALPHA` |
| 5 | `obj.draw_effects()` | Per-object light halos + particles | `BLEND_RGB_ADD` |
| 6 | `draw_hud()` | Time/season HUD (skipped if inventory open) | Normal |
| 7 | Emote rendering | Emote sprites with camera offset | Normal |
| 8 | `dialogue_manager.draw()` | Active dialogue box | Normal |
| 9 | `speech_bubble.draw()` | NPC speech bubble | Normal |
| 10 | `inventory_ui.draw()` | Inventory overlay (if open) | Normal |
| 11 | `chest_ui.draw()` | Chest overlay (if open) | Normal |
| 12 | Custom Cursor | The absolute last rendering step | Normal |

**Partial occlusion is applied between Pass 3 and Pass 3b** (`_apply_partial_occlusion` called after `draw_foreground`, before `custom_draw(min_depth=...)`).

**Grass wading is applied at Pass 3c**, immediately **before** `custom_draw(min_depth=player.depth)` — the composite is baked into `sprite.image` so Y-sort depth ordering governs visibility naturally. See §4.6.

### 4.2. Background Rendering (`draw_background`)

- Iterates `map_manager.layer_order` sorted by ascending order value
- Layers with `depth <= player.depth` are rendered
- For **each layer**, in order:
  1. **Static tiles**: blit the pre-rendered full-layer surface via `map_manager.get_layer_surface(..., max_bg_depth=player.depth)` — single blit at camera offset
  2. **Animated tiles**: batch-blit only animated tiles from **that same layer** via `get_visible_animated_chunks(viewport, layer_id=layer_id)` → `screen.fblits()`

> **Critical ordering invariant (TC-RENDER-001)**: Animated tiles from layer L must be drawn AFTER static tiles of layer L, and BEFORE static or animated tiles of layer L+1. The previous implementation drew ALL static surfaces first then ALL animated tiles in one batch — this caused animated tiles (e.g. water) to overdraw static tiles from higher-order layers (e.g. bridge planks), making the bridge invisible.

### 4.3. Foreground Rendering with Partial Occlusion (`draw_foreground` + `_apply_partial_occlusion`)

#### 4.3.1. `draw_foreground()` — Collecte des rects occludants

```python
def draw_foreground(self) -> list[tuple[pygame.Rect, int, pygame.Surface | None]]:
```

**Retourne** : liste de tuples `(screen-space Rect, depth, occluded_image | None)` pour tous les tiles actifs avec `depth > player.depth`. Liste vide `[]` si aucun tile occludant visible.

> **Note (AR — CS-001) :** Le type réel est `OccludingRect = list[tuple[pygame.Rect, int, pygame.Surface | None]]` (3-tuple). Le 3e élément `occluded_image` est la surface semi-transparente pré-calculée du tile, ou `None` si le tile n'a pas de variante occludée. Voir [render_manager.py L10](../../src/engine/render_manager.py#L10).

**Boucle principale (Source A — tiles statiques) :**

```python
occluding_rects = []  # remplace l'ancien player_occluded = False

for px, py, tile_id, depth in self.game.map_manager.get_visible_chunks(
    self._viewport_world, min_depth=player_depth
):
    tile_data = tiles[tile_id]
    screen_pos = (px + cam_offset.x, py + cam_offset.y)

    # Collecter le rect pour TOUS les tiles depth > player (NPCs compris)
    if depth > player_depth:
        occluding_rects.append((
            pygame.Rect(screen_pos, (self.game.tile_size, self.game.tile_size)),
            depth
        ))

    # Rendu du tile — walk guard
    if not walk_active and depth > player_depth:
        self._tile_rect.topleft = screen_pos
        if player_screen_rect.colliderect(self._tile_rect):
            screen.blit(tile_data.occluded_image or tile_data.image, screen_pos)
        else:
            normal_blits.append((tile_data.image, screen_pos))
    else:
        normal_blits.append((tile_data.image, screen_pos))
```

**Source B — Tiles animés :**

```python
for px, py, tile_id, depth in self.game.map_manager.get_visible_animated_chunks(
    self._viewport_world
):
    if depth > player_depth:
        screen_pos = (px + cam_offset.x, py + cam_offset.y)
        occluding_rects.append((pygame.Rect(screen_pos, (self.game.tile_size, self.game.tile_size)), depth))
```

> **Note :** Aujourd'hui aucun tile animé n'a `depth > 1`. Cette branche est inerte mais sera activée automatiquement dès qu'un tile animé foreground sera créé.

```python
return occluding_rects  # list[tuple[pygame.Rect, int, pygame.Surface | None]], screen-space
```

L'ancien `player_occluded: bool` est **supprimé**. `draw_scene()` ne teste plus `if is_occluded:` — il passe directement `occluding_rects` à `_apply_partial_occlusion`.

#### 4.3.2. `_apply_partial_occlusion(occluding_rects)` — Swap-and-Restore

Méthode privée de `RenderManager`. Appelée **avant** `custom_draw(min_depth=player.depth)`.

**Principe :** Pour chaque sprite intersectant au moins un rect occludant, générer une surface composite temporaire où seule la zone occludée est en alpha. Remplacer temporairement `sprite.image` par celle-ci. Retourne un dict pour restauration après le rendu.

```python
def _apply_partial_occlusion(
    self, occluding_rects: list[tuple[pygame.Rect, int]]
) -> dict[pygame.sprite.Sprite, pygame.Surface]:
    if not occluding_rects:
        return {}

    cam_offset = self.game.visible_sprites.offset
    saved_images = {}
    player_depth = self.game.player.depth
    walk_active = getattr(self.game, "_intra_walk_target", None) is not None

    for sprite in self.game.visible_sprites.get_sorted_sprites():
        if not sprite.image or not sprite.rect:
            continue
        if getattr(sprite, "depth", 1) < player_depth:
            continue  # uniquement les sprites du pass 3b
        if walk_active and sprite == self.game.player:
            continue  # player est invisible pendant la marche scriptée

        # visual_rect identique à custom_draw — cohérence obligatoire
        visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
        sprite_screen_rect = pygame.Rect(
            (visual_rect.left + cam_offset.x, visual_rect.top + cam_offset.y),
            visual_rect.size,
        )

        sprite_depth = getattr(sprite, "depth", 1)
        intersections = [
            sprite_screen_rect.clip(occ_rect)
            for occ_rect, tile_depth in occluding_rects
            if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
        ]
        if not intersections:
            continue

        # Surface composite SRCALPHA
        composite = pygame.Surface(visual_rect.size, pygame.SRCALPHA)
        composite.blit(sprite.image, (0, 0))  # copie opaque complète

        for isect in intersections:
            if isect.width <= 0 or isect.height <= 0:
                continue
            local_rect = pygame.Rect(
                isect.x - sprite_screen_rect.x,
                isect.y - sprite_screen_rect.y,
                isect.width,
                isect.height,
            )
            composite.fill((0, 0, 0, 0), local_rect)  # vider la zone AVANT le blit
            alpha_surface = pygame.Surface(local_rect.size, pygame.SRCALPHA)
            alpha_surface.blit(sprite.image, (0, 0), local_rect)
            alpha_surface.set_alpha(Settings.OCCLUSION_ALPHA)
            composite.blit(alpha_surface, local_rect.topleft)

        saved_images[sprite] = sprite.image
        sprite.image = composite

    return saved_images
```

**Contraintes d'implémentation critiques :**

| Contrainte | Raison |
|---|---|
| `sprite.image.get_size()` lu dynamiquement à chaque appel | Frames de taille variable à prévoir |
| `visual_rect` calculé avec `bottomright=sprite.rect.bottomright` | Identique à `custom_draw` — toute divergence = décalage visuel |
| `fill((0, 0, 0, 0), local_rect)` AVANT le blit alpha | Indispensable — Pygame conserve les pixels opaques de la destination si on ne les vide pas |
| Surface composite `SRCALPHA` allouée par sprite occludé par frame | Taille max 32×48px — négligeable en mémoire |
| `tile_depth > sprite_depth` strict | Égalité = pas d'occlusion |

#### 4.3.3. Walk guard

Pendant un scripted walk (`_intra_walk_target` is set), le player est invisible (`_player_transparent`). `_apply_partial_occlusion` **ne doit pas traiter le player** (alpha artifacts sur sprite invisible), mais **doit continuer à traiter les NPCs**.

```python
occluding_rects = self.draw_foreground()

# _apply_partial_occlusion skippera le player en interne si walk_active est vrai
saved_images = self._apply_partial_occlusion(occluding_rects)

self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

for sprite, original_image in saved_images.items():
    sprite.image = original_image
```

> `draw_foreground()` retourne toujours une **liste** (jamais `False`). Le walk guard est géré à l'intérieur de `_apply_partial_occlusion` de manière ciblée.

### 4.4. Lighting Integration

Two lighting passes render after foreground:
1. **Additive window beams**: Always drawn (even during day) — trapezoid light cones
2. **Night overlay**: Only when `night_alpha > 0` — full-screen dark surface with torch punch-through circles

### 4.5. Effects Pass

After lighting, each interactive object with `draw_effects` method renders:
- Light halos (additive blending)
- Particles (additive blending with alpha fade)

Both receive `cam_offset` and `night_alpha` for correct positioning and intensity.

### 4.6. Grass Wading Pass (`_apply_grass_wading_to_images` + `_build_wading_composite`)

Applied at **Pass 3c** — **before** `custom_draw(min_depth=player.depth)`. Creates the visual illusion that sprites are walking **inside** the grass rather than on top of it.

**Root cause of the pre-blit design**: if grass wading were blitted to the screen *after* `custom_draw`, the player's wading pixels (drawn last in Y-sort) would bleed over the heads of NPCs already rendered at the same screen coordinates. By baking the composite into `sprite.image` before `custom_draw`, Y-sort depth ordering governs visibility naturally — a higher-Y sprite's wading zone is always drawn on top of a lower-Y sprite's full body.

**Trigger**: the tile at the sprite foot position has `properties.material == "grass"` (queried via `MapManager.get_grass_tile_image_at()`).

**Effect:**
1. **Pre-blit image swap**: `_build_wading_composite` copies the current `sprite.image` into a new `SRCALPHA` surface and paints the grass tile pixels over the bottom `GRASS_WADING_DEPTH` rows at `wading_alpha` opacity. `_apply_grass_wading_to_images` replaces `sprite.image` with this composite and returns `{sprite: original_image}` for restoration after `custom_draw`.

**Algorithm — `_apply_grass_wading_to_images` (orchestrator):**

```python
def _apply_grass_wading_to_images(
    self,
    cam_offset: pygame.Vector2 | None = None,
    pre_occlusion_originals: dict[object, pygame.Surface] | None = None,
) -> dict[object, pygame.Surface]:
    """Returns {sprite: pre-wading original} for sprites whose image was composited.

    If pre_occlusion_originals (from _apply_partial_occlusion) is provided, sprites
    already in that dict are stacked (wading over occlusion composite) but NOT
    added to the returned dict — the caller's occlusion restore loop handles them.
    """
    if not self.game.map_manager:
        return {}
    if cam_offset is None:
        cam_offset = self.game.visible_sprites.offset

    pre_occ = pre_occlusion_originals or {}
    wading_only_originals: dict[object, pygame.Surface] = {}

    for sprite in self.game.visible_sprites.get_sorted_sprites():
        if not sprite.image or not sprite.rect:
            continue
        if getattr(sprite, "depth", 1) < self.game.player.depth:
            continue  # Pass 2 sprites are already below the grass layer

        # walk_active is computed as:
        # walk_active = getattr(self.game, '_intra_walk_target', None) is not None
        if walk_active and sprite == self.game.player:
            continue  # Player is invisible during scripted walk

        composite = self._build_wading_composite(
            sprite, cam_offset, tile_size, wading_depth, wading_alpha
        )
        if composite is not None:
            if sprite not in pre_occ:
                wading_only_originals[sprite] = sprite.image
            sprite.image = composite  # stack on current (may be occlusion composite)

    return wading_only_originals
```

**Algorithm — `_build_wading_composite` (pixel builder):**

```python
def _build_wading_composite(
    self,
    sprite,
    cam_offset: pygame.Vector2,
    tile_size: int,
    wading_depth: int,
    wading_alpha: int,
) -> pygame.Surface | None:
    """Returns a new SRCALPHA composite of sprite.image with grass pixels over the
    bottom wading_depth rows, or None if the sprite is not standing on grass."""
    visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
    sprite_screen_rect = pygame.Rect(
        (visual_rect.left + cam_offset.x, visual_rect.top + cam_offset.y),
        visual_rect.size,
    )
    foot_world_x = sprite.rect.centerx
    foot_world_y = sprite.rect.bottom - 2
    grass_img = self.game.map_manager.get_grass_tile_image_at(foot_world_x, foot_world_y)
    if not isinstance(grass_img, pygame.Surface):
        return None

    # Build the small wading surface (tile-grid-aligned crop)
    wading_rect = pygame.Rect(
        sprite_screen_rect.left,
        sprite_screen_rect.bottom - wading_depth,
        sprite_screen_rect.width,
        wading_depth,
    ).clip(sprite_screen_rect)
    if wading_rect.width <= 0 or wading_rect.height <= 0:
        return None

    wading_surf = pygame.Surface(wading_rect.size, pygame.SRCALPHA)
    # ... tile-grid blit loop (same pixel arithmetic as before) ...
    wading_surf.set_alpha(wading_alpha)

    # Composite: copy full sprite image, then paint the wading zone over it
    composite = pygame.Surface(visual_rect.size, pygame.SRCALPHA)
    composite.blit(sprite.image, (0, 0))
    local_wading_top = wading_rect.y - sprite_screen_rect.y
    composite.blit(wading_surf, (0, local_wading_top))
    return composite
```

**Call site in `draw_scene()` (Pass 3c — BEFORE custom_draw):**

```python
# After _apply_partial_occlusion swap:
wading_saved = self._apply_grass_wading_to_images(
    cam_offset, pre_occlusion_originals=saved_images
)
# Now draw (composites baked into sprite.image):
self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)
# Restore all images:
for sprite, original_image in saved_images.items():
    sprite.image = original_image
for sprite, original_image in wading_saved.items():
    sprite.image = original_image
```

> **Constraint:** `_apply_grass_wading_to_images` MUST always receive `pre_occlusion_originals` from the preceding `_apply_partial_occlusion` call, even if the dict is empty (`{}`). This prevents stale occlusion composites from being restored as originals — if `pre_occlusion_originals` were omitted, a sprite already composited by occlusion would be added to `wading_only_originals` with its *composited* image as the "original", causing permanent contamination after restore.

**Grass tile alignment**: the grass crop is aligned to the 32×32 tile grid (not to the sprite position) to prevent the texture from sliding as the sprite moves within a tile.

**Settings** (see §6 for config wiring):

| Constant | Default | Semantics |
|---|---|---|
| `Settings.GRASS_WADING_DEPTH` | `10` | Height in px of the wading zone (≈bottom third of a 32px sprite) |
| `Settings.GRASS_WADING_ALPHA` | `140` | Opacity of the grass re-blit zone: 255=fully opaque grass, 0=no effect |

## 5. SpriteSheet — Grid Extraction Utility

### 5.1. Loading

```python
sheet = SpriteSheet("path/to/sprite.png")
# sheet.valid → True if loaded successfully
```

**Fallback**: If file missing or invalid → `valid=False`, `sheet=None`. All extraction methods return blue dummy surfaces.

### 5.2. Extraction API

| Method | Input | Output | Use Case |
|--------|-------|--------|----------|
| `load_grid(cols, rows)` | Column/row count | `list[Surface]` row-major | Player (4×4), NPC (4×4) |
| `load_grid_by_size(frame_w, frame_h)` | Frame dimensions in px | `list[Surface]` row-major | Interactive objects (variable size) |

Both methods:
1. Calculate frame dimensions from sheet size
2. Iterate row-by-row, column-by-column
3. Subsurface-blit each frame onto a new `SRCALPHA` surface
4. Return flat list indexed `[row * cols + col]`

### 5.3. `load_grid_by_size` Extras

Stores `last_cols` and `last_rows` on the instance for callers that need the detected grid dimensions (used by `InteractiveEntity` for dynamic column detection).

### 5.4. Fallback Surfaces

| Condition | Fallback |
|-----------|----------|
| `transparent=False` | 32×32 blue solid surface |
| `transparent=True` | 32×32 fully transparent SRCALPHA surface |

## 6. Cross-Spec Contracts

### Produces

| Identifiant | Format | Consommateurs |
|---|---|---|
| `RenderManager.draw_foreground()` → `OccludingRect` | `list[tuple[pygame.Rect, int, pygame.Surface \| None]]` — (screen-space Rect, depth, occluded_image) | `draw_scene()` (même module), [render-pipeline-optimization.md](./render-pipeline-optimization.md#L1) |

### Consumes
N/A - Not applicable

### Public Interface
N/A - Not applicable



| Identifiant | Format | Producteur |
|---|---|---|
### Consumes

| Identifiant | Format | Producteur |
|---|---|---|
| `MapManager.get_visible_chunks(min_depth)` | Iterator[(px, py, tile_id, depth)] | `src/map/manager.py` |
| `MapManager.get_visible_animated_chunks(viewport)` | Iterator[(px, py, tile_id, depth)] | `src/map/manager.py` |
| `CameraGroup.get_sorted_sprites()` | list[Sprite] | `src/entities/groups.py` |
| `Settings.OCCLUSION_ALPHA` | int (0–255) | `src/config.py` |
| `MapManager.get_grass_tile_image_at(px, py)` | `pygame.Surface \| None` | `src/map/manager.py` — see [map-world-system.md §4.2](./map-world-system.md#L83) |
| `Settings.GRASS_WADING_DEPTH` | `int` (pixels) | `src/config.py` |
| `Settings.GRASS_WADING_ALPHA` | `int` (0–255) | `src/config.py` |
| `BaseEntity.current_stair_offset` | `float` | `src/entities/base.py` — see [stair-movement.md §1.4](./stair-movement.md). Applied as additional Y-offset in `custom_draw()` via `getattr(sprite, 'current_stair_offset', 0.0)`. Default `0.0` for non-stair sprites. |
| `BaseEntity.current_stair_clip` | `float` | `src/entities/base.py` — see [stair-movement.md §1.4](./stair-movement.md). When `> 0`, triggers composition-based clipping of the sprite's bottom pixels in `custom_draw()`. Default `0.0` for non-stair sprites. |

### Tracked Interface Changes

| Method | Old contract | New contract | Specs impactées |
|--------|-------------|-------------|-----------------|
| `draw_foreground()` | `bool` | `OccludingRect` = `list[tuple[pygame.Rect, int, pygame.Surface \| None]]` | `intra-map-teleport.md §4.6, §9.2` (corrigé), `render-pipeline-optimization.md` |
| `_apply_partial_occlusion()` | n/a (nouveau) | `dict[Sprite, Surface]` | — |
| `_apply_grass_wading_to_images()` | screen-blit (supprimé) | `dict[Sprite, Surface]` swap-and-restore, called BEFORE `custom_draw` | This spec §4.6 |
| `_build_wading_composite()` | n/a (nouveau) | `pygame.Surface | None` — composite or None if not on grass | This spec §4.6 |

## 7. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| 1 | Map layers are statically ordered by depth. | Low | Verified by CLI test run: (pytest tests/map/test_map.py) |
| 2 | Camera is always bound to player. | Low | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 3 | Frustum culling margin is 0. | Medium | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 4 | `visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)` identique dans `custom_draw` et `_apply_partial_occlusion` | Low | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 5 | `Settings.OCCLUSION_ALPHA` identique pour NPCs et player (même expérience visuelle) | Low | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 6 | Les tiles foreground sont tous de taille `TILE_SIZE × TILE_SIZE` (32×32) | Low | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 7 | Max 2-3 NPCs occludés simultanément → perf négligeable | Medium | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 8 | Tiles animés avec `depth > 1` n'existent pas encore — branche inerte jusqu'à création | Low | Verified by CLI test run: (pytest tests/map/test_map.py) |
| 9 | Toutes les grass autotiles (`00-grass-1/2/3/4/5`) ont `depth=0` — tiles de fond | Low | Verified by CLI test run: (pytest tests/map/test_map.py) |
| 10 | `material="grass"` est défini au niveau du tileset (toutes tuiles du tileset) — pas besoin de propriété par-tile | Low | Verified by CLI test run: (pytest tests/map/test_map.py) |
| 11 | Au maximum 3–4 sprites visibles simultanément → overhead blit per-sprite négligeable | Medium | Verified by CLI test run: (pytest tests/engine/test_render_manager.py) |
| 12 | `tile.image` retourné par `get_grass_tile_image_at` est une surface 32×32 stable — pas de copy nécessaire | Low | Verified by CLI test run: (pytest tests/map/test_map.py) |


## 8. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Sort sprites every frame unconditionally | Use dirty-flag cache, re-sort only on position change | O(n log n) sort per frame kills performance |
| Blit off-screen sprites | Check `screen_rect.colliderect()` first | Wasted GPU blits on large maps |
| Use `sprite.rect.topleft` for rendering | Use `bottomright` anchoring | Tall sprites sink into tiles |
| Render lighting before foreground | Render lighting after foreground (Pass 4) | Light must overlay all world geometry |
| Create new Surface per frame for layers | Pre-render and cache layer surfaces | Layer surface creation is expensive |
| Use `sprite.image.get_rect()` for physical position | Use `sprite.rect` (logical hitbox) | Prevents visual/physical desync |
| Call `screen.blit()` per-tile in loops | Accumulate in list, call `screen.fblits()` once | Individual blit calls have high Python overhead; fblits is ~5× faster for bulk ops |
| `getattr(tile, 'depth', 0)` on `TileMapData` | `tile.depth` direct access | `TileMapData.depth` always set; getattr adds 847K unnecessary calls/600 frames |
| Draw ALL background static surfaces, then ALL animated tiles | Draw static + animated per-layer in order (TC-RENDER-001) | Animated tiles from lower-order layers (e.g. water) overdraw static tiles from higher-order layers (e.g. bridge planks) |
| `sprite.image.set_alpha(OCCLUSION_ALPHA)` directly | Create SRCALPHA composite; swap-and-restore `sprite.image` | Mutates the shared spritesheet frame, contaminating all future frames |
| Cache sprite size in `_apply_partial_occlusion` | Use `sprite.image.get_size()` dynamically | Frames can have variable sizes in the future |
| Calculate `visual_rect` differently from `custom_draw` | Use exactly `get_rect(bottomright=sprite.rect.bottomright)` | Inconsistency = visual misalignment between rendered sprite and composite zone |
| Guard `_apply_partial_occlusion` globally in `draw_scene()` | Pass `walk_active` and skip ONLY the player sprite internally | A global guard disables occlusion and wading for all other NPCs in the scene |
| Do a second tile scan in `_apply_partial_occlusion` | Reuse rects collected in `draw_foreground()` | Duplicated work |
| Ignore depth in `_apply_partial_occlusion` | Check `tile_depth > sprite_depth` | A tile must not occlude a sprite at the same or higher depth |
| Return `bool` from `draw_foreground()` | Return `list[tuple[pygame.Rect, int]]` | Bool insufficient — rects and depth needed for precise zone occlusion |
| Probe terrain at `sprite.rect.centerx, sprite.rect.centery` | Probe at foot: `sprite.rect.centerx, sprite.rect.bottom - 2` | Chest-height probe misses ground material — must probe at feet |
| Blit grass wading to screen AFTER `custom_draw` | Call `_apply_grass_wading_to_images()` BEFORE `custom_draw` (Pass 3c pre-blit) | Screen-space blit after draw causes wading pixels from a lower-Y sprite (player) to bleed over heads of higher-Y sprites (NPCs) already rendered |
| Allocate a full-sized `pygame.Surface` for the grass wading overlay | Use a small `pygame.Surface` matched exactly to the `wading_rect` size (e.g. 32x10) | Allocating large surfaces per frame degrades performance |
| Blit the full grass tile image | Use `area=grass_crop` to extract only the relevant pixels | Without crop, blit overdraws beyond the wading zone |
| Apply wading to sprites with `depth < player.depth` | Skip — Pass 2 entities are already below the grass layer | Background entities are behind grass; wading on them is incorrect |
| Skip composite stacking with occlusion | Pass `pre_occlusion_originals` from `_apply_partial_occlusion` to `_apply_grass_wading_to_images` | Wading must stack on the occlusion composite, not the raw original image |
| Guard `_apply_grass_wading_to_images` globally in `draw_scene()` | Pass `walk_active` and skip ONLY the player sprite internally | A global guard disables grass wading for all other NPCs in the scene |
| Read `sprite._vertical_move` in `custom_draw()` to apply stair offset | Read `sprite.current_stair_offset` via `getattr(sprite, 'current_stair_offset', 0.0)` | `_vertical_move` is the raw property dict; `current_stair_offset` is the interpolated float ready for rendering. Using `_vertical_move` directly produces a static snap instead of smooth interpolation. |

## 9. Test Case Specifications

### Unit Tests

| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-001 | `calculate_offset` | Player at center | offset = (0, 0) |
| TC-002 | `calculate_offset` | Player at (0, 0) | offset clamped to (0, 0) |
| TC-003 | `get_sorted_sprites` | Sprites at Y=100, Y=50 | Sorted [Y=50, Y=100] |
| TC-SORT-001 | `get_sorted_sprites` — sort_y override | Bridge sort_y=100, player rect.bottom=300 | Bridge before player in result |
| TC-SORT-002 | `get_sorted_sprites` — mixed sort keys | Bridge sort_y=50, NPC bottom=150, player bottom=300 | [bridge, npc, player] order |
| TC-004 | Frustum culling | Sprite at (-100, -100) | Not blitted |
| TC-005 | `SpriteSheet.load_grid` | 4×4, valid file | 16 surfaces |
| TC-006 | `SpriteSheet.load_grid_by_size` | 32×48 frames | Correct frame count + last_cols/rows |
| TC-007 | `mark_dirty` | Called after position change | Cache rebuilds on next sort |
| UT-001 | `draw_foreground()` | Aucun tile depth > 1 visible | Retourne `[]` |
| UT-002 | `draw_foreground()` | 1 tile depth 2 visible, overlappant player rect | Retourne liste avec 1 tuple (Rect, depth) |
| UT-003 | `draw_foreground()` | Tile animé depth 2 visible | Tuple du tile animé dans la liste |
| UT-004 | `draw_foreground()` | Tile depth 2 mais `walk_active=True` | Liste retournée (collecte inchangée) |
| UT-005 | `_apply_partial_occlusion` | `occluding_rects=[]` | Retour immédiat `{}`, aucun blit |
| UT-006 | `_apply_partial_occlusion` | Sprite hors intersection de tous les rects | Sprite non retraité (skip) |
| UT-007 | `_apply_partial_occlusion` | Sprite avec intersection partielle (moitié basse) | Composite : moitié haute opaque, moitié basse alpha |
| UT-008 | `_apply_partial_occlusion` | Sprite (depth=1) entièrement dans le rect occludant (depth=2) | Composite entier en alpha |
| UT-009 | `_apply_partial_occlusion` | Sprite avec 2 tiles occludants qui se chevauchent | Les deux intersections appliquées |
| UT-010 | `_apply_partial_occlusion` | Sprite (depth=2) intersectant rect occludant (depth=2) | Sprite non retraité (tile_depth non strictement supérieur) |
| UT-011 | `_apply_partial_occlusion` | `walk_active=True`, sprite = player | Return `{}`, skip player |
| GW-UT-001 | `_apply_grass_wading_to_images` | `get_grass_tile_image_at()` returns Surface; sprite on grass | sprite in returned dict; `sprite.image` replaced with composite |
| GW-UT-002 | `_apply_grass_wading_to_images` | `get_grass_tile_image_at()` returns None (sprite on dirt) | Returned dict empty; `sprite.image` unchanged |
| GW-UT-003 | `_apply_grass_wading_to_images` | `sprite.rect = None` | Skip silently — no crash |
| GW-UT-004 | `_apply_grass_wading_to_images` | `sprite.image = None` | Skip silently — no crash |
| GW-UT-005 | `_apply_grass_wading_to_images` | `self.game.map_manager = None` | Return `{}` immediately — no crash |
| GW-UT-006 | `_build_wading_composite` | Sprite at bottom screen edge — `wading_rect` extends off-screen | `wading_rect.clip()` reduces height; composite returned without crash |
| GW-UT-007 | `_apply_grass_wading_to_images` | Two sprites: one on grass, one on dirt | Only grass sprite in returned dict |
| GW-UT-008 | `_apply_grass_wading_to_images` | `walk_active=True`, sprite = player | Player not in returned dict (skipped) |
| GW-UT-009 | `_build_wading_composite` | Sprite with red image, green grass surface | Upper body pixels in composite still red (no black bar) |

### Integration Tests

| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| IT-001 | Player sous tile depth 2 | Map mock avec tile depth 2 au-dessus du player rect | `draw_foreground()` retourne liste non vide ; `_apply_partial_occlusion` appelé |
| IT-002 | NPC semi-occludé | NPC sprite 32×48, tile occludant sur la moitié basse | Surface composite différente de l'image originale sur la zone occludée |
| IT-003 | Rétrocompat scripted walk | `_intra_walk_target` actif | `_apply_partial_occlusion` skip le player, mais traite les NPCs |
| IT-004 | Full draw_scene | Game with loaded map + entities | No exceptions, correct pass order |
| IT-005 | Layer ordering | Map with Tiled `order` property | Layers sorted by `order` int, not name prefix |
| IT-006 | Multi-layer render | Map with multiple layers | Lowest `order` value drawn bottom-most |
| IT-007 | Two-pass entity draw | Entity with depth=player.depth | Absent in pass 2 (max_depth=depth-1), present in pass 3b (min_depth=depth) |
| GW-IT-001 | Full draw_scene — sprite on grass | Map mock with grass tile under player | `_apply_grass_wading_to_images` runs without exception; no regression in existing render passes |
| GW-IT-002 | NPC on grass | NPC sprite on grass tile | NPC in returned dict; `sprite.image` replaced with composite |
| GW-IT-003 | Scripted walk guard | `_intra_walk_target` set | `_apply_grass_wading_to_images` skips player, processes NPCs |

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| IT-005 | `test_layer_recursive_order` | `../../tests/map/test_map.py:L41` |
| IT-006 | `test_map_manager_render_layer` | `../../tests/map/test_map.py:L128` |
| GW-UT-001–008 | `test_grass_wading_*` | `../../tests/engine/test_render_manager.py` |

## 10. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| No display surface | `pygame.display.get_surface()` is None | Set `half_width/height = 0` | Camera offset stays at origin |
| Missing sprite image | `sprite.image is None` | Skip in `custom_draw` / `_apply_partial_occlusion` / `_apply_grass_wading_to_images` | No composite attempt |
| Missing sprite rect | `sprite.rect is None` | Skip in `_apply_partial_occlusion` / `_apply_grass_wading_to_images` | No composite attempt |
| Mock surface in tests | TypeError in `pygame.draw.rect` | Caught in try-except | Skip debug rendering |
| Spritesheet load fail | `pygame.error` | Log error, `valid=False` | Return blue dummy surfaces |
| Division by zero | Frame dims = 0 | Guard in `load_grid` | Return empty list |
| Intersection rect taille 0 | `pygame.Rect.clip()` retourne Rect(0,0,0,0) | `if isect.width > 0 and isect.height > 0` | Skip silencieux |
| `pygame.Surface()` fails | `pygame.error` | Non attrapé — erreur fatale (hors RAM) | — |
| `map_manager` is None in `_apply_grass_wading_to_images` | Guard at method entry | `return {}` immediately | No wading, no crash |
| `get_grass_tile_image_at` returns None | `if not isinstance(grass_img, Surface): return None` in `_build_wading_composite` | Skip sprite | No composite |
| `wading_rect` empty after clip | `if wading_rect.width <= 0: return None` in `_build_wading_composite` | Skip sprite | No composite |

## 11. Deep Links

- **`CameraGroup`**: [groups.py L4](../../src/entities/groups.py#L4)
- **`RenderManager`**: [render_manager.py L6](../../src/engine/render_manager.py#L6)
- **`draw_foreground()`**: [render_manager.py L54](../../src/engine/render_manager.py#L54)
- **`draw_scene()`**: [render_manager.py L128](../../src/engine/render_manager.py#L128)
- **`_apply_partial_occlusion()`**: [render_manager.py L168](../../src/engine/render_manager.py#L168)
- **`CameraGroup.custom_draw()`**: [groups.py L91](../../src/entities/groups.py#L91)
- **`CameraGroup.get_sorted_sprites()`**: [groups.py L76](../../src/entities/groups.py#L76)
- **SpriteSheet**: [spritesheet.py L7](../../src/graphics/spritesheet.py#L7)
- **`MapManager.get_visible_chunks()`**: [manager.py L152](../../src/map/manager.py#L152)
- **`MapManager.get_visible_animated_chunks()`**: [manager.py L202](../../src/map/manager.py#L202)
- **`Settings.OCCLUSION_ALPHA`**: [config.py L136](../../src/config.py#L136)
- **`RenderManager._apply_grass_wading_to_images()`**: [render_manager.py L504](../../src/engine/render_manager.py#L504)
- **`RenderManager._build_wading_composite()`**: [render_manager.py L407](../../src/engine/render_manager.py#L407)
- **`MapManager.get_grass_tile_image_at()`**: [manager.py](../../src/map/manager.py#L1) — see [map-world-system.md §4.2](./map-world-system.md#L83)
- **`Settings.GRASS_WADING_DEPTH`**: [config.py](../../src/config.py#L1)
- **`Settings.GRASS_WADING_ALPHA`**: [config.py](../../src/config.py#L1)
- **Grass tileset (source)**: [00-grass-1.tsx L1](../../assets/tiled/autotiles/00-grass-1.tsx#L1)
- **ADR (Partial Occlusion)**: [ADR-007](../ADRs/ADR-007-partial-occlusion-surface-composite.md#L1)
- **Engine core spec**: [engine-core.md §R](./engine-core.md#L1)
- **Unit tests (render manager)**: [test_render_manager.py L1](../../tests/engine/test_render_manager.py#L1)
- **Unit tests (render order)**: [test_render_order.py L1](../../tests/engine/test_render_order.py#L1)
- **Unit tests (graphics)**: [test_graphics.py L1](../../tests/graphics/test_graphics.py#L1)

## 12. Component File Tree

```
src/
  config.py
  engine/
    render_manager.py
  entities/
    groups.py
  graphics/
    spritesheet.py
  map/
    manager.py
scripts/
  dev/
    profile_game.py
tests/
  engine/
    test_render_manager.py
path/
  to/
    sprite.png
```
