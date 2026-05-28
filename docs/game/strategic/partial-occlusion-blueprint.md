# Blueprint Stratégique — Occlusion Partielle des Sprites Entités

> Document Type: Strategic
> Créé: 2026-05-22

## Problème

Les sprites NPC (32×48px visuellement, 32×32px hitbox) reçoivent un alpha global
(`set_alpha(OCCLUSION_ALPHA)`) dès qu'une partie quelconque de leur sprite chevauche un
tile foreground (depth > player.depth). Ce comportement est visuellement incorrect :
si seuls les pieds du NPC sont derrière un mur, la tête l'est aussi.

**Comportement attendu :** seule la portion du sprite physiquement sur le tile occludant
devient semi-transparente. Le reste reste opaque.

## Métriques de succès

- Partie basse du sprite sur tile depth 2 → alpha visible
- Partie haute du sprite hors tile depth 2 → opaque
- Transition (chevauchement partiel) → split clair et stable
- 60 FPS maintenu (clock.get_fps() > 55 avec 2 NPCs occludés)
- Player : alpha global inchangé — TC-OCC-001/002 restent verts

## Décision architecturale (→ ADR-007)

**Option retenue : Surface composite SRCALPHA par NPC occludé**

Pour chaque NPC dont le sprite visuel intersecte un tile occludant :
1. Créer une surface temporaire `SRCALPHA` aux dimensions du sprite
2. Blit normal de l'image complète (opaque)
3. Pour chaque intersection sprite×tile : dessiner la zone en alpha
4. Blit de la surface composite sur l'écran

Calcul O(1) par intersection via `pygame.Rect.clip()`.
Surface allouée uniquement en cas d'occlusion (cas rare).

**Alternatives rejetées :**
- `set_clip()` sur screen : logique d'inversion difficile à lire
- Modifier `custom_draw()` API : couple trop `groups.py` au système d'occlusion

## Pipeline impacté

```
draw_foreground() → list[pygame.Rect]   ← CHANGE: bool → list (screen-space rects)
draw_scene() → utilise la liste pour le pass 3b NPC
custom_draw() → inchangé (CameraGroup reste générique)
```

## Périmètre des sprites concernés

L'occlusion partielle s'applique à **tous les sprites** du pass 3b (`custom_draw(min_depth=player.depth)`) :
- NPCs (sprite > TILE_SIZE)
- **Player** (même logique, même alpha)
- Interactives si elles ont un sprite plus grand qu'un tile

La logique est générique — pas de traitement spécifique par type d'entité.

## Exclusions explicites

| Exclusion | Rationale |
|---|---|
| Tiles animés foreground | ⚠️ Décision en attente — voir Gap #2 |
| Cache zones occludantes | YAGNI — max 2-3 sprites occludés simultanément |
| Lighting interaction | Alpha sprite n'impacte pas le système de lumières |

## Gaps résolus avant SPEC

| # | Gap | Décision |
|---|---|---|
| 1 | `draw_foreground()` retourne un bool → tests à adapter | Changer le type de retour : `list[pygame.Rect]` (liste vide = pas d'occlusion, évalue à False → rétrocompat partielle) |
| 2 | Tiles animés foreground inclus ? | ✅ **Oui — inclus.** Les tiles animés n'ont pas encore de depth > 1 mais en auront. La collecte des rects occludants scanne `get_visible_animated_chunks()` en plus des statiques. Quand les tiles animés depth > 1 existeront, ça marche automatiquement. |
| 3 | Taille sprite variable dans le futur ? | ✅ **Prévoir** — utiliser `sprite.image.get_size()` dynamiquement à chaque frame, jamais de taille cachée. Surface composite allouée à la taille courante du frame actif. |
| 4 | Player générique ? | ✅ **Oui — player inclus.** La logique est appliquée à tous les sprites du pass 3b. Le player perd son `set_alpha()` global au profit de l'occlusion partielle. |

**Tous les gaps sont résolus. STRATEGY complète. Prêt pour SPEC.**

