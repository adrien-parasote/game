# ADR-008 — Migration vers pygame.FRect : Décision de Non-Migration (Phase 1)

**Date :** 2026-05-26
**Status :** ✅ Accepted — Migration différée

## Contexte

Le guide de référence `pygame_ce_python_312_best_practices.md §2.2` recommande l'utilisation
de `pygame.FRect` pour les entités mobiles afin d'éliminer le jitter sub-pixel.

Le projet utilise actuellement `pygame.Rect` (entier) pour les hitboxes et positions de rendu,
combiné avec `pygame.math.Vector2` pour les positions sub-pixel (`pos`, `target_pos`).

## Analyse coût/bénéfice

**Bénéfice :**
- Supprimerait le double-stockage `Vector2 pos` + `Rect` dans `BaseEntity`
- Éliminerait les arrondis manuels `int(self.pos.x)`, `int(self.pos.y)`
- Conformité totale avec le guide de référence §2.2

**Coût :**
- Impact sur `base.py`, `player.py`, `npc.py`, `groups.py`, `collision_checker.py`
- Potentiel de régression sur la détection de collisions (FRect vs Rect en collision check)
- Effort estimé : >4h + 2h de tests de régression collision

**Jitter actuel :** Non observé. Le système `Vector2 pos` + `Rect` arrondi fonctionne
correctement. Aucun rapport de jitter en gameplay.

## Décision

**Ne pas migrer vers FRect en Phase 1.**

Le double-système est fonctionnel. Le bénéfice (simplification du code) ne justifie pas
le risque de régression sur les collisions et l'effort de migration.

## Conditions de révision

Reconsidérer si :
1. Du jitter sub-pixel est observé en distribution (écrans haute résolution)
2. La migration vers FRect est proposée dans une release dédiée avec test suite de collision complète
3. pygame-ce fournit un guide de migration officiel FRect

## Fichiers non modifiés

- `src/entities/base.py`
- `src/entities/player.py`
- `src/entities/groups.py`
- `src/engine/collision_checker.py`
