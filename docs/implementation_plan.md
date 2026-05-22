# Implementation Plan — Intra-Map Teleport & Walk Transition

This implementation plan details the addition of efficient intra-map teleportation and smooth "walk" transitions within the same map, bypassing costly full map reload cycles (`_load_map()`).

## User Review Required

> [!IMPORTANT]
> The walk transition has been re-architected to integrate directly with the player's core physics engine (`BaseEntity.move(dt)`). This solves a critical animation collision identified during Adversarial Review (where `is_moving` would otherwise be force-reset to `False` every frame, breaking walking animation and footstep SFX).

> [!NOTE]
> The camera group rendering (`CameraGroup`) and world structure (`MapManager`) remain untouched and strictly out of scope, guaranteeing zero structural regressions.

## Proposed Changes

---

### Component: Spatial Interactions

#### [MODIFY] [interaction.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/interaction.py)
- In `check_teleporters()`, detect if `tp.target_map` is empty (`""`) or matches `self.game._current_map_name`.
- If intra-map, call `self.game.intra_map_teleport(tp.target_spawn_id, tp.transition_type)` and preserve the subsequent `break`.
- Else, fall back to the existing `self.game.transition_map(...)`.

---

### Component: Map Operations

#### [MODIFY] [map_loader.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/map_loader.py)
- Implement `resolve_spawn_by_id(target_spawn_id: str) -> tuple[int, int] | None`.
- Reads coordinates from `self.game.map_manager._entities` in-memory. Zero disk I/O.
- Returns tile center coordinates `(x + half_tile, y + half_tile)`.

---

### Component: Game Loop & Player Movement

#### [MODIFY] [game.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- Add state field `self._intra_walk_target: pygame.math.Vector2 | None = None` in `_init_groups()`.
- Implement `_start_intra_walk(target: pygame.math.Vector2)`:
  - Sets `_intra_walk_target = target`.
  - Sets `player.target_pos = target` and `player.is_moving = True` to drive native physics movement.
  - Updates initial player facing direction (`current_state`) toward target.
- Implement `_tick_intra_walk(dt)`:
  - If `player.is_moving` is `False`, terminates the walk (sets `_intra_walk_target = None` and resets `player.direction`).
  - Else, continuously updates `player.current_state` toward the walk target to support smooth facing changes during walk.
- In `_update_core_state(dt)`, intercept updates if `self._intra_walk_target is not None`:
  - Run `self.visible_sprites.update(dt)` to let `player.update(dt)` execute `move(dt)` and animation frames natively.
  - Run `self._tick_intra_walk(dt)` to handle arrival.
  - Skip standard input, npc updates, and teleporter checks.

---

### Component: Testing

#### [NEW] [test_intra_map_teleport.py](file:///Users/adrien.parasote/Documents/perso/game/tests/engine/test_intra_map_teleport.py)
- Comprehensive test suite including 10 unit tests and 3 integration tests covering all requirements (detection, spawn resolution, teleport, walk cycle, and input blocking).

## Verification Plan

### Automated Tests
- Running the newly implemented unit and integration tests:
  ```bash
  pytest tests/engine/test_intra_map_teleport.py -v
  ```
- Running the entire project test suite to ensure zero regressions:
  ```bash
  pytest
  ```

### Manual Verification
- Testing Tiled map configuration locally.
- Verifying smooth player sprite animations and footstep SFX play continuously during the scripted walk transition.
