# ADR-007 — Occlusion Partielle : Surface Composite vs Scissor Clip vs API Modifier

**Date :** 2026-05-22
**Statut :** Accepté
**Contexte :** Feature d'occlusion partielle des sprites NPC (sprites > TILE_SIZE)

## Contexte

Les sprites NPC (32×48px) sont plus grands qu'un tile (32×32px). Quand un NPC passe
derrière un tile foreground (depth > player.depth), l'implémentation actuelle applique
`set_alpha()` global sur toute l'image — incorrect visuellement. Il faut rendre seule
la partie du sprite sur le tile concerné en alpha.

Trois approches évaluées.

## Options

### Option A — Surface composite SRCALPHA (retenue)

Pour chaque NPC occludé, créer une surface temporaire `SRCALPHA` aux dimensions du sprite.
Blit opaque complet, puis blit de la zone occludée en alpha via `pygame.Rect.clip()`.

**Avantages :**
- Logique localisée dans `RenderManager.draw_scene()`
- `CameraGroup.custom_draw()` reste inchangé (générique)
- Calcul O(1) par intersection
- Surface allouée seulement si NPC occludé (cas rare)
- Lisible, testable

**Inconvénients :**
- 1 `Surface()` alloc par NPC occludé par frame (≈ 32×48px SRCALPHA)
- Sur 2 NPCs occludés simultanément → 2 petites allocs/frame

### Option B — Modifier `custom_draw()` API

Passer une liste de `(rect, alpha)` zones occludantes à `CameraGroup.custom_draw()`,
gérer le clipping lors du blit de chaque sprite.

**Rejetée car :**
- Couple l'API générique `CameraGroup` au système d'occlusion spécifique
- `custom_draw()` devient non-testable sans mock des zones occludantes
- Violente la SRP : CameraGroup = camera + Y-sort, pas occlusion

### Option C — `pygame.Surface.set_clip()` (scissor)

Utiliser le clipping natif de la surface écran pour séparer les zones opaques/alpha.
`screen.set_clip(opaque_zone)` + blit opaque, puis `screen.set_clip(occluded_zone)` + blit alpha.

**Rejetée car :**
- Logique de complement de rect difficile pour des formes non-rectangulaires
- Risque d'oublier de reset le clip → artefacts graphiques globaux
- Moins lisible que la composition explicite

## Décision

**Option A** — Surface composite SRCALPHA dans `draw_scene()`.

## Conséquences

- `draw_foreground()` change son type de retour : `bool` → `list[pygame.Rect]`
  (les screen-space rects des tiles occludants actifs)
- `draw_scene()` itère sur les sprites du pass 3b pour appliquer l'occlusion partielle
- Tests TC-OCC-001/002 à adapter (bool → truthiness de la liste)
- Player garde son alpha global actuel (inchangé)

## Invariant de performance

`len(occluded_rects)` est borné par le nombre de tiles visibles depth > 1.
Sur le viewport 1280×720 avec tiles 32×32 : max ~1400 tiles visibles,
mais les tiles occludants sont une petite fraction.
Les NPCs occludés simultanément : typiquement 0-2.
Impact perf : négligeable.
