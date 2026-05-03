import pygame
import os
import logging
from typing import Dict, Optional
from src.config import Settings

# Ambients play at most 60 % of SFX_VOLUME — audible atmospheric background
# without competing with footsteps and interaction cues.
AMBIENT_VOLUME_SCALE = 0.6

# Falloff parameters for distance-based ambient volume.
AMBIENT_MAX_DISTANCE: float = 300.0
AMBIENT_MIN_FALLOFF: float = 0.05

class AudioManager:
    """
    Handles playback of BGM and SFX.
    Ensures BGM continuum across maps and handles volume scaling.

    Ambient sound architecture — propose / flush model:
    - Each active entity calls `propose_ambient(name, distance)` during update().
    - Multiple entities sharing the same sound name contribute their distance.
    - At end of frame, `flush_ambient()` resolves one audio channel per sound name,
      setting volume from the minimum (closest) distance proposed this frame.
    - Sounds with no proposals are automatically stopped.
    """
    def __init__(self):
        self.bgm_dir = os.path.join("assets", "audio", "bgm")
        self.sfx_dir = os.path.join("assets", "audio", "sfx")

        self.current_bgm: Optional[str] = None
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.ambient_sounds: Dict[str, pygame.mixer.Sound] = {}
        # Accumulates (sound_name → min_distance) proposals for the current frame.
        self._ambient_proposals: Dict[str, float] = {}
        self.is_muted: bool = False

        # Initialize mixer if not already done
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
                pygame.mixer.set_num_channels(32)
            except pygame.error as e:
                logging.warning(f"Audio system failed to initialize: {e}")
                self.is_enabled = False
                return

        self.is_enabled = True
        self.preload_sfx()
        logging.info("Audio Manager initialized.")

    def toggle_mute(self):
        """Toggle mute state for all audio."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0)
            for sound in self.sounds.values():
                sound.set_volume(0)
            for sound in self.ambient_sounds.values():
                sound.set_volume(0)
        else:
            self.update_volumes()
        logging.info(f"Audio mute state: {self.is_muted}")

    def preload_sfx(self):
        """Preload all SFX files into memory."""
        if not self.is_enabled or not os.path.exists(self.sfx_dir):
            return

        for file in os.listdir(self.sfx_dir):
            if file.endswith(".ogg"):
                name = file[:-4]  # Remove .ogg extension
                try:
                    path = os.path.join(self.sfx_dir, file)
                    self.sounds[name] = pygame.mixer.Sound(path)
                    self.sounds[name].set_volume(Settings.SFX_VOLUME)
                except pygame.error as e:
                    logging.warning(f"Failed to load SFX {file}: {e}")

    def play_bgm(self, name: str, loop: bool = True, fade_ms: int = 500):
        """
        Play a background music track.
        If the same track is requested, it does nothing to preserve the continuum.
        """
        if not self.is_enabled or not name:
            return

        if name == self.current_bgm and pygame.mixer.music.get_busy():
            return  # Continuum maintained

        filename = f"{name}.ogg"
        path = os.path.join(self.bgm_dir, filename)

        if not os.path.exists(path):
            logging.error(f"BGM file not found: {path}")
            return

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(Settings.BGM_VOLUME)
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self.current_bgm = name
            logging.info(f"Playing BGM: {name}")
        except pygame.error as e:
            logging.error(f"Failed to play BGM {name}: {e}")

    def stop_bgm(self, fade_ms: int = 500):
        """Stop background music with a fadeout."""
        if not self.is_enabled:
            return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
            self.current_bgm = None
            logging.info("Stopping BGM")

    def play_sfx(self, name: str, source_id: str = None, volume_multiplier: float = 1.0) -> bool:
        """
        Play a sound effect.
        Note: The source_id is provided to identify the emitter, preventing overlapping issues.
        Currently, Pygame handles overlap natively reasonably well, but source_id allows
        tracking specific object channels in the future if needed.
        """
        if not self.is_enabled or not name:
            return False

        sound = self.sounds.get(name)
        if not sound:
            # Try to load it if not preloaded
            filename = f"{name}.ogg"
            path = os.path.join(self.sfx_dir, filename)
            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(Settings.SFX_VOLUME * volume_multiplier)
                    self.sounds[name] = sound
                except pygame.error as e:
                    logging.error(f"Failed to load SFX {name}: {e}")
                    return False
            else:
                logging.warning(f"SFX file not found: {path}")
                return False

        # Stop the sound if it's currently playing to prevent flanging / overlapping from rapid triggers
        # By default, a Sound play() uses an available channel, but we can stop it first.
        sound.stop()
        sound.set_volume(Settings.SFX_VOLUME * volume_multiplier)
        sound.play()
        logging.debug(f"Playing SFX: {name} (source: {source_id})")
        return True

    def update_volumes(self):
        """Update volumes dynamically if Settings change."""
        if not self.is_enabled:
            return

        pygame.mixer.music.set_volume(Settings.BGM_VOLUME)
        for sound in self.sounds.values():
            sound.set_volume(Settings.SFX_VOLUME)

    # ── Ambient audio — propose / flush model ─────────────────────────────────

    def propose_ambient(self, name: str, distance: float) -> None:
        """Register an ambient source for this frame.

        Multiple entities can propose the same sound name; the minimum distance
        (closest active source) is retained. flush_ambient() applies the result
        once per frame.
        """
        if not name:
            return
        current_min = self._ambient_proposals.get(name, float('inf'))
        self._ambient_proposals[name] = min(current_min, distance)

    def flush_ambient(self) -> None:
        """Apply proposals accumulated this frame.

        - One audio channel per unique sound name.
        - Volume = falloff from the minimum (closest) proposed distance.
        - Sounds with no proposals are stopped automatically.
        Called once per game frame after all entity updates.
        """
        if not self.is_enabled:
            self._ambient_proposals.clear()
            return

        active_names = set(self._ambient_proposals.keys())

        for name, min_dist in self._ambient_proposals.items():
            # Start the loop if not already playing
            if name not in self.ambient_sounds:
                filename = f"{name}.ogg"
                path = os.path.join(self.sfx_dir, filename)
                if not os.path.exists(path):
                    logging.warning(f"Ambient SFX not found: {path}")
                    continue
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.play(loops=-1)
                    self.ambient_sounds[name] = sound
                    logging.debug(f"Ambient started: {name}")
                except pygame.error as e:
                    logging.error(f"Failed to start ambient {name}: {e}")
                    continue

            # Update volume from closest source
            sound = self.ambient_sounds.get(name)
            if sound and not self.is_muted:
                falloff = max(AMBIENT_MIN_FALLOFF,
                              1.0 - (min_dist / AMBIENT_MAX_DISTANCE))
                volume = Settings.SFX_VOLUME * AMBIENT_VOLUME_SCALE * falloff
                sound.set_volume(volume)

        # Stop channels that had no proposals this frame
        for name in list(self.ambient_sounds.keys()):
            if name not in active_names:
                self.ambient_sounds[name].stop()
                del self.ambient_sounds[name]
                logging.debug(f"Ambient stopped (no proposals): {name}")

        self._ambient_proposals.clear()

    def stop_ambient(self, source_id: str) -> None:
        """Explicitly stop a named ambient sound (e.g. on state transition)."""
        if source_id in self.ambient_sounds:
            self.ambient_sounds[source_id].stop()
            del self.ambient_sounds[source_id]
            logging.debug(f"Ambient stopped: {source_id}")

    def stop_all_ambients(self) -> None:
        """Stop every currently playing ambient sound."""
        for sound in self.ambient_sounds.values():
            sound.stop()
        self.ambient_sounds.clear()
        self._ambient_proposals.clear()
