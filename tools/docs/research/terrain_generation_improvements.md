# Research Results: Terrain Generation Improvements

### Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | **Tuile de base & Formes organiques** | L'analyse mentionne l'importance des "S-curves" et formes organiques pour éviter l'effet grille. | `extract/terrain_analysis.md`, `core/texture.py` |
| 2 | **Élévation et Murs (Verticalité)** | Le générateur actuel est 100% plat (top-down simple). L'analyse demande une extrusion vers le bas pour simuler la roche/les falaises. | `extract/terrain_analysis.md`, existant |
| 3 | **Placement des Props (Poisson Disk)** | Actuellement `asset_creator` ne place pas d'objets (arbres, rochers). L'analyse préconise le Poisson Disk Sampling. | `extract/terrain_analysis.md`, algorithmes de clustering |
| 4 | **Ombrage (Shadow Pass)** | Indispensable pour ancrer les objets et murs au sol. | `extract/terrain_analysis.md` |
| 5 | **Animation des Fluides** | L'eau et la lave nécessitent 2 à 3 frames d'animation. Le système actuel ne génère qu'une image statique par tuile. | `extract/terrain_analysis.md`, spritesheets |

### Source Evaluation & Gap Analysis

| Source | Key Findings | Gaps in Current `asset_creator` |
|--------|-------------|---------------------------------|
| `terrain_analysis.md` (Étape 1) | Bruit Perlin basse rés, formes organiques asymétriques. | On utilise `OpenSimplex`, mais on manque de "Domain Warping" (distorsion de domaine) pour créer des S-curves. |
| `terrain_analysis.md` (Étape 2) | Autotiling (47 variations), bords rasés. | L'autotiling 47 tuiles est déjà implémenté (`minimap.py`). Il manque la gestion des "bords rasés" pour la transition entre couches. |
| `terrain_analysis.md` (Étape 3) | Extrusion des bords pour faire des murs striés. | **Totalement absent.** |
| `terrain_analysis.md` (Étape 4) | Poisson Disk Sampling pour les props (arbres, etc). | **Totalement absent.** `asset_creator` ne gère que les textures de sol, pas les objets superposés (props). |
| `terrain_analysis.md` (Étape 5) | Ombre portée avec décalage X/Y. | **Totalement absent.** |
| `terrain_analysis.md` (Étape 6) | Animation 3-4 frames (fluides). | **Totalement absent.** Le pipeline actuel est purement statique. |

### Discovered Patterns & Recommendations

1. **Amélioration du Sol (Domain Warping)**
   - **Pattern :** Appliquer une déformation (Domain Warping) au bruit OpenSimplex actuel en utilisant un second bruit pour décaler les coordonnées X et Y avant l'échantillonnage. Cela cassera l'effet "grille" et créera les "S-curves" organiques demandées.

2. **Génération de Murs (Extrusion)**
   - **Pattern :** Ajouter un module `core/elevation.py`. Pour chaque bordure basse d'une couche, extruder les pixels vers le bas sur H pixels, en appliquant un bruit directionnel (vertical) pour simuler des stries de roche.

3. **Génération d'Objets & Ombres (Props Layer)**
   - **Pattern :** Ajouter un module `core/props.py`. Utiliser l'algorithme "Fast Poisson Disk Sampling" pour générer des points. À chaque point, dessiner un sprite basique (arbre/rocher) et générer une sous-couche d'ombre (pixels noirs avec opacité) décalée de quelques pixels (ex: +2X, +2Y).

4. **Spritesheets Animés**
   - **Pattern :** Modifier le pipeline d'export. Pour les presets "fluides" (eau, lave), générer N variations de la texture de base (en décalant la phase du bruit ou le seuil) et exporter chaque frame séquentiellement dans la spritesheet ou générer un TSX avec des tags d'animation.

### Recommendation
- **Chosen approach:** **Adapt & Build**
- **Justification:** Le moteur de base (gestion GUI, autotile Wang blob 47, palette) est déjà très robuste. Il faut l'étendre avec de nouvelles passes de génération : distorsion de bruit (warp), extrusion (murs), et clustering (props).
- **Impact on spec:** Le pipeline devra passer d'un simple `Texture -> Autotile` à `Base Texture (Warped) -> Autotile -> Murs -> Props (Poisson) -> Animation (Optionnel)`. La GUI devra intégrer de nouveaux sliders (ex: "Hauteur des falaises", "Densité des arbres", "Warp strength").

---
