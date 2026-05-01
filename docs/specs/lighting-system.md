# Lighting System Specification

This document serves as the Technical Specification for the Dynamic Lighting System, adhering to the Stream Coding v6.0 methodology.

## 1. System Overview

The game utilizes a Pygame-native lighting system designed for 60 FPS performance without shaders. 
The system leverages `pygame.BLEND_RGBA_SUB` to subtract alpha values from a global `_night_overlay`. By erasing darkness in specific shapes (radial gradients for torches, trapezoid beams for windows), we simulate light sources.

## 2. Window Lighting

### 2.1 Detection & Positioning
- **Primary**: Tiled rectangle objects with `type="18-light"` in the `00-system` layer. Each rectangle defines the exact pixel region where light originates (bottom of the window). This supports arbitrary window sizes and placement.
- **Fallback**: If no `18-light` objects exist, tiles with property `type="window"` are scanned and beam origins are inferred from tile positions.
- **Caching**: `MapManager.get_window_positions()` returns `List[Tuple[cx, y, width]]` — cached at map load.

### 2.2 Beam Shape
- **Trapezoid**: Widens from `beam_top_width` (default 24px) at the window to `beam_bottom_width` (default 52px) at the floor.
- **Height**: `beam_height` = 70px.
- **Horizontal diffusion**: Per-pixel gaussian falloff (`exp(-1.65 * dist²)`) — soft edges, no hard lines.
- **Vertical decay**: `(1 - t)^0.6` — gradual fade from top to bottom.
- **Oval bottom**: In the last 35% of height, corner pixels fade progressively via `corner_fade = max(0, 1 - bp * d_corner * 1.8)`. Center column is unaffected → natural oval floor illumination.
- **No numpy dependency**: Pure `pygame.Surface.set_at()` with cache (max 64 surfaces).

### 2.3 Dynamic Slant (Sun/Moon Rotation)
The beam slant (horizontal drift of the beam center over its height) is computed dynamically from the time of day using two cosine waves blended by brightness:

```
sun_angle  = 2π × (hour - 6) / 24      → cos = +1 at 6h, 0 at 12h, -1 at 18h
moon_angle = 2π × (hour - 18) / 24     → cos = +1 at 18h, 0 at 0h, -1 at 6h

sun_slant  = max_slant × cos(sun_angle)
moon_slant = max_slant × 0.5 × cos(moon_angle)

slant = sun_slant × brightness + moon_slant × (1 - brightness)
```

- `max_slant` = 28px
- **No discontinuity**: the brightness blend (`0.0 ↔ 1.0`) ensures smooth dawn/dusk transitions.
- Cache key includes slant quantised to ±2px to avoid excessive surface regeneration.

### 2.4 Color & Intensity
Tied to `TimeSystem.brightness`:
- Noon (`brightness=1.0`): Warm white `(255, 248, 220)`, master_alpha ≈ 191.
- Midnight (`brightness=0.0`): Cool blue `(160, 180, 255)`, master_alpha ≈ 64.
- Intermediate values are linearly interpolated.

## 3. Torch Lighting

- **Sources**: Objects in `InteractiveEntity` with `sub_type` in `['lamp', 'lantern', 'torch', 'fire', 'candle']` or `halo_size > 0`.
- **Rendering**: Torch halos are applied to the `_night_overlay` via `BLEND_RGBA_SUB` to cleanly erase the darkness.
- **Animation**: The flickering logic (sine waves on alpha/scale) remains but now modulates the subtractive mask.

## 4. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Generate window beam polygons every frame | Pre-render beam surfaces and cache them | Creating polygons per-frame kills performance |
| Use `BLEND_RGB_ADD` for darkness reduction | Use `BLEND_RGBA_SUB` on the night overlay's alpha channel | ADD creates blown-out white areas; SUB correctly restores the original scene colors |
| Apply lighting directly to the screen surface | Compose all lighting onto a dedicated `_night_overlay` surface first | Allows complex blending without permanently altering the scene pixels |
| Iterate over all tiles every frame to find windows | Cache window coordinates during map load | `O(W*H)` per frame is too slow; cache is `O(N)` where N is number of windows |
| Rely on tileset filename for window detection | Use Tiled `18-light` rectangle objects (or `type="window"` tile property as fallback) | Precise pixel-level control independent of tile grid |
| Use a hard if/else for day/night slant | Blend sun and moon cosine waves by brightness | Avoids discontinuous jumps at dawn/dusk |
| Depend on numpy/surfarray for per-pixel rendering | Use `pygame.Surface.set_at()` | No external dependency; surfarray can fail on some pygame builds |

## 5. Test Case Specifications

### Unit Tests Required (`tests/test_lighting.py`)
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| LT-001 | Window Cache | MapManager with window tiles | `get_window_positions()` returns `List[(cx, y, width)]` | Map with 0 windows |
| LT-002 | Beam Color Sync | `brightness=1.0` (Noon) | Beam color is warm (R>B) | `brightness=0.0` yields cool blue (B>R) |
| LT-003 | Torch Compositing | Torch overlay subtraction | Night alpha is reduced around torch center | Overlapping lights |
| LT-004 | Night Overlay | `night_alpha = 180` | Overlay filled with 180 alpha | `night_alpha = 0` yields empty overlay |
| LT-005 | Sun Slant Morning | `hour=6, brightness=1.0` | slant > 0 (east) | |
| LT-006 | Sun Slant Noon | `hour=12, brightness=1.0` | slant ≈ 0 (zenith) | |
| LT-007 | Sun Slant Evening | `hour=18, brightness=0.5` | slant < 0 (west) | |
| LT-008 | Moon Slant Midnight | `hour=0, brightness=0.0` | slant ≈ 0 (zenith) | |
| LT-009 | Slant Continuity | All 48 half-hours | max jump < 5px between consecutive readings | |
| LT-010 | Beam Surface Shape | top=24, bot=52, slant=0 | Top-center alpha > 150, edge alpha < 10 | Slant shifts brightest mid-row pixel |
| LT-011 | Oval Bottom | 80% height row | Center alpha > edge alpha | |
| LT-012 | Beam Cache | Same params twice | Returns identical object | Cache evicts after 64 |

## 6. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| Invalid Blend Mode | Platform doesn't support `BLEND_RGBA_SUB` | `pygame.error` caught during initialization | Fall back to `BLEND_RGB_MULT` on a black surface | ERROR | Once |
| Extreme Time Skew | `brightness` outside `[0.0, 1.0]` | Clamp `brightness` value before color lerp | `max(0.0, min(1.0, b))` | WARN | None |

## 7. Deep Links

- **LightingManager**: [lighting.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/lighting.py)
- **Window Position Detection**: [manager.py#get_window_positions](file:///Users/adrien.parasote/Documents/perso/game/src/map/manager.py)
- **Time/Brightness Logic**: [time_system.py#L90](file:///Users/adrien.parasote/Documents/perso/game/src/engine/time_system.py#L90)
- **Night Overlay Usage**: [game.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- **Lighting Tests**: [test_lighting.py](file:///Users/adrien.parasote/Documents/perso/game/tests/test_lighting.py)
