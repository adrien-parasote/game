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
**Pattern :** Toujours utiliser le pipeline Blob pour la génération de terrains. L'implémentation de référence est `tools/src/asset_creator/core/converter_xp.py` + `converter_mv.py` + `tsx_generator.py` (l'ancien `scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py` a été supprimé le 2026-06-04 et remplacé par ce pipeline).

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

## L-TOOL-005 · 2026-06-03 · Universal · Procedural Generation Seamlessness
**Contexte :** Génération procédurale de textures de sol (pixel art) nécessitant une répétition parfaite aux bords (seamless/tileable).
**Outcome :** Le bruit de Perlin 2D standard génère des coutures (seams) visibles aux bords. La projection de l'espace 2D en coordonnées 4D `(cos(x)*r, sin(x)*r, cos(y)*r, sin(y)*r)` sur un tore garantit mathématiquement une continuité parfaite sans logique complexe de blending aux bords.
**Pattern :** Pour toute texture procédurale devant boucler (seamless), utiliser la projection toroïdale 4D plutôt qu'un Perlin 2D classique.

## L-TOOL-006 · 2026-06-04 · Project-Specific · Seamless Isometric Procedural Scatter
**Contexte :** Génération de tuiles (herbes, rochers) nécessitant un bouclage parfait et un tri par profondeur (Z-Order) en vue top-down/isométrique.
**Outcome :** Un placement aléatoire avec un simple modulo pour boucler les bords détruit le Z-order (les éléments du bas écrasent les éléments du haut s'ils bouclent). De plus, l'aléatoire pur crée des amas disgracieux (clumping).
**Pattern :**
1. Placer les éléments sur une grille régulière avec un décalage aléatoire ("Jittered Grid") pour une densité organique mais homogène.
2. Générer virtuellement les éléments non seulement sur la tuile courante, mais aussi sur les 8 tuiles voisines (grille 3x3 : `[-W, 0, W]`).
3. Trier **tous** les éléments de cette grille 3x3 globalement selon l'axe Y (Z-Order).
4. Dessiner les éléments, le centre sera ainsi mathématiquement parfait avec ses voisins sans coupure visuelle de profondeur.

## L-TOOL-007 · 2026-06-04 · Universal · Complexity Refactoring via Pure Helpers
**Contexte :** `converter_mv._build_mv_tile` dépassait les seuils C901 et PLR0915 (complexité cyclomatique + trop de statements).
**Evidence :** Refactoring `_build_mv_tile` → 4 fonctions `_pick_tl/tr/bl/br(n,s,e,w,diag) -> tuple[int,int]` a passé les gates sans réécrire la logique métier. Résultat : 77/77 tests PASS, lint clean.
**Pattern :** Quand une fonction atteint C901/PLR0915, extraire les branches de sélection (qui renvoient uniquement une valeur scalaire ou un tuple de coordonnées) en fonctions `_pick_*` pures. Chaque helper doit : (1) prendre les booléens directionnels (N/S/E/W/diag) comme arguments, (2) renvoyer uniquement des coordonnées ou un indice, (3) avoir aucun side-effect. La fonction parente appelle `_pick_*` pour les coordonnées, puis fait le `crop/paste`. Cette décomposition laisse la logique de dispatch visible dans la fonction parente tout en réduisant la complexité mesurée.

## A-TOOL-001 · 2026-06-04 · Universal · Déclaration prématurée de constantes non utilisées
**Contexte :** `converter_mv.py` déclarait `SUBTILE = 16` en tête de module. La logique utilisait `tile_size // 2` calculé dynamiquement.
**Evidence :** `git diff` révèle `SUBTILE = 16` supprimé en HARDEN sans impact sur 77 tests. Identifié par `ruff check --select F401` + revue manuelle.
**Anti-pattern :** Déclarer une constante module-level "par précaution" avant de valider qu'elle est réellement référencée dans le code du même module. AI-gen anti-pattern #1 (single-use helper jamais utilisé).
**Fix :** Avant de déclarer une constante, vérifier qu'elle est référencée au moins une fois dans le même fichier (`grep -c "SUBTILE" converter_mv.py`). Si 0 ou 1 (la déclaration elle-même) → ne pas déclarer, utiliser l'expression directement.

## L-TOOL-008 · 2026-06-04 · Universal · Caractères ambigus Unicode dans les docstrings Python
**Contexte :** Docstrings des convertisseurs utilisaient `×` (U+00D7, multiplication sign) pour décrire des dimensions (ex: "96×128 px").
**Evidence :** `ruff check --select RUF002,RUF003` a bloqué sur plusieurs fichiers nécessitant de remplacer `×` par `x` ASCII. Corrigé en plusieurs itérations sur `converter_xp.py`, `converter_mv.py`, `tsx_generator.py`.
**Pattern :** Dans les docstrings Python, utiliser exclusivement des caractères ASCII pour les dimensions et unités : `96x128 px` (pas `96×128 px`), `2x3 grid` (pas `2×3 grid`). Ruff règles RUF002 (docstring) et RUF003 (commentaire) rejettent tout caractère Unicode "ambigus" (qui ressemble à un ASCII mais en est différent). Appliquer cette règle dès l'écriture de spec — les exemples dans la spec deviennent du code copiable.
