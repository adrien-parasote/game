# ADR-001 — Architecture : GameStateManager externe à Game

**Date :** 2026-05-02  
**Status :** ✅ Accepté

## Contexte

`game.py` fait 854 lignes. Il faut ajouter un Menu Principal, un Menu Pause et un système de sauvegarde. Deux options ont été évaluées.

## Options évaluées

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A (retenue)** | `GameStateManager` externe orchestre `Game` comme objet | Zero régression, `game.py` inchangé, testable séparément | `Game.run()` doit devenir `run_frame(dt)` |
| **B (rejetée)** | Intégrer state machine dans `game.py` | Un seul fichier | `game.py` → ~1200L, viole règle 800L, risque de régression sur 444 tests |

## Décision

Option A. `GameStateManager` est le nouveau point d'entrée. Il possède une boucle principale et délègue le rendu/update à l'état courant (`TitleScreen`, `Game`, `PauseScreen`).

`Game.run()` est remplacé par `Game.run_frame(dt) -> GameEvent` qui retourne un événement (`PAUSE_REQUESTED`, `QUIT`, `None`) au lieu de boucler indéfiniment.

## Conséquences

- `main.py` instancie `GameStateManager` au lieu de `Game`
- `Game` reçoit 2 nouveaux hooks : `run_frame(dt)` et `save_state() -> dict`
- Les 444 tests existants ne sont pas affectés (ils instancient `Game` directement)
