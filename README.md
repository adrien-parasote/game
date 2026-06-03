# ⚔️ RPG Tile Engine & The Heir's Awakening

[![Python Version](https://img.shields.io/badge/python-3.12+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/built%20with-pygame--ce-orange?style=flat-square&logo=pygame)](https://pyga.me/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square&logo=python&logoColor=white)](https://github.com/astral-sh/ruff)

Bienvenue dans le "Meta-Workspace" de **The Heir's Awakening**. Ce répertoire racine est le point d'entrée pour les développeurs, centralisant le moteur de jeu, les outils de génération procédurale, et les configurations de nos agents IA (Stream Coding).

> 📖 **Joueurs, Scénaristes et Game Designers :**  
> Tout ce qui concerne l'histoire, les mécaniques (GDD), la vision globale et la feuille de route du jeu se trouve sur notre **[Wiki GitHub Officiel](https://github.com/adrien-parasote/game/wiki)**.

---

## 🏗️ Architecture du Projet

Le projet adopte une séparation stricte entre le moteur technique et la documentation métier (Lore/GDD) pour garder le code propre et éviter la surcharge cognitive.

- **[`game/`](./game)** : Le moteur RPG construit avec Pygame-CE. Contient le code source, les entités, le rendu, les tests et la documentation *strictement technique* (Spécifications IA, ADRs).
- **[`tools/`](./tools)** : Outils de développement autonomes (Générateur de tilesets procédural avec Dear PyGui).
- **[`assets/`](./assets)** : Ressources partagées (images, audio, données) utilisées par le jeu et les outils.
- **[`scripts/`](./scripts)** : Pipelines de build, gestion de release, et vérifications de qualité.
- **`game-wiki/`** *(Non versionné ici)* : Si vous l'avez cloné, ce dossier "fantôme" (ignoré par Git) contient le wiki local permettant l'édition de la documentation humaine côte à côte avec le code.

---

## 🚀 Getting Started (Développeurs)

### Prérequis
- **Python 3.12+**
- **Make** (optionnel, mais recommandé)

### Lancement Rapide
Pour travailler sur un domaine spécifique, naviguez dans son répertoire :
```bash
# Pour le moteur de jeu :
cd game
make setup  # Initialise le venv et installe les dépendances
make run    # Lance le jeu

# Pour les outils procéduraux :
cd tools
make setup
make run
```

### Installation Manuelle (Sans Make)
1. `cd game` (ou `cd tools`)
2. `python -m venv venv`
3. Activation : `source venv/bin/activate` (Linux/macOS) ou `venv\Scripts\activate` (Windows)
4. `pip install -r requirements.txt`

---

## 🧪 Qualité & IA (Stream Coding)

Ce projet est activement développé avec des agents IA respectant une méthodologie stricte (Stream Coding).

- **Testing** : Lancez `make test` à la racine, ou dans `game/`.
- **Linting & Formattage** : `ruff check .`
- **Validation IA** : `verify.py` et `spec_conformance.py` assurent que le code généré respecte à 100% les spécifications (`game/docs/specs/`).
- **Sentinelles Git** : Ne jamais bypasser les hooks sans raison valable. Les commits sont formatés sémantiquement.

---

## 📜 Licence
MIT
