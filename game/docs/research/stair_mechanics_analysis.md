# Analyse : Bug Mécanique des Escaliers (Stairs)

## 1. Origine du problème (Code)
Le problème des sauts brusques ("monte au milieu", "trop haut") vient d'un **bug dans `game/src/map/manager.py`**.
À la ligne 339, la fonction `get_vertical_move_props` contient ceci :
```python
"visual_y_offset": int(props.get("visual_y_offset", 0)),
```
Cette ligne écrase complètement le calcul de fallback de l'offset (qui alterne entre 0 et -16) et force l'offset à 0 pour toutes les tuiles n'ayant pas la propriété explicite dans Tiled.
En conséquence, le personnage ne "glisse" pas vers le haut sur la première moitié de l'escalier, puis subit un saut abrupt de 32 pixels au moment du déplacement diagonal.

## 2. Origine du problème (Tiled)
Le système `_apply_stair_interception` et `VERTICAL_MOVE_MAP` dans `base.py` **exige** que les escaliers soient tracés physiquement en zigzag (marches en diagonale sur la grille Tiled) et non en bloc horizontal.

Quand le joueur avance vers la droite sur un escalier montant vers la droite :
1. Sur une tuile `stair_half = False` : le joueur avance horizontalement `(1, 0)`.
2. Sur une tuile `stair_half = True` : le joueur avance en diagonale `(1, -1)` (il change de ligne `Y` physique dans la map).

Si ton escalier est dessiné comme un bloc droit ou une grande ligne horizontale (`(x,y)`, `(x+1, y)`, `(x+2, y)`), le deuxième mouvement (qui est diagonal `(1, -1)`) va **sortir physiquement** le personnage de la ligne de l'escalier (d'où le "ne suit pas la ligne basse" ou le fait qu'il avance tout droit s'il retombe sur une tuile sans propriété d'escalier).

## 3. Comment fixer le sujet

**Dans le code (`game/src/map/manager.py`) :**
Il faut remplacer la clé du dictionnaire de retour :
```python
# Remplacer (ligne 339) :
"visual_y_offset": int(props.get("visual_y_offset", 0)),
# Par :
"visual_y_offset": visual_y_offset,
```

**Dans Tiled :**
Pour qu'un escalier droit fonctionne de manière fluide, ses tuiles doivent être posées sur la map avec un motif en zigzag :
* Position `(x, y)` : Tuile de début de marche (offset `0`, `stair_half = False`). Mouvement résultant : `(1, 0)`.
* Position `(x+1, y)` : Tuile de fin de marche (offset `-16`, `stair_half = True`). Mouvement résultant : `(1, -1)`.
* Position `(x+2, y-1)` : Tuile de début de la marche suivante (offset `0`, `stair_half = False`). Mouvement résultant : `(1, 0)`.
* Position `(x+3, y-1)` : Tuile de fin de la marche suivante (offset `-16`, `stair_half = True`). Mouvement résultant : `(1, -1)`.

*Note : Ces propriétés ont été appliquées dans `01-stairs.tsx` pour chaque bloc 2x3 et simple.*

## 4. Asymétrie Montée/Descente (Corrigée)

Un second bug majeur touchait le sens de déplacement (descente). La logique dictant si le joueur devait bouger en diagonale était strictement fixée à `should_move_diagonally = stair_half`.

* À la **montée**, cela fonctionne (la seconde moitié de la marche = diagonale).
* À la **descente**, cela provoquait un zigzag incorrect, car la marche doit se descendre sur sa **première** moitié (qui correspond physiquement à la même tuile `stair_half=False`).

**Correction appliquée dans `base.py` :**
L'algorithme vérifie maintenant la direction :
- **En montée :** `should_move_diagonally = stair_half`
- **En descente :** `should_move_diagonally = not stair_half`

*(Les tests unitaires dans `test_stair_movement.py` ont également été corrigés pour refléter cette symétrie physique).*
