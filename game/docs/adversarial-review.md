# Adversarial Review: ADR 003 — Stair Climbing Positioning and Alignment
> Reviewer source: cross-model (Agent Self-Simulation)

## 0. Epistemic Pre-Scan
- **Cross-Spec Consistency:** N/A (Single spec)
- **Verifiable Claims:** No external claims. Internal claims regarding Pygame (`pygame.Rect`) and tile dimension (32px / 12px) are standard or consistent with prior configurations.
- **Hidden Assumptions:**
  - *Assumption*: Entities move linearly and `total step distance` never equals zero during `update()`.
  - *Assumption*: Every sprite rendered by `CameraGroup` will have the `current_stair_offset` attribute.
  - *Assumption*: The "next flat tile" can be explicitly classified as a "stair tile" or "floor tile" by some unspecified property.

## 1. Multi-Lens Roundtable Synthesis
- **Lenses applied:** 🔒 Security, 💰 Cost, 🔧 Ops, 🚀 Perf, 👤 User, ♻️ Evol, 🎯 Scope

### Cross-Reference Matrix
| Finding A | Finding B | Signal Type | Description |
|-----------|-----------|-------------|-------------|
| 🚀 #1 | 👤 #1 | 🔁 Pattern | Fragile math around "total step distance" interpolation (ZeroDivision risk and visual judder on interrupt) |
| ♻️ #1 | 🎯 #1 | 🕳️ Blind spot | Interface mismatch: CameraGroup assumes all Sprites have `current_stair_offset`, mixing logic into base entity |
| 🎯 #2 | ♻️ #2 | 🎯 Convergence | Vague classification logic: "If next tile is stair..." lacks explicit property mapping |

### Signals
**🎯 Convergence: Vague Tile Classification**
- Both Scope and Evol lenses flagged the phrase "If the next flat tile is a stair tile... If the next flat tile is a floor tile". Without defining the exact property check (e.g. `hasattr(tile, 'vertical_move')` or `tile.properties.get('stair')`), the implementation has an implicit degree of freedom.

**🕳️ Blind spot: CameraGroup Sprite Heterogeneity**
- `CameraGroup.custom_draw` iterates over all `pygame.sprite.Sprite` instances. If static decorations, items, or particles are added to this group without inheriting from `BaseEntity`, accessing `sprite.current_stair_offset` will cause an `AttributeError`.

**🔁 Pattern: Fragile Interpolation State**
- The interpolation calculation `progress = 1.0 - (distance to target / total step distance)` is fragile. It assumes a fixed start and end point. If the player changes direction mid-step, or if the entity hits a wall and stops, distance calculation may break or divide by zero.

---

## 2. Adversarial Stress-Test Findings

Based on the signals above, here is the hostile critic's review of the spec looking for guaranteed code generation failures:

**[HIGH] — ZeroDivisionError and State Corruption during Interpolation**
Location: Section 2, Point 2 (Visual Offset Interpolation)
Problem: The formula `progress = 1.0 - (distance to target / total step distance)` assumes `total step distance` is non-zero and static. If a move is blocked or the entity is standing still but `update(dt)` runs, or if `total step distance` is uninitialized, the AI will write code that crashes with `ZeroDivisionError`. Additionally, the formula breaks if the entity's target changes mid-step.
Fix: Rewrite to explicitly dictate the calculation mechanism: "Store `self.stair_start_time` and `self.stair_duration`. Compute `progress = min(1.0, elapsed_time / stair_duration)`. If not moving, `progress = 1.0`." Alternatively, specify: "Guard the calculation: `if total_distance <= 0: progress = 1.0` and clearly define how `total step distance` is cached at the start of the move."

**[HIGH] — AttributeError in CameraGroup.custom_draw**
Location: Section 2, Point 2
Problem: The spec states "apply `sprite.current_stair_offset` during rendering". An AI will write `stair_y_offset = sprite.current_stair_offset`. Since `CameraGroup` can contain native `pygame.sprite.Sprite` objects (like particles) that lack this attribute, the game will crash.
Fix: Change the instruction to explicitly require safe property access: "Use `getattr(sprite, 'current_stair_offset', 0)` when fetching the offset in `CameraGroup.custom_draw`."

**[MEDIUM] — Ambiguous Stair Tile Identification**
Location: Section 2, Point 1 (Symmetric Step-Off Rule)
Problem: The spec says "If the next flat tile is a stair tile...". An AI has to guess how to check this. It might write `if 'stair' in tile.name` or `if tile.depth == 1`. If it guesses wrong, the symmetric step-off will fail, leaving the Y-drift bug unfixed.
Fix: Explicitly define the condition. E.g., "Identify a stair tile by checking if `map_manager.get_vertical_move_props(tx, ty)` returns a valid dictionary."

## Verdict
| Aspect | Status |
|--------|--------|
| Ready to build? | **NO** — needs resolution of HIGH findings. |
| Highest confidence issue | `AttributeError` in `CameraGroup` for non-BaseEntity sprites. |
| Biggest risk | `ZeroDivisionError` in progress interpolation. |
| Missing from the spec | Explicit safe access in CameraGroup; Safe math for step interpolation; Concrete property check for stair tile identification. |

> **Next Step for USER:** Please review the findings and confirm if we should update `docs/adr/003-stair-climbing-alignment.md` to address these flaws, or if you prefer to fix them yourself. Once addressed, I will re-run the verification gate.
