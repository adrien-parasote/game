import pygame
import os
import logging
from typing import Dict, Optional
from src.config import Settings

class AudioManager:
    """
    Handles playback of BGM and SFX.
    Ensures BGM continuum across maps and handles volume scaling.
    """
    def __init__(self):
        self.bgm_dir = os.path.join("assets", "audio", "bgm")
        self.sfx_dir = os.path.join("assets", "audio", "sfx")
        
        self.current_bgm: Optional[str] = None
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.is_muted: bool = False
        
        # Initialize mixer if not already done
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
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

    def play_sfx(self, name: str, source_id: str = None):
        """
        Play a sound effect.
        Note: The source_id is provided to identify the emitter, preventing overlapping issues.
        Currently, Pygame handles overlap natively reasonably well, but source_id allows
        tracking specific object channels in the future if needed.
        """
        if not self.is_enabled or not name:
            return
            
        sound = self.sounds.get(name)
        if not sound:
            # Try to load it if not preloaded
            filename = f"{name}.ogg"
            path = os.path.join(self.sfx_dir, filename)
            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(Settings.SFX_VOLUME)
                    self.sounds[name] = sound
                except pygame.error as e:
                    logging.error(f"Failed to load SFX {name}: {e}")
                    return
            else:
                logging.error(f"SFX file not found: {path}")
                return
        
        # Stop the sound if it's currently playing to prevent flanging / overlapping from rapid triggers
        # By default, a Sound play() uses an available channel, but we can stop it first.
        sound.stop()
        sound.set_volume(Settings.SFX_VOLUME)
        sound.play()
        logging.debug(f"Playing SFX: {name} (source: {source_id})")

    def update_volumes(self):
        """Update volumes dynamically if Settings change."""
        if not self.is_enabled:
            return
            
        pygame.mixer.music.set_volume(Settings.BGM_VOLUME)
        for sound in self.sounds.values():
            sound.set_volume(Settings.SFX_VOLUME)
