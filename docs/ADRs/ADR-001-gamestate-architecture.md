# ADR-001 — Architecture: External GameStateManager Orchestrating Game

**Date:** 2026-05-02  
**Status:** ✅ Accepted

## Context

`game.py` is 854 lines long. We need to introduce a Main Menu, a Pause Menu, and a save system. Two structural options were evaluated.

## Evaluated Options

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A (Selected)** | External `GameStateManager` orchestrating `Game` as an object | Zero regressions, `game.py` remains unchanged, separately testable | `Game.run()` must become `run_frame(dt)` |
| **B (Rejected)** | Integrating the state machine directly inside `game.py` | Single file structure | `game.py` expands to ~1200 LOC, violating the 800-line rule, risking regressions across 444 tests |

## Decision

Option A. `GameStateManager` is established as the new entry point. It hosts the main gameplay loop and delegates rendering and updates to the current active state (`TitleScreen`, `Game`, `PauseScreen`).

`Game.run()` is replaced with `Game.run_frame(dt) -> GameEvent`, which returns contextual events (`PAUSE_REQUESTED`, `QUIT`, `None`) to the manager instead of looping infinitely.

## Consequences

- `main.py` instantiates `GameStateManager` instead of `Game`.
- `Game` receives two new hooks: `run_frame(dt)` and `save_state() -> dict`.
- The 444 existing unit tests are unaffected (they instantiate `Game` directly in isolation).
