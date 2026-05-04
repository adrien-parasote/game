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


### L-UX-001 · 2026-04-28 · U · Minor Rework
**Interruption-first feedback chaining**

New visual feedback (emotes, effects) must clear/overwrite existing ones immediately — never wait for the previous animation to finish.

```python
# ❌ blocks rapid interactions
if len(self.emote_group) == 0:
    self.emote_group.add(sprite)

# ✅ clear first, add immediately
self.emote_group.empty()
self.emote_group.add(sprite)
```

---

---

### A-UX-001 · 2026-04-28 · U · Minor Rework
**Hardcoded keyboard constants**

```python
# ❌
if event.key == pygame.K_e:

# ✅
if event.key == Settings.INTERACT_KEY:
```

---

---

### A-UI-002 · 2026-04-30 · U · Major Rework
**Missing event dispatch for new UI components in game loop**

Adding `handle_event()` to a UI class does nothing unless the game loop explicitly calls it. The absence is silent — clicks register in pygame but reach no handler.

```python
# ❌ chest_ui.handle_event never called → all arrow clicks silently swallowed
def _handle_events(self):
    for event in pygame.event.get():
        if self.inventory_ui.is_open:
            self.inventory_ui.handle_input(event)
        # chest_ui missing entirely

# ✅ every UI component with handle_event must be wired
def _handle_events(self):
    for event in pygame.event.get():
        if self.inventory_ui.is_open:
            self.inventory_ui.handle_input(event)
        if self.chest_ui.is_open:
            self.chest_ui.handle_event(event)
```

**Rule:** When adding any new UI component with interactive state, immediately add its dispatch to `_handle_events()`. Write a test that calls `handle_event()` via a simulated click and asserts a state change.
**Evidence:** Chest UI arrows did nothing for entire session until `handle_event` wired. commit `ff92747`.

---

---

### A-UI-003 · 2026-04-30 · U · Major Rework
**Page-based vs window-based offset clamping are different formulas**

For **window-based** scrolling (slide 1 slot at a time), max_offset = `capacity - visible`. For **page-based** scrolling (jump a full page at a time), max_offset = `capacity - 1`.

```python
# ❌ window-based clamp applied to page-based jump
# capacity=24, visible=18 → max_offset=6 → offset=min(18,6)=6 → shows [6:24]=18 slots (wrong)
max_offset = capacity - visible
self._inv_offset = min(self._inv_offset + visible, max_offset)

# ✅ page-based: clamp to capacity-1 so partial last page is reachable
# capacity=24, visible=18 → offset=min(18, 23)=18 → shows [18:24]=6 slots (correct)
self._inv_offset = min(self._inv_offset + _INV_SLOTS_VISIBLE, self._capacity() - 1)
```

**Rule:** In spec, declare navigation mode explicitly: `WINDOW` (1-slot slide) or `PAGE` (full-page jump). Apply the correct clamp formula for each.
**Evidence:** Took 3 correction rounds; `visible_count` exposé the wrong formula. commit `ff92747`.

---

---

### A-UI-004 · 2026-04-30 · U · Minor Rework
**Left/right arrow semantic direction must be explicit in spec**

"Left arrow" and "right arrow" are physical; "advance" and "rewind" are semantic. Without a clear mapping, implementations diverge and require swap iterations.

```markdown
# ✅ Spec must state this explicitly:
# ▶ Right arrow → advance window (higher indices) — visible when more items ahead
# ◀ Left arrow  → rewind window (lower indices)  — visible when offset > 0
```

**Rule:** For any scrollable UI, the spec must include a table: `Physical Arrow | Data Direction | Visibility Condition`.
**Evidence:** 2 direction swaps in one session (left↔right wiring). commit `ff92747`.

---

---

### L-UI-006 · 2026-04-30 · U · Minor Rework
**visible_count must guard both rendering AND hover hit-testing**

After fixing rendering to only draw N slots, the hover zone loop still iterates all 18 `_inv_slot_positions`, making invisible slots hoverable and triggering out-of-bounds states.

```python
# ❌ hover registers on invisible slots 6–17 even when only 6 are drawn
for i, rect in enumerate(self._inv_slot_positions):
    if rect.collidepoint(mouse_pos):
        self._hovered_inv_slot = i

# ✅ same visible_count used in both draw and hover
visible_count = min(_INV_SLOTS_VISIBLE, max(0, self._capacity() - self._inv_offset))
for i, rect in enumerate(self._inv_slot_positions[:visible_count]):
    if rect.collidepoint(mouse_pos):
        self._hovered_inv_slot = i
```

**Rule:** Any `visible_count` guard introduced for rendering must immediately be applied to all hit-test loops over the same positions list.
**Evidence:** Hover on ghost slots after page 2 scroll. Fixed in same commit `ff92747`.

---

*Last optimized: 2026-04-30 — added A-UI-002, A-UI-003, A-UI-004, L-UI-006 from ChestUI paged inventory session.*

---

## ✅ Optimisation globale — 2026-04-30

---

### A-UI-005 · 2026-05-01 · U · Minor Rework
**UI Decoupling from Temporal Animations**

**What happened:** Halting an NPC mid-tile causes visual sliding and snapping issues. The code was then updated to let the NPC finish its tile movement, but the UI bubble appeared instantly, causing the bubble to slide along with the NPC. We then implemented a `pending_npc_dialogue` queue.

**Root cause:** Temporal coupling. Assuming that the logical trigger (pressing 'Interact') and the visual response (opening the UI) must happen on the same frame. For animated entities in a grid-based game, actions often need to be queued until the current animation/movement cycle finishes.

```python
# ❌ Triggering synchronous UI events (like dialogue bubbles) instantly on entities that have asynchronous or continuous state transitions (like grid movement).
res = npc.interact(self.game.player)
if res:
    self.game._trigger_npc_bubble(npc, res)

# ✅ Implement an event queue or a `pending_action` state in the main update loop.
res = npc.interact(self.game.player)
if res:
    if npc.is_moving:
        self.game._pending_npc_dialogue = (npc, res)
    else:
        self.game._trigger_npc_bubble(npc, res)
```

**Rule:** When an interaction occurs on a moving entity, store the intent, let the entity resolve its current interpolation (e.g., finish walking to the next tile), and only trigger the UI callback when `entity.is_moving == False`.
**Evidence:** `src/engine/interaction.py` queueing logic: `if npc.is_moving: self.game._pending_npc_dialogue = (npc, res)`. Tests failed initially because Mock objects have properties that evaluate to True in python, requiring explicit `npc.is_moving = False` in `tests/test_interaction.py`.

---

*Last optimized: 2026-05-01 — optimization session: A-UI-005.*

---

---
### L-UI-010 · 2026-05-04 · U · Perfect
**Engraved vs Extruded text effect direction**

The visual perception of "sunken" (engraved) vs "raised" (extruded) text depends entirely on the shadow and highlight offsets relative to the main text.

- **Extruded (Raised)**: Highlights at Top-Left (`-1, -1`), Shadows at Bottom-Right (`+1, +1`). This simulates an object above the surface catching light on its upper edge.
- **Engraved (Sunken)**: Shadows at Top-Left (`-1, -1`), Highlights at Bottom-Right (`+1, +1`). This simulates a hole where the top-left inner edge is in shadow and the bottom-right inner edge catches light.

✅ **Rule for Engraving:**
```python
# Pass 1 — Shadow (top-left -1, -1) : cast by the upper edge of the hole
shadow = font.render(label, True, SHADOW_COLOR)
# Pass 2 — Highlight (bottom-right +1, +1) : lit inner far edge
light  = font.render(label, True, LIGHT_COLOR)
# Pass 3 — Text (0, 0) : the bottom of the engraving (should be slightly darker than stone)
text   = font.render(label, True, TEXT_COLOR)

screen.blit(shadow, r.move(-1, -1))
screen.blit(light,  r.move(1, 1))
screen.blit(text,   r)
```

**Evidence:** `PauseScreen._blit_engraved()` fix after user reported "extruded" look. commit `pending`.
