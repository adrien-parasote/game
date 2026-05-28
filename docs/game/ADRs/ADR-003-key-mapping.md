# ADR-003 — Key Mapping: ESC → Pause Menu

**Date:** 2026-05-02  
**Status:** ✅ Accepted (Revised)

## Context

`ESC` (`K_ESCAPE`) was originally mapped as the `quit_key` in `gameplay.json` — it terminated the game immediately on press. With the introduction of the Pause Menu, `ESC` must trigger the pause overlay instead of abruptly exiting.

The introduction of a dedicated "Quit" key (`F4`) was evaluated and **rejected**: it is not the standard convention on macOS. The user exits the game via the standard OS shortcuts `Cmd+Q` or the window close button — which Pygame natively handles via `pygame.QUIT`.

## Decision

| Key / Action | Pygame Constant | Role |
|---|---|---|
| `ESC` | `K_ESCAPE` | Open Pause Menu (in-game) / Return to Main Menu (in Pause) |
| Close Window / `Cmd+Q` | `pygame.QUIT` | Close the game (OS-level handling, natively supported) |

The `quit_key` property is **removed** from `gameplay.json` — window closure delegates to standard OS behaviors.

## Consequences

- `gameplay.json`: `quit_key` property deleted.
- `GameStateManager._handle_events()` intercepts `K_ESCAPE` globally and handles state transition `PLAYING → PAUSED`.
- `pygame.QUIT` (closing the window) is intercepted in `GameStateManager` to cleanly shut down the event loop.
- `Game._handle_events()` no longer handles `K_ESCAPE` directly.
- Existing unit tests remain fully valid — they instantiate `Game` in isolation.
