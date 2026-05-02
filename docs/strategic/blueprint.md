# Strategic Blueprint — Phase 1 : Game Flow & Save System

**Document type :** Strategic  
**Date :** 2026-05-02  
**Status :** ✅ Approuvé — Gaps résolus, prêt pour SPEC

---

## 🎯 Problème résolu

Le joueur ne peut pas quitter et reprendre une partie. Le jeu s'ouvre directement sur la map sans écran d'accueil. Toute progression est perdue à la fermeture.

**Outcome cible :** Lancer le jeu → choisir une sauvegarde → jouer → sauvegarder manuellement → quitter → reprendre exactement là où on en était.

---

## 📊 Critères de succès

| Critère | Cible |
|---|---|
| Menu Principal fonctionnel | 4 boutons : Nouvelle Partie, Charger, Options (stub), Quitter |
| Sauvegarde complète | WorldState + Inventory + Equipment + TimeSystem + Player position + map courante |
| Chargement sans régression | Toutes les entités restaurées dans le bon état |
| Menu Pause fonctionnel | Reprendre / Sauvegarder / Quitter vers menu |
| Couverture tests | ≥80% sur SaveManager, GameStateManager |
| Zéro régression | 444 tests existants continuent de passer |

---

## 🏗️ Architecture — Décision centrale

**`GameStateManager` comme orchestrateur externe à `Game`**

```
main.py
  └── GameStateManager.run()        ← nouveau, boucle principale
        ├── state = TITLE
        │     └── TitleScreen.draw/handle_event()
        ├── state = PLAYING
        │     └── Game.run_frame()   ← Game modifié pour tick-par-tick
        └── state = PAUSED
              └── PauseScreen.draw/handle_event() (overlay)
```

**Pourquoi pas intégrer dans `game.py` :** Déjà 854 lignes. Ajouter la state machine + 3 écrans = ~1200 lignes. Violation règle 800L max.  
**Pourquoi pas refonte totale :** `Game` préservé intact → zéro régression sur les 444 tests.

→ Voir **ADR-001**

---

## 📁 Stockage des sauvegardes

- **Répertoire :** `saves/` à la racine du projet
- **Fichiers :** `saves/slot_1.json`, `saves/slot_2.json`, `saves/slot_3.json`
- **Format :** JSON lisible (pas de pickle, pas de SQLite)
- **Git :** `saves/` dans `.gitignore` — les saves sont locales, jamais commitées

→ Voir **ADR-002**

---

## ⌨️ Mapping des touches

| Touche / Action | Rôle |
|---|---|
| `ESC` (`K_ESCAPE`) | Ouvrir Pause (en jeu) / Retour menu principal (en Pause) |
| Fermeture fenêtre / `Cmd+Q` | Quitter le jeu (standard macOS, géré par `pygame.QUIT`) |

`quit_key` est **supprimé** de `gameplay.json` — pas de touche dédiée, standard OS uniquement.

→ Voir **ADR-003**

---

## 🎮 Fonctionnalités (ordre d'implémentation)

| # | Module | Fichier | Dépendances |
|---|---|---|---|
| 1 | **SaveManager** | `src/engine/save_manager.py` | WorldState, Inventory, TimeSystem |
| 2 | **TitleScreen** | `src/ui/title_screen.py` | SaveManager, assets menu/ (4 boutons : Nouvelle Partie, Charger, Options, Quitter) |
| 3 | **GameStateManager** | `src/engine/game_state_manager.py` | TitleScreen, Game |
| 4 | **PauseScreen** | `src/ui/pause_screen.py` | SaveManager, assets menu/ |
| 5 | **Game hooks** | `src/engine/game.py` | SaveManager |
| 6 | **main.py** | `src/main.py` | GameStateManager |

---

## 🚫 Ce qu'on ne construit PAS

| Exclusion | Rationale |
|---|---|
| Autosave automatique | Déféré Phase 1.5 — UX à définir (quand ? quelle fréquence ?) |
| Screenshots dans les slots | Déféré — nécessite un timing de capture précis (après rendu) |
| Menu Options fonctionnel | Bouton présent mais stub — sliders audio = Phase 3 |
| Chiffrement des saves | Projet solo — non nécessaire |
| Cloud saves | Hors scope complet |

---

## 🔗 Références

- ADRs : `docs/ADRs/ADR-001-gamestate-architecture.md`, `ADR-002-save-format.md`, `ADR-003-key-mapping.md`
- Assets : `assets/images/menu/00-title_logo.png` … `04-save_slot.png`
- Spec détaillée : `docs/specs/game-flow-spec.md` *(à créer en SPEC)*
- Codemaps actuels : `docs/codemaps/architecture.md`
