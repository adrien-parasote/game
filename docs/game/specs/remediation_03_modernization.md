# Spec — Steps 8 to 11: Python 3.12 Modernization

> Document Type: Implementation
> **Covers:** @override, Type aliases, ADR-008 FRect, pathlib.Path ✅
> **Blueprint Reference:** [`best_practices_remediation_blueprint.md`](../strategic/best_practices_remediation_blueprint.md#implementation-plan--10-steps)
> **Best Practices Guide:** [`pygame_ce_python_312_best_practices.md`](./pygame_ce_python_312_best_practices.md#section-4-typing)
> **Status:** DONE — Steps 8-11 implemented and verified (pyright: 0 errors, pytest: 1094/1094)

---

## Context

Four low-severity improvements to modernize the codebase toward Python 3.12:

1. **`@override`**: Lack of decorators on inherited methods prevents Pyright from detecting parent signature breaks.
2. **`type` Type Aliases**: Complex annotations duplicated in `render_manager.py` without named aliases.
3. **ADR-008 FRect**: Documented decision not to migrate (Vector2+Rect works). Creates a trace for future decisions.
4. **`pathlib.Path`**: Migration of 55 `os.path.join` occurrences to `pathlib.Path` across 28 files (`src/config.py`, `src/engine/`, `src/entities/`, `src/ui/`, `src/map/tmj_parser.py`). Only `src/main.py:6` (bootstrap `sys.path`) retains `os`.

---

## Constraints

| Tier | Examples |
|---|---|
| **Always do** | `@override` only on methods that actually override a defined parent method (not on implemented abstract methods). Place `type` aliases at the top of the file, after imports. |
| **Ask first** | Add `@override` to a method if the parent method is not clearly identifiable. |
| **Never do** | Modify the logic of methods decorated with `@override`. `@override` is a pure annotation decorator — no runtime behavior. Do not touch methods that do not override a parent method (e.g., subclass-specific methods). |

---

## Cross-Spec Contracts

### Produces
| Identifier | Format | Consumers |
|---|---|---|
| `docs/ADRs/ADR-008-frect.md` | Markdown | Future reference for FRect decision |

### Consumes
N/A — purely local modifications.

### Public Interface
N/A.

### External Invocations
N/A.

### Tracked Concepts
| Concept | Status | Mentioned in |
|---|---|---|
| `FRect` | Documented decision (ADR-008): not migrated in Phase 1 | `camera-rendering.md`, `entities-system.md` |

---

## Step 8 — `@override` on Inherited Methods

### Complete Inventory

| Class | Method | File | Parent | Approx. Line |
|---|---|---|---|---|
| `Player` | `update(dt)` | `src/entities/player.py` | `BaseEntity` | ~150 |
| `CameraGroup` | `add(*sprites)` | `src/entities/groups.py` | `pygame.sprite.Group` | ~68 |
| `CameraGroup` | `remove(*sprites)` | `src/entities/groups.py` | `pygame.sprite.Group` | ~72 |
| `NPC` | `update(dt)` | `src/entities/npc.py` | `BaseEntity` | To verify |

### Implementation

**Import to add (Python 3.12 stdlib — zero dependencies):**
```python
from typing import override
```

**Pattern:**
```python
class Player(BaseEntity):
    @override
    def update(self, dt: float) -> None:
        ...  # unchanged existing body

class CameraGroup(pygame.sprite.Group):
    @override
    def add(self, *sprites: pygame.sprite.Sprite) -> None:
        ...  # unchanged existing body
```

**Rule:** Only modify the import line and the method declaration line. Zero changes to the method body.

**Pyright Verification:** With `@override` and `typeCheckingMode: basic`, Pyright will raise an error if the signature differs from the parent — that is the objective.

### Modified Files

- `src/entities/player.py`
- `src/entities/groups.py`
- `src/entities/npc.py`

---

## Step 9 — `type` Type Aliases for Complex Signatures

### Signatures to Alias Inventory

Complex annotations identified in `render_manager.py`:

```python
# Currently inline (duplicated or unreadable):
list[tuple[pygame.Surface, tuple[int, int]]]   # list of blits
list[tuple[pygame.Rect, int]]                   # occluding rects
```

### Implementation

**At the top of `src/engine/render_manager.py`, after imports:**
```python
# Python 3.12 type aliases
type BlitSequence = list[tuple[pygame.Surface, tuple[int, int]]]
type OccludingRect = list[tuple[pygame.Rect, int]]
```

**Usage in method signatures:**
```python
def _collect_blit_items(self) -> BlitSequence:
    ...

def _get_occluding_rects(self) -> OccludingRect:
    ...
```

**Rule:** Only for types appearing ≥2 times in the file or whose readability clearly benefits from a name. No aliases for simple, already readable types (`str`, `int`, `float`, `pygame.Surface`).

### Modified File

- `src/engine/render_manager.py`

---

## Step 10 — ADR-008: FRect Decision

### Document to Create: `docs/ADRs/ADR-008-frect-migration.md`

```markdown
# ADR-008 — Migration to pygame.FRect: Non-Migration Decision (Phase 1)

**Date:** 2026-05-26
**Status:** ✅ Accepted — Migration deferred

## Context

The reference guide `pygame_ce_python_312_best_practices.md §2.2` recommends using
`pygame.FRect` for mobile entities to eliminate sub-pixel jitter.

The project currently uses `pygame.Rect` (integer) for hitboxes and rendering positions,
combined with `pygame.math.Vector2` for sub-pixel positions (`pos`, `target_pos`).

## Cost/Benefit Analysis

**Benefit:**
- Would remove double storage of `Vector2 pos` + `Rect` in `BaseEntity`
- Would eliminate manual rounding `int(self.pos.x)`, `int(self.pos.y)`
- Full compliance with reference guide §2.2

**Cost:**
- Impact on `base.py`, `player.py`, `npc.py`, `groups.py`, `collision_checker.py`
- Potential for regression in collision detection (FRect vs Rect in collision checks)
- Estimated effort: >4h + 2h of collision regression testing

**Current Jitter:** Not observed. The rounded `Vector2 pos` + `Rect` system works
correctly. No jitter reports in gameplay.

## Decision

**Do not migrate to FRect in Phase 1.**

The dual-system is functional. The benefit (code simplification) does not justify the
risk of collision regressions and migration effort.

## Revision Conditions

Reconsider if:
1. Sub-pixel jitter is observed in distribution (high-resolution screens)
2. FRect migration is proposed in a dedicated release with a full collision test suite
3. pygame-ce provides an official FRect migration guide

## Unmodified Files

- `src/entities/base.py`
- `src/entities/player.py`
- `src/entities/groups.py`
- `src/engine/collision_checker.py`
```

---

## Step 11 (Optional) — Migration `os.path.join` → `pathlib.Path`

> **⚠️ Optional step.** Does not block Steps 1-10. Decide separately.

### Inventory

~60 occurrences of `os.path.join` in `src/`. Major concentrations:

| Module | Approx. Occurrences | Criticality |
|---|---|---|
| `src/engine/asset_manager.py` | ~5 | High — path of all assets |
| `src/engine/save_manager.py` | ~8 | High — save paths |
| `src/ui/hud.py` | 2 | Low |
| `src/map/tmj_parser.py` | ~10 | Medium |
| Other UI modules | ~15 | Low |

### Migration Pattern

```python
# BEFORE
import os
path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "HUD", "00-clock.png")
path = os.path.normpath(path)

# AFTER
from pathlib import Path
path = Path(__file__).parent / ".." / ".." / "assets" / "images" / "HUD" / "00-clock.png"
path = path.resolve()  # equivalent to normpath but absolute
```

### Implementation Rule

1. Migrate **file by file**, not in bulk.
2. Verify that calling functions accept `Path` or `str` (pygame-ce accepts both).
3. `Path.resolve()` replaces `os.path.normpath()` + `os.path.abspath()`.
4. `Path(__file__).parent` replaces `os.path.dirname(__file__)`.
5. Existing tests must pass without modification.

### Verification

```bash
grep -rn "os.path.join" src/  # → 0 after complete migration
grep -rn "import os" src/     # → only files using os.environ, os.path.exists, etc.
```

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | `@override` on an implemented abstract method | Decorating a method with `@override` that implements `@abstractmethod` | `@override` = replaces a **concrete** parent method. Check [`entities-system.md`](./entities-system.md#base-entity) for hierarchy |
| 2 | Type aliases for simple types | `type Name = str` or `type Count = int` | Alias only composite types: ≥2 levels of nesting or length > 40 chars |
| 3 | `type Alias = ...` in the middle of a file | Declaring an alias after `def` or `class` | Aliases go after imports, before the first `def` or `class` |
| 4 | Modifying method body when adding `@override` | Combining the addition of `@override` with a body refactor | `@override` is strictly an annotation decorator. Zero body modification |
| 5 | `pathlib.Path` mixed with `str` without conversion | `pygame.image.load(Path("assets/img.png"))` if the API expects `str` | Always verify the target API. Use `str(path)` if necessary at the call site |
| 6 | ADR-008 without revision conditions | "Do not migrate FRect" without defining when to review the decision | Document the 3 revision conditions in [`ADR-008`](../ADRs/ADR-008-frect-migration.md#revision-conditions) |
| 7 | Pathlib migration on shared files without tests | Migrate `asset_manager.py` without verifying that existing tests cover paths | Run tests after migrating each file. Verify coverage via [`verification-loop`](./../agents/skills/verification-loop/SKILL.md) |

---

## Test Case Specifications

### Unit Tests — @override

**TC-001**: `Player.update(dt=0.016)` runs without error with `@override` added
```python
# Arrange: valid player instance
# Act: player.update(0.016)
# Assert: no TypeError, no AttributeError
```

**TC-002**: `CameraGroup.add(sprite)` runs without error with `@override`
```python
# Assert: sprite in group after add()
```

**TC-003**: `CameraGroup.remove(sprite)` runs without error with `@override`
```python
# Assert: sprite not in group after remove()
```

**TC-004**: Static verification — `@override` present on the 4 targeted methods
```bash
grep -n "@override" src/entities/player.py src/entities/groups.py src/entities/npc.py
# → 4 results
```

### Unit Tests — Type Aliases

**TC-005**: `render_manager.py` correctly imports its own aliases (no ImportError)
```python
from src.engine.render_manager import RenderManager  # clean import
```

**TC-006**: Static verification — `type BlitSequence` present in `render_manager.py`
```bash
grep "^type " src/engine/render_manager.py  # → ≥1 result
```

### Unit Tests — Pathlib (if Step 11 executed)

**TC-007**: `AssetManager.get_image(path)` returns the same surface before and after migration
```python
# Assert: surface.get_size() identical before/after migration
```

**TC-008**: `SaveManager._saves_dir` is a valid path after migration
```python
# Assert: Path(sm._saves_dir).exists() (after creation)
```

**TC-009**: Static verification
```bash
grep -rn "os.path.join" src/  # → 0 (if complete migration)
```

### Integration Tests

**IT-001**: Full gameplay — player moves, NPC moves, sprites added/removed → no behavioral regressions

**IT-002**: Pyright with `@override` → 0 additional errors (overrides are correct)

---

## Error Handling Matrix

| Error | Fallback | Logging |
|---|---|---|
| Pyright `reportGeneralTypeIssues` on `@override` — signature incompatible with parent | Correct signature to match parent — visible Pyright error blocks the commit | `pyright src/` in the CI pipeline |
| Unresolved `type` alias — Python < 3.12 used | `SyntaxError` on parsing. Verify `python --version` = 3.12+ | Clear message: "type statement requires Python 3.12+" |
| `Path` vs `str` incompatibility — pygame-ce API expects `str` | `str(path)` at the call site — do not modify the receiving API | `TypeError` caught in TC-003 test |
| ADR-008 not created — Step 10 ignored | No runtime impact — purely documentary | N/A |

---

## Bundling & Native-Module Audit

- **BM1:** N/A
- **BM2:** N/A
- **BM3:** N/A
- **BM4:** N/A — no constant renaming in this spec

---

## File Tree

```
src/
├── entities/
│   ├── player.py                    [MODIFY] — @override on update()
│   ├── groups.py                    [MODIFY] — @override on add() and remove()
│   └── npc.py                       [MODIFY] — @override on update()
└── engine/
    └── render_manager.py            [MODIFY] — BlitSequence, OccludingRect type aliases

docs/
└── ADRs/
    └── ADR-008-frect-migration.md   [NEW] — FRect non-migration decision

# Optional Step 11 — same files + os.path.join removal
```

---

## Assumptions

| Assumption | Risk | Validation |
|---|---|---|
| `BaseEntity.update(dt)` has the same signature as `Player.update(dt)` | Low | Verify `base.py` signature before `@override` |
| `pygame.sprite.Group.add/remove` accept `*sprites` (same signature) | Low | Verified in pygame-ce docs |
| `type` statement is available (Python 3.12+) | Low | `python --version` = 3.12 in venv |
| Step 11 (pathlib) does not break existing relative paths | Medium — `Path.resolve()` makes relative paths absolute | Verify each path before migrating |
