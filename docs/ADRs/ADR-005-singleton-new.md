# ADR-005 — `__new__` Singleton Pattern for AssetManager and I18nManager

**Date:** 2026-04-28  
**Status:** ✅ Accepted

---

## Context

Multiple game modules need access to `AssetManager` (image/font cache) and `I18nManager` (translations) without generating cyclic imports. Both managers are stateless by design (pure caches) and must be accessible from any module without requiring explicit constructor injection.

## Decision

Implement both `AssetManager` and `I18nManager` using the Python `__new__` singleton pattern:

```python
class AssetManager:
    _instance: "AssetManager | None" = None

    def __new__(cls) -> "AssetManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance
```

**Access Pattern:** Call `AssetManager()` directly from any module without needing to import or manage shared instances.

## Rejected Alternatives

| Alternative | Reason for Rejection |
|---|---|
| Module-level singleton (global variable) | Difficult to test due to persistent state leaking across unit tests |
| Dependency injection (constructor) | Generates cyclic imports between UI components and the core engine |
| `@classmethod` factory | More verbose and less idiomatic in Python than native class instantiation |

## Consequences

**Positive:**
- Zero-configuration global access from any module.
- Prevents cyclic dependencies.
- Behaves identically to a global module, but remains easily testable via resetting `_instance = None`.

**Constraints / Negatives:**
- Never call `AssetManager()` inside hot paths (e.g., rendering loops) — see performance warning `A-ARCH-002` in `game_engine.md`.
- Store the manager reference as an instance attribute during initialization: `self._assets = AssetManager()`.
- Tests that modify the singleton's internal state must explicitly reset it: `AssetManager._instance = None`.

## References

- `src/engine/asset_manager.py` — `AssetManager` implementation.
- `src/engine/i18n.py` — `I18nManager` implementation.
- `docs/specs/00_MASTER.md` Section 2 (Global Registry).
- Learning `A-ARCH-002` in `.agents/learnings/game_engine.md`.
