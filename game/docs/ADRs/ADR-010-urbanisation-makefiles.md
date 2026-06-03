# Plan d'Urbanisation : Makefiles & Environnements

## Objectif
Simplifier l'infrastructure du projet pour n'avoir **qu'un seul environnement virtuel** et **un seul Makefile**.

## Changements Proposés

### 1. Centralisation des Dépendances
Au lieu d'avoir `game/requirements.txt` et `tools/requirements.txt`, nous allons avoir un seul `requirements.txt` à la racine.
Nous en profiterons pour nettoyer les dépendances obsolètes de l'ancien `asset_creator` (`dearpygui`, `opensimplex`) et ajouter `customtkinter`.

#### [NEW] requirements.txt
```txt
# Core Dependencies
pygame-ce==2.5.7
numpy
Pillow
customtkinter==5.2.2
PyYAML

# Development & Testing
pytest==9.0.3
pytest-cov==6.1.0
ruff==0.9.9
pyright==1.1.396
pyobjc-framework-Cocoa; sys_platform == 'darwin'
```
#### [DELETE] game/requirements.txt
#### [DELETE] tools/requirements.txt

---

### 2. Makefile Unique à la racine
Un seul fichier `Makefile` pour tout orchestrer. Il créera un unique `venv` à la racine et utilisera les configurations globales déjà présentes dans `pyproject.toml`.

#### [MODIFY] Makefile
Le nouveau Makefile contiendra :
- `make setup` : Crée le venv racine et installe le `requirements.txt` global.
- `make run-game` : Lance le jeu.
- `make run-tools` : Lance le générateur procédural.
- `make test` : Lance `pytest` (qui couvre déjà `game/` et `tools/`).
- `make lint` / `make typecheck` : Commandes utilitaires pour `ruff` et `pyright`.
- `make clean` : Nettoie les caches et le `venv`.

#### [DELETE] game/Makefile
#### [DELETE] tools/Makefile
