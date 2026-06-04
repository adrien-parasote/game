# Live Preview Architecture 

Le but de cette mise à jour est de séparer la génération visuelle (Live Preview) de l'exportation des fichiers, offrant une expérience beaucoup plus interactive et réactive.

## Proposed Changes

La logique actuelle (`on_generate`) mélange la génération de l'image en RAM et l'exportation sur le disque. Nous allons séparer ces deux responsabilités.

### `tools/src/asset_creator/gui/app.py`

- **[MODIFY]** `app.py`
  - Renommer le bouton "Generate" en **"Export to Tiled"**.
  - Ajouter des écouteurs d'événements (`command` ou `trace`) sur tous les inputs (Texture Type, Palette, Seed Slider, Scale Slider).
  - Implémenter un mécanisme de **Debouncing (anti-rebond)** : Lorsqu'un slider est déplacé rapidement, on ne génère pas 60 images par seconde. On attend que l'utilisateur s'arrête pendant ~150-200ms avant de lancer le thread de génération. `root.after` est parfait pour gérer ce délai.
  - La méthode `generate_thread` ne doit **plus exporter** les fichiers `.png` et `.tsx`. Elle doit uniquement stocker la dernière `img_32` générée dans l'état de la classe (ex: `self.current_img_32`) et mettre à jour les aperçus (gros plan et grille 3x3).
  - Créer une nouvelle méthode `on_export()` appelée par le bouton "Export to Tiled". Cette méthode utilisera `self.current_img_32` pour appeler la couche d'export (`exporter.py`).
  - Lancer une génération initiale automatique au démarrage de l'application pour que l'aperçu ne soit pas vide.

### `tools/docs/specs/phase-1-simple-tiles.md`

- **[MODIFY]** `phase-1-simple-tiles.md`
  - Mettre à jour la section architecture pour refléter la séparation entre Live Preview et Export.
  - Mettre à jour les tests d'intégration (`IT-001` et `IT-002`) pour refléter les deux étapes (mise à jour UI vs clic sur export).

## Open Questions

> [!IMPORTANT]
> **Performance du Live Preview** : La génération procédurale en Python prend quelques dizaines de millisecondes (jusqu'à ~100ms). Un délai de *debounce* de 200ms sur les sliders te semble-t-il confortable, ou préfères-tu essayer de générer *à chaque frame* (risque de ralentissement si le slider est glissé très vite) ? 

## Verification Plan

### Automated Tests
- Mettre à jour `test_app.py` pour valider que la génération se lance sans exportation.
- Tester que le bouton Export appelle bien la fonction d'export en s'assurant que le bouton n'est actif que si une preview a été générée.

### Manual Verification
- Jouer avec les sliders (Scale, Seed) pour s'assurer que la preview se met à jour fluidement et que le système ne plante pas si l'utilisateur bouge très vite la souris.
- Cliquer sur "Export to Tiled" et vérifier que le fichier est correctement créé dans le dossier `output/`.
