# Documentation Split & Global Readme Update

Ce plan détaille la répartition de la documentation existante entre le repository technique et le wiki "humain", ainsi que la refonte du README principal pour refléter cette nouvelle architecture.

## 1. Séparation de la documentation

### A. Documentation Humaine / Lore (Vers `game-wiki/`)
Ces documents s'adressent aux Game Designers, Scénaristes et Joueurs. Ils ne contiennent pas de détails d'implémentation code.
- **[MOVE]** Déplacer `game/docs/strategic/game_vision.md` vers `game-wiki/Game_Vision.md`.
- **[NEW]** Créer la structure de base du wiki (basée sur le `Home.md` actuel) :
  - `game-wiki/GDD_Mecaniques.md` (Game Design Document)
  - `game-wiki/Lore_Univers.md` (Histoire, Personnages)

### B. Documentation Technique (Reste dans `game/docs/`)
Ces documents s'adressent aux Développeurs et à l'IA.
- **[KEEP]** `game/docs/strategic/MASTER_ROADMAP.md` (Contient les micro-versions et l'architecture technique).
- **[KEEP]** `game/docs/specs/` (Toutes les spécifications d'implémentation IA).
- **[KEEP]** `game/docs/ADRs/` (Décisions d'architecture).

## 2. Amélioration du README global (`/README.md`)

Le fichier `README.md` à la racine sera refondu pour devenir la vitrine du projet et le point d'entrée du "Meta-Workspace".

**Nouvelle structure du README :**
1. **Introduction & Vision globale :** Présentation du RPG "The Heir's Awakening".
2. **L'Architecture du Projet (Le Split) :**
   - Lien clair vers le [Wiki GitHub](https://github.com/adrien-parasote/game/wiki) pour le Lore et le Game Design.
   - Explication de la structure technique (`game/`, `tools/`, `assets/`).
3. **Getting Started (Développeurs) :** Instructions pour lancer le jeu et les outils de génération procédurale.
4. **Qualité et IA (Stream Coding) :** Mention des règles de contribution assistées par IA et de la couverture de test.

## User Review Required

> [!IMPORTANT]
> 1. Êtes-vous d'accord pour conserver le `MASTER_ROADMAP.md` dans la partie technique (étant donné qu'il contient le découpage en micro-versions de code), ou souhaitez-vous en extraire une version simplifiée pour le Wiki ?
> 2. Est-ce que le déplacement exclusif de la Vision (`game_vision.md`) vers le Wiki vous convient pour démarrer l'alimentation ?

Validez ce plan et je m'occuperai de déplacer les fichiers, de structurer le Wiki, et de réécrire le README global.
