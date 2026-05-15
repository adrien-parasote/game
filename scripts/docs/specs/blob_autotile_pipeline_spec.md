> Document Type: Implementation

# Spec : Blob Autotile Pipeline (47 tiles)

**Script :** `scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py`
**Remplace :** `scripts/autotiles/rpgmaker_autotile_to_tiled.py` (16 tiles edge-only → coin artefacts)
**Research :** [devium/tiled-autotile](https://github.com/devium/tiled-autotile)

---

## Contexte et décision

Le script 16-tile edge-only génère des artefacts aux **coins diagonaux** car il ne connaît que 4 voisins (T/R/B/L). La solution correcte est le format **47-tile blob** qui encode les 8 voisins (T/R/B/L + 4 diagonales).

**ADR-002 :** Adopt `devium/tiled-autotile` sub-tile assembly logic, adapted pour notre pipeline standalone.

---

## Assumptions

| # | Assumption | Risk |
|---|-----------|------|
| A1 | L'autotile source RPG Maker XP est 96×128 px (statique) ou N×96×128 (animé) | Low |
| A2 | Les 47 combinations devium couvrent tous les cas visuels du blob | Low — validé sur des milliers de jeux RPG |
| A3 | Tiled `type="mixed"` (corner+edge) supporte les 47 tiles blob | Low — confirmé doc Tiled 1.10 |
| A4 | Le wangid blob encodes 8 directions : TL,T,TR,R,BR,B,BL,L | Low — format Tiled TSX |

| Constante | Valeur | Description |
|-----------|--------|-------------|
| SUBTILE | 16 | Demi-tile en px |
| TILE_SIZE | 32 | Tile en px |
| BLOB_COUNT | 47 | Nombre de tiles blob (49 slots, 2 vides) |

---

## Format source RPG Maker XP (96×128)

```
6 colonnes × 8 lignes de sub-tiles 16×16
Col 0-5, Row 0-7

Layout (en tiles 32×32) :
  [A][B][C]    A=isolated, B=inner-corners, C=variant
  [D][E][F]    D=left-edge, E=top-edge, F=right-edge
  [G][H][I]    G=left, H=CENTER (full), I=right
  [J][K][L]    J=bot-left, K=bot-edge, L=bot-right
```
Les inner-corners (`B`) se trouvent aux colonnes 4-5, lignes 0-1, et NON aux colonnes 2-3 (qui sont transparentes dans l'eau).

---

## Les 47 combinations (sub-tiles)

L'implémentation n'utilise pas la liste devium 49 mais reconstruit dynamiquement les 47 bitmasks de terrain (`BLOB_BITMASKS`) via une logique modulaire `_quarter()` qui mappe chaque coin vers son sub-tile 16x16 exact dans la source.

```python
BLOB_BITMASKS = (
    0, 2, 8, 10, 11, 16, 18, 22, 24, 26, 27, 30, 31, 64, 66, 72,
    74, 75, 80, 82, 86, 88, 90, 91, 94, 95, 104, 106, 107, 120,
    122, 123, 126, 127, 208, 210, 214, 216, 218, 219, 222, 223,
    248, 250, 251, 254, 255
)
```

## Bitmask → tile index

Le bitmask 8 bits encode les voisins : `NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128`

**Règle blob :** Si un voisin cardinal (N/E/S/W) est absent, ses diagonales adjacentes sont ignorées dans la construction de la sous-tuile pour éviter le "tearing".
L'index est simplement la position dans `BLOB_BITMASKS`. Il y a exactement 47 slots par frame, sans padding vide.

---

## Données de sortie

### Strip PNG

```
Dimensions : (47 × 32) × 32 = 1504 × 32 px
Tiles 0-46 : positions BLOB_BITMASKS
```

### TSX XML

```xml
<tileset version="1.10" tiledversion="1.10.0"
         name="{stem}" tilewidth="32" tileheight="32"
         tilecount="47" columns="47">
  <image source="{rel_png}" width="1568" height="32"/>

  <!-- Animations (si N > 1) : même logique que le script animé -->
  <tile id="{i}">
    <animation>
      <frame tileid="{i}"       duration="{ms}"/>
      <frame tileid="{49 + i}"  duration="{ms}"/>
      ...
    </animation>
  </tile>

  <wangsets>
    <wangset name="{stem}" type="mixed" tile="-1">
      <wangcolor name="{stem}" color="#4488ff" tile="-1" probability="1"/>
      <!-- 47 wangtiles (slots 41 et 48 ignorés) -->
      <wangtile tileid="{i}" wangid="{_blob_wang_id(bitmask)}"/>
    </wangset>
  </wangsets>
</tileset>
```

### wangid blob (type="mixed")

Format Tiled mixed exact: `Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft`

```python
def _blob_wang_id(bitmask: int) -> str:
    nw = (bitmask >> 0) & 1
    n  = (bitmask >> 1) & 1
    ne = (bitmask >> 2) & 1
    e  = (bitmask >> 4) & 1
    se = (bitmask >> 7) & 1
    s  = (bitmask >> 6) & 1
    sw = (bitmask >> 5) & 1
    w  = (bitmask >> 3) & 1
    # Note : Tiled Wang ID expects exact array order
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
```

---

## Interface CLI

```
python3 scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py <input.png>
        [--tsx PATH] [--png PATH] [--frame-duration MS]
```

Identique au script animé. Si `width == 96` → static (pas d'animation). Si `width > 96` → animé.

---

## Algorithme

```python
def convert(input_path, tsx_path, png_path, frame_duration):
    src = _open_and_validate(input_path)   # OSError → sys.exit
    n_frames = src.width // 96

    strip = _build_blob_strip(src, n_frames)
    strip.save(png_path)

    _generate_tsx(png_path, tsx_path, tsx_path.stem, n_frames, frame_duration)
    _print_success(...)

def _build_blob_strip(src, n_frames):
    # 49 slots par frame
    total = n_frames * 49
    strip = Image.new("RGBA", (32 * total, 32))

    for frame_idx in range(n_frames):
        frame = src.crop((frame_idx*96, 0, (frame_idx+1)*96, 128))
        for slot, combo in enumerate(BLOB_COMBINATIONS):
            if combo:
                tile = _assemble_tile(frame, combo)
            else:
                tile = Image.new("RGBA", (32, 32))  # transparent
            x = (frame_idx * 49 + slot) * 32
            strip.paste(tile, (x, 0))
    return strip

def _assemble_tile(frame, combo):
    # combo = (TL, BR, TR, BL) sub-tile coords
    tile = Image.new("RGBA", (32, 32))
    offsets = [(0,0), (16,16), (16,0), (0,16)]
    for (col, row), (dx, dy) in zip(combo, offsets):
        sub = frame.crop((col*16, row*16, col*16+16, row*16+16))
        tile.paste(sub, (dx, dy))
    return tile
```

---

## Error Handling Matrix

| Error | Response | Message |
|-------|----------|---------|
| Fichier absent | `sys.exit` | `ERROR: File not found: {path}` |
| Image corrompue | `sys.exit` | `ERROR: Cannot open image: {e}` |
| height ≠ 128 | `sys.exit` | `ERROR: Expected height 128px, got {h}px` |
| width % 96 ≠ 0 | `sys.exit` | `ERROR: Width not a multiple of 96px` |
| frame_duration ≤ 0 | `sys.exit` | `ERROR: --frame-duration must be > 0` |
| N == 1 | warning | `WARNING: Single frame — static output` |
| mkdir échoue | `sys.exit` | `ERROR: Could not create output directory: {e}` |
| PNG write échoue | `sys.exit` | `ERROR: Cannot write PNG: {e}` |
| TSX write échoue | `sys.exit` | `ERROR: Cannot write TSX: {e}` |

---

## Anti-patterns

| # | Anti-pattern | Correct |
|---|-------------|---------|
| AP-1 | Réutiliser `_build_tile` (4-bit edge) | Utiliser `_assemble_tile` avec les 49 combinations |
| AP-2 | wangset `type="edge"` | `type="mixed"` pour blob corner+edge |
| AP-3 | 16 wangtiles | 47 wangtiles (slots 41 et 48 omis) |
| AP-4 | wangid format `T,0,R,0,B,0,L,0` | Format mixed `TL,T,TR,R,BR,B,BL,L` |
| AP-5 | tilecount=49 fixe | `tilecount = n_frames * 49` |
| AP-6 | Inclure les slots vides (41,48) dans les wangtiles | Les omettre — tiles transparentes, pas de terrain |
| AP-7 | Ignorer les diagonales dans le bitmask | Appliquer la règle blob : diagonal=0 si cardinal absent |

---

## Test Case Specifications

### UT-001 — _assemble_tile : dimensions correctes
**Input :** frame 96×128 synthétique, combo index 8 (center full)
**Expected :** tile 32×32 RGBA

### UT-002 — _blob_mask : règle diagonal
**Input :** n=True, nw=True, w=False
**Expected :** nw forcé à 0 (w absent)

### UT-003 — _blob_wang_id : bitmask 255 (entouré)
**Input :** bitmask=255
**Expected :** `"1,1,1,1,1,1,1,1"`

### UT-004 — _blob_wang_id : bitmask 0 (isolé)
**Input :** bitmask=0
**Expected :** `"0,0,0,0,0,0,0,0"`

### UT-005 — Strip statique : dimensions
**Input :** Image 96×128
**Expected :** strip size == (1568, 32)

### UT-006 — Slots vides transparents
**Input :** slot 41 et 48
**Expected :** pixels = (0,0,0,0) RGBA

### UT-007 — Validation height
**Input :** Image 96×64
**Expected :** SystemExit, "height"

### UT-008 — Validation width
**Input :** Image 100×128
**Expected :** SystemExit, "multiple"

### IT-001 — Pipeline statique complet
**Input :** grass.png 96×128
**Expected :** PNG 1568×32, TSX tilecount=49, 47 wangtiles, type="mixed"

### IT-002 — Pipeline animé N=4
**Input :** water.png 384×128, frame_duration=200
**Expected :** PNG 7056×32 (4×49×32), 47 `<tile><animation>` de 4 frames

### IT-003 — Bitmask 255 → slot 46 (center)
**Input :** bitmask=255
**Expected :** BITMASK_TO_IDX[255] == 46

### IT-004 — Image relative dans TSX
**Input :** tsx dans `tilesets/`, png dans `images/`
**Expected :** `<image source>` est relatif

---

## Deep Links

- Tiled mixed Wang : https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#wangset
- devium/tiled-autotile : https://github.com/devium/tiled-autotile
- Script Blob : [rpgmaker_blob_autotile_to_tiled.py](../../autotiles/rpgmaker_blob_autotile_to_tiled.py#L1)
