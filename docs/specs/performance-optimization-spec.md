# Performance Optimization Spec

> Document Type: Implementation
> Version: 1.0 — 2026-05-04
> Audit source: `docs/brain/fcb4f254/performance_audit.md`

## Scope

14 optimisations réparties sur 6 modules. Aucun changement architectural.
Toutes les modifications sont rétrocompatibles avec la suite de tests existante.

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| A1 | `rotozoom(surf, 0, scale)` est équivalent à `smoothscale` pour angle=0 | Low | Vérifier visuellement après impl. |
| A2 | Les 58 halos oscillent dans `[0.72, 1.0]` — 10 buckets de 0.03 couvrent l'intervalle | Low | Calculé depuis les constantes min/max dans title_screen.py |
| A3 | `distance_squared_to()` est disponible sur `pygame.math.Vector2` (pygame-ce 2.5.7) | Low | Vérifié dans la doc pygame-ce |
| A4 | `colliderect((x, y, w, h))` accepte un tuple 4-uple dans pygame-ce | Low | Confirmé dans la doc SDL/pygame |
| A5 | Le Y-sort peut être caché sans impact sur la correction visuelle tant que les sprites sont triés au moins une fois par frame de mouvement | Medium | Valider visuellement — si bug, revenir à sorted() systématique |

---

## Module 1 — `src/ui/title_screen.py` (P1, P2, P3)

### Décisions d'implémentation

**P1 — Remplacement de rotozoom par lookup de surfaces pré-calculées**

Au `__init__`, pour chaque rayon unique dans `BACKGROUND_LIGHTS` et `MUSHROOM_LIGHTS` :
- Calculer `scale_range = [0.72, 1.0]` avec 10 buckets de pas `0.028`
- Pré-générer `N_SCALE_BUCKETS = 10` surfaces via `pygame.transform.smoothscale`
- Stocker : `_light_halos_scaled[radius][bucket_idx] -> Surface`
- Stocker : `_mushroom_halos_scaled[(color_key, radius)][bucket_idx] -> Surface`

En `draw()`, remplacer `rotozoom(halo_surf, 0, display_scale)` par :
```python
bucket = min(N_SCALE_BUCKETS - 1, int((display_scale - SCALE_MIN) / SCALE_STEP))
rendered = _light_halos_scaled[hr][bucket]
```

Constantes à définir dans `title_screen.py` (pas dans `_constants.py`) :
```python
_HALO_SCALE_MIN = 0.72   # valeur flicker min observée
_HALO_SCALE_MAX = 1.00   # valeur flicker max
_HALO_N_BUCKETS = 10
_HALO_SCALE_STEP = (_HALO_SCALE_MAX - _HALO_SCALE_MIN) / (_HALO_N_BUCKETS - 1)
```

**P2 — Cache des surfaces gaussian_blur (titre + hover)**

Nouveaux attributs initialisés dans `_load_assets()` :
- `_title_surf_cache: pygame.Surface` — surface composite titre (blur+text), jamais re-générée
- `_menu_hover_cache: dict[int, pygame.Surface]` — surface composite par index d'item en hover

Invalidation : uniquement quand `_hovered_item` change (comparer valeur précédente).
`_prev_hovered_item: int | None = -2` — sentinelle initiale pour forcer le premier rendu.

Logique dans `_blit_halo_text()` → devient `_render_halo_text()` (retourne Surface, ne blit pas).
`draw()` appelle `_render_halo_text()` uniquement si le cache est invalide, sinon `blit()` direct.

**P3 — Pre-render des surfaces menu (idle + hover)**

Dans `_load_assets()`, après la construction des fonts :
```python
self._menu_label_surfaces: list[dict] = []  # [{idle: Surface, hover: Surface}, ...]
for key, default in zip(_MENU_ITEM_KEYS, _MENU_ITEM_DEFAULTS):
    label = self._i18n.get(key, default=default)
    self._menu_label_surfaces.append({
        "idle": self._render_engraved(label),   # Surface composite 3 passes
        "hover": self._render_halo_text(label, ...),  # Surface composite blur+text
    })
```

`_blit_engraved()` et `_blit_halo_text()` sont décomposées en :
- `_render_engraved(label) -> Surface` (compose sans blit)
- `_render_halo_text(label, ...) -> Surface` (compose sans blit)
- `_draw_engraved(surf, cx, cy)` (blit seul)
- `_draw_halo_text(surf, cx, cy)` (blit seul)

`_draw_menu_items()` blit depuis `_menu_label_surfaces[i]["idle"|"hover"]`.

### Anti-Patterns (P1-P3)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Appeler `rotozoom()` dans `draw()` | Lookup dans `_light_halos_scaled` | `rotozoom` = O(pixels) par frame |
| Appeler `gaussian_blur()` dans `draw()` | Blit depuis cache | `gaussian_blur` = CPU intensive |
| Appeler `font.render()` dans `draw()` | Blit depuis `_menu_label_surfaces` | `render()` crée Surface SDL à chaque appel |
| Recréer le cache si `_hovered_item` n'a pas changé | Comparer avec `_prev_hovered_item` | Invalider uniquement sur changement réel |
| Stocker les surfaces en dict sans bucket borné | Utiliser `min(N-1, ...)` sur l'index | Éviter IndexError sur valeurs hors range |
| Utiliser `rotozoom` pour angle=0 | Utiliser `smoothscale` dans le précalcul | `smoothscale` est optimisé pour scale sans rotation |

### Test Case Specifications (P1-P3)

| TC ID | Composant | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| TC-001 | `_load_assets` | init TitleScreen | `_light_halos_scaled` contient 10 surfaces par rayon | rayon = 0 : skip |
| TC-002 | `_load_assets` | init TitleScreen | `_mushroom_halos_scaled` contient 10 surfaces par (color, radius) | MUSHROOM_LIGHTS vide : dict vide |
| TC-003 | `draw()` | `_light_time=0.0` | `rotozoom` n'est PAS appelé | flicker min/max boundaries |
| TC-004 | `draw()` | `_hovered_item=None` (no change) | `gaussian_blur` n'est PAS appelé | premier frame : forcer le rendu |
| TC-005 | `draw()` | `_hovered_item=0` → `_hovered_item=1` | cache invalidé pour item 0 et 1 | `_hovered_item=None` → no cache needed |
| TC-006 | `_render_halo_text` | label str, font, colors | Retourne Surface avec alpha > 0 | label vide : Surface valide |
| TC-007 | `_render_engraved` | label str | Retourne Surface avec dimensions > 0 | label vide : Surface valide |
| TC-008 | `_menu_label_surfaces` | post-init | len == len(_MENU_ITEM_KEYS) | items ajoutés dynamiquement |
| TC-009 | bucket calc | `display_scale=_HALO_SCALE_MIN` | bucket_idx = 0 | scale < min → clamp à 0 |
| TC-010 | bucket calc | `display_scale=_HALO_SCALE_MAX` | bucket_idx = N_BUCKETS-1 | scale > max → clamp à N-1 |

### Error Handling Matrix (P1-P3)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| `BACKGROUND_LIGHTS` vide | `len == 0` | `_light_halos_scaled = {}` | DEBUG |
| `MUSHROOM_LIGHTS` vide | `len == 0` | `_mushroom_halos_scaled = {}` | DEBUG |
| `bucket` hors range | `min(N-1, max(0, bucket))` | Clamp silencieux | None |
| `gaussian_blur` AttributeError (pygame standard) | `except AttributeError` (existant) | Fallback déjà implémenté | WARNING |

---

## Module 2 — `src/entities/groups.py` (P4)

### Décisions d'implémentation

Cache du Y-sort avec flag dirty :
- `_sorted_cache: list[Sprite] = []`
- `_cache_dirty: bool = True`

`get_sorted_sprites()` retourne le cache si `_cache_dirty == False`, sinon trie et met en cache.
Le flag est mis à `True` quand :
1. Un sprite est ajouté/retiré du groupe (`add()` / `remove()` / `empty()`)
2. Appelé explicitement via `mark_dirty()` — méthode publique

`CameraGroup.mark_dirty()` sera appelé depuis `BaseEntity.move()` quand `self.is_moving` passe à `True`.

Override de `add()` et `remove()` pour auto-invalider le cache.

### Anti-Patterns (P4)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Appeler `sorted()` chaque frame | Utiliser le cache et le flag dirty | `sorted()` = O(n log n) + allocation liste |
| Marquer dirty chaque frame | Marquer dirty uniquement sur changement | Annule le bénéfice du cache |
| Override `update()` pour invalider | Overrider `add()`/`remove()` | Moment correct d'invalidation |

### Test Case Specifications (P4)

| TC ID | Composant | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| TC-011 | `get_sorted_sprites()` | groupe vide | `[]` | aucun sprite |
| TC-012 | cache | 2e appel sans ajout/retrait | même objet liste (pas recalculé) | single sprite |
| TC-013 | dirty flag | `add(sprite)` | `_cache_dirty = True` | ajout multiple |
| TC-014 | dirty flag | `remove(sprite)` | `_cache_dirty = True` | retrait absent |
| TC-015 | `mark_dirty()` | appel manuel | `_cache_dirty = True` | appel répété |
| TC-016 | Y-sort | sprites à Y différents | retournés triés par `rect.bottom` croissant | Y identiques |

### Error Handling Matrix (P4)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| Groupe vide au tri | `len(sprites()) == 0` | Retourner `[]` | None |

---

## Module 3 — `src/engine/render_manager.py` (P5, P6)

### Décisions d'implémentation

**P5 — Tuple au lieu de Rect dans `draw_foreground()`**

```python
# Avant
dest_rect = pygame.Rect(screen_pos[0], screen_pos[1], self.game.tile_size, self.game.tile_size)
if player_screen_rect.colliderect(dest_rect):

# Après
if player_screen_rect.colliderect((screen_pos[0], screen_pos[1], ts, ts)):
```
`ts = self.game.tile_size` — lu une seule fois avant la boucle.

**P6 — Set `_active_torches` maintenu dans `Game`**

Ajout dans `Game.__init__()` : `self._active_torches: set = set()`

Méthode `Game._update_active_torches(entity)` appelée depuis :
- `InteractionManager._check_object_interactions()` après `obj.interact()`
- `InteractiveEntity.restore_state()` (via `entity.game._update_active_torches(entity)`)
- `Game._update()` pour les entités `day_night_driven` (une fois par frame, mais uniquement les entités `day_night_driven`)

Logique : `entity.is_on and entity.halo_size > 0` → add, sinon discard.

Dans `draw_scene()` :
```python
# Avant
active_torches = [obj for obj in self.game.interactives if ...]
# Après
active_torches = self.game._active_torches
```

### Anti-Patterns (P5-P6)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| `pygame.Rect()` dans la boucle tile | Passer tuple `(x, y, w, h)` à `colliderect()` | Évite allocation objet par tile |
| List comprehension sur `interactives` chaque frame | Maintenir `_active_torches: set` | Set lookup O(1), pas d'iteration |
| Appeler `_update_active_torches` chaque frame pour toutes les entités | Appeler uniquement sur changement d'état | Évite le O(n) redondant |

### Test Case Specifications (P5-P6)

| TC ID | Composant | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| TC-017 | `draw_foreground` | player hors foreground | `colliderect` appelé avec tuple | tile au bord écran |
| TC-018 | `_active_torches` | `interact()` torch on | entity ajoutée au set | halo_size=0 → non ajoutée |
| TC-019 | `_active_torches` | `interact()` torch off | entity retirée du set | entité absente → no error |
| TC-020 | `draw_scene()` | nuit active | `create_overlay` reçoit `_active_torches` | set vide → overlay sans trous |
| TC-021 | `restore_state` | is_on=True, halo_size>0 | entity dans `_active_torches` | game=None → no-op |

### Error Handling Matrix (P5-P6)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| `entity.game` absent au `restore_state` | `hasattr(entity, 'game')` | No-op sur `_update_active_torches` | None |
| Set vide pour `_active_torches` | N/A (set vide = valid) | Overlay sans masques torches | None |

---

## Module 4 — `src/engine/interaction.py` (P7)

### Décisions d'implémentation

Remplacer `distance_to()` par `distance_squared_to()` dans toutes les fonctions de proximité.
Définir des constantes au niveau module :

```python
_RANGE_SQ_48 = 48.0 ** 2   # 2304.0
_RANGE_SQ_16 = 16.0 ** 2   # 256.0
_RANGE_SQ_45 = 45.0 ** 2   # 2025.0
_RANGE_SQ_20_X = 20.0 ** 2 # 400.0  (pour alignement orthogonal)
```

Fonctions impactées :
- `_check_interactive_emote()` : `dist >= range_dist` → `sq_dist >= _RANGE_SQ_48`
- `_check_pickup_emote()` : idem
- `_check_npc_emote()` : idem
- `_check_pickup_interactions()` : `dist >= range_dist` → `sq_dist >= _RANGE_SQ_48` ; `dist < 16` → `sq_dist < _RANGE_SQ_16`
- `_check_object_interactions()` : `dist < 16` → `sq_dist < _RANGE_SQ_16` ; `dist < 48` → `sq_dist < _RANGE_SQ_48` ; `dist < 45` → `sq_dist < _RANGE_SQ_45`
- `_check_chest_auto_close()` : `dist > 45` → `sq_dist > _RANGE_SQ_45`

**IMPORTANT** : `is_on_top = dist < 16.0` → `is_on_top = sq_dist < _RANGE_SQ_16`
L'utilisation de `distance_to()` pour le `vol_mult` de l'audio RESTE inchangée (besoin de la vraie distance).

### Anti-Patterns (P7)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| `distance_to()` pour les garde-fous de range | `distance_squared_to()` + constantes `_RANGE_SQ_*` | sqrt coûteux pour comparaison |
| Recalculer `range ** 2` inline | Constantes module-level | Évite recalcul à chaque frame |
| Remplacer `distance_to()` dans le calcul du `vol_mult` audio | Laisser `distance_to()` pour l'audio | Vol audio nécessite distance réelle |
| Nommer les constantes `DIST_48` | Nommer `_RANGE_SQ_48` | Évite confusion distance vs distance² |

### Test Case Specifications (P7)

| TC ID | Composant | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| TC-022 | `_check_interactive_emote` | obj à dist=47 | emote déclenchée | dist exactement = 48 : pas d'emote |
| TC-023 | `_check_interactive_emote` | obj à dist=49 | pas d'emote | dist=0 : is_on_top |
| TC-024 | `_check_pickup_emote` | pickup à dist=15 | emote déclenchée (is_on_top) | dist=16 : alignement requis |
| TC-025 | `_check_object_interactions` | obj à dist=44 | interaction valide | dist=45 : invalide |
| TC-026 | `_check_chest_auto_close` | dist=46 | chest fermé | dist=44 : chest reste ouvert |
| TC-027 | audio vol_mult | dist calculé | vol_mult entre 0.4 et 1.0 | utilise `distance_to()` (pas sq) |

### Error Handling Matrix (P7)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| `distance_squared_to` absent (pygame old) | N/A — pygame-ce 2.5.7 confirmé | N/A | N/A |

---

## Module 5 — `src/entities/interactive.py` (P9, P13, P14)

### Décisions d'implémentation

**P9 — Éliminer `.copy()` dans `draw_effects()`**

Remplacer le pattern `copy()` + `fill(MULT)` par blit avec `set_alpha()` :
```python
# Avant
render_surf = self.light_mask_cache[scale_idx].copy()
m = max(0, min(255, int(round(255 * global_factor * self.f_alpha))))
if m < 255: render_surf.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)

# Après
render_surf = self.light_mask_cache[scale_idx]
m = max(0, min(255, int(round(255 * global_factor * self.f_alpha))))
render_surf.set_alpha(m)
surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)
```

**IMPORTANT** : `set_alpha()` sur une Surface sans SRCALPHA est un alpha global (surface-level), ce qui est
fonctionnellement équivalent au `BLEND_RGB_MULT` avec valeur uniforme `(m, m, m)`.
Les `light_mask_cache` surfaces sont créées avec `pygame.Surface(...)` (sans SRCALPHA) → `set_alpha()` est applicable.

**P13 — `pygame.time.get_ticks()` une fois par frame**

Dans `Game._update()`, calculer `_ticks_ms = pygame.time.get_ticks()` avant la boucle interactives.
Passer via `entity.update(dt, ticks_ms=self._ticks_ms)`.

Modifier la signature de `InteractiveEntity.update(dt, ticks_ms=None)`.
Fallback : `ticks = ticks_ms if ticks_ms is not None else pygame.time.get_ticks()`.

**P14 — Supprimer l'allocation Surface dans le rendu particules**

```python
# Avant (ligne 405)
surface.blit(pygame.Surface((p['size']*2, p['size']*2)), (int(p['x'] + cam_offset.x), ...))
pygame.draw.circle(surface, color, ...)

# Après — supprimer la ligne blit, garder uniquement draw.circle
pygame.draw.circle(surface, color, (int(p['x'] + cam_offset.x), int(p['y'] + cam_offset.y)), p['size'])
```

La ligne `surface.blit(pygame.Surface(...))` blit une surface noire sans blend flag → aucun effet visuel.

### Anti-Patterns (P9, P13, P14)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| `.copy()` sur light_mask_cache par frame | `set_alpha()` sur surface existante | Évite allocation Surface |
| `get_ticks()` par entité | Passer `ticks_ms` depuis `Game._update()` | 1 appel SDL vs N appels |
| `blit(Surface(...))` noir sans blend | Supprimer la ligne | Opération sans effet visuel |
| Changer la signature `update(dt)` sans fallback | `update(dt, ticks_ms=None)` | Rétrocompatibilité tests |

### Test Case Specifications (P9, P13, P14)

| TC ID | Composant | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| TC-028 | `draw_effects` | entité lumineuse, dark_factor=1.0 | `set_alpha(255)` appelé, pas de `.copy()` | m=255 : set_alpha(255) |
| TC-029 | `draw_effects` | `global_darkness=0` | `set_alpha` avec m=`int(0.15*255)` | dark_factor=0 → 0.15 floor |
| TC-030 | `update(dt, ticks_ms=500)` | entité lumineuse non-animée | `ticks_ms` utilisé pour `time_sec` | ticks_ms=None → get_ticks() |
| TC-031 | `draw_effects` | particules actives | `pygame.Surface` non alloué dans la boucle particules | 0 particules : pas d'appel |
| TC-032 | `update(dt)` | appel sans ticks_ms | fallback sur `get_ticks()` | signature rétrocompatible |

### Error Handling Matrix (P9, P13, P14)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| Surface sans support `set_alpha` | N/A — pygame.Surface toujours supporté | N/A | N/A |
| `ticks_ms=None` passé | Check `if ticks_ms is not None` | Fallback `pygame.time.get_ticks()` | None |

---

## Module 6 — `src/engine/game.py` (P11, P12)

### Décisions d'implémentation

**P11 — Supprimer code mort**

Les méthodes suivantes dans `game.py` ne sont jamais appelées (remplacées par `RenderManager`) :
- `_draw_background()` (lignes 429–460)
- `_draw_foreground()` (lignes 462–482)
- `_draw_hud()` (lignes 484–486)

Suppression pure. Aucun impact fonctionnel.

**P12 — Pre-allouer `_viewport_world_rect`**

Dans `Game.__init__()` après création de `self.screen` :
```python
self._viewport_world_rect = pygame.Rect(0, 0, Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT)
```

Dans `_update()` — remplacer les 3 lignes de création par mise à jour in-place :
```python
offset = self.visible_sprites.offset
self._viewport_world_rect.x = -int(offset.x) - 128
self._viewport_world_rect.y = -int(offset.y) - 128
self._viewport_world_rect.width = self.screen.get_width() + 256
self._viewport_world_rect.height = self.screen.get_height() + 256
```

### Anti-Patterns (P11-P12)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Garder `_draw_background/foreground/hud` dans `game.py` | Les supprimer | Code mort → confusion + maintenance |
| `screen.get_rect().move(...)` chaque frame | Pre-allouer + mise à jour in-place | 2 allocations Rect évitées |
| `inflate_ip` sur un Rect créé inline | Appliquer les marges dans les valeurs init | Même résultat, 0 allocation |

### Test Case Specifications (P11-P12)

| TC ID | Composant | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| TC-033 | `Game.__init__` | init sans map | `_viewport_world_rect` existe | `skip_map_load=True` |
| TC-034 | `_update()` | offset=(−100, −50) | `_viewport_world_rect.x == -28, y == 22` (−(−100)−128=−28) | offset=0 |
| TC-035 | méthodes supprimées | `hasattr(game, '_draw_background')` | `False` | N/A |
| TC-036 | `_active_torches` | init | `set()` vide | N/A |

### Error Handling Matrix (P11-P12)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| offset non-entier | `int(offset.x)` | Conversion explicite | None |

---

## Integration Tests

| TC ID | Flow | Setup | Verification | Teardown |
|-------|------|-------|--------------|----------|
| IT-001 | TitleScreen draw loop sans transform | Init TitleScreen avec BACKGROUND_LIGHTS non vide, appeler `draw()` 10× | `pygame.transform.rotozoom` n'est PAS appelé ; `_light_halos_scaled` utilisé | N/A |
| IT-002 | Interaction distance_squared vs distance_to sémantique équivalente | Configurer obj à dist=45 et dist=47 du player, appeler `_check_interactive_emote()` | dist=47 → emote ; dist=45+ → no emote (même comportement qu'avant migration) | N/A |
| IT-003 | Game._update NPC visibility avec rect pré-alloué | Créer Game mocké avec 3 NPCs à positions variées, appeler `_update()` 2× avec offset différent | `_viewport_world_rect` réutilisé (même objet id), `npc.is_visible` mis à jour correctement | N/A |

---

## Deep Links

- **Audit source** : [performance_audit.md](../../.gemini/antigravity/brain/fcb4f254-aa2a-4df8-a2c4-670ad9e422b1/performance_audit.md#L1)
- **TitleScreen** : [title_screen.py L1](../../src/ui/title_screen.py#L1)
- **TitleScreen constants** : [title_screen_constants.py L1](../../src/ui/title_screen_constants.py#L1)
- **CameraGroup** : [groups.py L51](../../src/entities/groups.py#L51)
- **RenderManager** : [render_manager.py L1](../../src/engine/render_manager.py#L1)
- **InteractionManager** : [interaction.py L1](../../src/engine/interaction.py#L1)
- **InteractiveEntity.update** : [interactive.py L308](../../src/entities/interactive.py#L308)
- **Game._update** : [game.py L637](../../src/engine/game.py#L637)
- **Tests title screen** : [test_title_screen.py L1](../../tests/ui/test_title_screen.py#L1)
- **Tests interaction** : [test_interaction.py L1](../../tests/engine/test_interaction.py#L1)
- **Tests render manager** : [test_render_manager.py L1](../../tests/engine/test_render_manager.py#L1)
- **Tests entities** : [test_lighting.py L1](../../tests/engine/test_lighting.py#L1)
