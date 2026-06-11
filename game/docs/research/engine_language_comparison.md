# Research: Is Python/pygame-ce the Right Choice for The Heir's Awakening?

> **Stage:** 🔬 DISCOVER  
> **Date:** 2026-06-11  
> **Decision type:** Adopt / Adapt / Build  
> **Scope:** Game engine language — not a feature spec

---

## Context

The current engine is **Python + pygame-ce**, with ~12 000 lines of source code across 40+ modules (`engine/`, `entities/`, `map/`, `graphics/`, `ui/`). The game is a **cozy 2D action-RPG** (Stardew Valley × Dungeon Meshi × FF9), targeting infinite-season open-world gameplay with NPCs, dialogue, familiars, weather, festivals, and co-op (v2.0).

---

## Candidates Evaluated

| # | Stack | Paradigm |
|---|-------|----------|
| A | **Python + pygame-ce** (current) | Framework: you build every system |
| B | **Godot 4** (GDScript or C#) | Full engine: editor + built-in systems |
| C | **Rust + Bevy** | Framework, ECS-first, zero-cost abstractions |
| D | **C++ + SDL / custom** | Framework, maximum hardware control |

---

## Performance Reality for This Project

### What pygame-ce can handle

pygame-ce is a **C-backed SDL2 wrapper** — Python is only the coordination layer. The inner loops (blitting, surface ops, event polling) run at C speed.

Real bottleneck sources (and whether they affect *The Heir's Awakening*):

| Bottleneck | Affected? | Mitigation already possible |
|---|---|---|
| Thousands of simultaneous moving entities | **No** — cozy RPG scope | Spatial partitioning |
| Full-map tile draw every frame | **Yes** | Chunking + static layer blit (standard pattern) |
| Complex real-time physics simulation | **No** — tile-based movement | N/A |
| GPU shaders / post-process lighting | **Partially** | Software lighting exists; GPU path requires custom C extension |
| Python GIL blocking async AI | **Minor** | AI is per-entity state machines, not parallel threads |

**Verdict on performance:** pygame-ce is **not** the bottleneck for this game's scope. The already-identified render_manager.py issues (870 LOC, heavy draw calls) are **architectural problems solvable in Python**, not language-ceiling problems.

### Where you would hit a real ceiling

- Hundreds of particles + dynamic lighting + large viewports simultaneously (~500+ entities in motion at 60 FPS)
- GPU shader-based post-processing (bloom, dynamic shadows from dozens of point lights)
- The v2.0 co-op case with complex synchronized physics

None of these are in scope for v1.0. The ceiling exists, but you're not close to it.

---

## Competitive Analysis

### 🟢 Python + pygame-ce (current)

**Strengths:**
- 12 000 LOC already written and tested
- Full control over every system — no "fighting the engine"
- Python productivity for game logic (dialogue trees, quest state, economy)
- pygame-ce is actively maintained with SIMD + performance patches
- Your existing toolchain (pytest, ruff, pyright) is mature

**Weaknesses:**
- No visual scene editor — level design is code + Tiled
- No built-in animation state machine — must implement manually
- No built-in shader pipeline — software lighting is CPU-bound
- Performance ceiling ~3–5x lower than Godot's C++ core

**Verdict:** `ADAPT` — address architectural bottlenecks, don't abandon ship

---

### 🟡 Godot 4 (GDScript / C#)

**Strengths:**
- Visual editor = massive productivity gain for maps, UI, animations
- Built-in TileMap, AnimationTree, CharacterBody2D, dialogue addons (Dialogic)
- GDScript is Python-like — shallow learning curve
- Vulkan renderer — real GPU acceleration
- Strong indie RPG ecosystem (tutorials, addons specifically for 2D RPGs)

**Weaknesses:**
- **12 000 LOC is a complete rewrite**, not a refactor — you cannot port Python to GDScript
- Scene/Node paradigm is a different mental model from your current OOP approach
- Estimated rewrite cost: **2–4 months** of focused work to reach feature parity
- GDScript is slower than C++ for hot paths (solvable with C# or GDExtension, but adds complexity)
- You lose your existing pytest/ruff/pyright investment entirely

**Verdict:** `BUILD` (new project) — worth it for a *next* game, not *this* one at 12k LOC

---

### 🔴 Rust + Bevy

**Strengths:**
- Highest performance ceiling of any option
- Memory safe, great for concurrent simulations
- Modern ECS architecture scales extremely well

**Weaknesses:**
- Bevy is still pre-1.0 — API breaks frequently
- Rust's borrow checker adds significant cognitive overhead for game logic
- ECS thinking is radically different from your current OOP entities
- Virtually no 2D RPG content toolchain
- Would be starting from zero

**Verdict:** `SKIP` — wrong tool for cozy RPG development velocity. Only relevant if performance is the primary goal, which it isn't.

---

### 🔴 C++ + SDL / custom

**Weaknesses:**
- Manual memory management
- No productivity gain over pygame-ce for 2D RPG logic
- Complete rewrite from scratch
- Unlikely to finish the game

**Verdict:** `SKIP` — overkill and counter-productive

---

## Decision Matrix

| Criterion | Weight | pygame-ce | Godot 4 | Rust/Bevy | C++ |
|---|---|---|---|---|---|
| Ship v1.0 velocity | 30% | ✅ High | ✅ High (post-learning) | ❌ Low | ❌ Low |
| Current codebase ROI | 25% | ✅ Full | ❌ Zero | ❌ Zero | ❌ Zero |
| Performance headroom | 20% | ⚠️ Enough for v1.0 | ✅ High | ✅ Very high | ✅ Very high |
| Visual tooling | 15% | ❌ None | ✅ Best-in-class | ❌ None | ❌ None |
| Ecosystem for 2D RPG | 10% | ⚠️ Adequate | ✅ Excellent | ❌ Sparse | ❌ None |
| **Weighted score** | | **~72/100** | **~58/100*** | **~22/100** | **~15/100** |

> *Godot scores ~80/100 for a **new** project. The penalty here is the 12k LOC writeoff + 2–4 months catch-up.

---

## Key Finding: What Actually Slowed You Down

The perf-audit (session `0b36b203`) identified **render_manager.py** (870 LOC) as the primary hotspot — excessive draw calls, no dirty-rect optimization, lighting recalculated every frame. These are **fixable within pygame-ce** without a language change.

The real question is not "is Python fast enough?" — it's "is the current architecture efficient?" And the answer is: it's fixable.

---

## Recommendation: `ADAPT` — Stay, Optimize

**Decision: Stay with Python + pygame-ce for v1.0.**

**Rationale:**
1. **Sunk cost is real investment** — 12 000 LOC with test coverage is months of work you'd throw away
2. **Performance ceiling is not reached** — the bottlenecks found are architectural, not language-level
3. **Migration to Godot = 2–4 months of zero new features** — for a side project, this likely means losing momentum and not shipping
4. **pygame-ce is actively improving** — not a dead-end technology

**If you reconsider for v2.0 / the next game:**  
→ Use **Godot 4 with C#** — best balance of editor productivity, GDScript familiarity, and performance. GDScript is close enough to Python that your game logic knowledge transfers directly.

---

## Open Questions

1. **Is there a specific feature you can't implement in pygame-ce?** (e.g., a shader effect, a specific physics behavior)
2. **Is the co-op target (v2.0) requiring true parallel simulation?** If yes, this could change the calculus.
3. **Is shipping v1.0 the primary goal, or is this also a learning/exploration project?** — If the latter, Godot exploration is low-cost.

---

## Sources

- Web research: pygame-ce benchmark patterns, Godot 4 RPG migration experience (reddit, godotengine.org, medium, 2024–2025)
- Project measurement: `find game/src -name "*.py" | xargs wc -l` → **11 996 lines** across 40 files
- Perf-audit session: `0b36b203` — render_manager identified as primary bottleneck
- Codebase: engine/render_manager.py (870 LOC), game.py (557 LOC), entities/interactive.py (552 LOC)
