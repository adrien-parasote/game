# Tooling Documentation Hub

Bienvenue dans la documentation du **Tooling** (Outillage). Ce répertoire contient l'ensemble des spécifications, blueprints, et recherches concernant les outils développés pour le jeu.

---

## 1. Asset Convertor

L'Asset Convertor est l'outil central (basé sur Dear PyGui) permettant de composer, dessiner et exporter des tuiles complexes (blobs, variations de terrain).

* **Spec Active** : [Asset Convertor Spec](./specs/asset_convertor_spec.md)
* **Stratégie / Blueprint** : [Asset Convertor Blueprint](./strategic/asset_convertor_blueprint.md)
* **ADR** : [ADR-001 Dear PyGui remplace Pygame](./ADRs/adr-001-dearpygui-replaces-pygame.md)

<details>
<summary><strong>Recherche Initiale</strong></summary>

* **Recherche GUI** : [python_gui_frameworks.md](./research/python_gui_frameworks.md)
* **Recherche Concept** : [asset_creation_tool.md](./research/asset_creation_tool.md)
</details>

---

## 2. Autotile Pipeline

Les outils d'autotiling transforment les assets de type "RPG Maker" vers le format "Wangset / Terrain" attendu par Tiled Map Editor (modèle "blob" 47 tuiles).

* **Spec Active** : [Autotile Converter Spec](./specs/autotile_converter_spec.md)
* **Stratégie** : [Autotile Pipeline Strategy](./strategic/autotile-pipeline-strategy.md)

<details>
<summary><strong>Recherche Initiale</strong></summary>

* **Recherche Tiled** : [autotile_to_tiled.md](./research/autotile_to_tiled.md)
</details>

---

## 3. Diagonal Walls

Génération des murs en diagonale avec ombres dynamiques.

* **Spec Active** : [Diagonal Wall Spec](./specs/diagonal_wall_spec.md)
* **Stratégie** : [Diagonal Wall Blueprint](./strategic/diagonal_wall_blueprint.md)
* **Recherche** : [Diagonal Wall Transformation](./research/diagonal_wall_transformation.md)

---

## 4. Code Quality & Constants

Extraction de constantes magiques, qualité du code et traduction.

* **Spec Active** : [Code Quality Constants and Translation](./specs/code_quality_constants_and_translation.md)
* **Stratégie** : [Constants Extraction Blueprint](./strategic/constants_extraction_blueprint.md)
* **Recherche** : [Code Optimization & Constants](./research/code_optimization_and_constants.md)
