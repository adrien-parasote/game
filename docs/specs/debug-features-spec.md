# Technical Spec: Debug Features

> Document Type: Implementation


Detailed implementation specification for the debug room and visual hitbox debugging.

## 1. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Render hitboxes in `Game._draw_scene` | Handle it in `CameraGroup.custom_draw` | Ensures hitboxes are correctly aligned with camera offset and Y-sorting. |
| Use `print()` for debug logs | Use `logging.debug()` | Maintain professional logging standards. |
| Break existing `is_initial_spawn` logic | Support both `pawn` and `spawn` variants | Backward compatibility with existing maps. |
| Hardcode map paths in multiple methods | Use `Settings.DEBUG_MAP` or local constant | Centralized configuration management. |
| Draw hitboxes when `DEBUG` is False | Add a strict conditional check | Avoid unnecessary draw calls and performance hits in production. |

## 2. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-CONF-01 | Settings | JSON with `debug.enabled: true` | `Settings.DEBUG == True` | Missing section (default to False) |
| TC-MAP-01 | Game Init | `DEBUG == True` | `default_map == "99-debug_room.tmj"` | Debug map file missing (fallback) |
| TC-SPAWN-01 | Game Spawn | Object with `is_initial_pawn: True` | Player position == Object position | Multiple spawn points (first one wins) |

### Integration Tests
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-DEBUG-01 | Startup Flow | `settings.json` set to debug | Check `Game._current_map_name` is debug room | Reset settings |
| IT-RENDER-01 | Render Loop | `DEBUG == True` | Verify `pygame.draw.rect` calls (via Mock) | — |

## 3. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging |
|------------|-----------|----------|----------|---------|
| Debug Map Missing | `os.path.exists()` check | Load `00-spawn.tmj` | Normal startup map | ERROR |
| Invalid JSON Debug Flag | `json.load()` exception | Use default `False` | Continue startup | WARNING |
| Prop Resolution Error | `_get_property` failure | Return default `None/False` | Ignore property | DEBUG |

## 4. Deep Links

- **Config System**: [src/config.py](file:///Users/adrien.parasote/Documents/perso/game/src/config.py)
- **Engine Loop**: [src/engine/game.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- **Drawing Logic**: [src/entities/groups.py](file:///Users/adrien.parasote/Documents/perso/game/src/entities/groups.py)

