# ADR-004 — Context Injection via `game: Any` pour le Refactoring Phase 1.5

**Date :** 2026-05-07  
**Statut :** Accepted  
**Contexte :** Phase 1.5 — Refactoring Technique

---

## Contexte

Pour faire descendre `game.py` sous 400 LOC, il est nécessaire d'extraire `EntityFactory`, `MapLoader`, `InputHandler` et `CollisionChecker` dans des modules séparés. Ces classes ont besoin d'accéder aux attributs de `Game` (groupes sprites, layout, map_manager, world_state, etc.).

## Options considérées

| Option | Description | Résultat |
|--------|-------------|---------|
| **A** `game: Any` | Passer `game` comme `Any` dans le constructeur | ✅ Choisi |
| **B** `TYPE_CHECKING` | `if TYPE_CHECKING: from src.engine.game import Game` | ❌ Crée cycles détectés par sentrux |
| **C** Protocol/ABC | `Game` implemente une IGameContext interface | ❌ Sur-ingénierie pour Phase 1.5 |
| **D** Fonctions module-level | `spawn_entities(game, entities)` | Partiel — OK pour `game_setup.py` et `spatial_utils.py` |

## Décision

Utiliser `from typing import Any` pour toutes les nouvelles classes qui reçoivent `game` en paramètre constructeur.

```python
from typing import Any

class EntityFactory:
    def __init__(self, game: Any) -> None:
        self.game = game
```

## Rationale

1. **Pattern établi** : `InteractionManager(game: Any)` et `RenderManager(game: Any)` utilisent déjà ce pattern (L-ARCH-007 prouvé).
2. **Zéro cycle** : `Any` évite tout cycle d'import détecté par sentrux. `TYPE_CHECKING` crée des cycles architecturaux même si Python ne crashe pas.
3. **Minimal** : Phase 1.5 est un refactoring LOC, pas un redesign architectural. Introduire des Protocols changerait l'interface publique de `Game`.
4. **Précédent testé** : Le pattern `InteractionManager(self)` est stable depuis Phase 1 avec 170 tests verts.

## Conséquences

- `game` reste un "God Object" — dette technique acceptée jusqu'à Phase 3+
- Les nouvelles classes ne peuvent pas être utilisées sans une instance `Game`
- Testabilité via `MagicMock()` pour `game` (pattern déjà utilisé dans les tests existants)
