# Specification: Stair Movement Mechanics

> Document type: Implementation

**Covers:** Stair Movement Feature — horizontal stairs (escaliers latéraux).
**Extension future:** Cette architecture supporte aussi les échelles (`ladder`) via la même classe Tiled.
**Revision:** v4 — post adversarial review corrections 2026-06-10.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run tests before committing. Validate `MapManager` property lookups gracefully (bounds check). |
| **Ask first** | Changing existing `get_direction_flags` signature. Changing `TileMapData` fields. |
| **Never do** | Modify `self.rect` for visual offsets. Reuse the `direction` property name for stair direction (collision with `direction_flags` system). Remove existing collision logic in `BaseEntity`. |

## Cross-Spec Contracts

### Produces

| Artifact | Type | Consommateurs |
|----------|------|---------------|
| `MapManager.get_vertical_move_props(tx, ty) → dict \| None` | Nouvelle méthode | map-world-system, npc-system |
| `BaseEntity._vertical_move: dict \| None` | Nouveau champ | camera-rendering |
| `VERTICAL_MOVE_MAP` | Nouvelle constante | engine-core |

### Consumes

| Artifact | Source | Usage |
|----------|--------|-------|
| `MapManager.tiles[id].properties` | map-world-system | Lecture de `stair_direction` dans `get_vertical_move_props` |
| `BaseEntity.start_move()` | entities-system | Point d'insertion de l'interception escalier |
| `CameraGroup.custom_draw()` | camera-rendering | Point d'insertion du `visual_y_offset` |
| `MapManager.get_direction_flags()` | map-world-system | Appelé APRÈS l'interception (ordre critique) |

### Public Interface

| Interface | Signature | Contrat |
|-----------|-----------|--------|
| `get_vertical_move_props` | `(tx: int, ty: int) → dict \| None` | Retourne `{stair_direction, movement_type, visual_y_offset}` ou `None` |
| `_vertical_move` | `dict \| None` | Mis à jour dans `start_move()` uniquement. Lu dans `custom_draw()` |
| `VERTICAL_MOVE_MAP` | `dict[tuple[tuple[int,int], str], tuple[int,int]]` | 4 mappings (input_dir, stair_dir) → intercepted_dir |

---

## 0. Tiled Configuration — Classe `01-vertical-move`

### 0.1 Pourquoi une classe dédiée

**Problème de collision de nom (VÉRIFIÉ dans le code) :** Le parser `tmj_parser.py` (L307-308) utilise `props["direction"]` pour construire `direction_flags` — le système qui contrôle quelles directions de sortie sont autorisées sur une tuile. Placer `direction="right"` sur une tuile d'escalier serait interprété comme "bloquer tout mouvement sauf vers la droite", cassant complètement la logique de déplacement.

**Solution :** La classe Tiled `01-vertical-move` avec un champ `stair_direction` (nom distinct) remplace `01-tileset_ground` pour les tilesets de déplacement vertical.

### 0.2 Définition de la classe Tiled `01-vertical-move` (IMPLÉMENTÉE)

Présente dans `game.tiled-project` (id=24) :

```json
{
    "id": 24,
    "members": [
        {"name": "depth",          "type": "int",    "value": 0},
        {"name": "material",       "type": "string", "value": ""},
        {"name": "movement_type",  "propertyType": "25-movement_type", "type": "string", "value": "stair"},
        {"name": "stair_direction","propertyType": "23-direction",     "type": "string", "value": ""},
        {"name": "visual_y_offset","type": "int",    "value": -12},
        {"name": "walkable",       "type": "bool",   "value": true}
    ],
    "name": "01-vertical-move",
    "type": "class"
}
```

**Champs :**
- `stair_direction` (enum `23-direction`, **défaut `""`**) : `"right"` = escalier montant vers la droite, `"left"` = montant vers la gauche. **Défaut vide = tuile neutre, pas un escalier.** Jamais `"any"` sur une tuile d'escalier.
- `movement_type` (enum `25-movement_type`, défaut `"stair"`) : `"stair"` | `"ladder"` — pour l'extension future.
- `visual_y_offset` (int, défaut `-12`) : décalage Y visuel en pixels lors du rendu sur cette tuile. Ajustable par tileset.
- `walkable` (bool, défaut `true`) : `false` sur les tuiles-murs. Géré par le système `is_walkable()` existant.
- `depth` (int, défaut `0`) : profondeur de rendu, identique à `00-tileset`.
- `material` (string, défaut `""`) : matériau pour les sons de pas.

### 0.3 Application dans `01-stairs.tsx` (VÉRIFIÉE — audit 2026-06-10)

**Comportement réel du parser (VÉRIFIÉ — tmj_parser.py L295-298) :**
Le tileset a `class="01-vertical-move"` dans son attribut XML, mais le parser (`_parse_tileset_properties`) ne résout PAS les classes Tiled via `TiledProject.resolve()` pour les tilesets (uniquement pour les objets, L108). Il lit uniquement les nœuds `<properties>` XML du TSX — et `01-stairs.tsx` n'en a PAS au niveau tileset.

**Conséquence :** `tileset_props = {}`. Seules les propriétés explicitement surchargées par tuile (nœuds `<property>` dans `<tile>`) apparaissent dans `tile.properties`. Les défauts de classe (`movement_type`, `visual_y_offset`) sont **absents**.

Résultat réel dans `tile.properties` :

```python
# Tuile marche droite (ex: id 0)
{
    "walkable": True,            # fallback hardcodé (_parse_tile_properties_and_anims L241)
    "depth": 0,                  # fallback hardcodé (L242)
    "direction": "any",          # fallback hardcodé (L243)
    "material": "stone",         # override explicite dans TSX
    "stair_direction": "right",  # override explicite dans TSX
    # ⚠️ "movement_type" et "visual_y_offset" sont ABSENTS
}

# Tuile neutre / vide (ex: id 4) — aucun nœud <tile> dans le TSX
{
    "walkable": True,            # fallback hardcodé (_process_single_tile L297)
    "depth": 0,                  # fallback hardcodé (L298)
    # ⚠️ "stair_direction" est ABSENT → get_vertical_move_props retourne None ✅
}
```

**Impact sur `get_vertical_move_props` :** La méthode gère l'absence via des valeurs par défaut :
- `props.get("movement_type", "stair")` → retourne `"stair"` ✅
- `int(props.get("visual_y_offset", -12))` → retourne `-12` ✅

Ces fallbacks codés en dur **doivent correspondre** aux défauts de la classe Tiled `01-vertical-move`. Si les défauts Tiled changent, les fallbacks doivent être mis à jour.

**Inventaire complet des tuiles (VÉRIFIÉ) :**

| Tuile(s) | Rôle | `walkable` | `stair_direction` |
|---------|------|-----------|------------------|
| 0, 6, 12, 18, 19, 24, 25, 30, 31 | 🪜 Marches droites | `True` | `"right"` (override explicite) |
| 1, 8, 14, 20, 21, 26, 27, 32, 33 | 🪜 Marches gauches | `True` | `"left"` (override explicite) |
| 2, 7, 13 | 🧱 Murs de l'escalier | `False` | `""` (hérité — ignoré car non-walkable) |
| 3, 4, 5, 9, 10, 11, 15, 16, 17, 22, 23, 28, 29, 34, 35 | ⬜ Neutres / vides | `True` | `""` (hérité — pas un escalier) |

**Règle de détection d'un escalier dans le code :**
`stair_direction` est non-vide ET non-None → tuile d'escalier.
`stair_direction == ""` → tuile neutre, `get_vertical_move_props` retourne `None`.

### 0.4 Détection des murs d'escalier

La détection des murs utilise le système existant `is_walkable()` dans `MapManager`. Les tuiles avec `walkable=false` (id 2, 7, 13) bloquent le mouvement via `walkable_func` dans `start_move`. Aucune propriété supplémentaire n'est nécessaire pour les murs : le système existant suffit.

### 0.5 Limitation du parser — résolution de classe TSX

Le parser `tmj_parser.py` ne résout PAS l'attribut `class=` sur les tilesets via `TiledProject.resolve()`. Les propriétés de classe non-surchargées (`movement_type`, `visual_y_offset`) ne sont pas disponibles dans `tile.properties`.

**Stratégie retenue :** Plutôt que de modifier le parser (impact sur tous les tilesets), la méthode `get_vertical_move_props` utilise des **valeurs par défaut codées en dur** qui correspondent aux défauts de la classe Tiled :

| Propriété | Défaut classe Tiled | Fallback dans `get_vertical_move_props` | Correspond ? |
|-----------|--------------------|-----------------------------------------|--------------|
| `movement_type` | `"stair"` | `props.get("movement_type", "stair")` | ✅ |
| `visual_y_offset` | `-12` | `int(props.get("visual_y_offset", -12))` | ✅ |
| `stair_direction` | `""` | `props.get("stair_direction", "")` | ✅ |

**Risque :** Si les défauts de la classe Tiled changent, les fallbacks dans le code doivent être mis à jour manuellement. Accepté car la classe Tiled est stable et les fallbacks sont centralisés dans une seule méthode.

---

## 1. Core Logic & Movement Interception

### 1.1 Table de mapping `VERTICAL_MOVE_MAP` (dans `config.py`)

Remplace le mapping hardcodé dans `start_move`. À ajouter dans `Settings` :

```python
# Maps (input_direction, stair_direction) → intercepted_direction
VERTICAL_MOVE_MAP: dict[tuple[tuple[int, int], str], tuple[int, int]] = {
    ((1, 0), "right"):  (1, -1),   # Droite sur escalier droit → montée diagonale
    ((-1, 0), "right"): (-1, 1),   # Gauche sur escalier droit → descente diagonale
    ((1, 0), "left"):  (1, 1),    # Droite sur escalier gauche → descente diagonale
    ((-1, 0), "left"):  (-1, -1),  # Gauche sur escalier gauche → montée diagonale
    # Extension future :
    # ((0, 1), "up"): (0, 1),   # Haut sur échelle → montée verticale (même tile_size, Y inversé pygame)
}
```

### 1.2 `MapManager` — nouvelle méthode `get_vertical_move_props`

```python
def get_vertical_move_props(self, tx: int, ty: int) -> dict | None:
    """
    Return vertical movement properties for the tile at (tx, ty), or None.

    Scans all layers at (tx, ty). Returns the first tile that has a
    'stair_direction' property (indicating a 25-vertical-move class tile).

    Returns:
        dict with keys 'stair_direction' (str), 'movement_type' (str),
        'visual_y_offset' (int) — or None if not a vertical-move tile.
    """
    if not (0 <= ty < self.height and 0 <= tx < self.width):
        return None

    for layer_id in reversed(self.layer_order):
        if layer_id not in self.layers:
            continue
        tile_id = self.layers[layer_id][ty][tx]
        if tile_id == 0 or tile_id not in self.tiles:
            continue
        tile = self.tiles[tile_id]
        props = tile.properties or {}
        stair_dir = props.get("stair_direction", "")
        if stair_dir:  # Non-empty string → explicit stair tile
            return {
                "stair_direction": stair_dir,
                "movement_type": props.get("movement_type", "stair"),
                "visual_y_offset": int(props.get("visual_y_offset", -12)),
            }
    return None  # "" or absent → neutral tile, not a stair
```

**Ordre de scan :** reversed(layer_order) = top-to-bottom → la tuile d'escalier la plus haute dans la pile de layers est retournée.

### 1.3 `BaseEntity` — flag `_vertical_move` et modification de `start_move()`

**Nouveau champ dans `__init__` :**
```python
self._vertical_move: dict | None = None  # Props 25-vertical-move de la tuile courante
```

**Ordre d'exécution dans `start_move()` (CRITIQUE — l'interception escalier doit être AVANT `get_direction_flags`) :**

```
1. Calcul de current_tx, current_ty
2. ── [NOUVEAU] ── Query get_vertical_move_props(current_tx, current_ty)
   a. Si tuile est un escalier :
      - Si input_dir == (0, 0) : laisser passer
      - Sinon : lookup VERTICAL_MOVE_MAP[(input_dir, stair_direction)]
        → Si mapping trouvé : remplacer self.direction par la direction interceptée
        → Si pas de mapping : reset direction + return (blocage silencieux complet de tout input non-géré, y compris diagonales)
      - Mettre à jour self._vertical_move avec les props
   b. Sinon (sol normal) : self._vertical_move = None
3. Check get_direction_flags (existant) — s'applique sur la direction DÉJÀ interceptée
4. Calcul target_pos = self.pos + self.direction * TILE_SIZE  (direction peut être diagonale)
5. World boundary clamping (existant)
6. Check walkable_func (existant) — vérifie la tuile cible diagonale
7. Set is_moving = True
```

**Pourquoi l'interception AVANT `get_direction_flags` :** Le check `get_direction_flags` utilise la direction demandée pour décider si le mouvement est autorisé. Si on vérifie `"right"` contre les flags d'une tuile d'escalier, et que la tuile a `direction="any"` (défaut), ça passe. Mais si l'ordre était inversé, une tuile d'escalier avec des flags restrictifs bloquerait avant l'interception.

### 1.4 Rendering — `visual_y_offset` via flag (PAS par frame)

**Anti-Pattern résolu :** La section précédente disait "update per frame". C'est incorrect et contradictoire avec l'Anti-Pattern #4.

**Règle définitive :** `self._vertical_move` est mis à jour UNIQUEMENT dans `start_move()` (une fois par déplacement). Le rendu lit `self._vertical_move["visual_y_offset"]` si non-None, sinon 0.

**Point d'intégration : `CameraGroup.custom_draw()`** ([groups.py#L94](file:///Users/adrien.parasote/Documents/perso/game/game/src/entities/groups.py#L94))

La modification se fait dans la méthode `custom_draw()` de `CameraGroup`, qui est le propriétaire du pipeline de rendu des entités (voir `camera-rendering.md`). Le code actuel (L124-129) :

```python
# Code actuel (groups.py L121-129)
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
offset_pos = visual_rect.topleft + self.offset
# ... culling ...
surface.blit(sprite.image, offset_pos)
```

Modification à appliquer — ajout du `y_offset` dans `offset_pos` :

```python
# Code modifié
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)

# ── [NOUVEAU] ── Décalage visuel escalier
stair_y_offset = 0
vm = getattr(sprite, '_vertical_move', None)
if vm is not None:
    stair_y_offset = vm["visual_y_offset"]

offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)
# ... culling avec offset_pos ...
surface.blit(sprite.image, offset_pos)
```

**Note :** `sprite.rect` n'est PAS modifié. La physique de collision reste intacte. `getattr` avec fallback `None` assure la compatibilité avec les sprites qui n'ont pas `_vertical_move` (obstacles, décorations).

**Limitation assumée (Snap Visuel) :** Étant donné que `_vertical_move` est mis à jour au début du déplacement en fonction de la tuile d'origine, le `y_offset` s'applique de façon binaire. Lorsqu'une entité commence à marcher depuis le sol vers un escalier, elle n'a pas d'offset. Lorsqu'elle s'arrête sur l'escalier puis entame son prochain pas, l'offset de `-12` s'applique d'un coup, créant un "snap" visuel de 12 pixels vers le haut. L'inverse se produit en sortant de l'escalier. Cette discontinuité esthétique est acceptée pour cette version afin d'éviter des calculs d'interpolation complexes par frame.

**Transition stair→floor :** Quand l'entité arrive sur une tuile normale et commence son déplacement suivant, `start_move()` met `self._vertical_move = None` → `stair_y_offset = 0` instantanément au prochain rendu.

---

## 2. NPC Pathfinding

### 2.1 Compatibilité avec le système actuel

L'interception dans `start_move()` s'applique à tous les `BaseEntity`. Si le pathfinder NPC génère des steps tile-by-tile sous forme de vecteurs directionnels `(1,0)`, `(-1,0)` etc. (ce qui est le cas standard), l'interception les corrige automatiquement en diagonal quand l'entité se trouve sur un escalier.

**Condition requise :** Le pathfinder doit opérer en grid-steps (direction vers la tuile suivante), pas en trajectoire pixel-directe. Si le pathfinder calcule un vecteur direct `(target_px - pos_px)`, il contournera `start_move()` et l'interception ne s'appliquera pas.

### 2.2 Coût diagonal dans l'algorithme A\*

Si le pathfinder utilise A\*, le coût d'une tuile d'escalier doit refléter le déplacement réel :
- Un pas diagonal couvre `√2 × TILE_SIZE` pixels mais coûte `1 tile` en temps de grille.
- Si A\* calcule les distances en tiles, les escaliers sont transparents (coût identique).
- Si A\* calcule les distances en pixels, ajouter un coût `√2` pour les tuiles avec `stair_direction`.

**[Tiled Author Task]** : Pas de configuration supplémentaire requise à ce stade si le pathfinder est grid-based. À réévaluer si les NPCs contournent les escaliers.

### 2.3 Cas limite : NPC arrive à destination en haut d'escalier

Si la cible NPC est une tuile au-delà du haut de l'escalier, le NPC traverse normalement via l'interception. Si la cible EST sur l'escalier, le NPC s'arrête à la position correcte (grid-alignée).

---

## 3. Anti-Patterns

| # | Anti-Pattern | Violation | Comportement correct |
|---|-------------|-----------|---------------------|
| 1 | Réutiliser `direction` pour la direction d'escalier | `direction` est réservé à `direction_flags` (tmj_parser.py L307). Placer `direction="right"` bloquerait tout mouvement sauf vers la droite. | Utiliser exclusivement `stair_direction`. |
| 2 | Modifier `self.rect` pour l'offset visuel | Casse la physique de collision. `rect` est utilisé pour le positionnement grid et la détection de collision. | Appliquer l'offset uniquement dans `offset_pos` lors du `blit()` dans `custom_draw()`. |
| 3 | Restreindre l'interception au Player | Tout `BaseEntity` passe par `start_move()`. Restreindre au Player empêcherait les NPCs de monter les escaliers. | L'interception dans `start_move()` s'applique à toutes les entités automatiquement. |
| 4 | Appeler `get_vertical_move_props` dans `update()` ou `move()` | Crée un appel par frame au lieu d'un appel par déplacement. Impact perf inutile. | Une seule lecture dans `start_move()`, résultat stocké dans `self._vertical_move`. |
| 5 | Inférer un escalier depuis les couches visuelles | Les couches visuelles peuvent contenir des décorations sans propriétés d'escalier. | Se baser uniquement sur `stair_direction` dans `tile.properties`. |
| 6 | Vérifier `get_direction_flags` AVANT l'interception escalier | La direction interceptée (diagonale) serait vérifiée contre les flags de la tuile source — risque de blocage incorrect. | L'interception escalier est toujours AVANT `get_direction_flags` dans `start_move()`. |
| 7 | Placer `stair_direction` non-vide sur des tuiles-murs | Les tuiles avec `walkable=false` ne doivent pas avoir de direction d'escalier. | `walkable=false` bloque le mouvement via `is_walkable()`. `stair_direction` reste vide sur les murs. |
| 8 | Supposer que `movement_type`/`visual_y_offset` sont dans `tile.properties` | Le parser ne résout pas les classes TSX (§0.5). Ces propriétés sont absentes sauf override explicite. | Utiliser `props.get("movement_type", "stair")` et `props.get("visual_y_offset", -12)` avec fallbacks. |

---

## 4. Error Handling Matrix

| Error State | Cause | Handling | Verification |
|-------------|-------|----------|--------------|
| Tile has no `stair_direction` property | Normal floor tile | `get_vertical_move_props` returns `None`. `self._vertical_move = None`. Movement normal. | VERIFIED (tmj_parser.py defaults) |
| `stair_direction` value not in `VERTICAL_MOVE_MAP` | Config manquante ou direction non-gérée | `start_move` laisse passer sans interception (mouvement orthogonal normal). Log WARNING. | ASSUMED |
| `get_vertical_move_props` called out of bounds | tx/ty hors carte | Bounds check en tête de fonction → retourne `None`. | SPECIFIED |
| Diagonal target not walkable | Tuile cible `walkable=False` | `walkable_func` remet `target_pos = self.pos`. Mouvement annulé silencieusement. | VERIFIED (base.py L101-104) |
| `self.game` or `map_manager` absent | Tests unitaires sans contexte | Guard existant `hasattr(self.game, "map_manager")` → skip. | VERIFIED (base.py L69) |
| `movement_type` inconnu (ex: `"ladder"`) | Extension non implémentée | Traité identiquement à `"stair"` par `VERTICAL_MOVE_MAP` (même clé). Extension future. | ASSUMED |

---

## Assumptions

| # | Hypothèse | Risque | Source Type | Gestion |
|---|-----------|--------|-------------|---------|
| A1 | `stair_direction` est dans `tile.properties` pour les tuiles avec override explicite dans le TSX | Faible | SHOW | VÉRIFIÉ — les 18 tuiles d'escalier ont un `<property>` explicite dans le TSX |
| A2 | `movement_type` et `visual_y_offset` sont absents de `tile.properties` (parser ne résout pas la classe TSX) | Moyen | SHOW | Géré via fallbacks hardcodés dans `get_vertical_move_props` qui correspondent aux défauts de classe (§0.5) |
| A3 | Le pathfinder NPC opère en grid-steps (direction vers la tuile suivante), pas en trajectoire pixel-directe | Moyen | SHOW | VÉRIFIÉ — npc.py L125-131 (process_ai) utilise des choix de vecteurs orthogonaux unitaires. |
| A4 | `TileMapData.properties` (champ existant, type `dict[str, Any] or None`) est le point d'accès. Aucune modification de schéma de `TileMapData` n'est nécessaire | Faible | SHOW | VÉRIFIÉ — le champ existe déjà (tmj_parser.py L20) |
| A5 | Le "snap" visuel de 12 pixels lors de la transition sol ↔ escalier est esthétiquement acceptable pour le moment, évitant de complexifier le rendu avec de l'interpolation. | Moyen | TELL | Tolérance assumée. Documenté dans §1.4. |

---

## 5. Test Case Specifications

### Unit Tests (`game/tests/entities/test_stair_movement.py`)

**MapManager :**
- `UT-001`: `get_vertical_move_props(tx, ty)` retourne `{"stair_direction": "right", "movement_type": "stair", "visual_y_offset": -12}` sur mock tile avec `stair_direction="right"`.
- `UT-002`: `get_vertical_move_props(tx, ty)` retourne `None` sur tuile sans `stair_direction`.
- `UT-003`: `get_vertical_move_props(-1, 0)` retourne `None` (out of bounds — bounds check).
- `UT-004`: `get_vertical_move_props(tx, ty)` retourne `None` sur tuile avec `direction="right"` mais sans `stair_direction` (vérifie qu'il n'y a pas de confusion de noms).

**BaseEntity — start_move sur escalier droit (`stair_direction="right"`) :**
- `UT-005`: Input `(1, 0)` → `direction` interceptée à `(1, -1)`, `target_pos` = `(pos.x+32, pos.y-32)`, `is_moving = True`.
- `UT-006`: Input `(-1, 0)` → `direction` interceptée à `(-1, 1)`, `target_pos` = `(pos.x-32, pos.y+32)`.
- `UT-007`: Input `(0, -1)` (Haut) → `is_moving` reste `False`, `direction` reset à `(0, 0)`. Blocage silencieux.
- `UT-008`: Input `(1, 1)` (Diagonale non-mappée) → `is_moving` reste `False`, `direction` reset à `(0, 0)`. Blocage silencieux (empêche la sortie diagonale).

**BaseEntity — start_move sur escalier gauche (`stair_direction="left"`) :**
- `UT-009`: Input `(-1, 0)` → direction interceptée à `(-1, -1)`, `target_pos` = `(pos.x-32, pos.y-32)`.
- `UT-010`: Input `(1, 0)` → direction interceptée à `(1, 1)`, `target_pos` = `(pos.x+32, pos.y+32)`.

**BaseEntity — transitions :**
- `UT-011`: Entité sur sol normal → `_vertical_move` est `None`. Input `(1, 0)` → mouvement orthogonal normal `(pos.x+32, pos.y)`.
- `UT-012`: Entité quitte une tuile d'escalier vers sol normal → `_vertical_move` est `None` après `start_move()`. Offset visuel = 0.
- `UT-013`: `walkable_func` retourne `False` pour la cible diagonale → `target_pos` = `pos`, `is_moving = False` (escalier bloqué par mur).

**Rendering offset :**
- `UT-014`: `_vertical_move = {"visual_y_offset": -12, ...}` → `draw_pos.y = entity.rect.y - 12`. `entity.rect.y` inchangé.
- `UT-015`: `_vertical_move = None` → `draw_pos.y = entity.rect.y` (pas d'offset).

**VERTICAL_MOVE_MAP (config) :**
- `UT-016`: `VERTICAL_MOVE_MAP[((1, 0), "right")] == (1, -1)` — vérifie que la table est correcte pour les 4 combinaisons.

### Integration Tests (`game/tests/integration/test_stairs_integration.py`)

- `IT-001`: Charger une mini-map avec une tuile `stair_direction="right"`. Spawner le joueur dessus. Input Droite. Asserter que `pos == (initial.x + 32, initial.y - 32)` et `is_moving = False` (déplacement terminé).
- `IT-002`: Même setup. Asserter que `_vertical_move["visual_y_offset"] == -12` pendant le mouvement, puis `_vertical_move = None` après avoir atteint une tuile sol.
- `IT-003`: Mini-map avec 3 tuiles d'escalier successives (`stair_direction="right"`). Joueur traverse les 3 tuiles en inputs Droite répétés. Asserter que la position finale est `(x + 96, y - 96)` (3 × diagonal).
- `IT-004`: Mini-map avec escalier entouré de murs (`walkable=False`). Input Haut sur tuile d'escalier → `is_moving = False`. Input Bas → `is_moving = False`.
- `IT-005`: NPC avec pathfinding vers une tuile au-delà d'un escalier. Asserter que le NPC traverse l'escalier en diagonale (via l'interception `start_move()`) sans se bloquer.
- `IT-006`: Tuile avec `direction="right"` (sans `stair_direction`) → `get_vertical_move_props` retourne `None`. Pas d'interception. Vérifie l'isolation du système `direction_flags`.

---

## 6. Deep Links

- `MapManager`: [game/src/map/manager.py#L1](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/manager.py#L1) — `get_direction_flags` (L119), nouveau `get_vertical_move_props`
- `BaseEntity`: [game/src/entities/base.py#L1](file:///Users/adrien.parasote/Documents/perso/game/game/src/entities/base.py#L1) — `start_move()` (L62), nouveau `_vertical_move`
- `CameraGroup.custom_draw`: [game/src/entities/groups.py#L94](file:///Users/adrien.parasote/Documents/perso/game/game/src/entities/groups.py#L94) — point d'intégration rendering y_offset (L121-129)
- `TmjParser._parse_tileset_properties`: [game/src/map/tmj_parser.py#L189](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/tmj_parser.py#L189) — lit les `<properties>` XML (ne résout PAS `class=`)
- `TmjParser._parse_tile_properties_and_anims`: [game/src/map/tmj_parser.py#L230](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/tmj_parser.py#L230) — fallbacks walkable/depth/direction (L241-243)
- `TmjParser._process_single_tile`: [game/src/map/tmj_parser.py#L276](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/tmj_parser.py#L276) — construction de `direction_flags` depuis `props["direction"]` (L307-308)
- `Settings` (config): [game/src/config.py#L1](file:///Users/adrien.parasote/Documents/perso/game/game/src/config.py#L1) — `VERTICAL_MOVE_MAP`
- Tileset escaliers: [assets/tiled/tiles/01-stairs.tsx#L1](file:///Users/adrien.parasote/Documents/perso/game/assets/tiled/tiles/01-stairs.tsx#L1) — `class="01-vertical-move"`, 36 tuiles
- Tiled Project (classes): [assets/tiled/game.tiled-project#L1](file:///Users/adrien.parasote/Documents/perso/game/assets/tiled/game.tiled-project#L1) — classe `01-vertical-move` (id=24)

## Project Deliverables Tree
```text
├── camera-rendering.md
├── game/tests/entities/test_stair_movement.py
└── game/tests/integration/test_stairs_integration.py
```
