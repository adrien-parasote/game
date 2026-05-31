# 🎯 Blueprint — Asset Creator Tool

## 1. What exact problem are you solving?

**Persona:** Adrien, développeur solo + AI assistant, créant un RPG 2D pixel art ("L'Éveil de l'Héritier").

**Problème actuel:**
- Les autotiles sont au format RPG Maker XP (96×128) — un format intermédiaire obsolète
- Créer un nouveau terrain demande : dessiner en format RPG Maker → exécuter un script de conversion → importer dans Tiled
- Aucun outil ne permet de générer directement des tilesets Tiled-natifs depuis une description de terrain
- La création d'assets pixel art est manuelle et chronophage

**Outcome mesurable:**
- Générer un tileset complet (47 tuiles blob + TSX Wang) pour un nouveau terrain en < 5 minutes
- Zéro étape de conversion — output directement compatible Tiled
- Qualité pixel art cohérente entre tous les terrains (palette partagée)

## 2. What are your success metrics?

| Métrique | Cible | Mesure |
|----------|-------|--------|
| Temps de génération d'un terrain complet | < 5 min (vs ~30 min actuellement) | Chrono CLI |
| Qualité visuelle | Seamless tiling, pas de jointures visibles | Test dans Tiled |
| Couverture terrains | 6 types (herbe, terre, eau, pavés, sable, neige) | Nombre de presets |
| Tests unitaires | ≥ 80% couverture | pytest --cov |
| Format natif Tiled | 100% compatible — import direct sans conversion | Test Tiled |

## 3. Why will you win?

**Avantage structurel:** L'algorithme blob 47-tuiles existe déjà dans le projet (prouvé, testé). On réutilise la logique d'assemblage de sub-tiles et de génération TSX Wang. Ce qu'on ajoute : un **pipeline de génération** en amont au lieu d'un extracteur de format RPG Maker.

**Avantage données:** Le projet a des learnings validés sur le format Tiled exact (L-MAP-002 : wangid order), les pièges de debugging (L-MAP-003 : transparent tiles), et les conventions d'assets (naming `NN-category[-variant].png`).

## 4. What's the core architecture decision?

**Architecture : CLI modulaire avec preview Pygame**

```
tools/asset_creator/
├── __init__.py
├── __main__.py              ← CLI entry point
├── cli.py                   ← argparse interface
├── config/
│   ├── terrain_presets.yaml  ← presets (grass, dirt, water...)
│   └── palettes/             ← palette files (hex, Lospec cache)
├── core/
│   ├── palette.py            ← palette loading/management
│   ├── terrain.py            ← terrain definition (dataclass)
│   ├── subtile.py            ← 16×16 sub-tile generation
│   ├── tile_assembler.py     ← 47-tile blob assembly from sub-tiles
│   └── texture.py            ← procedural texture generation (noise, patterns)
├── exporters/
│   ├── png_exporter.py       ← PNG strip output
│   └── tsx_exporter.py       ← TSX Wang set XML output
├── preview/
│   └── pygame_preview.py     ← visual preview window
└── generators/
    ├── base.py               ← abstract generator
    ├── noise_generator.py    ← opensimplex-based
    ├── pattern_generator.py  ← rule-based patterns
    └── ai_generator.py       ← AI-assisted generation (future)
```

**Décisions clés:**
- **Outil indépendant** dans `tools/` — pas de dépendance vers `src/`
- **Sub-tile first** : tout terrain = 13 sub-tiles (16×16) → assemblées en 47 tuiles (32×32)
- **Config-driven** : chaque terrain décrit en YAML (palette, type de texture, paramètres)
- **Exporteurs séparés** : PNG et TSX découplés pour tester indépendamment

## 5. What's the tech stack rationale?

| Choix | Justification |
|-------|---------------|
| **Python 3.12+** | Même version que le projet, pas de friction |
| **Pillow** | Déjà utilisé dans les scripts existants, référence pixel art |
| **NumPy** | Performance pour manipulation de pixels en masse |
| **opensimplex** | Noise procédural sans brevets, pur Python, tileable |
| **Pygame** (preview) | Déjà dépendance du projet, léger pour une fenêtre de preview |
| **PyYAML** | Config lisible, standard |
| **xml.etree** (stdlib) | TSX output, déjà utilisé dans les scripts existants |
| **pytest** | Framework de test du projet |

## 6. What are the features?

Ordonnées par dépendance d'implémentation :

| # | Feature | Description | Dépend de |
|---|---------|-------------|-----------|
| F1 | **Palette system** | Charger/définir des palettes (custom YAML + Lospec) | — |
| F2 | **Sub-tile generator** | Générer les 13 sub-tiles (16×16) pour un terrain via noise/patterns | F1 |
| F3 | **Tile assembler** | Assembler 47 tuiles blob (32×32) depuis les 13 sub-tiles | F2 |
| F4 | **PNG exporter** | Exporter le strip PNG (47×32 px × 32 px) | F3 |
| F5 | **TSX exporter** | Générer le .tsx Wang set XML natif Tiled | F3 |
| F6 | **Terrain presets** | Presets YAML pour herbe, terre, eau, pavés, sable, neige | F1, F2 |
| F7 | **CLI interface** | `python -m tools.asset_creator generate --terrain grass` | F4, F5, F6 |
| F8 | **Pygame preview** | Fenêtre de preview pour visualiser les tuiles avant export | F3 |
| F9 | **Variantes** | Générer N variantes d'un même terrain (seed différente) | F2 |
| F10 | **AI generation** | Génération avancée via descriptions textuelles | F2 |

## 7. What are you NOT building?

| Exclusion | Raison |
|-----------|--------|
| **Éditeur pixel art** | Aseprite/LibreSprite existent, on génère pas on dessine pas |
| **Map editor** | Tiled existe et est utilisé, on ne le remplace pas |
| **Remplacement du game engine** | Aucune dépendance vers `src/`, outil 100% standalone |
| **Import RPG Maker** | On élimine ce format, les scripts existants restent pour la rétrocompat |
| **Éditeur de map dans Pygame** | La preview montre les tuiles, pas un éditeur de carte |
| **Animation de tuiles** | Hors scope V1 — les autotiles animés (eau) viendront plus tard |
| **Transitions multi-terrain** | V1 = 1 terrain vs vide (couleur 0). Multi-terrain = V2 |

---

## Gap Discovery

| # | Gap | Impact si non résolu | Owner |
|---|-----|---------------------|-------|
| 1 | **Format exact des sub-tiles** : les 13 sub-tiles sont-elles exactement les mêmes que celles extraites du format RPG Maker, ou doit-on les redéfinir pour le format natif Tiled ? | Mauvais assemblage → tuiles cassées dans Tiled | Research (vérifier avec l'algo blob existant) |
| 2 | **Qualité "IA/algorithmes avancés"** : qu'est-ce que "génération avancée" signifie concrètement ? Stable Diffusion local ? API externe ? Algorithmes procéduraux sophistiqués ? | Sur-engineering ou sous-livraison | User (clarifier les attentes) |
| 3 | **Preview Pygame** : doit-elle simuler l'auto-tiling (placer les 47 tuiles sur une mini-map de test) ou juste afficher le strip ? | Complexité de la preview (simple grid vs map simulée) | User |
| 4 | **Eau animée** : exclue de V1, mais est-ce un bloquant pour les maps actuelles ? | L'eau reste au format RPG Maker converti si non traité | User |
| 5 | **Cohérence palette inter-terrains** : comment s'assurer que herbe + terre + eau utilisent des couleurs cohérentes ensemble ? | Terrains visuellement incohérents quand mélangés sur une map | Design (palette globale vs par-terrain) |

---

## Relevant Learnings

| ID | Pattern | Impact sur ce projet |
|----|---------|---------------------|
| L-MAP-002 | wangid exact order: `N,NE,E,SE,S,SW,W,NW` | Le TSX exporter DOIT utiliser cet ordre exact |
| L-MAP-003 | Transparent tiles vs missing IDs | Le PNG exporter doit vérifier qu'aucune tuile n'est 100% transparente |
| A-MAP-004 | "topmost ≠ underfoot" depth semantics | Les tuiles générées doivent avoir les bonnes custom properties (depth, walkable) |
