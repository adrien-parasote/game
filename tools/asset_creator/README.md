# Asset Creator Tool

Outil CLI de génération de tilesets blob (47 tuiles) pour [Tiled Map Editor](https://www.mapeditor.org/).

Génère des fichiers **PNG** (tileset strip) + **TSX** (Wang set XML) directement utilisables dans Tiled, à partir de palettes de couleurs et de textures procédurales.

## Utilisation rapide

```bash
# Lister les terrains disponibles
python3 -m tools.asset_creator list

# Générer un tileset herbe
python3 -m tools.asset_creator generate --terrain grass

# Générer avec un seed spécifique + preview Pygame
python3 -m tools.asset_creator generate --terrain dirt --seed 42 --preview

# Générer 3 variantes
python3 -m tools.asset_creator generate --terrain water --variants 3

# Nom de fichier personnalisé
python3 -m tools.asset_creator generate --terrain sand --name desert_sand

# Previewer un tileset existant
python3 -m tools.asset_creator preview assets/images/autotiles/grass.png
```

## Terrains disponibles

| Preset | Palette | Texture | Edge |
|--------|---------|---------|------|
| `grass` | forest_grass (verts) | noise | organic |
| `dirt` | dry_dirt (bruns) | noise | organic |
| `paving_stone` | stone_path (gris) | stippled | straight |
| `sand` | sand (jaunes sable) | noise | dithered |
| `snow` | snow (blancs/bleus) | stippled | dithered |
| `water` | water (bleus) | noise | organic |

## Sortie

Par défaut :
- **PNG** → `assets/images/autotiles/<nom>.png` — strip horizontal de 47 tuiles 32×32
- **TSX** → `assets/tiled/autotiles/<nom>.tsx` — Wang set type `mixed` pour autotiling blob

Les fichiers TSX référencent le PNG via un chemin relatif et sont directement importables dans Tiled.

## Architecture

```
tools/asset_creator/
├── __main__.py          # Point d'entrée (python3 -m tools.asset_creator)
├── cli.py               # Commandes CLI (generate, list, preview)
├── config/
│   ├── palettes/        # 6 palettes YAML (4 couleurs + rôles)
│   └── terrain_presets.yaml  # Définitions des terrains
├── core/
│   ├── palette.py       # Chargement palette YAML → Palette dataclass
│   ├── texture.py       # Génération procédurale (noise toroïdal, patterns)
│   ├── subtile.py       # 20 sub-tiles 16×16 (4 quadrants × 5 types)
│   ├── terrain.py       # Configuration terrain (TerrainConfig)
│   └── tile_assembler.py  # Assemblage 47 tuiles blob depuis les sub-tiles
├── exporters/
│   ├── png_exporter.py  # Export PNG avec validation
│   └── tsx_exporter.py  # Export TSX (Wang set XML)
└── preview/
    └── pygame_preview.py  # Preview Pygame (strip + mini-map)
```

## Pipeline de génération

```
Palette YAML ─→ Texture procédurale ─→ 20 Sub-tiles ─→ 47 Blob tiles ─→ PNG + TSX
     │                  │                     │                │
  4 couleurs      bruit toroïdal         masques d'edge    bitmask NW/N/NE
  + rôles         (seamless tiling)      + bordures        W/E/SW/S/SE
```

1. **Palette** — 4 couleurs (shadow, base, highlight, accent) depuis un fichier YAML
2. **Texture** — bruit Simplex 4D toroïdal pour du tiling parfaitement seamless, ou patterns (solid, dithered, stippled, striped)
3. **Sub-tiles** — 20 pièces de 16×16 (fill, edge_v, edge_h, outer_corner, inner_corner) × 4 quadrants, avec masques de distance + bruit pour des bords organiques
4. **Assemblage** — composition des 47 configurations blob (bitmask 8 voisins) en sélectionnant le bon sub-tile par quadrant
5. **Export** — PNG strip validé (pas de tuile transparente) + TSX avec Wang IDs

## Créer un terrain personnalisé

### 1. Créer une palette

```yaml
# config/palettes/ma_palette.yaml
name: ma_palette
colors:
  - "#2d5a1e"   # shadow (le plus sombre)
  - "#3e7c27"   # base
  - "#5a9e3a"   # highlight
  - "#7bc04f"   # accent (le plus clair)
roles:
  shadow: 0
  base: 1
  highlight: 2
  accent: 3
```

### 2. Ajouter le terrain dans `config/terrain_presets.yaml`

```yaml
terrains:
  mon_terrain:
    palette: ma_palette
    texture:
      type: noise        # noise | solid | dithered | stippled | striped
      scale: 0.15         # échelle du bruit (plus petit = plus lisse)
      octaves: 3          # couches de détail
      persistence: 0.5    # atténuation par octave
      thresholds: [-0.2, 0.4, 0.8]  # seuils de mapping couleur
    edge:
      style: organic      # organic | straight | dithered
      width: 3            # largeur de transition en pixels
      noise_scale: 0.3    # amplitude du bruit sur les bords
```

### 3. Générer

```bash
python3 -m tools.asset_creator generate --terrain mon_terrain --preview
```

## Preview Pygame

La preview affiche :
- **En haut** : le strip complet des 47 tuiles
- **En bas** : une mini-map aléatoire montrant les tuiles en contexte

Contrôles :
- `ESPACE` — régénérer la mini-map
- `ESC` — quitter

## Dépendances

- `Pillow` — manipulation d'images
- `opensimplex` — bruit Simplex pour les textures procédurales
- `PyYAML` — lecture des fichiers de configuration
- `pygame-ce` — preview (optionnel, l'export fonctionne sans)

## Tests

```bash
# Tests unitaires + intégration (216 tests)
python3 -m pytest tests/tools/asset_creator/ -v

# Uniquement les tests d'intégration
python3 -m pytest tests/tools/asset_creator/test_integration.py -v
```
