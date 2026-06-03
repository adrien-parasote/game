# Strategic Blueprint — Asset Creator: Organic Terrain Generation (Domain Warping)

> **Date:** 2026-06-03
> **Status:** STRATEGY

---

## 1. What exact problem are you solving?

**Persona:** Solo game developer using the Asset Creator to generate 2D top-down terrains.

**Current pain:** The base texture générée par le bruit OpenSimplex standard produit des formes trop régulières et rectilignes ("grid-like"). L'analyse des assets de référence (Slynyrd) montre que l'œil humain perçoit mieux le terrain procédural s'il contient des "S-curves" et des formes asymétriques organiques. L'outil actuel ne permet pas de générer ces courbes.

**Measurable outcome:** Le générateur de texture intègre une distorsion spatiale (Domain Warping) produisant des formes organiques asymétriques. L'utilisateur peut régler l'intensité de cette distorsion en temps réel via l'interface GUI (paramètres `warp_scale` et `warp_strength`). La génération d'un tileset complet reste suffisamment rapide (< 1s) pour permettre un retour interactif fluide.

---

## 2. What are your success metrics?

| Metric | Target | Timeline |
|--------|--------|----------|
| Visuel (Formes) | Apparition claire de "S-curves" et disparition de l'effet grille rectiligne | Immédiat |
| Performance (Tileset) | Génération d'un tileset complet de 47 tuiles en moins de 1s avec la distorsion activée | Immédiat |
| Intégration GUI | Les paramètres de warp sont exposés et modifiables en direct sans casser l'UI | Immédiat |
| Seamless Tiling | La tuile générée reste parfaitement répétable (seamless) sur ses 4 bords malgré la distorsion | Immédiat |

---

## 3. Why will you win?

**Structural advantage:** Nous n'avons pas besoin de changer le moteur de rendu ou d'ajouter une nouvelle dépendance. Le **Domain Warping** est une technique purement mathématique (échantillonner un bruit pour décaler les coordonnées d'échantillonnage d'un autre bruit). Le système actuel basé sur `OpenSimplex` peut le faire de manière performante. De plus, notre architecture sépare proprement l'état de la GUI (`TextureParams`) du moteur de rendu `core/texture.py`, ce qui rend l'ajout de paramètres triviaux.

---

## 4. What's the core architecture decision?

### ADR-004: Utilisation du Domain Warping pour les formes organiques
**Decision:** Implémenter une passe de déformation (Warp) sur les coordonnées (x,y) avant d'évaluer le bruit multi-octaves.
**Rationale:** C'est la méthode la plus standard et performante en génération procédurale pour obtenir des effets fluides et organiques (type marbre, nuages étirés, ou terrain naturel) sans complexifier l'algorithme de base.

---

## 5. What's the tech stack rationale?

| Choice | Rationale |
|--------|-----------|
| **OpenSimplex** | Déjà intégré au projet. Produit moins d'artefacts directionnels que le Perlin Noise classique, ce qui est parfait pour une distorsion organique. |
| **Math 4D (Torus)** | Actuellement utilisé pour le "seamless tiling". La distorsion devra elle aussi s'opérer dans l'espace projeté ou de manière modulaire pour conserver la répétabilité parfaite. |

---

## 6. What are the features?

Ordered by implementation dependency:

| # | Feature | Dependencies | Priority |
|---|---------|-------------|----------|
| F1 | **Warp Parameters** — Ajout de `warp_scale` et `warp_strength` à `TextureParams` | None | 🔴 Required |
| F2 | **Domain Warping Algorithm** — Modification de `core/texture.py` pour déformer les coordonnées (x,y) avant de calculer la texture, tout en préservant le wrapping toroïdal (seamless). | F1 | 🔴 Required |
| F3 | **GUI Integration** — Ajout des sliders pour le warp dans `gui/app.py` sous le panneau Texture | F1 | 🔴 Required |
| F4 | **Preset Updates** — Mise à jour des YAML (ex: `grass.yaml`) pour inclure des valeurs par défaut pour le warp | F1 | 🔴 Required |

---

## 7. What are you NOT building?

| Excluded | Rationale |
|----------|-----------|
| **Génération de Murs / Falaises (Extrusion)** | Explicitement exclu par l'utilisateur ("roadmap future"). Focus sur la tuile de base. |
| **Placement d'objets (Props / Poisson Disk)** | Explicitement exclu par l'utilisateur ("roadmap future"). |
| **Animation des fluides (Lave/Eau)** | Explicitement exclu par l'utilisateur ("roadmap future"). |

---

## Gap Discovery

| # | Gap | Impact if unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | **Seamless Domain Warping** | Résolu. | User / Agent |
| 2 | **Impact sur les performances (x3 échantillons)** | Le Domain Warping demande de calculer le bruit 2 fois de plus par pixel. | Agent (besoin de benchmarker / optimiser pendant la conception) |
| 3 | **Espace dans la GUI (DPG)** | Nouveaux paramètres ajoutés. Faut-il grouper les paramètres avancés ou ajouter une scrollbar ? | Agent (vérifier layout) |

---

## Resolved Gaps

| # | Gap | Decision |
|---|-----|----------|
| R1 | **Seamless Domain Warping** | **Résolu.** Le site suggéré ([RPG Maker Grass Autotile](https://www.rpgmakerweb.com/blog/making-a-custom-grass-autotile-from-scratch)) explique la technique du *cut, shift and fill* (couper l'image en 2, la décaler de 50%, puis repeindre la jointure). Au lieu d'utiliser un bruit 4D complexe pour la distorsion, nous pouvons mathématiquement appliquer ce wrapping sur les offsets générés (avec un modulo) pour que la distorsion rejoigne parfaitement les bords opposés. |

---

## 🚀 Future Roadmap

Les éléments suivants ont été identifiés durant la phase de recherche mais sont intentionnellement sortis du scope actuel pour être traités dans de prochaines itérations :

1. **Génération de Murs et Falaises (Extrusion) :**
   - Étendre les bordures de la couche de base vers le bas pour créer de la verticalité.
   - Ajouter un bruit directionnel (vertical) pour simuler la texture de la roche.

2. **Placement des Props (Végétation, Rochers) :**
   - Intégrer un algorithme de *Poisson Disk Sampling* pour répartir de manière naturelle des objets sur le terrain.
   - Éviter les superpositions artificielles et le placement en grille stricte.

3. **Passe d'Ombrage (Shadow Pass) :**
   - Générer une ombre portée automatiquement pour les props et les murs afin de les ancrer visuellement au sol (décalage de quelques pixels avec masque sombre).

4. **Animation des Fluides (Eau / Lave) :**
   - Mettre en place la génération de spritesheets à 3 ou 4 frames en modifiant la phase du bruit dans le temps pour un effet de liquide mouvant.
