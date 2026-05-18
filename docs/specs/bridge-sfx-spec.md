# Technical Specification — Bridge SFX : `material`, `sfx_open`, `sfx_close` [Implementation]

> Document Type: Implementation
> Parent Spec: docs/specs/bridge-subtype-spec.md
> Status: IMPLEMENTED — 2026-05-18

---

## 1. Problem Statement

Trois propriétés ont été ajoutées à la classe Tiled `11-interactive_object` :

| Propriété | Type | Valeur par défaut | Rôle |
|-----------|------|-------------------|------|
| `material` | string | `""` | Matériau sous les pieds du joueur (ex : `"wood"`) pour les footsteps |
| `sfx_open` | string | `""` | SFX à jouer quand `is_on` passe à `True` (pont abaissé) |
| `sfx_close` | string | `""` | SFX à jouer quand `is_on` passe à `False` (pont relevé) |

Ces propriétés sont **définies dans `game.tiled-project`** et **sérialisées dans les `.tmj`** mais **ignorées par le code Python**. Deux symptômes observables :

1. **WARNING répété** : `SFX file not found: assets/audio/sfx/04-footstep_water.ogg` — le joueur marche sur un pont en bois, mais le système lit la tuile d'eau en dessous.
2. **Aucun son** à l'ouverture/fermeture du pont (ni `sfx_open`, ni `sfx_close` ne sont parsés).

---

## 2. Behavioral Contract

### 2.1. `sfx_open` / `sfx_close` — Logique de sélection du SFX

Lors d'un toggle d'état (`interact()` ou `toggle_entity_by_id()`), le SFX joué suit cette priorité :

```
is_on passe à True  → sfx_open  si non vide, sinon sfx (fallback rétrocompat)
is_on passe à False → sfx_close si non vide, sinon sfx (fallback rétrocompat)
sfx_open ET sfx_close vides → sfx (comportement actuel inchangé)
sfx ET sfx_open ET sfx_close vides → aucun son (comportement actuel)
```

La sélection se fait **après** l'appel à `obj.interact()` (qui fait le toggle), donc `entity.is_on` reflète déjà le nouvel état au moment du choix.

### 2.2. `material` — Priorité footstep

Quand le joueur marche sur une entité qui est dans `walkable_override_entities` (pont baissé), le matériau de l'entité remplace le matériau de la tuile de carte sous-jacente.

```
Priorité de résolution du matériau footstep :
  1. Entité walkable_override sous les pieds + entity.material non vide → entity.material
  2. Sinon → map_manager.get_terrain_material_at() (comportement actuel)
```

### 2.3. Invariants

- Si `sfx_open` et `sfx_close` sont tous les deux vides, le comportement est **strictement identique** à l'existant — aucune régression pour les entités existantes (portes, coffres, leviers).
- `material` vide sur une entité override → on retombe sur la tuile, comportement actuel.
- `sfx_open`/`sfx_close` sont appliqués **aussi bien** lors d'une interaction directe du joueur que lors d'un toggle à distance via `target_id`.

---

## 3. Implementation Changes

### 3.1. `src/engine/entity_factory.py` — `spawn_interactive()` (L119-149)

Parser et transmettre les 3 nouvelles propriétés au constructeur `InteractiveEntity`.

**Current (L146-148) :**
```python
sfx=str(_get_property(props, "sfx", "")),
sfx_ambient=str(_get_property(props, "sfx_ambient", "")),
day_night_driven=bool(_get_property(props, "day_night_driven", False)),
```

**New :**
```python
sfx=str(_get_property(props, "sfx", "")),
sfx_open=str(_get_property(props, "sfx_open", "")),
sfx_close=str(_get_property(props, "sfx_close", "")),
sfx_ambient=str(_get_property(props, "sfx_ambient", "")),
material=str(_get_property(props, "material", "")),
day_night_driven=bool(_get_property(props, "day_night_driven", False)),
```

---

### 3.2. `src/entities/interactive.py`

#### 3.2.1. Signature `__init__` (L37-68)

Ajouter 3 paramètres après `sfx_ambient` :

```python
sfx_open: str = "",
sfx_close: str = "",
material: str = "",
```

#### 3.2.2. Appel `_parse_properties` (L72-92)

Transmettre les 3 nouveaux paramètres à `_parse_properties` et `_parse_misc`.

**Current :**
```python
self._parse_properties(
    ...
    sfx,
    sfx_ambient,
    day_night_driven,
)
```

**New :**
```python
self._parse_properties(
    ...
    sfx,
    sfx_open,
    sfx_close,
    sfx_ambient,
    material,
    day_night_driven,
)
```

#### 3.2.3. Signature `_parse_properties` (L134-138)

```python
def _parse_properties(
    self, sub_type, start_row, end_row, is_on, is_animated, depth, position,
    off_position, halo_size, halo_color, halo_alpha, particles, particle_count,
    activate_from_anywhere, sprite_sheet, facing_direction,
    sfx, sfx_open, sfx_close, sfx_ambient, material, day_night_driven,
):
```

Transmettre `sfx_open`, `sfx_close`, `material` à `_parse_misc`.

#### 3.2.4. `_parse_misc` (L206-212)

**Current :**
```python
def _parse_misc(self, particles, particle_count, activate_from_anywhere, sfx, sfx_ambient):
    self.particles = particles
    self.particle_count = particle_count
    self.particles_list = []
    self.activate_from_anywhere = activate_from_anywhere
    self.sfx = sfx
    self.sfx_ambient = sfx_ambient
```

**New :**
```python
def _parse_misc(
    self, particles, particle_count, activate_from_anywhere,
    sfx, sfx_open, sfx_close, sfx_ambient, material
):
    self.particles = particles
    self.particle_count = particle_count
    self.particles_list = []
    self.activate_from_anywhere = activate_from_anywhere
    self.sfx = sfx
    self.sfx_open = sfx_open
    self.sfx_close = sfx_close
    self.sfx_ambient = sfx_ambient
    self.material = material
```

---

### 3.3. `src/engine/interaction.py`

#### 3.3.1. Extraction d'une helper privée `_resolve_sfx`

Évite la duplication de la logique entre `_trigger_object_interaction` et `toggle_entity_by_id`.

```python
@staticmethod
def _resolve_sfx(entity) -> str:
    """Return the SFX name to play after a state toggle.

    Priority: sfx_open/sfx_close (directional) > sfx (generic) > "" (silent).
    The entity.is_on value reflects the NEW state (post-toggle).
    Only `str` values are considered valid (guards against dynamic mock attrs).
    """
    def _get_str(obj, attr):
        val = getattr(obj, attr, "")
        return val if isinstance(val, str) else ""

    if entity.is_on:
        return _get_str(entity, "sfx_open") or _get_str(entity, "sfx")
    return _get_str(entity, "sfx_close") or _get_str(entity, "sfx")
```

#### 3.3.2. `_trigger_object_interaction` (L114-134)

**Current (L117-124) :**
```python
if getattr(obj, "sfx", None):
    dist = p_pos.distance_to(obj.pos)
    vol_mult = max(0.4, 1.0 - dist / 120.0)
    self.game.audio_manager.play_sfx(
        str(obj.sfx),
        str(getattr(obj, "element_id", "")),
        volume_multiplier=vol_mult,
    )
```

**New :**
```python
sfx_name = self._resolve_sfx(obj)
if sfx_name:
    dist = p_pos.distance_to(obj.pos)
    vol_mult = max(0.4, 1.0 - dist / 120.0)
    self.game.audio_manager.play_sfx(
        sfx_name,
        str(getattr(obj, "element_id", "")),
        volume_multiplier=vol_mult,
    )
```

#### 3.3.3. `toggle_entity_by_id` (L305-308)

**Current :**
```python
if getattr(entity, "sfx", None):
    self.game.audio_manager.play_sfx(
        str(entity.sfx), str(getattr(entity, "element_id", ""))
    )
```

**New :**
```python
sfx_name = self._resolve_sfx(entity)
if sfx_name:
    self.game.audio_manager.play_sfx(
        sfx_name, str(getattr(entity, "element_id", ""))
    )
```

---

### 3.4. `src/entities/player.py` — `_update_animation` (L108-126)

**Current (L110-114) :**
```python
material = None
if self.game and self.game.map_manager:
    material = self.game.map_manager.get_terrain_material_at(
        int(self.pos.x), int(self.pos.y)
    )
```

**New :**
```python
material = self._resolve_footstep_material()
```

**New private method** (< 20 lignes) :
```python
def _resolve_footstep_material(self) -> str | None:
    """Return the footstep material at the player's current position.

    Priority:
      1. Active walkable_override entity (e.g. lowered bridge) with a material set.
      2. Map tile material via map_manager (existing behavior).
    """
    if self.game:
        for entity in getattr(self.game, "walkable_override_entities", ()):
            if not entity.rect:
                continue
            if not entity.rect.collidepoint(int(self.pos.x), int(self.pos.y)):
                continue
            entity_material = getattr(entity, "material", "")
            if entity_material:
                return entity_material

    if self.game and self.game.map_manager:
        return self.game.map_manager.get_terrain_material_at(
            int(self.pos.x), int(self.pos.y)
        )
    return None
```

---

## 4. Files NOT Changed

| Fichier | Raison |
|---------|--------|
| `collision_checker.py` | Aucun changement de logique collision |
| `audio.py` | `play_sfx` accepte déjà n'importe quel nom string |
| `map_loader.py` | Parsing Tiled délégué à `entity_factory.py` |
| `interactive_constants.py` | Pas de nouvelle constante nécessaire |
| `interactive_lighting.py` / `interactive_particles.py` | Non concernés |

---

## 5. Test Case Specifications

### 5.1. Unit Tests — `tests/entities/test_interactive.py`

| Test ID | Description | Input | Expected |
|---------|-------------|-------|----------|
| UT-001 | `sfx_open` stocké sur l'entité | `sfx_open="bridge_open"` | `entity.sfx_open == "bridge_open"` |
| UT-002 | `sfx_close` stocké sur l'entité | `sfx_close="bridge_close"` | `entity.sfx_close == "bridge_close"` |
| UT-003 | `material` stocké sur l'entité | `material="wood"` | `entity.material == "wood"` |
| UT-004 | Defaults à vide si non fourni | Pas de `sfx_open` dans Tiled | `entity.sfx_open == ""` |

### 5.2. Unit Tests — `tests/engine/test_interaction.py`

| Test ID | Description | Input | Expected |
|---------|-------------|-------|----------|
| UT-010 | `_resolve_sfx` → `sfx_open` quand `is_on=True` | `sfx_open="o", sfx="g", is_on=True` | Retourne `"o"` |
| UT-011 | `_resolve_sfx` → `sfx_close` quand `is_on=False` | `sfx_close="c", sfx="g", is_on=False` | Retourne `"c"` |
| UT-012 | Fallback sur `sfx` si `sfx_open` vide | `sfx_open="", sfx="g", is_on=True` | Retourne `"g"` |
| UT-013 | Fallback sur `sfx` si `sfx_close` vide | `sfx_close="", sfx="g", is_on=False` | Retourne `"g"` |
| UT-014 | Retourne `""` si tout est vide | `sfx_open="", sfx_close="", sfx=""` | Retourne `""` |
| UT-015 | Régression : entité sans `sfx_open`/`sfx_close` → `sfx` utilisé | `sfx="01-lever"` uniquement | Retourne `"01-lever"` (inchangé) |

### 5.3. Unit Tests — `tests/entities/test_player.py`

| Test ID | Description | Input | Expected |
|---------|-------------|-------|----------|
| UT-020 | Override entity avec `material="wood"` → retourne `"wood"` | Player sur pont lowered, `material="wood"` | `_resolve_footstep_material() == "wood"` |
| UT-021 | Override entity sans `material` → fallback map_manager | Player sur pont, `material=""` | Appel `map_manager.get_terrain_material_at()` |
| UT-022 | Pas d'override entity → fallback map_manager | Player sur tuile normale | Appel `map_manager.get_terrain_material_at()` |
| UT-023 | Régression : comportement footstep inchangé hors pont | Player sur tuile `"stone"`, aucune override entity | Retourne `"stone"` |

### 5.4. Integration Tests

| Test ID | Description | Expected |
|---------|-------------|----------|
| IT-001 | Pont déclenché via levier (`target_id`) → `sfx_open` joué | `audio_manager.play_sfx("bridge_open", ...)` |
| IT-002 | Pont re-déclenché → `sfx_close` joué | `audio_manager.play_sfx("bridge_close", ...)` |
| IT-003 | Joueur marche sur pont abaissé avec `material="wood"` | `audio_manager.play_sfx("04-footstep_wood", ...)` |

---

## 6. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Lire `entity.is_on` **avant** `interact()` pour déterminer le SFX | Lire `entity.is_on` **après** `interact()` | `interact()` fait le toggle — l'état post-toggle est l'état réel |
| Dupliquer la logique sfx dans `_trigger_object_interaction` ET `toggle_entity_by_id` | Utiliser `_resolve_sfx()` partagé | Single Responsibility, testable unitairement |
| Faire `entity.material or map_manager...` directement dans `_update_animation` | Déléguer à `_resolve_footstep_material()` | Réduire la profondeur de nesting, testabilité |
| Checker `entity.sfx_open` avec `getattr(..., None)` sans `or ""` | Utiliser `getattr(..., "") or getattr(..., "")` | Un string vide `""` est falsy — le fallback doit fonctionner |
| Ignorer la gestion du chargement des propriétés `sfx_open`, `sfx_close`, `material` depuis Tiled | Valider que l'usine les transmet aux objets | Les modifications du `.tmj` sont ignorées si l'EntityFactory ne les relaie pas correctement |

---

## 7. Error Handling

| Erreur | Response | Fallback | Logging |
|--------|----------|----------|---------|
| Fichier audio `sfx_open` / `sfx_close` absent | `audio_manager.play_sfx` retourne `False` | Silence — pas de crash | `WARNING: SFX file not found: ...` (existant dans `audio.py`) |
| `material` non reconnu par le système audio | Aucune — le matériau est une string libre | `play_sfx("04-footstep")` (fallback existant L124-125 dans `player.py`) | Aucun log additionnel nécessaire |
| `walkable_override_entities` absent sur `game` | `getattr(self.game, "walkable_override_entities", ())` → tuple vide | Fallback immédiat sur `map_manager` | Aucun |

---

## 8. Deep Links

- **`entity_factory.spawn_interactive`**: [entity_factory.py L119](../../src/engine/entity_factory.py#L119)
- **`InteractiveEntity.__init__`**: [interactive.py L37](../../src/entities/interactive.py#L37)
- **`InteractiveEntity._parse_misc`**: [interactive.py L212](../../src/entities/interactive.py#L212)
- **`InteractionManager._trigger_object_interaction`**: [interaction.py L114](../../src/engine/interaction.py#L114)
- **`InteractionManager._resolve_sfx`**: [interaction.py L290](../../src/engine/interaction.py#L290)
- **`InteractionManager.toggle_entity_by_id`**: [interaction.py L305](../../src/engine/interaction.py#L305)
- **`Player._update_animation`**: [player.py L88](../../src/entities/player.py#L88)
- **`Player._resolve_footstep_material`**: [player.py L127](../../src/entities/player.py#L127)
- **Tiled project class definition**: [game.tiled-project L185-260](../../assets/tiled/game.tiled-project#L185)
- **Bridge entity in debug map**: [99-debug_room.tmj L752](../../assets/tiled/maps/99-debug_room.tmj#L752)
- **Parent spec**: [bridge-subtype-spec.md](./bridge-subtype-spec.md#L1)

---

## 9. Assumptions validées

| # | Assumption | Risque | Statut |
|---|---|---|--------|
| A1 | `sfx_open` joue quand `is_on` passe à `True` | Low | ✅ Validé |
| A2 | `sfx_close` joue quand `is_on` passe à `False` | Low | ✅ Validé |
| A3 | Fallback sur `sfx` si `sfx_open`/`sfx_close` vide | Low | ✅ Validé |
| A4 | `material` utilisé uniquement pour les footsteps | Low | ✅ Validé |
| A5 | Priorité walkable_override pour footsteps — tests existants non cassés | Medium | ✅ Validé |
