# ADR-006 — Pre-render Cache Pattern pour les surfaces UI statiques

**Date :** 2026-05-07  
**Statut :** ✅ ACCEPTED — Implémenté (commit `perf-constants`)

---

## Contexte

Le moteur de jeu présentait trois catégories de dette technique impactant les performances runtime et la maintenabilité :

1. **Allocations de Surface par frame** : `_blit_halo_text()` (partagé entre `pause_screen.py`, `save_menu.py`, `title_screen_draw.py`) allouait `pygame.Surface` + exécutait `gaussian_blur()` à 60 FPS lors des états hover. `chest_draw._draw_title()` instanciait un objet Font à chaque frame de draw. `hud.draw()` construisait `I18nManager()` à chaque frame.

2. **Valeurs magic orphelines** : 40+ tuples RGB, tailles en pixels, tailles de fonts et couleurs d'engraving étaient hardcodées dans 5 fichiers non-constants (`save_menu.py`, `pause_screen.py`, `chest_draw.py`, `dialogue.py`, `lighting.py`), violant l'architecture `_constants.py` établie.

3. **Un commentaire en français** dans `game_state_manager.py:133` violant la politique all-English.

## Décision

**Pattern pre-render cache** : les surfaces de texte statiques sont calculées une seule fois à `__init__` (ou `refresh()` pour le texte dépendant de données), stockées dans `dict[key → Surface]`, invalidées uniquement quand la source change. Ce pattern existait déjà dans `title_screen.py` (ligne 168).

**Aucune nouvelle abstraction.** Aucune nouvelle classe. Extension des fichiers `_constants.py` existants ou création d'un seul nouveau (`save_menu_constants.py`).

| Amélioration | Avant | Après |
|---|---|---|
| Surface allocs dans `_blit_halo_text` par frame | 2 allocs + 1 gaussian_blur par item hover | 0 (pre-render à init) |
| Font créé dans `_draw_title()` | 1 par frame (60×/s) | 0 (cached dans mixin init) |
| `I18nManager()` dans `draw()` | 1 par frame | 0 (cached dans `__init__`) |
| Magic values dans fichiers non-constants | 40+ | 0 |

## Alternatives rejetées

| Alternative | Raison du rejet |
|---|---|
| NumPy vectorization de `_create_beam_surface()` | Spec séparée nécessaire, hors scope |
| Nouvelle couche d'abstraction UI | Inutile — extension des patterns existants suffisante |
| Changements de l'asset pipeline | Hors scope — refactor uniquement |

## Conséquences

**Positives :**
- Zéro allocation `Surface` dans les hot paths de draw (pause menu, save menu, HUD)
- Architecture `_constants.py` complète : tous les modules UI ont leur fichier constants dédié
- Comportement observable inchangé — refactor pur

**Contraintes :**
- Les surfaces pre-render doivent être invalidées explicitement si la donnée source change (ex: `SaveMenuOverlay.refresh()` reconstruit `_cached_title_surfs`)
- Pattern `_rendered_idle` / `_rendered_hover` : deux listes séparées, `draw()` indexe selon l'état hover

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `src/ui/pause_screen.py` | `_make_engraved_surface()` + `_make_halo_surface()` au `__init__` |
| `src/ui/save_menu.py` | `_cached_title_surfs` pre-render dans `refresh()` |
| `src/ui/chest_draw.py` | Font cached dans mixin `__init__` |
| `src/ui/hud.py` | `self._i18n = I18nManager()` dans `__init__` |
| `src/ui/save_menu_constants.py` | *(nouveau)* 15 constantes |
| `src/ui/pause_screen_constants.py` | +12 nouvelles constantes |
| `src/engine/lighting_constants.py` | `BEAM_COLOR_MOON`, `BEAM_COLOR_SUN` |
| `src/ui/dialogue_constants.py` | `DIALOGUE_SHADOW_COLOR`, `DIALOGUE_TEXT_COLOR` |
| `src/ui/chest_constants.py` | `CHEST_TITLE_TEXT`, `CHEST_TEXT_COLOR`, `CHEST_SLOT_FALLBACK_COLOR` |
| `src/engine/game_state_manager.py` | Fix commentaire français ligne 133 |

## Références

- Learning `L-UI-011` — Pre-render cache pattern (`.agents/learnings/ui.md`)
- Learning `L-UI-012` — Constants-first refactor order (`.agents/learnings/ui.md`)
- Spec stratégique originale : `docs/strategic/perf-constants-audit-strategy.md` *(archivée — ce ADR en est la forme canonique)*
