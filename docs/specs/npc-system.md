<!-- Document Type: Implementation -->

# Technical Specification - NPC System [Implementation]

> Document Type: Implementation


This document specifies the technical implementation of the Non-Playable Character (NPC) system, extending the existing `BaseEntity` and SpriteSheet architecture.

## 1. Goal Description
To populate the world with static and dynamic NPCs using a decoupled architecture, leveraging existing entity bounds and sprite-sheet rendering systems, enabling basic interactions and localized behaviors.

## 2. Component Changes

### [IMPLEMENTED] `src/entities/npc.py`
The `NPC` class inherits from `BaseEntity` and implements specific AI behaviors.
- **Visuals**: Uses SpriteSheet with a configurable grid. Default is `4×4` (4 cols × 4 rows, frames 32×48px). Override via `sheet_cols` / `sheet_rows` Tiled properties.
  - `frames_per_dir = sheet_cols` drives animation cycling (columns = animation frames, rows = directions).
  - Guards use **one spritesheet per facing direction** (e.g. `05-guard_left.png`, `05-guard_right.png`) with `sheet_cols=4, sheet_rows=4` (32×96px frames). Since the asset only contains one visual direction duplicated across all 4 rows, `interact()` changing `current_facing` will select a different row but visually display the same sprite.
- **States**: `idle`, `wander`, `interact`.
- **Sub-type**: Controlled by the `sub_type` Tiled property (enum `21-sub_type`):
  - `npc` (default): wandering AI active, `process_ai()` runs normally. Animation cycles columns only when `is_moving=True`; resets to frame 0 at idle.
  - `static_npc`: AI fully disabled — `process_ai()` is skipped every frame. NPC stays at spawn position and **continuously loops its animation** (columns cycle at `animation_speed` fps regardless of movement). Remains interactable via `interact()`, which changes `current_facing` to face the player.
- **`facing_direction` param** (`str | None`): Optional constructor parameter. When set, overrides the default `"down"` initial facing for ALL NPC types (both `npc` and `static_npc`). Passed from Tiled via `EntityFactory.spawn_npc()`. Valid values: `"down"`, `"left"`, `"right"`, `"up"`.
- **Wander Radius**: AI logic enforces a distance check (in tiles) from the original `spawn_pos`. Unused for `static_npc`.
- **Position Persistence**: Subscribes to `world_state`. NPC coordinates `[x, y]` and `facing` are saved using their `_world_state_key` (if present) upon unspawning or map unloading.
- **Name**: Mapped from the `name` property in Tiled, used for the UI name plate.
- **game reference**: The `game` attribute MUST be set by `EntityFactory.spawn_npc()`. Without it, `BaseEntity.start_move()` uses `Settings.MAP_SIZE` (default 32) for boundary clamping, which traps NPCs placed beyond pixel 1024 on larger maps.

### [IMPLEMENTED] `src/entities/base.py`
- Provided `interact(initiator)` method stub for subclass overrides.
- Shared movement and boundary logic.

### [IMPLEMENTED] `src/engine/interaction.py`
- **[IMPLEMENTED]** Handles all spatial proximity and orientation checks for NPCs.
- **[IMPLEMENTED]** Triggers the **interact** emote (!) above the player when in proximity (<48px).
- **[IMPLEMENTED]** Triggers `npc.interact()` → `Game._trigger_npc_bubble(npc, element_id)` → `SpeechBubble`.

### [IMPLEMENTED] `src/ui/speech_bubble.py`
- Nine-patch bubble rendered **above** the NPC's sprite using nine-patch 32×32 tiles from `assets/images/HUD/`.
- Tail (`21-bubble_queue.png`) anchored to `npc.rect.top` with configurable `tail_gap`.
- **Name Plate**: Renders NPC name at top-left using `23-bubble_name.png` (using subsurface slicing for variable width).
- Text auto-wrapped to `max_width_px=224` (7 tiles) using narrative font.
- Layout governed by constants: `_PADDING_TOP = 20`, `_PADDING_BOTTOM = 0`, `_PADDING_X = 30`. Max 4 lines per page.
- Pagination via `page` index stored in `Game._npc_bubble`; `22-bubble_arrow.png` shown on multi-page.

### [IMPLEMENTED] `src/engine/game.py`
- **[IMPLEMENTED]** Manages `npcs` sprite group.
- **[IMPLEMENTED]** Manage NPC spawning in `_spawn_entities`.
- **[IMPLEMENTED]** Integrated NPCs into `_is_collidable` logic (NPCs act as dynamic obstacles).
- **[IMPLEMENTED]** `_npc_bubble` state dict `{npc, text, page}` for active speech bubble.
- **[IMPLEMENTED]** `_trigger_npc_bubble()` — resolves i18n key and opens bubble.
- **[IMPLEMENTED]** `_advance_npc_bubble()` — pages forward or closes, resets NPC to `idle`.
- **[IMPLEMENTED]** `_load_map()` resets `_npc_bubble = None` on map change.

---

## 3. 📋 SPEC: NPC AI and Interaction Logic

This section defines the behavior and failure modes for autonomous entities.

### 3.1. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| NPCs check collisions with each other | NPCs use `_is_collidable` (shared logic) | Prevents overlapping and ensures physical presence |
| Hardcode NPC dialogue in `npc.py` | Use external JSON/YAML | Allows localization and scale |
| Continuous pathfinding | Intermittent grid step randomizer | Reduces CPU overhead per NPC |
| Move NPCs when off-camera | Freeze distant NPCs (see §3.1.1) | Enlarged viewport (128px) determines `is_visible` |
| `Player` handles dialogue UI | `Game` or UI_Manager handles dialogue | Decouples rendering overlay from input entity |
| Manual property parsing in AI logic | Use `TmjParser` properties dict | Centralizes data extraction and simplifies AI classes |
| Immediate full-text display | Use Paginated Dialogue System | Improves readability for long NPC dialogues |
| Call `start_move()` without `game` set | Always ensure `npc.game = self.game` before `walkable_func` is used | Without `game`, boundary clamping uses wrong map size (BUG-1 regression) |
| Leave `direction` set after a blocked move | Clear `self.direction = Vector2(0,0)` in `start_move()` on block | Causes `move()` to retry every frame → visual "spinning" (BUG-2 regression) |

#### 3.1.1. CPU Freeze Optimization (Detail)

The engine skips update logic for NPCs that are off-screen to reduce CPU overhead in maps with many NPCs.

**Mechanism**:
1. Each frame, `Game` calculates an enlarged viewport: `screen_rect.inflate_ip(128, 128)` — adds **128px margin** on all 4 sides
2. For each NPC, if `npc.rect` does **not** collide with the enlarged viewport → `npc.is_visible = False`
3. NPCs with `is_visible == False` skip their `update(dt)` call entirely

**What is SKIPPED** when `is_visible=False`:
| Component | Skipped | Rationale |
|-----------|---------|-----------|
| AI state machine | ✅ | No need to wander when invisible |
| Movement (`move()`) | ✅ | No grid interpolation needed |
| Animation frame tick | ✅ | No visual to update |
| Ambient sound proposal | ✅ | Too far to hear |

**What is NOT SKIPPED** when `is_visible=False`:
| Component | Active | Rationale |
|-----------|--------|-----------|
| Collision detection | ✅ | NPCs remain solid obstacles for the player |
| Position persistence | ✅ | `save_state()` uses last known position |
| Sprite group membership | ✅ | NPC can become visible again on camera move |

**128px margin rationale**: Prevents NPCs from "popping in" at screen edges. An NPC 1 tile off-screen begins updating before becoming visible, allowing it to start walking naturally into view.


### 3.2. NPC Animation & Facing

#### Layout standard (rows = directions, cols = frames)
| Row | Direction | Frame index formula |
|-----|-----------|---------------------|
| 0 | Down | `0 * fpd + frame_col` |
| 1 | Left | `1 * fpd + frame_col` |
| 2 | Right | `2 * fpd + frame_col` |
| 3 | Up | `3 * fpd + frame_col` |

`fpd = sheet_cols` (frames per direction). Direction offsets: `0, fpd, fpd*2, fpd*3`.

#### Comportement d'animation par sub_type
| sub_type | Cycle actif quand | Reset frame 0 |
|----------|-------------------|---------------|
| `npc` | `is_moving == True` uniquement (et `state != 'interact'`) | Oui, à l'arrêt (après 2 frames consécutives stopped) |
| `static_npc` | **Toujours** hors dialogue (cycle permanent si `state != 'interact'`, indépendant de `is_moving`. Le bloc conditionnel d'animation DOIT explicitement incrémenter `frame_index` si `sub_type == 'static_npc'` et `state != 'interact'`, ou si `is_moving`) | Non (ignorer le reset à l'arrêt normal ; figer le frame actuel en interaction) |

#### Vitesses
- **Animation speed**: Mêmes règles de calcul pour les deux subtypes, basées sur la vitesse de l'entité : `self.animation_speed = (1.0 / 0.15) * self.speed / Settings.PLAYER_SPEED`.
- **Movement speed** (`npc` uniquement): `0.4 × Settings.PLAYER_SPEED`.

#### Facing
- `interact()` calcule `diff = initiator.pos - self.pos` et met à jour `current_facing` (horizontal prioritaire si `|dx| > |dy|`).
- Le `static_npc` utilise `current_facing` pour sélectionner la bonne row d'animation, même sans bouger.
- `facing_direction` au constructeur initialise `current_facing` pour tous les NPCs (dynamic et static) avant le premier frame.

### 3.3. Test Case Specifications

#### Unit & Behavior Tests
| Test ID | Fichier | Component | Input | Expected Output |
|---------|---------|-----------|-------|-----------------|
| TC-001 | `test_entities.py:L26` | NPC Init | Spawn at (16,16) | `NPC.rect.size` == (32,32), anchored correctly |
| TC-002 | `test_entities.py:L115` | NPC Wander | Wander radius=1 | `NPC.pos` never exceeds radius from spawn |
| TC-003 | `test_entities.py:L255` | CPU Freeze | `is_visible=False` | NPC bypasses `move()` logic |
| TC-004 | `test_entities.py:L126` | AI State | Trigger interaction | NPC enters `interact` state and faces player |
| TC-005 | `test_npc.py:L118` | Static NPC base | `sub_type='static_npc'` | `process_ai()` skipped, `_action_timer` frozen, `state` stays `idle`, `interact()` retourne `element_id` |
| TC-006 | `test_npc.py` | Static NPC animation | `sub_type='static_npc'`, `update(dt=1.0)` | `frame_index > 0.0` (cycle permanent sans `is_moving`) |
| TC-007 | `test_npc.py` | Static NPC anim idle | `sub_type='static_npc'`, pas de mouvement, 2 frames | `frame_index` continue d'avancer (ne reset PAS à 0) |
| TC-008 | `test_npc.py` | facing_direction init static | `NPC(sub_type='static_npc', facing_direction='left')` | `current_facing == 'left'` |
| TC-009 | `test_npc.py` | facing_direction init dynamic | `NPC(sub_type='npc', facing_direction='left')` | `current_facing == 'left'` (applicable à tous les NPCs) |
| TC-010 | `test_npc.py` | Static NPC interaction freeze | `sub_type='static_npc'`, `state='interact'`, `update(dt)` | `frame_index` reste figé (ne cycle pas en dialogue) |

#### Integration Tests
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-001 | Player interacts | Player faces NPC, presses E | `InteractionManager` triggers `npc.interact()` | Clear groups |
| IT-002 | NPC Spawn | Tiled Map with NPC data | `Game` spawns instances in `npcs` group | Clear groups |

## Error Handling

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Spritesheet | FileNotFoundError | Use generic blue rectangle (via existing logic) | `is_moving` set false to prevent visual artifacts |
| Invalid Path/Wander | Wall collision returned by `walkable_func` | Cancel wander: clear `direction = Vector2(0,0)`, set `state = "idle"` | Re-eval after AI cooldown (2–5s). Direction MUST be cleared to prevent spin-in-place (BUG-2). |
| Wrong boundary clamping | `npc.game` is `None` → `MAP_SIZE` fallback used | All movement targets clamped to wrong world_height → NPC stuck | `spawn_npc()` MUST set `npc.game = self.game` before any movement (BUG-1). |
| Incorrect sprite grid | `sheet_cols`/`sheet_rows` not set for non-default sheet | Sprite frames sliced with wrong dimensions → image cropped | Always set `sheet_cols` + `sheet_rows` in Tiled object props when using non-standard spritesheet layout. |
| Missing Dialogue Key | i18n lookup returns `None` | Log warning, no bubble shown | NPC stays in `interact` state until player moves away |
| Missing Map Properties | `props.get()` returns `None` | Use engine defaults (NPC speed, etc.) | Log Warning |

## Anti-patterns

| ❌ Anti-Pattern | Impact | ✅ Correct Behavior |
|---|---|---|
| Animer un `static_npc` uniquement si `is_moving` | Frame_index reste à 0 → sprite figé | Brancher sur `sub_type == 'static_npc' or is_moving` pour incrémenter `frame_index` et cycler en permanence. |
| Appliquer `facing_direction` au `sub_type='npc'` | Le NPC wandering change de direction via l'AI — override silencieux trompeur | `facing_direction` ne s'applique qu'aux `static_npc` |
| Déplacer `05-guard_*.png` dans `sprites/` | `InteractiveEntity._load_assets()` cherche dans `sprites/`, `NPC.__init__` cherche dans `characters/` — mauvais dossier → FileNotFoundError | Garder tous les spritesheets NPC dans `assets/images/characters/` |
| Utiliser un layout sprite (rows=frames, cols=variants) pour un static_npc | `_update_animation` utilise rows=directions → mauvaises frames affichées | Toujours utiliser le layout character (rows=directions, cols=frames) pour les spritesheets NPC |
| Réinitialiser `frame_index = 0` quand `not is_moving` pour un `static_npc` | Coupe l'animation en boucle à chaque frame d'arrêt | Ignorer le bloc `elif not self._was_moving` pour les `static_npc` |

## 4. Deep Links
- **`NPC` class**: [npc.py L8](../../src/entities/npc.py#L8)
- **`BaseEntity`**: [base.py L1](../../src/entities/base.py#L1)
- **`InteractionManager`**: [interaction.py L1](../../src/engine/interaction.py#L1)
- **`SpeechBubble`**: [speech_bubble.py L1](../../src/ui/speech_bubble.py#L1)
- **NPC-related game logic**: [game.py L1](../../src/engine/game.py#L1)
- **Unit tests (entities)**: [test_entities.py L26](../../tests/entities/test_entities.py#L26)
- **Integration tests (interaction)**: [test_interaction.py L169](../../tests/engine/test_interaction.py#L169)
- **Regression tests (NPC stuck bug)**: [test_npc_stuck_bug.py L1](../../tests/entities/test_npc_stuck_bug.py#L1)
- **EntityFactory tests**: [test_entity_factory.py L1](../../tests/entities/test_entity_factory.py#L1)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-001 | `test_entity_initialization` | `../../tests/entities/test_entities.py:L26` |
| TC-002 | `test_npc_ai_state_machine` | `../../tests/entities/test_entities.py:L115` |
| TC-003 | `test_npc_update_invisible_skips` | `../../tests/entities/test_entities.py:L255` |
| TC-004 | `test_npc_interact_faces_initiator_horizontal` | `../../tests/entities/test_entities.py:L126` |
| TC-005 | `TestStaticNPC` (6 tests) | `../../tests/entities/test_npc.py:L118` |
| TC-006 | `test_static_npc_animates_when_idle` | `../../tests/entities/test_npc.py` |
| TC-007 | `test_static_npc_anim_continues_when_idle` | `../../tests/entities/test_npc.py` |
| TC-008 | `test_static_npc_facing_direction_init` | `../../tests/entities/test_npc.py` |
| TC-009 | `test_npc_facing_direction_init` | `../../tests/entities/test_npc.py` |
| TC-010 | `test_static_npc_anim_frozen_during_interaction` | `../../tests/entities/test_npc.py` |
| IT-001 | `test_handle_interaction_npc` | `../../tests/engine/test_interaction.py:L169` |
| IT-002 | `test_npc_interact_freezes_ai` | `../../tests/entities/test_entities.py:L165` |

## Assumptions
| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | Le spritesheet d'un `static_npc` suit le layout character (rows=directions, cols=frames) | Low | Visuel in-game + test TC-006 |
| 2 | `facing_direction` est pris en compte pour tous les NPCs (dynamic et static) | Low | TC-009 |
| 3 | `animation_speed` utilise la même formule de scaling pour tous les NPCs | Low | TC-006 |
| 4 | Un `static_npc` avec un seul fichier sprite (une direction fixe) ne changera jamais de row — `interact()` met à jour `current_facing` mais l'image affichée est contrainte par les frames disponibles | Medium | Test visuel in-game |
| 5 | `_action_timer` reste à 0 pour un `static_npc` (l'AI ne s'exécute jamais) | Low | TC-005 existant |
