import os
import pygame
import logging
from src.config import Settings

HUD_SCALE: float = 0.4

class DialogueManager:
    """
    Manages the UI for game dialogues, including typewriter effect 
    and interaction cursor.
    """
    
    def __init__(self):
        self.is_active = False
        self.state = "IDLE" # IDLE, SCROLLING, WAITING
        
        # UI Assets
        self._textbox_surf = self._load_scaled_image("05-textbox.png")
        self._cursor_surf = self._load_scaled_image("06-cursor.png")
        
        # Text State
        self._full_text = ""
        self._current_text = ""
        self._char_index = 0.0
        self._type_speed = 0.05 # Seconds per character
        
        # Font setup
        self._font = self._load_font()
        self._text_color = (240, 235, 210) # Warm off-white from GameHUD
        self._shadow_color = (0, 0, 0)
        self._shadow_offset = 1
        
        # Position cache
        self._update_layout()

    def _load_scaled_image(self, filename: str) -> pygame.Surface:
        """Load and scale a HUD asset."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "HUD", filename)
        try:
            raw = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(
                raw, (int(raw.get_width() * HUD_SCALE), int(raw.get_height() * HUD_SCALE))
            )
        except (pygame.error, FileNotFoundError) as e:
            logging.error(f"DialogueManager: Could not load {filename}: {e}")
            # Fallback to a semi-transparent colored box if asset is missing
            fallback = pygame.Surface((800 * HUD_SCALE, 200 * HUD_SCALE), pygame.SRCALPHA)
            fallback.fill((30, 30, 30, 200))
            return fallback

    def _load_font(self) -> pygame.font.Font:
        """Reuse existing font loading logic."""
        for name in ("freesansbold", "dejavusans", "sans-serif", None):
            try:
                return pygame.font.SysFont(name, 16, bold=True)
            except Exception:
                continue
        return pygame.font.Font(None, 16)

    def _update_layout(self):
        """Pre-calculate screen positions for UI elements."""
        screen_w = Settings.WINDOW_WIDTH
        screen_h = Settings.WINDOW_HEIGHT
        
        box_w = self._textbox_surf.get_width()
        box_h = self._textbox_surf.get_height()
        
        # Position at the bottom with 20px margin (like clock)
        self._box_pos = ((screen_w - box_w) // 2, screen_h - box_h - 20)
        
        # Cursor at bottom right of the box
        self._cursor_pos = (
            self._box_pos[0] + box_w - self._cursor_surf.get_width() - 20,
            self._box_pos[1] + box_h - self._cursor_surf.get_height() - 20
        )
        
        # Text margins (internal to box)
        self._text_margin = 30

    def start_dialogue(self, text: str):
        """Initiate a new dialogue sequence."""
        if not text:
            return
        self._full_text = text
        self._current_text = ""
        self._char_index = 0.0
        self.is_active = True
        self.state = "SCROLLING"

    def close_dialogue(self):
        """End the dialogue and return control to the game."""
        self.is_active = False
        self.state = "IDLE"
        self._full_text = ""
        self._current_text = ""

    def advance(self):
        """Handle player action key during dialogue."""
        if self.state == "SCROLLING":
            # Skip to end of text
            self._current_text = self._full_text
            self._char_index = float(len(self._full_text))
            self.state = "WAITING"
        elif self.state == "WAITING":
            # Close dialogue
            self.close_dialogue()

    def update(self, dt: float):
        """Progress the typewriter effect."""
        if not self.is_active or self.state != "SCROLLING":
            return
            
        self._char_index += dt / self._type_speed
        idx = int(self._char_index)
        
        if idx >= len(self._full_text):
            self._current_text = self._full_text
            self.state = "WAITING"
        else:
            self._current_text = self._full_text[:idx]

    def _render_text_wrapped(self, surface: pygame.Surface, text: str, pos: tuple, max_width: int):
        """Simple text wrapping logic for the dialogue box."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            w, _ = self._font.size(test_line)
            if w < max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        y_offset = 0
        for line in lines:
            # Shadow
            s_surf = self._font.render(line, True, self._shadow_color)
            surface.blit(s_surf, (pos[0] + self._shadow_offset, pos[1] + y_offset + self._shadow_offset))
            # Main
            m_surf = self._font.render(line, True, self._text_color)
            surface.blit(m_surf, (pos[0], pos[1] + y_offset))
            y_offset += self._font.get_height() + 5

    def draw(self, screen: pygame.Surface):
        """Render the dialogue UI elements."""
        if not self.is_active:
            return
            
        # Draw Box
        screen.blit(self._textbox_surf, self._box_pos)
        
        # Draw Text
        text_x = self._box_pos[0] + self._text_margin
        text_y = self._box_pos[1] + self._text_margin
        max_w = self._textbox_surf.get_width() - (self._text_margin * 2)
        self._render_text_wrapped(screen, self._current_text, (text_x, text_y), max_w)
        
        # Draw Cursor if waiting
        if self.state == "WAITING":
            # Simple blink effect
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                screen.blit(self._cursor_surf, self._cursor_pos)
