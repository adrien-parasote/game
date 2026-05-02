# ADR-003 — Mapping des touches : ESC → Pause

**Date :** 2026-05-02  
**Status :** ✅ Accepté (révisé)

## Contexte

`ESC` (`K_ESCAPE`) était mappé comme `quit_key` dans `gameplay.json` — il quittait le jeu immédiatement. Avec l'introduction du menu Pause, `ESC` doit ouvrir ce menu au lieu de quitter brutalement.

La question d'une touche dédiée "Quitter" (`F4`) a été évaluée et **rejetée** : ce n'est pas le standard sur macOS. L'utilisateur quitte via `Cmd+Q` ou le bouton de fermeture de fenêtre — pygame gère déjà cela nativement via `pygame.QUIT`.

## Décision

| Touche / Action | Pygame Constant | Rôle |
|---|---|---|
| `ESC` | `K_ESCAPE` | Ouvrir menu Pause (en jeu) / Retour menu principal (en Pause) |
| Fermeture fenêtre / `Cmd+Q` | `pygame.QUIT` | Quitter le jeu (géré par l'OS, déjà supporté) |

`quit_key` est **supprimé** de `gameplay.json` — la fermeture passe par le standard OS.

## Conséquences

- `gameplay.json` : clé `quit_key` supprimée
- `GameStateManager._handle_events()` intercepte `K_ESCAPE` globalement et bascule `PLAYING → PAUSED`
- `pygame.QUIT` (fermeture fenêtre) est intercepté dans `GameStateManager` pour arrêter proprement la boucle
- `Game._handle_events()` ne gère plus `K_ESCAPE` directement
- Les tests existants restent valides — ils instancient `Game` en isolation
