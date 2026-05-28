# ADR-004 — Context Injection via `game: Any` for Technical Refactoring Phase 1.5

**Date:** 2026-05-07  
**Status:** ✅ Accepted  
**Context:** Technical Refactoring Phase 1.5  

---

## Context

To successfully refactor `game.py` below 400 LOC, it is necessary to extract `EntityFactory`, `MapLoader`, `InputHandler`, and `CollisionChecker` into separate modules. These classes need access to `Game` properties (sprite groups, layout, map_manager, world_state, etc.).

## Evaluated Options

| Option | Description | Result |
|--------|-------------|---------|
| **A** `game: Any` | Pass the `game` object reference as an `Any` type in the constructor | ✅ Selected |
| **B** `TYPE_CHECKING` | Use `if TYPE_CHECKING: from src.engine.game import Game` | ❌ Generates architectural cycles detected by Sentrux |
| **C** Protocol/ABC | Have `Game` implement a formal `IGameContext` interface | ❌ Over-engineered for Phase 1.5 |
| **D** Module-level functions | Delegate to free functions like `spawn_entities(game, entities)` | Partial — adopted for `game_setup.py` and `spatial_utils.py` |

## Decision

Adopt `from typing import Any` for all newly extracted classes that receive `game` as a constructor parameter:

```python
from typing import Any

class EntityFactory:
    def __init__(self, game: Any) -> None:
        self.game = game
```

## Rationale

1. **Established Pattern**: `InteractionManager(game: Any)` and `RenderManager(game: Any)` already use this pattern successfully (proven by `L-ARCH-007`).
2. **Zero Cycles**: Typing `game` as `Any` avoids all cyclic imports detected by Sentrux. Relying on `TYPE_CHECKING` still generates architectural import coupling, even if Python doesn't crash at runtime.
3. **Minimalism**: Phase 1.5 is a LOC-reduction refactor, not a deep architectural overhaul. Introducing structural Protocols would change the public interface of `Game` unnecessarily.
4. **Tested Precedent**: The `InteractionManager(self)` pattern has been stable since Phase 1, maintaining 170 green tests.

## Consequences

- `game` remains a "God Object" — technical debt accepted until Phase 3+.
- Newly extracted classes cannot function without a valid `Game` instance.
- Mocking is handled easily via `MagicMock()` for `game` (a pattern widely used in existing tests).
