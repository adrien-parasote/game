# Project Learnings Registry

> **Usage:** Read before any BUILD session. Each entry = one confirmed pattern or anti-pattern with evidence.
> **Format:** ID · Date · Scope [P=project-specific | U=universal] · Outcome

---

## 🎧 Audio & Engine Setup

### L-AUDIO-001 · 2026-05-01 · U · Minor Rework
**Pygame Audio Channel Exhaustion**

Pygame defaults to 8 audio channels. Using `play(loops=-1)` for spatial ambient audio quickly exhausts these channels if multiple emitters exist, silently dropping transient sounds (footsteps, interactions).

```python
# ❌ default channels
pygame.mixer.init()

# ✅ explicitly increase channels for ambient systems
pygame.mixer.init()
pygame.mixer.set_num_channels(32)
```

**Evidence:** Ambient torches silenced player footsteps because all 8 channels were held by continuous loops (2026-05-01).

---

### L-AUDIO-002 · 2026-05-01 · P · Minor Rework
**Dynamic Audio File Fallbacks**

Calling `play_sfx` with a dynamically generated file name (e.g. `04-footstep_{material}.ogg`) causes total silence and log spam if the specific variant file doesn't exist.

```python
# ❌ blindly hoping the variant exists
audio_manager.play_sfx(f"footstep_{material}")

# ✅ check success and fallback
success = audio_manager.play_sfx(f"footstep_{material}")
if not success and material:
    audio_manager.play_sfx("footstep_base")
```

**Rule:** Always make `play_sfx` return a boolean indicating success, and implement a fallback to a generic base sound when using dynamic suffixes.
**Evidence:** Missing `04-footstep_stone.ogg` caused "SFX file not found" errors and silent footsteps (2026-05-01).

---

### L-AUDIO-003 · 2026-05-03 · U · Major Rework
**`Sound.stop()` + `Sound.play()` dans le même frame = tick silencieux SDL_mixer**

Appeler `sound.stop()` immédiatement avant `sound.play()` dans la même méthode produit un tick silencieux : SDL_mixer vide le buffer audio au `stop()`, puis le remplit au `play()`, mais la fenêtre de sortie audio peut passer avant que le premier échantillon soit disponible. Le son est techniquement joué (`play_sfx → True`) mais inaudible.

```python
# ❌ stop() + play() = tick silencieux probable en SDL_mixer
def play_sfx(self, name, volume_multiplier=1.0):
    sound.stop()
    sound.set_volume(Settings.SFX_VOLUME * volume_multiplier)
    sound.play()  # retourne True mais rien n'est audible

# ✅ laisser pygame gérer les canaux libres naturellement
def play_sfx(self, name, volume_multiplier=1.0):
    sound.set_volume(Settings.SFX_VOLUME * volume_multiplier)
    sound.play()  # utilise un canal libre du pool de 32
```

**Règle :** Pour les SFX transitoires (footsteps, interactions) dont le taux de déclenchement est ≥ 100ms, ne jamais appeler `Sound.stop()` avant `Sound.play()`. Réserver `stop()` aux cas où l'overlap est explicitement indésirable (musique, loops longs).

**Evidence :** `logging.warning` confirmait `play_sfx returned True` mais aucun son audible. Suppression de `sound.stop()` → sons de pas immédiatement audibles. commit `f9ba3b9`.

---

### A-AUDIO-002 · 2026-05-03 · U · Major Rework
**`Sound.stop()` stoppe TOUS les canaux de ce Sound — utiliser `channel.stop()` pour un scope précis**

`pygame.mixer.Sound.stop()` arrête le son sur **tous** les canaux qui jouent cet objet Sound, pas seulement le plus récent. Dans un système ambient avec `flush_ambient()`, stopper un son ambient (pour libérer le slot quand aucune proposition n'arrive) via `Sound.stop()` risque d'arrêter d'autres sons si le buffer SDL est partagé entre instances chargées du même fichier.

```python
# ❌ Sound.stop() — scope global sur tous les canaux du Sound
self.ambient_sounds[name].stop()  # stoppe potentiellement d'autres SFX préchargés

# ✅ Channel.stop() — scope limité au canal spécifique
channel = sound.play(loops=-1)           # stocker le Channel retourné
self.ambient_channels[name] = channel    # dans un dict séparé
# ...
channel = self.ambient_channels.pop(name, None)
if channel:
    channel.stop()  # stoppe uniquement CE canal
```

**Règle :** Tout son ambient démarré avec `sound.play(loops=-1)` doit stocker le `Channel` retourné. L'arrêt passe par `channel.stop()`, jamais `sound.stop()`.

**Evidence :** `audio.py::flush_ambient` — migration Sound.stop() → channel.stop(). commit `5d7523b`.

---

### L-AUDIO-004 · 2026-05-03 · U · Spec Wrong
**Vérifier l'amplitude des fichiers audio avec ffmpeg avant de livrer**

Pygame `Sound.set_volume()` est plafonné à 1.0 par SDL_mixer. Si un fichier `.ogg` est encodé à une amplitude intrinsèquement faible (ex: -22 dB peak), `volume_multiplier=10` donne le même résultat que `volume_multiplier=1` — on est déjà au plafond matériel. Le son est inaudible mais `play_sfx` retourne `True`.

```bash
# Diagnostic — mesurer l'amplitude réelle du fichier
ffmpeg -i assets/audio/sfx/04-footstep_stone.ogg -af "volumedetect" -f null - 2>&1 | grep max_volume
# → max_volume: -22.0 dB  ← trop faible, cible: -1 dB

# Fix — normaliser à -1 dB peak
ffmpeg -y -i input.ogg -af "volume=21dB" /tmp/normalized.ogg && mv /tmp/normalized.ogg input.ogg
```

**Règle :** Tout fichier SFX ajouté au projet doit être vérifié avec `ffmpeg -af volumedetect`. Cible : `max_volume` entre **-3 dB et -1 dB**. En dessous de -10 dB → normaliser avant commit.

**Evidence :** `04-footstep.ogg` + `04-footstep_stone.ogg` à -22 dB → normalisés à -1 dB (+21 dB). Sons de pas audibles après normalisation. commit `582966c`.

---

### L-AUDIO-005 · 2026-05-03 · P · Perfect
**Pattern propose/flush pour audio ambient multi-source**

Plusieurs entités du même type (ex: 3 torches) partageant le même sample audio créaient des conflits de canaux et un calcul de volume incorrect (lié à l'entité la plus à droite, pas la plus proche).

```python
# ❌ 1 canal par entité — conflits, volume lié à l'entité arbitraire
def update(self, dt):
    self.audio_manager.play_ambient(self.sfx_ambient, element_id=self.element_id, distance=dist)

# ✅ Propose/Flush — 1 canal par nom de son, volume = source la plus proche
# Chaque entité propose sa distance ce frame
def update(self, dt):
    self.audio_manager.propose_ambient(self.sfx_ambient, distance=dist)

# flush_ambient() résout 1 fois par frame : volume basé sur min(distances proposées)
def flush_ambient(self):
    for name, min_dist in self._ambient_proposals.items():
        falloff = max(AMBIENT_MIN_FALLOFF, 1.0 - (min_dist / AMBIENT_MAX_DISTANCE))
        sound.set_volume(Settings.SFX_VOLUME * AMBIENT_VOLUME_SCALE * falloff)
    self._ambient_proposals.clear()
```

**Règle :** Pour tout groupe d'entités partageant un sample audio, utiliser le pattern propose/flush : `propose_ambient(name, distance)` dans `entity.update()`, `flush_ambient()` une fois en fin de frame dans la boucle principale.

**Evidence :** 2 torches dans la debug room → volume suit la plus proche, plus de conflit de canal. commits `5d7523b`, `5ea0f14`.

## 🧪 Testing

### L-TEST-001 · 2026-04-28 · U · Perfect
**State flags and numeric attributes on MagicMock**

`MagicMock` auto-creates child attributes as `Mock` objects, not typed values. Numeric operations (`>`, `.magnitude()`) on Mocks raise `TypeError`. Boolean state gates stay falsy.

```python
# ❌ direction.magnitude() → Mock → TypeError
game.player = MagicMock()
game._update(0.016)

# ✅ assign real types for every attribute used in math or guards
game.player = MagicMock()
game.player.direction = pygame.math.Vector2(0, 0)  # real Vector2
game.player.is_moving = False                       # real bool
mock_sheet.valid = True                             # real flag
game._update(0.016)
```

**Rule:** For any Pygame entity mock, assign `pygame.math.Vector2` for `direction`/`pos`/`target_pos`, and explicit booleans for all gate flags.
**Evidence:** `SpriteSheet.valid` (2026-04-28); `player.direction.magnitude()` in 3 game.py tests (2026-04-30).

---

### L-TEST-002 · 2026-04-28 · U · Minor Rework
**Gated state transitions need explicit `update(dt)` calls**

State-machine operations (animations, interactions) are gated by busy flags like `is_animating`. Without calling `update(dt)` between steps, consecutive operations always fail.

```python
# ❌ second interact() silently fails — is_animating still True
entity.interact(player)
entity.interact(player)

# ✅ tick to clear the gate
entity.interact(player)
entity.update(0.1)
entity.interact(player)
```

---

### L-TEST-003 · 2026-04-28 · U · Minor Rework
**Centralized headless initialization in `conftest.py`**

Scattered `pygame.init()` + `SDL_VIDEODRIVER=dummy` calls across test files cause drift and environment-dependent failures.

✅ Put all global fixtures (headless driver, mock asset loader) in `tests/conftest.py`. Organize test files by domain (`test_engine.py`, `test_ui.py`, `test_map.py`…).

**Evidence:** 11 files → 6 domain modules, 100% pass rate after consolidation.

---

### L-TEST-004 · 2026-04-28 · U · Minor Rework
**Mock native Pygame objects by property, not by method**

`pygame.Rect.collidepoint` and similar are C-level — read-only, impossible to mock directly.

```python
# ❌ raises AttributeError — C method is read-only
mocker.patch.object(rect, 'collidepoint', return_value=True)

# ✅ manipulate the rect so the real method returns what you need
rect.topleft = (target_x, target_y)
```

---

### A-TEST-001 · 2026-04-28 · U · Major Rework
**Blind `__init__` mocking leaves attributes unset**

```python
# ❌ crashes downstream with AttributeError
with patch.object(MyClass, '__init__', return_value=None):
    obj = MyClass()
obj.some_flag  # → AttributeError

# ✅ recreate all public attributes after patching __init__
with patch.object(MyClass, '__init__', return_value=None):
    obj = MyClass()
    obj.some_flag = True
    obj.config = {}
```

---

### A-TEST-002 · 2026-04-28 · U · Major Rework
**Singleton state pollution (Settings)**

Modifying `src.config.Settings` in a test without restoring causes non-deterministic failures in unrelated tests depending on execution order.

```python
# ❌ leaks into subsequent tests
Settings.DEBUG = True

# ✅ always restore
original = Settings.DEBUG
Settings.DEBUG = True
try:
    ...
finally:
    Settings.DEBUG = original
```

---

### A-TEST-003 · 2026-04-30 · U · Minor Rework
**`patch('builtins.open', side_effect=...)` intercepts all I/O**

A global `side_effect` on `builtins.open` blocks every file read in the process — i18n loaders, config files, everything.

```python
# ❌ crashes in I18nManager._load_locale, not the target path
with patch('builtins.open', side_effect=Exception("IO error")):
    game = Game()

# ✅ selective open — only raise for the target path
real_open = builtins.open
def selective_open(path, *args, **kwargs):
    if "world.world" in str(path):
        raise Exception("IO error")
    return real_open(path, *args, **kwargs)

with patch('builtins.open', side_effect=selective_open):
    game = Game()
```

---

### A-TEST-004 · 2026-04-30 · P · Minor Rework
**`pygame.Surface.get_size()` after `__init__` rescaling**

`InventoryUI.__init__` rescales all surfaces (including fallbacks) via `smoothscale`. Asserting the original fallback size always fails.

```python
# ❌ fails — fallback (32,32) becomes (1200,1200) after smoothscale
assert ui.bg.get_size() == (32, 32)

# ✅ assert existence or type, not size
assert ui.bg is not None
assert isinstance(ui.bg, pygame.Surface)
```

**Generalized rule:** After any UI `__init__` that rescales assets, assert existence/type — never assert `get_size()`.

---

## 🎮 Game Engine

### L-GAME-001 · 2026-04-28 · U · Perfect
**Footprint-based interaction center**

Decouple the visual sprite position (`midbottom` alignment) from the logical interaction center (footprint center). Supports varied asset sizes and tall sprites without breaking grid-consistent interaction math.

---

### A-EVENT-002 · 2026-05-03 · P · Minor Rework
**`pygame.event.post()` re-queues events handled by the orchestrator**

`GameStateManager._handle_playing()` re-posts filtered events via `pygame.event.post()` so `Game._handle_events()` can consume them. If BOTH layers handle the same key (e.g., `TOGGLE_FULLSCREEN_KEY`), the key triggers twice per press — double-toggling fullscreen.

```python
# ❌ Orchestrator handles K_p AND re-posts it to Game which also handles K_p
filtered = [e for e in events if not (e.type == KEYDOWN and e.key == K_ESCAPE)]
for event in filtered:
    pygame.event.post(event)  # K_p survives the filter
# Then Game._handle_events() sees K_p and calls toggle_fullscreen() again

# ✅ Remove the duplicate handler from Game._handle_events()
# The orchestrator (_process_global_events) owns all cross-state keys.
# Game._handle_events() only handles gameplay-local keys (interact, inventory...).
```

**Règle :** Keys handled in the orchestrator's `_process_global_events()` MUST be removed from `Game._handle_events()`. If `pygame.event.post()` is used, the inner game handler is a secondary consumer — it will see every non-filtered event.

**Evidence:** `K_p` toggled fullscreen twice per press. Fixed by removing handler from `Game._handle_events()`. commit `ca94c9c`.

---

### L-ARCH-001 · 2026-04-28 · U · Perfect
**Composite keys for cross-map resource scoping**

Use `{map_base_name}-{element_id}` as keys in WorldState and DialogueManager. Prevents ID collisions across maps (e.g., two maps both with a `chest_01` object).

---

### A-GAME-001 · 2026-04-28 · U · Minor Rework
**Unthrottled spatial polling**

Proximity checks that trigger visual/audio side-effects every frame without a cooldown cause effect stacking and sprite duplication.

✅ Always gate proximity effects with `_emote_cooldown` (or equivalent) before triggering.

---

### A-GAME-002 · 2026-04-28 · U · Minor Rework
**Tile vs pixel coordinate mixups**

Passing pixel coords to functions expecting tile indices (or vice-versa) causes silent out-of-bounds errors (`is_collidable(128, 0)` → wrong tile).

✅ Name all coordinate parameters explicitly (`tile_x`, `pixel_x`) and convert at the boundary.

---

### L-ARCH-002 · 2026-04-30 · U · Major Rework
**Spec must define close sequence, not just close trigger**

Specifying WHEN to close an entity without specifying WHAT the close sequence is generates bugs for each missing step.

| Step | Action | Method |
|------|--------|--------|
| 1 | Toggle entity state | `entity.interact(player)` |
| 2 | Play SFX | `audio_manager.play_sfx(entity.sfx)` |
| 3 | Persist state | `world_state.set(key, {...})` |
| 4 | Close UI | `ui.close()` |
| 5 | Suppress follow-up feedback | reset proximity target + cooldown |

✅ Centralize all steps in `_close_X()`, called from **every** close path (zone exit, action key, etc.).
**Evidence:** 5 separate bugs in ChestUI auto-close. commit `6c7f811`.

---

### L-ARCH-003 · 2026-04-30 · U · Major Rework
**Frame-invariant checks belong in `update()`, not in conditional sub-functions**

A check placed inside a conditional branch only runs when that branch fires. If the check must fire every frame, it must live directly in `update()`.

```python
# ❌ _check_chest_auto_close() only runs when NO entity in proximity range
def _check_proximity_emotes(self):
    ...
    if nothing_in_range:
        self._check_chest_auto_close()  # missed when player is near other entity

# ✅ always-running checks go directly in update()
def update(self, dt):
    self._check_proximity_emotes()  # conditional
    self._check_chest_auto_close()  # always — regardless of proximity state
```

✅ **Spec rule:** State explicitly "Checked every update tick" or "Checked conditionally on [X]" to prevent ambiguous call-site choices.

---

### A-ARCH-003 · 2026-05-01 · U · Minor Rework
**Rendering loop disconnected from dynamic properties**

When an object's state (e.g., `is_on`) transitions from an event-driven boolean to a dynamically computed property (e.g., based on `TimeSystem.brightness`), the rendering state (e.g., sprite index) must be actively synchronized in the `update()` loop.

```python
# ❌ Rendering sprite column only updates on explicit interaction
def interact(self):
    self.is_on = not self.is_on
    self._update_col_index()  # OK for manual, but misses auto-toggles

# ✅ Polling dynamic state in the update loop
def update(self, dt):
    if getattr(self, 'day_night_driven', False):
        self._update_col_index()  # Sync visual state with computed property
```

**Rule:** When replacing static state variables with dynamically computed properties, ensure the `update()` loop polls and synchronizes any visual or layout properties that depend on them.
**Evidence:** Day/night torches computed `is_on=False` correctly at dawn, but rendered the "ON" sprite because `col_index` was only updated during `interact()`.

---

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

## 🔧 Spec & Agent Workflow

### L-SPEC-001 · 2026-04-28 · U · Minor Rework
**Define procedural assets by boundary values**

In implementation specs, describe generated geometry/textures by **Start, End, Step/Falloff** values — not prose. Eliminates ambiguity in generation loops (e.g., center-to-edge alpha gradients).

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

### A-UX-001 · 2026-04-28 · U · Minor Rework
**Hardcoded keyboard constants**

```python
# ❌
if event.key == pygame.K_e:

# ✅
if event.key == Settings.INTERACT_KEY:
```

---

### A-AGENT-001 · 2026-04-28 · U · Major Rework
**Blind file overwrites with stale context**

Replacing large file chunks from outdated memory destroys working code (I18n, UI scaling, etc.) and starts endless `AttributeError` loops.

✅ Always `view_file` before editing. Use targeted `multi_replace_file_content`. On accidental corruption: `git checkout -- <file>` immediately.

---

### A-AGENT-002 · 2026-04-28 · U · Major Rework
**Skipping Stream Coding pipeline stages**

Jumping to BUILD without SPEC, or skipping VERIFY/HARDEN, generates vibe-coded output that diverges from spec and requires expensive rework.

✅ Never write implementation code without RED tests (TDD Gate). Never commit without `/learn-eval` + `/doc-update`.

---

### A-SPEC-001 · 2026-04-28 · U · Minor Rework
**Ambiguous spritesheet definitions**

Describing an asset as "animated" without stating grid layout (rows × columns) and frame mapping causes incorrect slicing (4×1 instead of 4×8).

✅ Always specify: `rows=4, cols=8, frame_duration=0.1s, animation_row={state: row_index}`.

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

### A-TEST-005 · 2026-04-30 · U · Spec Wrong
**Tests qui passent silencieusement sur un contrat brisé (duck-typing Pygame)**

`pygame.Rect.collidepoint()` accepte un `Vector2` en Python — il déstructure automatiquement en `(x, y)`. Un test appelant `_is_collidable(Vector2(0,0))` passait vert même si la signature déclarée attendait `(float, float)`.

```python
# ❌ test passe mais le contrat est faux — Vector2 ≠ float
assert game._is_collidable(pygame.math.Vector2(0, 0)) is True

# ✅ tester avec les types exacts de la signature déclarée
assert game._is_collidable(0.0, 0.0) is True
```

**Règle :** Toujours inspecter la signature déclarée avant d'écrire un test. En Pygame, `collidepoint` est suffisamment permissif pour masquer des erreurs de type → vérifier avec `mypy` ou des annotations `float` strictes.

**Evidence :** `test_engine.py::test_game_is_collidable` — 3 appels avec Vector2 corrigés en floats. `game.py::_is_collidable(px_center: float, py_center: float)`.

---

### A-ARCH-001 · 2026-04-30 · U · Minor Rework
**Disk I/O dans une méthode appelée à chaque ouverture de panneau**

`ChestUI._compute_layout()` appelait `_load_slot_image()` (chargement disque + `convert_alpha()`) à chaque ouverture de coffre. L'image était déjà disponible en attribut depuis `__init__`.

```python
# ❌ I/O disque à chaque open() — spike CPU visible
self._slot_img = pygame.transform.smoothscale(
    self._load_slot_image(),   # charge depuis disque
    (slot_size, slot_size)
)

# ✅ scale depuis l'attribut déjà en mémoire — zéro I/O
self._slot_img = pygame.transform.smoothscale(self._slot_img, (slot_size, slot_size))
```

**Règle :** Toute méthode `_compute_layout()` / `_rebuild_layout()` ne doit jamais déclencher d'I/O disque. Les assets sont chargés UNE FOIS dans `__init__`. La spec doit explicitement mentionner « No disk I/O in `draw()` or `_compute_layout()` ».

**Evidence :** `chest.py::_compute_layout` ligne 350 — `_load_slot_image()` remplacé par `self._slot_img`.

---

### A-ARCH-002 · 2026-04-30 · U · Spec Wrong
**Singleton réinstancié à chaque appel — leurre de performance**

`_trigger_dialogue()` dans `game.py` appelait `I18nManager()` (constructeur) à chaque dialogue déclenché. Le singleton `__new__` retourne la même instance, mais le pattern visuel `SomeManager()` dans une méthode d'update/event signal une intention de réinstanciation.

```python
# ❌ pattern trompeur — semble créer une nouvelle instance
msg = I18nManager().get(f"dialogues.{full_key}")

# ✅ utiliser l'attribut de classe — intention claire
msg = self.i18n.get(f"dialogues.{full_key}")
```

**Règle :** Les singletons ne doivent jamais être appelés par leur constructeur dans des méthodes chaudes. Toujours stocker la référence singleton comme attribut d'instance (`self.i18n = I18nManager()`) dans `__init__` et utiliser `self.i18n` partout.

**Scope :** Universal — s'applique à tout singleton (AudioManager, Settings, etc.).

**Evidence :** `game.py::_trigger_dialogue` ligne 402.

---

### L-TEST-005 · 2026-04-30 · U · Perfect
**Fichier de tests ciblé par rapport de couverture**

Plutôt que d'ajouter des tests dispersés dans des fichiers existants, créer un fichier `test_coverage_gaps.py` unique regroupant tous les tests ciblés sur les branches manquantes identifiées par `--cov-report=term-missing`. Plus facile à supprimer/réorganiser et clairement séparé des tests fonctionnels.

```bash
# Identifier exactement les lignes manquantes
pytest --cov=src --cov-report=term-missing -q 2>&1 | grep "module_name"

# Résultat → fichier unique organisé par module
# tests/test_coverage_gaps.py::TestI18nCoverage
# tests/test_coverage_gaps.py::TestInteractiveCoverage
# ...
```

**Règle :** Pour toute session de couverture ciblée, créer `test_coverage_gaps.py` avec classes par module. Ne jamais disperser ces tests dans les fichiers existants — ils deviennent introuvables.

**Evidence :** +51 tests en 1 fichier, coverage 89%→92%. Aucune régression dans les 216 tests existants.

---

### L-ARCH-004 · 2026-04-30 · U · Perfect
**Dispatcher thin + helpers privés pour les méthodes > 50L**

`_spawn_entities()` (93L) et `_check_proximity_emotes()` (68L) ont été décomposées en dispatcher léger + helpers privés focalisés, sans changer le comportement observable.

**Pattern :**
```python
# ❌ 90 lignes de if/elif avec logique imbriquée
def _spawn_entities(self, entities):
    for ent in entities:
        if type == "interactive":
            # 40 lignes...
        elif type == "teleport":
            # 15 lignes...

# ✅ dispatcher 20L + helpers 20-30L chacun
def _spawn_entities(self, entities):
    for ent in entities:
        if type == "interactive": self._spawn_interactive(ent, props, map_name)
        elif type == "teleport":  self._spawn_teleport(ent, props)

def _spawn_interactive(self, ent, props, map_name): ...  # 30L
def _spawn_teleport(self, ent, props): ...               # 12L
```

**Règle :** Toute méthode >40L qui contient un `if/elif` de dispatch doit être décomposée. Le dispatcher ne doit faire que router — aucune logique métier.

**Evidence :** `game.py` (-70L sur `_spawn_entities`), `interaction.py` (-55L sur `_check_proximity_emotes`), `inventory.py` (-60L sur `draw`). Zéro régression.

---

### A-SPEC-002 · 2026-04-30 · P · Spec Wrong
**POSITION_TO_DIR inversé dans la spec vs code**

`interactive-objects.md` documentait `0=Up, 1=Right, 2=Left, 3=Down`. Le code (`InteractiveEntity.POSITION_TO_DIR`) implémentait `0=Down, 1=Left, 2=Right, 3=Up`. La spec et le code divergeaient depuis la création du module.

**Cause :** Le mapping a été défini dans le code avant d'être documenté. La spec a été écrite de mémoire, inversée.

**Règle :** Pour tout mapping constant (enum-like), toujours extraire la valeur depuis le code source avec `grep` avant de documenter. Ne jamais documenter de mémoire.

```bash
# ✅ vérifier avant de documenter
grep -n "POSITION_TO_DIR" src/entities/interactive.py
```

**Scope :** Project-specific mais le pattern est universel — voir L-SPEC-001.

**Evidence :** `interactive-objects.md` ligne 24 corrigée. Confirmé avec `InteractiveEntity.POSITION_TO_DIR` dans `interactive.py`.

---

### A-TEST-006 · 2026-04-30 · U · Major Rework
**Render-only branches résistent à la couverture sans display réel**

`chest.py` est resté à 84% après tous les tests ciblés. Les branches non couvertes (lignes 205-216, 248-304, 354-356, 550-588) sont toutes dans des méthodes de rendu qui appellent `pygame.Surface.blit()`, `pygame.image.load()`, ou `pygame.transform.smoothscale()` sur des assets réels.

Sans display réel (`SDL_VIDEODRIVER=dummy`), `blit()` fonctionne mais les branches conditionnelles sur la présence d'un asset valide (`if self._slot_img is not None`) ne peuvent être testées sans charger de vrais fichiers PNG.

**Pattern empirique :**
```
Couverture atteignable sans assets réels : ~84-88% pour les modules UI lourds
Couverture atteignable avec assets réels (CI avec display) : ~95%+
```

**Règle :** Accepter un plafond de couverture de ~85% pour les modules UI render-only en tests headless. Ne pas investir davantage sans infrastructure CI avec display. Documenter ce plafond dans le `Makefile` ou `.coverage.ini`.

```ini
# .coveragerc ou pyproject.toml — exclure les branches render-only
[coverage:report]
exclude_lines =
    if.*_img is not None
    screen\.blit\(
```

**Evidence :** `chest.py` 84% stable même après 8 tests ciblés supplémentaires. `inventory.py` 100% obtenu car ses branches render ne dépendent pas d'assets fichiers.

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

### A-AGENT-003 · 2026-05-01 · U · Spec Wrong
**Verify @property vs method before calling**

Generated `self.time_system.world_time()` with parentheses, but `world_time` is a `@property`. Runtime crash: `'WorldTime' object is not callable`.

```python
# ❌ Assumes world_time is a method
wt = self.time_system.world_time()

# ✅ Verify first — it's a property
wt = self.time_system.world_time
```

**Rule:** Before calling any attribute from an external module, verify whether it's a property or method:
```bash
grep -n "def world_time\|world_time = " src/engine/time_system.py
```

**Scope:** Universal — Python @property vs method mixups cause `TypeError: 'X' object is not callable`.
**Evidence:** Runtime crash on `_compute_slant()` first call. Fixed by removing parentheses.

---

*Last optimized: 2026-05-01 — added L-REND-002, L-REND-003, A-AGENT-003 from window lighting beam session.*

---

### L-TEST-006 · 2026-05-01 · U · Perfect
**Domain-based test directory structure**

Organiser les tests par domaine métier (mirroring `src/`) produit un ratio signal/bruit maximal : la prochaine IA sait immédiatement où chercher sans lire tous les fichiers.

```
tests/
├── conftest.py          # Global SDL init, shared fixtures
├── engine/              # mirrors src/engine/
├── entities/            # mirrors src/entities/
├── map/                 # mirrors src/map/
├── ui/                  # mirrors src/ui/
└── graphics/            # mirrors src/graphics/
```

**Règle :** Chaque nouveau module `src/<domain>/foo.py` → créer `tests/<domain>/test_foo.py`. Jamais de test à la racine `tests/` sauf `conftest.py`.

**Evidence :** 23 fichiers plats → 16 fichiers dans 5 domaines. 436/436, 0 régression. commit `484ccfa`.

---

### A-TEST-007 · 2026-05-01 · P · Minor Rework
**Slice `lines[start:end]` sans validation syntaxique → `IndentationError`**

Extraire un bloc de code par slicing de lignes sans valider que `start` pointe sur la première ligne non-indentée du bloc (def/class) produit un fichier syntaxiquement invalide.

```python
# ❌ start peut pointer sur une ligne DANS le corps du bloc précédent
lines = source.splitlines()
start = next(i for i, l in enumerate(lines) if 'class TestX' in l)
helper_lines = lines[32:77]  # estimation empirique → fragile
with open("out.py", "w") as f:
    f.write("\n".join(helper_lines))  # → IndentationError si mal calé

# ✅ valider avec ast.parse avant d'écrire
import ast
candidate = "\n".join(lines[start:end])
try:
    ast.parse(candidate)
    with open("out.py", "w") as f:
        f.write(candidate)
except SyntaxError as e:
    raise RuntimeError(f"Slice invalide [L{start}:L{end}]: {e}")
```

**Règle générale :** Pour les migrations 1:1, utiliser `shutil.copy()`. Réserver les scripts de slicing aux extractions de classes isolées, toujours validées avec `ast.parse()` avant écriture.

**Evidence :** `tests/entities/test_interactive.py` — `IndentationError` à la ligne 13 corrigé en 30s après refactoring du script. commit `484ccfa`.

---

*Last optimized: 2026-05-01 — added L-TEST-006, A-TEST-007 from test suite urbanization session.*

---

### L-ARCH-005 · 2026-05-01 · U · Perfect
**Decoupling Engine God Objects**

`game.py` accumulated rendering loops, collision mathematics, state updates, and interactions, making test maintenance highly coupled and increasing CPU overhead per frame with excessive class lookups.

**Pattern :**
```python
# ❌ Logic bundled in the main loop class
class Game:
    def _is_collidable(self, x, y): ...
    def _draw_scene(self): ...
    def _update(self): 
        # mixing spatial, rendering, input
```

```python
# ✅ Extract logic into highly focused Manager classes
class Game:
    def __init__(self):
        self.render_manager = RenderManager(self)
        self.interaction_manager = InteractionManager(self)
        
    def _draw(self):
        self.render_manager.draw_scene()
```

**Règle :** Main engine loops should act exclusively as Event Dispatchers and Timers. Complex spatial queries, collision checks, and layered rendering MUST be decoupled into dedicated `Manager` classes that are passed a reference to the main state.

**Evidence :** `InteractionManager` and `RenderManager` extracted, eliminating >200 lines from `game.py`. 100% test coverage maintained without architectural breakage.

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



## Learning: Mock Dependency Drift

**Date:** 2026-05-03
**Spec:** Performance Optimization Plan
**Outcome:** Minor Rework
**Project:** Python Pygame Engine

### What happened
Added `layer_depths` caching to `MapManager` and used it in `RenderManager`. The implementation code was perfect, but the unit tests for `RenderManager` failed because `game.map_manager` was a `MagicMock` and `layer_depths` evaluated to a mock object instead of a dict, causing a `TypeError` on comparison.

### Root cause
Adding a new property to a core dependency (`MapManager`) without simultaneously updating the test mocks in dependent classes (`test_render_manager.py`).

### Anti-pattern (what to avoid)
❌ **Don't**: Add properties to a class without updating the `MagicMock` setups in the test files of other classes that depend on it.

✅ **Do Instead**: When adding a property to Class A, search the test suite for `MagicMock()` setups of Class A and explicitly assign the new property to the mock.

### Evidence
- Test failure in `test_render_manager_draw_background`: `TypeError: \'<=\' not supported between instances of \'MagicMock\' and \'int\'`

### Scope
- [x] Universal (applies across projects)

---

### L-ARCH-005 · 2026-05-03 · U · Perfect
**Extract Mixins to preserve test mock boundaries**

The `ChestUI` monolithic class (923 lines) needed splitting to comply with the <400 line rule. However, doing so via structural delegation (`self.transfer_manager._transfer()`) would break dozens of existing tests in `test_chest.py` that mock internal `ui._transfer_...` and `ui._draw_...` methods directly.

**Pattern (what to reproduce)**
When refactoring monolithic classes that are heavily mocked in existing unit tests, use **Composition via Mixins** instead of Component Delegation to satisfy file-size constraints without triggering massive test rewrites.

By extracting the logic into Mixin classes (`ChestTransferMixin`, `ChestLayoutMixin`, `ChestDrawMixin`) and having `ChestUI` inherit from them, the namespace remained identical. All 471 tests in the suite passed immediately without needing to update mock targets.

**Evidence:**
- `src/ui/chest.py` successfully split into 5 domain-specific files (`chest.py`, `chest_layout.py`, `chest_transfer.py`, `chest_draw.py`, `chest_constants.py`).
- The entire `pytest tests/ui/test_chest.py` suite (87 tests) passed with 0 functional changes to the tests themselves.

---

### L-ARCH-006 · 2026-05-03 · U · Minor Rework
**Private Constants Exporting with Wildcard Imports**

When extracting UI configuration into a dedicated `_constants.py` file, we encountered 31 `NameError` test failures in the Python test suite. 

**Anti-pattern (what to avoid)**
Using `from module_constants import *` will **not** import any constants prefixed with an underscore (e.g. `_ASSET_DIR`, `_FONT_PATH`), as Python treats them as private to the module. If these variables are needed in the consumer file, they will be undefined.

**Pattern (what to reproduce)**
When extracting private constants, you must either:
1. Rename the constants to remove the underscore (making them public).
2. Explicitly import the underscored variables alongside the wildcard import:
   `from module_constants import *`
   `from module_constants import _PRIVATE_VAR`
3. Define `__all__` in the constants file.

We chose option 2 to make the usage explicit.

**Evidence:**
- Extracted constants from 5 UI files into `_constants.py` files.
- `test_game.py` failed with `NameError: name '_MENU_ITEM_KEYS' is not defined`.
- Fixed by adding explicit imports for underscored variables, bringing the test suite back to 100% pass rate.
