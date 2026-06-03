# Learnings: Tooling (L-TOOL)

> Domaine: `TOOL`
> Périmètre: Développement d'outils, scripts de conversion, Asset Creator, générateurs.

## L-TOOL-001 · 2026-05-31 · Universal · UI Framework Python
**Contexte :** Outil Asset Creator avec UI interactive.
**Outcome :** `Dear PyGui` est nettement supérieur à `Pygame` pour développer des outils d'édition complexes en Python. Pygame nécessite de gérer manuellement la boucle d'événements, le layout et les composants UI, menant à du code spaghetti. Dear PyGui offre des layouts natifs, des modales, du drag-and-drop et un système de thèmes tout en gardant d'excellentes performances (rendu GPU).
**Pattern :** Utiliser Dear PyGui pour tout nouvel outil interne nécessitant une interface graphique riche, en séparant la vue du state applicatif (cf. `gui/state.py`).

## L-TOOL-002 · 2026-05-31 · Universal · Autotile Pipeline
**Contexte :** Conversion de tuiles RPG Maker vers Tiled Map Editor (Wangsets).
**Outcome :** Le format Tiled "Edge" (16 tuiles) provoque des artefacts visuels sur les angles internes et externes (les diagonales). La solution correcte est le modèle "Blob" (47 tuiles, `type="mixed"` dans Tiled) qui encode 8 directions (4 cardinales + 4 diagonales).
**Pattern :** Toujours utiliser le pipeline Blob (`rpgmaker_blob_autotile_to_tiled.py`) pour la génération de terrains. Les tuiles statiques RPG Maker doivent être découpées en 4 sous-tuiles par combinaison.

## L-TOOL-003 · 2026-05-31 · Project-Specific · Extraction de constantes
**Contexte :** Amélioration de la base de code du tooling.
**Outcome :** Garder les dimensions de tuiles (ex: `TILE_SIZE`, `SUBTILE_SIZE`) hardcodées dans plusieurs modules mène à des erreurs lors d'un changement de résolution globale ou d'adaptation d'échelle.
**Pattern :** Extraire toutes les valeurs magiques dans un `constants.py` au sein du module d'outil (ex: `tools/asset_creator/core/constants.py`) et l'importer dans l'UI et le core.

## L-TOOL-004 · 2026-06-03 · Universal · macOS Native Dock Icon for Python GUI
**Contexte :** Remplacement de l'icône par défaut (la "fusée" de Python) sur macOS pour l'application `asset_creator` (Dear PyGui).
**Outcome :** Il est possible de surcharger l'icône de l'application native macOS à la volée, sans packager l'application dans un `.app`, via l'API Cocoa.
**Pattern :** Utiliser la librairie `pyobjc-framework-Cocoa` pour injecter l'icône au démarrage avec `AppKit.NSApplication`. Exemple :
```python
import AppKit
app = AppKit.NSApplication.sharedApplication()
icon = AppKit.NSImage.alloc().initWithContentsOfFile_("assets/icon.png")
app.setApplicationIconImage_(icon)
```
