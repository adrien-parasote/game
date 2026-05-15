# ADR-005 — `__new__` Singleton pour AssetManager et I18nManager

**Date :** 2026-04-28  
**Statut :** ACCEPTED

---

## Contexte

Plusieurs modules du jeu ont besoin d'accéder à `AssetManager` (cache d'images/fonts) et `I18nManager` (traductions) sans dépendance circulaire. Ces deux managers sont stateless par nature (caches purs) et doivent être accessibles depuis n'importe quel module sans injection explicite.

## Décision

Implémenter `AssetManager` et `I18nManager` avec le pattern `__new__` singleton :

```python
class AssetManager:
    _instance: "AssetManager | None" = None

    def __new__(cls) -> "AssetManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance
```

**Pattern d'accès :** `AssetManager()` depuis n'importe quel module, sans `import` d'instance partagée.

## Alternatives rejetées

| Alternative | Raison du rejet |
|---|---|
| Module-level singleton (variable globale) | Difficile à tester (état persistant entre tests) |
| Dependency injection (constructeur) | Crée des cycles d'import entre les modules UI et engine |
| `@classmethod` factory | Plus verbeux, moins idiomatique en Python |

## Conséquences

**Positives :**
- Accès zero-config depuis n'importe quel module
- Pas de dépendance circulaire
- Comportement identique à un module global mais testable via `_instance = None` reset

**Négatives / Contraintes :**
- Ne jamais appeler `AssetManager()` dans des méthodes chaudes (hot path) — voir `A-ARCH-002` dans `game_engine.md` (leurre de performance)
- Stocker la référence comme attribut d'instance dans `__init__` : `self._assets = AssetManager()`
- Tests qui modifient l'état du singleton doivent le resettre via `AssetManager._instance = None`

## Référence

- `src/engine/asset_manager.py` — implémentation `AssetManager`
- `src/engine/i18n.py` — implémentation `I18nManager`
- `docs/specs/00_MASTER.md` section 2 (Global Registry)
- Learning `A-ARCH-002` dans `.agents/learnings/game_engine.md`
