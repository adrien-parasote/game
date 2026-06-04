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

## A-TOOL-002 · 2026-06-04 · Universal · Confusion "absence de surface" vs "virages internes" dans le template XP

**Contexte :** Correction de coordonnées B-tiles dans `converter_xp.py` (session 2026-06-04).
**Evidence :** Un fix précédent avait changé les inner corners de (4,0)-(5,1) vers (2,0)-(3,1). Résultat : carrés jaunes/beiges sur la map à chaque virage concave. 1206 tests passaient quand même (cf. A-TOOL-003). L'utilisateur a dû fournir 2 screenshots + le tutoriel local pour identifier la régression.
**Anti-pattern :** Dans le template XP 96x128, les zones col 2-3 (rows 0-1) et col 4-5 (rows 0-1) sont adjacentes et visuellement similaires sur une texture uniforme. La zone col 2-3 est l'"absence de surface" (fond visible quand aucun autotile n'est placé). Utiliser cette zone comme source des virages internes injecte la couleur du fond (souvent beige/sable) dans les quadrants concaves.
**Fix :** Les virages internes (B-tiles) sont TOUJOURS en col 4-5, rows 0-1 du template XP 96x128 :
  - B-TL = (4,0) — virage NW (N+W présents, NW absent)
  - B-TR = (5,0) — virage NE
  - B-BL = (4,1) — virage SW
  - B-BR = (5,1) — virage SE
Référence : tutoriel RPG Maker FR "Réaliser un autotile" (Oniromancie). Vérification : cf. L-TOOL-009.

## L-TOOL-009 · 2026-06-04 · Universal · Autotile coloré synthétique pour vérification des coordonnées

**Contexte :** Validation des coordonnées B-tiles après détection de régression dans `converter_xp.py`.
**Evidence :** Test de ~30 lignes créant un autotile synthétique avec 4 couleurs distinctes aux positions B-tile, converti en 47 tiles, validé par échantillonnage du pixel central de chaque quadrant sur les bitmasks 254/251/223/127. Résultat en <1s avec preuve irréfutable : TL=JAUNE ✓, TR=CYAN ✓, BL=VIOLET ✓, BR=ROUGE ✓.
**Pattern :** Pour vérifier que les inner corners lisent bien la bonne zone source :
```python
# 1. Créer autotile synthétique avec 4 couleurs distinctes aux B-tiles
test = Image.new('RGBA', (96, 128), fond_color)
colors = {(4,0): YELLOW, (5,0): CYAN, (4,1): VIOLET, (5,1): RED}
for (col, row), color in colors.items():
    test.paste(Image.new('RGBA',(16,16),color), (col*16, row*16))
# 2. Convertir + sampler le pixel central de chaque quadrant
tiles = convert_xp(test)
arr = np.array(tiles[BLOB_BITMASKS.index(254)])  # NW missing
assert arr[8, 8, :3].tolist() == list(YELLOW[:3])   # TL = JAUNE
# Répéter pour bitmasks 251 (TR=CYAN), 223 (BL=VIOLET), 127 (BR=ROUGE)
```
Ce test doit figurer dans `test_converter_xp.py` comme TC-B01 à TC-B04. À lancer dès qu'une coordonnée B-tile est modifiée.

## A-TOOL-003 · 2026-06-04 · Universal · Sample uniforme masquant des coordonnées incorrectes

**Contexte :** `sample_xp.png` est quasi-uniforme (vert homogène) — la suite de 1206 tests passait même avec des coordonnées B-tiles incorrectes pointant vers la zone "absence de surface".
**Evidence :** Avec B-tiles à (2,0)-(3,1) au lieu de (4,0)-(5,1) : 1206/1206 tests PASS (dont `test_converter_xp.py`). La régression n'était visible qu'en runtime avec un vrai autotile multi-zone (herbe/sable).
**Anti-pattern :** Utiliser un sample de texture uniforme comme seule fixture pour les tests de coordonnées de conversion. Un sample uniforme rend tous les quadrants identiques : `assert result[i].size == (32,32)` passe toujours, `assert result[0] != result[46]` échoue silencieusement.
**Fix :** Toute suite de tests pour un convertisseur d'autotile DOIT inclure :
1. Un test avec sample uniforme (valide les propriétés de structure : taille, mode, count)
2. Un test avec autotile synthétique multi-zone (valide les coordonnées de lecture)
Cf. L-TOOL-009 pour le pattern d'autotile synthétique.

## L-TOOL-008 · 2026-06-04 · Universal · Caractères ambigus Unicode dans les docstrings Python
**Contexte :** Docstrings des convertisseurs utilisaient `×` (U+00D7, multiplication sign) pour décrire des dimensions (ex: "96×128 px").
**Evidence :** `ruff check --select RUF002,RUF003` a bloqué sur plusieurs fichiers nécessitant de remplacer `×` par `x` ASCII. Corrigé en plusieurs itérations sur `converter_xp.py`, `converter_mv.py`, `tsx_generator.py`.
**Pattern :** Dans les docstrings Python, utiliser exclusivement des caractères ASCII pour les dimensions et unités : `96x128 px` (pas `96×128 px`), `2x3 grid` (pas `2×3 grid`). Ruff règles RUF002 (docstring) et RUF003 (commentaire) rejettent tout caractère Unicode "ambigus" (qui ressemble à un ASCII mais en est différent). Appliquer cette règle dès l'écriture de spec — les exemples dans la spec deviennent du code copiable.

## L-TOOL-010 · 2026-06-04 · Universal · Cyclomatic Complexity Reduction via Bitmask Dispatch Table
**Contexte :** `converter_mv._bitmask_to_shape` had multiple conditional `if`/`elif` branches to map cardinal and diagonal flags to shape indices, raising cyclomatic complexity to 16.
**Evidence :** Replacing branch logic with `ck = int(n) | (int(s) << 1) | (int(w) << 2) | (int(e) << 3)` and indexing into a list of lambdas (`_SHAPE_RESOLVERS`) reduced cyclomatic complexity of `_bitmask_to_shape` to 1, passing Ruff check C901 and Sentrux P7 Architecture quality gate.
**Pattern :** When mapping complex combinations of boolean flags (e.g. 4 directions + diagonals) to discrete target indices, pack the boolean flags into a bitmask integer `ck` and use a lookup table (list of lambda functions or values) indexed by `ck` to dispatch the resolved index. This replaces branching with $O(1)$ lookup math, keeping cyclomatic complexity at 1.
