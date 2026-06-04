# Asset Convertor Spec — Terrain Generation Core (Domain Warping)

> Document Type: Implementation
> **Covers:** F1, F2, F3, F4

## Deep Links

- [V4 Strategic Blueprint](../strategic/terrain_generation_core_blueprint.md#L1)
- [GUI Spec](./asset_convertor_spec.md#L1)
- [Texture module](../../../tools/asset_convertor/core/texture.py#L1)
- [App module](../../../tools/asset_convertor/gui/app.py#L1)
- [State module](../../../tools/asset_convertor/gui/state.py#L1)

## Assumptions

| # | Assumption | Risk | Source Type / Validation |
|---|---|---|---|
| 1 | Continuous noise offsets naturally wrap when projected to the torus | Low | SHOW - mathematically guaranteed by `math.cos` and `math.sin` wrapping. |
| 2 | Floating point precision issues far from 0 can cause seams | Medium | SHOW - Fixed by applying modulo `width`/`height` to offsets before torus projection. |
| 3 | Defaulting `warp_scale` to 0.05 gives good macro structures | Low | SHOW - Tunable in GUI, visually confirmed. |
| 4 | The +1000 offset for `dy` noise provides sufficient decorrelation from `dx` | Medium | ASSUMED — valid when `warp_scale × 1000 > 1` noise period (i.e., `warp_scale > ~0.001`). At extremely low `warp_scale` values, decorrelation degrades and diagonal streak artifacts may appear. Minimum `warp_scale` is clamped to `0.01` (see Error Handling Matrix). |

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Preserve seamless toroidal noise output. Ensure GUI sliders debounce rapid updates (300ms) to avoid CPU lockup. Use `Image.NEAREST` for internal scaling. Run tests before committing. **Domain warp MUST use NumPy vectorized operations — no scalar per-pixel loops (see Domain Warping Algorithm).** |
| **Ask first** | Changing the `TextureParams` schema in a way that breaks existing YAML presets not explicitly updated. Adding new dependencies. |
| **Never do** | Implement fluid animation, props placement, or wall extrusion in this iteration. Mutate `TextureParams` directly (it must remain a frozen dataclass). |

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `tools/asset_convertor/core/texture.py` | Python Module | This spec § "Domain Warping Algorithm" | `gui/pipeline.py`, `core/tile_assembler.py` |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/asset_convertor/gui/state.py` | Python Module | `specs/asset_convertor_spec.md` | GUI Spec |
| `tools/asset_convertor/gui/app.py` | Python Module | `specs/asset_convertor_spec.md` | GUI Spec |
| `tools/asset_convertor/config/terrain_presets.yaml` | YAML | `specs/asset_convertor_spec.md` | Presets |

### [MODIFICATION REQUIRED] Consuming specs that must be updated

| Spec | Method / Field | Required Change |
|---|---|---|
| `specs/asset_convertor_spec.md` | `AppState.to_texture_config()` | Must map `warp_scale` and `warp_strength` from `AppState` to the returned `TextureParams` instance. **This update is mandatory before this spec's tests can pass.** |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Dataclass Field | `warp_scale` | `TextureParams` in `core/texture.py` |
| Dataclass Field | `warp_strength` | `TextureParams` in `core/texture.py` |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| N/A | N/A — this spec invokes no external interfaces outside standard Python libraries and OpenSimplex. | N/A |

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| TextureParams | Modified to add warp parameters | `specs/asset_convertor_spec.md` |
| Seamless Tiling | Enforced via Toroidal noise math + wrapping offsets | `./autotile_converter_spec.md` |

## TextureParams Schema

The two new fields are added to the existing `TextureParams` frozen dataclass in `tools/asset_convertor/core/texture.py`:

```python
@dataclass(frozen=True)
class TextureParams:
    # ... existing fields unchanged ...
    warp_scale: float = 0.05      # [NEW] Spatial frequency of warp noise
    warp_strength: float = 0.0    # [NEW] Displacement magnitude (0.0 = no warp, backward-compatible)
```

Constraints:
- Both fields are `float` (not `int`)
- Both have keyword defaults — no positional change to the existing interface
- `frozen=True` is preserved (immutability enforced)
- `warp_scale` minimum value is `0.01` (clamped in Error Handling Matrix)

**Extension rule (for Phase 3+):** All future `TextureParams` fields MUST have a default value. YAML preset loading MUST be lenient — ignore unknown fields, use defaults for missing fields. This ensures every old preset remains loadable without modification.

### Seed Allocation Table

To prevent seed collisions across future procedural passes, seed offsets are allocated as follows:

| Offset | Purpose | Spec |
|--------|---------|------|
| `seed + 0` | Base terrain noise | `specs/asset_convertor_spec.md` |
| `seed + 1` | Reserved (do not use) | — |
| `seed + 2` | Warp noise X (`warp_noise_x`) | This spec |
| `seed + 3` | Warp noise Y (`warp_noise_y`) | This spec |
| `seed + 4` | Elevation pass (Phase 3) | TBD — reserve now, implement in elevation spec |
| `seed + 5` | Props / Poisson disk (Phase 3) | TBD — reserve now, implement in props spec |
| `seed + 6+` | Future passes | Each new spec must allocate from this table |

> **Rule:** Any new procedural pass that needs a seed MUST add a row to this table in the relevant spec before implementation.

## Domain Warping Algorithm

To produce organic "S-curves" matching the RPG Maker grass autotile aesthetic while maintaining perfect seamless tiling:

### Pre-implementation: Call-Site Audit (MANDATORY)

Before changing `_compute_multi_octave_noise(x: int, y: int, ...)` to `(x: float, y: float, ...)`, run:

```bash
rg '_compute_multi_octave_noise' tools/
```

For each call site found: verify no `isinstance(x, int)` type checks on x/y. Document all call sites here before implementing. In Python, `int` is a subtype of `float` so the change is safe for arithmetic, but explicit type guards would break.

### Vectorization Contract (MANDATORY)

> ⛔ **Implementation MUST use NumPy vectorized operations.** Scalar per-pixel loops (`for x in range(W): for y in range(H):`) are forbidden. On a 256×256 texture, a scalar loop produces 65,536 iterations × 3 noise calls = ~196,608 function calls, causing 10–60s generation time that makes the GUI unusable.

The warp offset arrays MUST be pre-computed as full `(height, width)` NumPy arrays before any tile assembly:

```python
# Correct — vectorized:
dx_map = sample_toroidal_noise_array(height, width, warp_scale, warp_noise_x)  # shape (H, W)
dy_map = sample_toroidal_noise_array(height, width, warp_scale, warp_noise_y)  # shape (H, W)
dx_map *= warp_strength
dy_map *= warp_strength
x_warped = (x_grid + dx_map) % width   # x_grid = np.arange(W) broadcast to (H, W)
y_warped = (y_grid + dy_map) % height
# Then sample base_noise over x_warped, y_warped using toroidal projection
```

### Thread Failure Contract

The generation pipeline runs in a daemon thread (Dear PyGui). Thread crashes MUST NOT be silent:

- The generation thread MUST wrap its entire body in `try/except Exception`.
- On any exception, serialize the error to a string and post it to the GUI main thread via a shared error queue (e.g., a `threading.Queue` instance on the `AppState`).
- The GUI's main loop MUST drain this error queue each frame and display any errors in a status bar within 200ms.
- `MemoryError` and NumPy errors during warp computation are the primary expected failure modes.

### Algorithm Steps

To produce organic "S-curves" matching the RPG Maker grass autotile aesthetic while maintaining perfect seamless tiling:
1. Instead of sampling `base_noise` directly at `(x, y)`, calculate offset arrays `dx_map` and `dy_map` for all pixels at once (vectorized — see Vectorization Contract above).
2. Initialize two separate noise generator instances: `warp_noise_x` with seed `seed + 2` and `warp_noise_y` with seed `seed + 3` (see Seed Allocation Table).
3. `dx_map` is pre-computed by sampling toroidal noise vectorially with `warp_noise_x` over the full `(H, W)` grid.
4. `dy_map` is pre-computed by sampling toroidal noise vectorially with `warp_noise_y` over the full `(H, W)` grid.
5. Multiply `dx_map` and `dy_map` element-wise by `warp_strength`.
6. Add `dx_map` and `dy_map` to the original coordinate grids:
   `x_warped = x_grid + dx_map`
   `y_warped = y_grid + dy_map`
7. Wrap the warped coordinates element-wise to ensure floating-point precision safety:
   `x_wrapped = x_warped % width`
   `y_wrapped = y_warped % height`
8. Project the wrapped coordinate arrays onto the torus and sample `base_noise` using the vectorized toroidal projection.

Modify the type signature of `_compute_multi_octave_noise` in `tools/src/asset_convertor/core/texture.py` to accept floats:
```python
def _compute_multi_octave_noise(
    x: float,
    y: float,
    width: int,
    height: int,
    params: TextureParams,
    noise_gen: OpenSimplex,
) -> float:
```

## GUI Slider Configuration

The new warp parameters must be exposed in the Dear PyGui layout inside `tools/src/asset_convertor/gui/app.py` under the texture parameters section with the following constraints:
- **Warp Strength Slider**:
  - Label: "Force Déformation" (French user-visible label)
  - Range: `0.0` to `50.0`
  - Step size: `0.5`
  - Default: `0.0`
  - **Safety boundary:** Values above `16.0` (= `tile_size / 2` for 32px tiles) produce abstract/non-representational textures. The slider MUST display a visual indicator (e.g., color change on the track or a tooltip) when the value exceeds `16.0`: `"⚠️ Force élevée — rendu abstrait possible"`. This range is intentionally allowed for creative use.
- **Warp Scale Slider**:
  - Label: "Échelle Déformation" (French user-visible label)
  - Range: `0.01` to `0.20`
  - Step size: `0.01`
  - Default: `0.05`

## Anti-Patterns

| # | Anti-Pattern | Why It's Wrong | Do Instead |
|---|-------------|----------------|------------|
| AP-01 | Adding warp logic AFTER toroidal projection | The torus projection is 4D. Distorting the 4D coordinates breaks the math and causes visible seams. | Distort the 2D `(x, y)` coordinates *before* computing the angle for toroidal projection. |
| AP-02 | Using `random.random()` for offsets | Random offsets produce TV static (white noise), not smooth organic S-curves. | Use continuous noise (OpenSimplex) for the offsets. |
| AP-03 | Hardcoding warp values in `app.py` | Breaks the separation of concerns. The GUI shouldn't contain generation logic. | Expose `warp_scale` and `warp_strength` in `TextureParams`. |
| AP-04 | Defaulting `warp_strength` to a high value | Breaks existing presets that rely on the classic noise look. | Default `warp_scale` to `0.05` and `warp_strength` to `0.0` for backward compatibility. |
| AP-05 | Missing the modulo wrap on offsets | If the offset pushes coordinates outside `[0, width)`, the torus projection will wrap naturally anyway, but floating point inaccuracies far from 0 can cause micro-seams. | Wrap coordinates using `(x + dx) % width` before angle projection. |

## Test Case Specifications

### Unit Tests — `TC-*`

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-001 | `TextureParams` backwards compatibility | `TextureParams(scale=0.1)` | `warp_scale` defaults to `0.05`, `warp_strength` defaults to `0.0` |
| TC-002 | Warp offset generation | `warp_strength = 10.0` | Output noise values differ from `warp_strength = 0.0` |
| TC-003 | Warp zero effect | Call `generate_texture(TextureParams(warp_strength=0.0))` twice with identical seed | Both outputs are pixel-for-pixel identical (`numpy.array_equal`). Also assert output equals the golden fixture stored at `tests/fixtures/texture_no_warp_seed42.npy` (a numpy array captured before the domain warp feature, committed to the repo). **Pre-condition:** if the fixture does not exist, generate it with `warp_strength=0.0` and commit it before this test can run. |
| TC-004 | Seamless validation (Horizontal) | Generate texture with warp, slice edges | Left column pixels match right column pixels (exact RGBA equality, not tolerance-based — seamless is guaranteed by the math) |
| TC-005 | Seamless validation (Vertical) | Generate texture with warp, slice edges | Top row pixels match bottom row pixels (exact RGBA equality) |

### Integration Tests — `IT-*`

| ID | Test | Scenario | Expected |
|----|------|----------|----------|
| IT-001 | Full pipeline with warp | Generate tileset with `warp_strength = 20` | All 47 tile slots generate without crashing |
| IT-002 | GUI State conversion | Update warp sliders in UI State | `AppState.to_texture_config()` correctly maps `warp_scale` and `warp_strength` into the returned `TextureParams` instance |
| IT-003 | Preset loading with warp | Load YAML with warp config | AppState parses and applies warp parameters correctly |

## Error Handling Matrix

| Error | Trigger | User Message | Recovery | Verified Status |
|-------|---------|-------------|----------|-----------------|
| Invalid warp parameter type | YAML preset contains string instead of float for `warp_strength` | "Preset '{name}' has invalid warp parameters. Using defaults." | Fallback to default `0.0` | ASSUMED |
| Negative `warp_scale` | Slider or YAML provides negative scale | N/A (silently take absolute value or clamp to `>0`) | Clamp to `0.01` minimum | ASSUMED |
| Negative or excessive `warp_strength` | Slider or YAML provides negative or `> 100.0` strength | N/A | Clamp to `[0.0, 100.0]` range | ASSUMED |
| Missing warp fields in old presets | Loading a V2 YAML without warp fields | N/A | Use default `0.0` | ASSUMED |
