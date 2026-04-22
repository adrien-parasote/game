import os
import pygame
import logging
from src.config import Settings

# Scaling factor to fit 2000px wide asset into 1280px screen (1280/2000 = 0.64)
HUD_SCALE: float = 0.64

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
        
        # Font setup
        self._font = self._load_font()
        self._text_color = (240, 235, 210) # Warm off-white
        self._shadow_color = (20, 20, 20)
        self._shadow_offset = 2
        
        # Layout cache
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
            fallback = pygame.Surface((int(2000 * HUD_SCALE), int(450 * HUD_SCALE)), pygame.SRCALPHA)
            fallback.fill((30, 30, 30, 200))
            return fallback

    def _load_font(self) -> pygame.font.Font:
        """Load a readable pixel-art style font."""
        for name in ("Verdana", "Arial", "sans-serif", None):
            try:
                # Scaled size for 0.64 HUD
                return pygame.font.SysFont(name, 22, bold=True)
            except Exception:
                continue
        return pygame.font.Font(None, 22)

    def _update_layout(self):
        """Pre-calculate screen positions for UI elements based on 2000x450 reference."""
        screen_w = Settings.WINDOW_WIDTH
        screen_h = Settings.WINDOW_HEIGHT
        
        box_w = self._textbox_surf.get_width()
        box_h = self._textbox_surf.get_height()
        
        # Box is fixed at bottom center
        self._box_pos = (0, screen_h - box_h)
        
        # BLUE ZONE: Message (x=230, y=80, w=1500, h=300 in raw)
        self._message_rect = pygame.Rect(
            self._box_pos[0] + int(230 * HUD_SCALE),
            self._box_pos[1] + int(80 * HUD_SCALE),
            int(1500 * HUD_SCALE),
            int(300 * HUD_SCALE)
        )
        
        # GREEN ZONE: Arrow (x=1750, y=320 in raw)
        self._cursor_pos = (
            self._box_pos[0] + int(1750 * HUD_SCALE),
            self._box_pos[1] + int(320 * HUD_SCALE)
        )

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
        """End the dialogue."""
        self.is_active = False
        self.state = "IDLE"

    def advance(self):
        """Action key handler."""
        if self.state == "SCROLLING":
            self._current_text = self._full_text
            self._char_index = float(len(self._full_text))
            self.state = "WAITING"
        elif self.state == "WAITING":
            self.close_dialogue()

    def update(self, dt: float):
        """Progress typewriter effect using Settings.TEXT_SPEED."""
        if not self.is_active or self.state != "SCROLLING":
            return
            
        # Use settings value
        speed = getattr(Settings, "TEXT_SPEED", 0.05)
        self._char_index += dt / speed
        idx = int(self._char_index)
        
        if idx >= len(self._full_text):
            self._current_text = self._full_text
            self.state = "WAITING"
        else:
            self._current_text = self._full_text[:idx]

    def _render_text_wrapped(self, surface: pygame.Surface, text: str, rect: pygame.Rect):
        """Render wrapped text within a target rectangle."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            w, _ = self._font.size(test_line)
            if w < rect.width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        line_h = self._font.get_height() + 4
        for i, line in enumerate(lines):
            y = rect.y + i * line_h
            if y + line_h > rect.bottom: break # Truncate if too many lines
            
            # Shadow
            s_surf = self._font.render(line, True, self._shadow_color)
            surface.blit(s_surf, (rect.x + self._shadow_offset, y + self._shadow_offset))
            # Main
            m_surf = self._font.render(line, True, self._text_color)
            surface.blit(m_surf, (rect.x, y))

    def draw(self, screen: pygame.Surface):
        """Render dialogue UI."""
        if not self.is_active:
            return
            
        # 1. Background Box
        screen.blit(self._textbox_surf, self._box_pos)
        
        # 2. Wrapped Message
        self._render_text_wrapped(screen, self._current_text, self._message_rect)
        
        # 3. Blinking Cursor
        if self.state == "WAITING":
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                screen.blit(self._cursor_surf, self._cursor_pos)
