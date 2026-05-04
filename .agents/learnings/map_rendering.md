## 🗺️ Map & Rendering

### L-MAP-001 · 2026-04-28 · U · Major Rework
**Semantic name-based layer ordering**

Tiled JSON layer order is unstable — nested groups reorder silently. Sort layers by semantic name prefix (`00-`, `01-`) in `MapManager` instead.

```python
# ✅
layer_order = sorted(raw_order, key=lambda lid: self.layer_names.get(lid, ""))
```

**Evidence:** Background (`00-layer`) disappeared due to group nesting. `tests/test_map.py` confirmed fix.

---

### L-REND-001 · 2026-04-28 · U · Perfect
**Additive light overlays applied after darkness**

Apply `BLEND_ADD` light sources after the global darkness surface. Applying before causes darkness to dim the light source.

---

### A-MAP-001 · 2026-04-28 · U · Major Rework
**Index-based layer priority** → See L-MAP-001 (same root cause).

---

## 🖼️ Rendering

### L-UI-007 · 2026-05-03 · U · Major Rework
**`pygame.display.update()` appartient exclusivement au main loop — jamais dans `_draw()`**

Appeler `pygame.display.update()` à l'intérieur de `_draw()` crée un double-flush par frame dès qu'un second composant (overlay, pause screen) dessine après `_draw()`. Le résultat est un scintillement visible : le premier flush montre le frame incomplet (sans l'overlay), le second le frame complet.

```python
# ❌ double-update → scintillement en PAUSED
def _draw(self):
    self.render_manager.draw_scene()
    pygame.display.update()  # flush prématuré avant l'overlay

# ✅ _draw() = rendu pur, GSM main loop = flush unique
def _draw(self):
    self.render_manager.draw_scene()
    # pygame.display.update() appelé une seule fois en fin de frame par GSM.run()
```

**Règle :** `pygame.display.update()` (ou `pygame.display.flip()`) doit être appelé **une seule fois par frame**, à la fin du main loop. Toute méthode `_draw()` interne ne fait que rendre vers la surface — pas flusher.

**Evidence :** Scintillement de l'écran pause → fix dans `game._draw()` commit `38892b2`. Scope: universel pygame.

**Scope :** Universal

---

### A-AUDIO-001 · 2026-05-03 · P · Spec Wrong
**Transition de scène sans arrêt audio = audio qui continue en arrière-plan**

Quand `_transition_to_title()` change l'état du GSM sans arrêter l'audio, la BGM et les ambients du jeu continuent de jouer par-dessus le menu principal.

```python
# ❌ transition sans cleanup audio
def _transition_to_title(self) -> None:
    pygame.mouse.set_visible(False)
    self.state = GameState.TITLE

# ✅ arrêt complet avant de changer d'état
def _transition_to_title(self) -> None:
    self._game.audio_manager.stop_bgm(fade_ms=500)
    for sid in list(self._game.audio_manager.ambient_sounds.keys()):
        self._game.audio_manager.stop_ambient(sid)
    pygame.mixer.stop()  # SFX channels résiduels
    pygame.mouse.set_visible(False)
    self.state = GameState.TITLE
```

**Règle :** Toute transition vers un état "vierge" (TITLE, GAME_OVER) doit inclure un **audio teardown complet** : BGM fade, ambient stop, `pygame.mixer.stop()`. La spec de chaque transition doit lister explicitement les ressources à nettoyer (audio, curseur, UI state).

**Evidence :** BGM + ambients du jeu jouaient sur le menu principal après "Menu Principal" depuis le pause screen. Fix commit `128d0e5`.

**Scope :** Project-specific (pattern général pygame universel)

---

### L-UI-008 · 2026-05-03 · P · Perfect
**Partage de l'effet gravé entre TitleScreen et PauseScreen via paramètre font**

L'effet `_blit_engraved` initialement hardcodé sur `self._menu_item_font` a été rendu réutilisable par l'ajout d'un paramètre `font: pygame.font.Font | None = None` :

```python
def _blit_engraved(
    self, label: str, cx: int, cy: int,
    font: pygame.font.Font | None = None
) -> None:
    f = font if font is not None else self._menu_item_font
    shadow = f.render(label, True, MENU_ENGRAVE_SHADOW)
    light  = f.render(label, True, MENU_ENGRAVE_LIGHT)
    text   = f.render(label, True, MENU_ENGRAVE_TEXT)
    r = text.get_rect(center=(cx, cy))
    self._screen.blit(shadow, r.move(1, 2))
    self._screen.blit(light,  r.move(-1, -1))
    self._screen.blit(text,   r)
```

`PauseScreen._blit_engraved()` est une copie directe de cette méthode avec son propre `_item_font`. Toutes les couleurs (`ENGRAVE_*`) sont des constantes module-level identiques dans les deux fichiers — single source of truth à extraire dans un `ui_constants.py` si un 3ème écran adopte le même style.

**Pattern :** Méthodes de rendu pures avec `font=None` (default au font principal) sont extensibles sans duplication.

**Evidence :** `TitleScreen._blit_engraved(font=self._back_label_font)` commit `40aa2da`, `PauseScreen._blit_engraved()` commit `69b9dde`. 467 tests passés.

**Scope :** Project-specific





### L-REND-002 · 2026-05-01 · U · Minor Rework
**Corner-fade approach for shaped surface bottoms**

Using `effective_t = t * (1 + dist * k)` to make edges fade faster than the center also dims the center column at the bottom, creating a spike/triangle shape instead of an oval.

```python
# ❌ Couples center and edge: center spikes because effective_t > 1 at edges
effective_t = t * (1.0 + dist_x * 0.9)
v_fade = max(0.0, 1.0 - effective_t) ** 0.35

# ✅ Keep v_fade independent, add a separate corner multiplier in the bottom zone only
v_fade = (1.0 - t) ** 0.6  # unchanged for all x
if t > 0.65:
    bp = (t - 0.65) / 0.35
    cf = max(0.0, 1.0 - bp * abs(x - cx) / half_w * 1.8)  # 1.0 at center, fades at edges
else:
    cf = 1.0
alpha = master_alpha * v_fade * h_fade * cf
```

**Rule:** Never modify a per-row decay function based on per-pixel horizontal distance. Add a separate multiplier that's always 1.0 at the center column.
**Evidence:** User screenshot showed spike; corner_fade approach restored trapezoid shape with oval bottom.

---

---

### L-REND-003 · 2026-05-01 · U · Minor Rework
**Continuous cosine blending for cyclic state transitions**

Hard `if brightness < threshold: moon else: sun` switches create visible discontinuities ("tic") at state transitions like dawn/dusk.

```python
# ❌ Binary switch — 42px jump at 18h
if brightness < 0.15:
    return moon_slant   # e.g., +14px
else:
    return sun_slant    # e.g., -28px at 18h

# ✅ Two continuous cosine waves blended by brightness
sun_slant  = max_slant * cos(2π * (hour - 6) / 24)
moon_slant = max_slant * 0.5 * cos(2π * (hour - 18) / 24)
slant = sun_slant * brightness + moon_slant * (1 - brightness)
```

**Rule:** For any cyclic parameter that transitions between two modes (day/night, seasons, tides), model each mode as an independent continuous function and blend by the existing continuous transition weight.
**Evidence:** Slant continuity test — max jump < 5px across 48 half-hour samples vs. 42px jump with if/else.

---

---
