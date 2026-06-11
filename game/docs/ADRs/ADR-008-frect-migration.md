# ADR-008 — Migration to pygame.FRect: Non-Migration Decision (Phase 1)

**Date:** 2026-05-26  
**Status:** ✅ Accepted — Migration deferred  

## Context

The reference guide `pygame_ce_python_312_best_practices.md §2.2` recommends using `pygame.FRect` for moving entities to eliminate sub-pixel jitter.

The project currently uses `pygame.Rect` (integer) for hitboxes and rendering positions, combined with `pygame.math.Vector2` for sub-pixel positions (`pos`, `target_pos`).

## Cost/Benefit Analysis

**Benefits:**
- Would remove the duplicate storage of `Vector2 pos` + `Rect` in `BaseEntity`
- Would eliminate manual rounding like `int(self.pos.x)`, `int(self.pos.y)`
- Full compliance with reference guide §2.2

**Costs:**
- Impact on `base.py`, `player.py`, `npc.py`, `groups.py`, and `collision_checker.py`
- Potential for regression in collision detection (FRect vs Rect in collision checking)
- Estimated effort: >4h + 2h of collision regression testing

**Current Jitter:** Not observed. The rounded `Vector2 pos` + `Rect` system functions correctly. No jitter reported during gameplay.

## Decision

**Do not migrate to FRect in Phase 1.**

The dual-system is functional. The benefit (code simplification) does not justify the risk of collision regression and the migration effort.

## Revision Conditions

Reconsider if:
1. Sub-pixel jitter is observed in distribution (high-resolution screens)
2. FRect migration is proposed in a dedicated release with a complete collision test suite
3. pygame-ce provides an official FRect migration guide

## Unmodified Files

- `src/entities/base.py`
- `src/entities/player.py`
- `src/entities/groups.py`
- `src/engine/collision_checker.py`
