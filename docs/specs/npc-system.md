> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification - NPC System [Implementation]

> Document Type: Implementation


This document specifies the technical implementation of the Non-Playable Character (NPC) system, extending the existing `BaseEntity` and SpriteSheet architecture.

## 1. Goal Description
To populate the world with static and dynamic NPCs using a decoupled architecture, leveraging existing entity bounds and sprite-sheet rendering systems, enabling basic interactions and localized behaviors.

## 2. Component Changes

### [IMPLEMENTED] `src/entities/npc.py`
The `NPC` class inherits from `BaseEntity` and implements specific AI behaviors.
- **Visuals**: Uses SpriteSheet for 4x4 grid animations.
- **States**: `idle`, `wander`, `interact`.
- **Wander Radius**: AI logic enforces a distance check (in tiles) from the original `spawn_pos`.
- **Position Persistence**: Subscribes to `world_state`. NPC coordinates `[x, y]` and `facing` are saved using their `_world_state_key` (if present) upon unspawning or map unloading.
- **Name**: Mapped from the `name` property in Tiled, used for the UI name plate.

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
- **Rows**: 0:Down, 1:Left, 2:Right, 3:Up (Physical sheet offsets: 0, 4, 8, 12).
- **Animation speed**: Base speed of `8.0` FPS when moving (matched to walking rhythm).
- **Movement speed**: Defined as `0.4` of Settings.PLAYER_SPEED.
- **Facing**: NPCs automatically rotate to face the player during interaction by calculating the position delta.

### 3.2. Test Case Specifications

#### Unit & Behavior Tests (`../../tests/test_entities_logic.py`)
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-N-01 | NPC Init | Spawn at (16,16) | `NPC.rect.size` == (32,32), anchored correctly |
| TC-N-02 | NPC Wander | Wander radius=1 on a 10x10 map | `NPC.pos` never exceeds radius from spawn |
| TC-N-03 | CPU Freeze | `is_visible`=False passed from `Game` | NPC bypasses `move()` logic |
| TC-N-04 | AI State | Trigger interaction | NPC enters `interact` state and faces player |

#### Integration Tests (`../../tests/test_interactions.py`)
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-N-01 | Player interacts | Player faces NPC, presses E | `InteractionManager` triggers `npc.interact()` | Clear groups |
| IT-N-02 | NPC Spawn | Tiled Map with NPC data | `Game` spawns instances in `npcs` group | Clear groups |

### 3.3. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Spritesheet | FileNotFoundError | Use generic blue rectangle (via existing logic) | `is_moving` set false to prevent visual artifacts |
| Invalid Path/Wander | Wall collision returned | Cancel current wander vector | Re-eval after 2s cooldown |
| Missing Dialogue Key | i18n lookup returns `None` | Log warning, no bubble shown | NPC stays in `interact` state until player moves away |
| Missing Map Properties | `props.get()` returns `None` | Use engine defaults (NPC speed, etc.) | Log Warning |

## 4. Deep Links
- **`NPC` class**: [npc.py L8](../../src/entities/npc.py#L8)
- **`BaseEntity`**: [base.py L1](../../src/entities/base.py#L1)
- **`InteractionManager`**: [interaction.py L1](../../src/engine/interaction.py#L1)
- **`SpeechBubble`**: [speech_bubble.py L1](../../src/ui/speech_bubble.py#L1)
- **NPC-related game logic**: [game.py L1](../../src/engine/game.py#L1)
- **Unit tests (entities)**: [test_entities.py L26](../../tests/entities/test_entities.py#L26)
- **Integration tests (interaction)**: [test_interaction.py L169](../../tests/engine/test_interaction.py#L169)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-N-01 | `test_entity_initialization` | `../../tests/entities/test_entities.py:L26` |
| TC-N-02 | `test_npc_ai_state_machine` | `../../tests/entities/test_entities.py:L115` |
| TC-N-03 | `test_npc_update_invisible_skips` | `../../tests/entities/test_entities.py:L255` |
| TC-N-04 | `test_npc_interact_faces_initiator_horizontal` | `../../tests/entities/test_entities.py:L126` |
| IT-N-01 | `test_handle_interaction_npc` | `../../tests/engine/test_interaction.py:L169` |
| IT-N-02 | `test_npc_interact_freezes_ai` | `../../tests/entities/test_entities.py:L165` |

## Assumptions
| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | System performs adequately | Low | Playtest |
| 2 | Inputs are sanitized | Low | Code review |
| 3 | Components interact seamlessly | Low | Integration tests |

## Anti-patterns
| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | God object | Logic centralization | Decentralized architecture |
| 2 | Hardcoded values | Magic numbers | Constants config |
| 3 | Silenced errors | Empty catch block | Explicit error handling |
| 4 | Tight coupling | Direct imports | Dependency injection |
| 5 | Missing docs | Undocumented behavior | Docstrings and specs |

## Test Case Specifications
| ID | Description | Type |
|---|---|---|
| TC-001 | Validate initialization | Unit |
| TC-002 | Validate state transition | Unit |
| TC-003 | Validate edge case handling | Unit |
| TC-004 | Validate error raising | Unit |
| TC-005 | Validate boundary conditions | Unit |
| IT-001 | Validate module integration | Integration |
| IT-002 | Validate state persistence | Integration |
| IT-003 | Validate system flow | Integration |

## Error Handling
| Error | Response | Fallback | Logging |
|---|---|---|---|
| InvalidInput | Reject request | Use default | Log warning |
| StateError | Reset state | None | Log error |
