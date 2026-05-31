# Plan d'implémentation — Extraction de constantes et Traduction (Tooling)

Ce plan décrit l'extraction systématique des constantes magiques du module `tools/asset_creator/` vers un fichier centralisé `constants.py`, ainsi que la traduction de tous les commentaires et logs en français restants vers l'anglais.

---

## User Review Required

> [!IMPORTANT]
> Ce refactoring est garanti sans régression. Les 361 tests unitaires et d'intégration existants dans `tests/tools/asset_creator/` seront exécutés pour valider la non-régression à chaque étape.

---

## Proposed Changes

### Centralisation des constantes

#### [NEW] [constants.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/core/constants.py)
* Création d'un module centralisé contenant toutes les dimensions de tuiles (`TILE_SIZE = 32`, `SUBTILE_SIZE = 16`, `NUM_BLOB_TILES = 47`), les configurations de bruit par défaut (`DEFAULT_NOISE_SCALE`, `DEFAULT_OCTAVES`, `DEFAULT_PERSISTENCE`, `DEFAULT_LACUNARITY`), les facteurs d'effets de bordure (`BORDER_SHADOW_FACTOR`, `BORDER_HIGHLIGHT_FACTOR`), la matrice de Bayer (`BAYER_4X4`), les répertoires d'export par défaut, les couleurs de l'application et les paramètres de preview Pygame.

#### [MODIFY] [subtile.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/core/subtile.py)
* Import et utilisation des constantes centralisées (comme `TILE_SIZE`, `SUBTILE_SIZE`, `BORDER_SHADOW_FACTOR`, `BORDER_HIGHLIGHT_FACTOR`).

#### [MODIFY] [texture.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/core/texture.py)
* Remplacement de la matrice `BAYER_4X4` et des paramètres de bruit par défaut par des imports de `constants.py`.

#### [MODIFY] [tile_assembler.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/core/tile_assembler.py)
* Remplacement de `BLOB_BITMASKS` et des tailles de tuiles par les constantes partagées.

#### [MODIFY] [pipeline.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/gui/pipeline.py)
* Remplacement des dimensions magiques de tuiles par `TILE_SIZE` et `NUM_BLOB_TILES`.

#### [MODIFY] [state.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/gui/state.py)
* Utilisation des chemins et des couleurs par défaut centralisés.

#### [MODIFY] [app.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/gui/app.py)
* Intégration des constantes de taille de tuile pour la peinture et le rendu DPG.

#### [MODIFY] [pygame_preview.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/preview/pygame_preview.py)
* Utilisation des constantes de grille de preview et de couleurs d'arrière-plan.

### Traduction Français → Anglais

* Audit de tous les fichiers de `tools/asset_creator` pour traduire les commentaires en français restants (principalement dans la CLI, l'UI et les explications d'algorithmes) vers l'anglais.

---

## Verification Plan

### Automated Tests
```bash
# Lancer toute la suite de tests pour s'assurer que le refactoring conserve 100% de la logique
./venv/bin/pytest tests/tools/
```
