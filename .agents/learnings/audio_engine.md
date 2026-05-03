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

