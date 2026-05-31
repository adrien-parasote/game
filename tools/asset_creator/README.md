# Asset Creator Tool

Outil de génération de tilesets blob (47 tuiles) pour [Tiled Map Editor](https://www.mapeditor.org/), avec **GUI interactive** et **CLI**.

Génère des fichiers **PNG** (tileset strip) + **TSX** (Wang set XML) directement utilisables dans Tiled, à partir de palettes de couleurs et de textures procédurales.

## GUI Interactive (V3)

Lancez l'interface graphique Dear PyGui pour créer des tilesets en temps réel :

```bash
python3 -m tools.asset_creator gui
```

### Fonctionnalités

- **Aperçu temps réel** — prévisualisation 4× d'une tuile avec mise à jour instantanée
- **Sliders de paramètres** — texture, détail, bordure, seed
- **Palette couleurs** — 4 pickers (Ombre, Base, Lumière, Accent) avec rampe OKLCh
- **Canvas de peinture** — mode autotile (Wang blob 47 tiles) + mode standalone
- **Historique** — panneau avec undo : cliquer pour restaurer un état précédent
- **Export** — PNG + TSX directement depuis l'interface
- **Thème macOS** — dark mode natif (Apple HIG)

## CLI

```bash
# Lister les terrains disponibles
python3 -m tools.asset_creator list

# Générer un tileset herbe
python3 -m tools.asset_creator generate --terrain grass

# Générer en qualité V2 (rampe OKLCh + dithering + détails)
python3 -m tools.asset_creator generate --terrain grass --quality v2

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
├── cli.py               # Commandes CLI (generate, list, preview, gui)
├── config/
│   ├── palettes/        # 6 palettes YAML (4 couleurs + rôles + rampe V2)
│   └── terrain_presets.yaml  # Définitions des terrains
├── core/
│   ├── color_ramp.py    # Espace couleur OKLCh, rampes avec hue-shift
│   ├── detail_overlay.py  # Détails procéduraux (herbe, terre, pierre, sable)
│   ├── minimap.py       # Calcul bitmask Wang blob (framework-agnostique)
│   ├── palette.py       # Chargement palette YAML → Palette dataclass
│   ├── subtile.py       # 20 sub-tiles 16×16 (4 quadrants × 5 types)
│   ├── terrain.py       # Configuration terrain (TerrainConfig, DetailConfig, EdgeConfig)
│   ├── texture.py       # Génération procédurale (noise toroïdal, patterns, V2 smooth ramp)
│   └── tile_assembler.py  # Assemblage 47 tuiles blob depuis les sub-tiles
├── exporters/
│   ├── png_exporter.py  # Export PNG avec validation
│   └── tsx_exporter.py  # Export TSX (Wang set XML)
├── gui/
│   ├── app.py           # Application Dear PyGui (fenêtre, layout, callbacks)
│   ├── canvas.py        # État du canvas de peinture (CanvasState)
│   ├── pipeline.py      # Pipeline de génération (texture → tiles → export)
│   ├── preview.py       # Conversion PIL → DPG texture (RGBA float32)
│   └── state.py         # AppState (dataclass gelée), chargement presets
└── preview/
    └── pygame_preview.py  # Preview Pygame legacy (strip + mini-map)
```

## Pipeline de génération

### V1 (basique)
```
Palette YAML ─→ Texture procédurale ─→ 20 Sub-tiles ─→ 47 Blob tiles ─→ PNG + TSX
     │                  │                     │                │
  4 couleurs      bruit toroïdal         masques d'edge    bitmask NW/N/NE
  + rôles         (seamless tiling)      + bordures        W/E/SW/S/SE
```

### V2 (qualité améliorée)
```
Palette YAML ─→ Rampe OKLCh ─→ Interpolation smooth ─→ Dithering Bayer
     │              │                   │                     │
  4 couleurs    hue-shift          perceptuellement       matrice ordonnée
  + ramp_config  ombre/lumière    uniforme (Oklab)       (2×2, 4×4, 8×8)
                                                               │
                                                    ─→ Detail overlay ─→ Sub-tiles ─→ ...
                                                         (herbe, terre,
                                                          pierre, sable)
```

1. **Palette** — 4 couleurs (shadow, base, highlight, accent) depuis un fichier YAML
2. **Rampe OKLCh** *(V2)* — génération d'une rampe 7-11 couleurs avec hue-shift (ombres froides, lumières chaudes)
3. **Texture** — bruit Simplex 4D toroïdal pour du tiling parfaitement seamless, ou patterns (solid, dithered, stippled, striped)
4. **Interpolation smooth** *(V2)* — mapping continu dans l'espace OKLCh (pas de banding)
5. **Dithering** *(V2)* — matrice de Bayer ordonnée pour transitions douces
6. **Detail overlay** *(V2)* — stamps procéduraux (brins d'herbe, grains de terre, fissures de pierre, grains de sable)
7. **Sub-tiles** — 20 pièces de 16×16 (fill, edge_v, edge_h, outer_corner, inner_corner) × 4 quadrants
8. **Assemblage** — composition des 47 configurations blob (bitmask 8 voisins) en sélectionnant le bon sub-tile par quadrant
9. **Export** — PNG strip validé (pas de tuile transparente) + TSX avec Wang IDs

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
# Optionnel — rampe V2 avec hue-shift
ramp:
  base_color: "#5a9e3a"
  steps: 9
  shadow_hue_shift: -15
  highlight_hue_shift: 10
  lightness_range: 0.25
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
    detail:
      type: grass_blades  # grass_blades | dirt_specks | stone_cracks | sand_grains | none
      density: 0.12
      max_height: 4
      max_length: 4
```

### 3. Générer

```bash
# Via CLI
python3 -m tools.asset_creator generate --terrain mon_terrain --quality v2 --preview

# Via GUI
python3 -m tools.asset_creator gui
```

## Preview Pygame (legacy)

La preview Pygame affiche :
- **En haut** : le strip complet des 47 tuiles
- **En bas** : une mini-map aléatoire montrant les tuiles en contexte

Contrôles :
- `ESPACE` — régénérer la mini-map
- `ESC` — quitter

## Dépendances

- `Pillow` — manipulation d'images
- `opensimplex` — bruit Simplex pour les textures procédurales
- `numpy` — calculs numériques (rampe OKLCh, dithering)
- `PyYAML` — lecture des fichiers de configuration
- `dearpygui` — GUI interactive (V3)
- `pygame-ce` — preview legacy (optionnel)

## Tests

```bash
# Tous les tests (371 tests)
python3 -m pytest tests/tools/asset_creator/ -v

# Uniquement les tests d'intégration
python3 -m pytest tests/tools/asset_creator/test_integration.py -v

# Tests GUI (état, preview, canvas)
python3 -m pytest tests/tools/asset_creator/test_gui_state.py tests/tools/asset_creator/test_gui_preview.py tests/tools/asset_creator/test_canvas.py -v
```
