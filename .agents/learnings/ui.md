## 🖥️ UI

### L-UI-001 · 2026-04-28 · U · Perfect
**Pre-paginate dialogue at `start_dialogue()` time**

Pre-wrap and group lines into fixed-size pages at dialogue start, not on-the-fly during typewriter animation. Ensures stable page breaks and simplifies skip→next→close progression.

---

### L-UI-002 · 2026-04-29 · P · Minor Rework
**Font sizing in large reading zones**

`Settings.FONT_SIZE_NARRATIVE` (14pt) is too small in full-height dialogue boxes. Use `int(size * 1.5)` for dedicated reading areas. For inventory descriptions, anchor at `stats_y + 5*s` (not `+30*s`) to avoid overflowing the parchment background.

---

### L-UI-003 · 2026-04-30 · U · Minor Rework
**Named offset constants as UI escape hatches**

Zone fractions (`_TITLE_ZONE_REL`, `_CONTENT_ZONE_REL`) derived from visual estimates cause iterative trial-and-error.

✅ **Measure zones before writing the spec** (image editor or PIL). Add named offset constants (`_TITLE_OFFSET_X`, `_TITLE_OFFSET_Y`, `_GRID_OFFSET_Y`) — default to zero, adjust once. Eliminates all subsequent launches.

**Evidence:** 8 game launches → `_TITLE_OFFSET_X=10, _TITLE_OFFSET_Y=15, _GRID_OFFSET_Y=-4`.

---

### L-UI-004 · 2026-04-30 · U · Perfect
**Pygame headless surface testing**

```python
# Setup in conftest.py
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# In tests — replace asset surfaces with dummy ones
monkeypatch.setattr(ui, "_bg", pygame.Surface((w, h)))
dummy.fill((255, 0, 0))

# Verify pixels (use tobytes, not deprecated tostring)
pixel = pygame.image.tobytes(screen, "RGB")
assert screen.get_at((x, y)) == (r, g, b, 255)
```

### L-UI-005 · 2026-04-30 · U · Perfect
**Pillow-driven layout analysis for background assets**

Measuring relative zones (fractions) for UI elements by eye is slow and error-prone. 

✅ **Use Pillow for automated zone detection.** Draw high-contrast marker pixels (e.g., Pure Red, Pure Blue) on the background asset. Run a script to extract the bounding box of these colors. Convert to relative fractions (`x/width`) to ensure scaling stability across resolutions.

**Evidence:** `07-chest.png` red/blue zones scanned via PIL. commit `a960147`.
ABSORB (2026-05-03): Colour sampling also used to derive text colours for panel overlays. `img.getpixel()` scan loop (no numpy) determines exact background luminance → chooses idle/hover text palette automatically. Evidence: Pillow analysis of `01-menu_background.png`, fond RGB(37,54,58), lum=50.7 → golden text. commit `0e2e271`.

---

### A-UI-001 · 2026-04-30 · U · Minor Rework
**Stretching small UI icons to fill interactive zones**

Scaling small assets (e.g., 26x26 icons) to fill larger interactive button zones causes visual distortion and "pixel bloat."

✅ **Scale by global factor and center.** Scale icons by the same global factor as the background (preserving native proportions), then blit them centered within the interactive zone rect instead of stretching to fill it. 

**Evidence:** Chest UI arrow hover distortion fixed by centering. commit `a4c98cb`.

---

### L-UI-006 · 2026-05-03 · U · Perfect
**3-pass engraved text effect for dark stone backgrounds**

Dark backgrounds (e.g., stone panel RGB(37,54,58)) require text that looks carved rather than drawn. A 3-blit stack achieves this with zero external assets:

```python
# Pass 1 — shadow (bottom-right +1,+2) : fond sombre de la gravure
shadow = font.render(label, True, (12, 20, 23))
# Pass 2 — reflet (top-left -1,-1) : bord supérieur éclairé
light  = font.render(label, True, (75, 105, 112))
# Pass 3 — texte principal : légèrement plus clair que la pierre
text   = font.render(label, True, (58, 85, 92))
r = text.get_rect(center=(cx, cy))
screen.blit(shadow, r.move(1, 2))
screen.blit(light,  r.move(-1, -1))
screen.blit(text,   r)
```

Colour derivation rule: `SHADOW ≈ stone ∗ 0.35`, `LIGHT ≈ stone ∗ 2.0`, `TEXT ≈ stone ∗ 1.6`. Hover switches to a single golden blit (no engraving) for strong contrast pop.

**Evidence:** `TitleScreen._blit_engraved()`. commit `81530d2`.

---

### A-UI-002 · 2026-05-03 · P · Minor Rework
**Asset renommage sans grep cross-fichiers**

Renommer ou supprimer un asset (`03-panel_background.png`) dans un fichier sans grep’per l’ensemble du codebase provoque un crash au premier lancement dans un second consommateur (`pause_screen.py`).

```bash
# ❌ Renommer sans vérifier
git mv 03-panel.png 02-panel.png

# ✅ Toujours grep avant de supprimer
grep -r '03-panel_background' src/ tests/
# puis traiter chaque hit avant de committer
```

**Règle :** Avant tout `git mv` ou `rm` d'asset, lancer `grep -r 'filename' src/ tests/` et résoudre tous les hits dans le même commit.

**Evidence:** `03-panel_background.png` supprimé dans `title_screen.py`, crash dans `pause_screen.py` découvert au lancement suivant. commit `974e3c8`.

---


### L-UI-007 · 2026-05-04 · U · Major Rework
**Coordonnées UI en espace logique fixe, pas `screen.get_size()`**

En fullscreen natif sur macOS, `pygame.display.set_mode((1280,720), FULLSCREEN).get_size()` peut retourner la résolution physique (ex: 2560×1600) au lieu de 1280×720. Utiliser `screen.get_size()` pour scaler le background ET placer des halos en coordonnées logiques 1280×720 produit un décalage systématique.

✅ **Calculer des facteurs de scale à l'init et les appliquer au rendu :**
```python
self._scale_x = screen.get_size()[0] / LOGICAL_W
self._scale_y = screen.get_size()[1] / LOGICAL_H
# Au rendu :
sx = int(logical_x * self._scale_x)
sy = int(logical_y * self._scale_y)
```

**Evidence:** `TitleScreen._light_scale_x/y`. 5+ sessions de calibration infructueuses avant identification.

---

### A-UI-003 · 2026-05-04 · U · Major Rework
**Outil de calibration : `FULLSCREEN | SCALED`, pas `FULLSCREEN` seul**

`pygame.FULLSCREEN` sans `SCALED` peut letterboxer si la résolution cible est indisponible — les coords souris ne correspondent plus à l'espace 1280×720. `FULLSCREEN | SCALED` étire le canvas et traduit automatiquement les coords souris.

```python
screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
```

**Evidence:** `scripts/calibrate_halos.py`. Résolution du décalage après 4 itérations.

---

### L-UI-008 · 2026-05-04 · U · Perfect
**Halos multi-types : dict[(color_key, radius)] pour surfaces pré-générées**

Pour rendre des halos de couleurs variées, pré-générer 1 surface par couple unique `(color_tuple, radius)` à l'init. Les lookup au render sont O(1) via double dict `{color_key: {radius: Surface}}`.

```python
# Init
for _lx, _ly, r, color in MUSHROOM_LIGHTS:
    ck = tuple(color)  # hashable key
    if ck not in self._mushroom_halos:
        self._mushroom_halos[ck] = {}
    if r not in self._mushroom_halos[ck]:
        self._mushroom_halos[ck][r] = _build_halo(ck, r)

# Render
surf = self._mushroom_halos.get(ck, {}).get(hr)
if surf is None: continue
```

**Evidence:** `TitleScreen._mushroom_halos`. Zéro rework. MUSHROOM_LIGHTS vide → pas d'init = backward-compatible.

---

### L-UI-009 · 2026-05-04 · U · Perfect
**Dual-mode calibration tool : M-key toggle évite de relancer le programme**

Un outil de calibration à mode unique force l'utilisateur à relancer pour calibrer un deuxième type d'entité (ici feu vs champignons). Un toggle `M` en runtime évite cela et conserve les deux listes en mémoire jusqu'au `S` final.

```python
mode = MODE_FIRE  # default
# M key → mode = MODE_MUSH if mode == MODE_FIRE else MODE_FIRE
# Two separate lists: fire_pts, mush_pts
# S → save both lists in one calibration_result.py
```

**Evidence:** `scripts/calibrate_halos.py`. Calibration 25 champignons en 1 session sans relancer.

---
