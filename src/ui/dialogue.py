import pygame
import os
import logging
from src.config import Settings

class DialogueManager:
    """
    Handles dialogue box rendering, text wrapping, and state management.
    Recalibrated for assets/images/hud/05-textbox.png (2000x450 layout).
    """
    
    def __init__(self):
        self.is_active = False
        self.message = ""
        self.title = ""
        
        # UI Assets
        self.dialogue_box = None
        self.next_arrow = None
        
        # Scaling (based on HUD scale 0.5)
        self.scale = 0.5
        
        # Style
        self._shadow_color = (20, 20, 20)
        self._shadow_offset = 2
        self._text_color = (255, 255, 255)
        
        # Fonts
        self.font_title = None
        self.font_message = None
        
        self._load_assets()

    def _load_assets(self):
        """Load HUD assets and prepare fonts."""
        try:
            hud_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "hud")
            
            # 1. Dialogue Box (05-textbox.png)
            box_path = os.path.join(hud_dir, "05-textbox.png")
            if os.path.exists(box_path):
                img = pygame.image.load(box_path).convert_alpha()
                w, h = img.get_size()
                self.dialogue_box = pygame.transform.smoothscale(img, (int(w * self.scale), int(h * self.scale)))
            
            # 2. Next Arrow (06-cursor.png)
            arrow_path = os.path.join(hud_dir, "06-cursor.png")
            if os.path.exists(arrow_path):
                img = pygame.image.load(arrow_path).convert_alpha()
                w, h = img.get_size()
                self.next_arrow = pygame.transform.smoothscale(img, (int(w * self.scale), int(h * self.scale)))
            
            # 3. Fonts
            font_size_msg = int(34 * self.scale * 1.5)
            font_size_title = int(38 * self.scale * 1.5)
            
            self.font_message = pygame.font.SysFont("Arial", font_size_msg)
            self.font_title = pygame.font.SysFont("Arial", font_size_title, bold=True)
            
        except Exception as e:
            logging.error(f"Failed to load dialogue assets: {e}")

    def start_dialogue(self, text: str, title: str = ""):
        """Activate the dialogue system with a message and optional title."""
        self.message = text
        self.title = title
        self.is_active = True
        logging.info(f"Dialogue started: [{title}] {text[:30]}...")

    def advance(self):
        """Close the dialogue when the user interacts."""
        self.is_active = False
        self.message = ""
        self.title = ""

    def update(self, dt: float):
        """Update any dialogue animations (placeholder)."""
        pass

    def _draw_text_with_shadow(self, surface, text, pos, color, font, max_width, line_spacing=1.2):
        """Draw multiline text with shadow and custom line spacing."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        y_offset = 0
        line_height = font.get_linesize() * line_spacing
        for line in lines:
            # Shadow
            shadow_surf = font.render(line, True, self._shadow_color)
            surface.blit(shadow_surf, (pos[0] + self._shadow_offset, pos[1] + y_offset + self._shadow_offset))
            # Main text
            line_surface = font.render(line, True, color)
            surface.blit(line_surface, (pos[0], pos[1] + y_offset))
            y_offset += line_height

    def draw(self, screen):
        """Draw the dialogue box with title and message."""
        if not self.is_active or not self.dialogue_box:
            return
            
        # 1. Position box at bottom
        box_rect = self.dialogue_box.get_rect(midbottom=(Settings.WINDOW_WIDTH // 2, Settings.WINDOW_HEIGHT - 20))
        screen.blit(self.dialogue_box, box_rect)
        
        # Recalibrated offsets based on target image (scaled by 0.5)
        # Original target margins: Left ~280px -> 140px scaled
        content_margin_x = 140
        
        # 2. Draw Title (RED Zone)
        if self.title and self.font_title:
            title_x = box_rect.x + content_margin_x
            title_y = box_rect.y + 42
            
            # Shadow
            s_surf = self.font_title.render(self.title, True, self._shadow_color)
            screen.blit(s_surf, (title_x + self._shadow_offset, title_y + self._shadow_offset))
            # Title
            title_surf = self.font_title.render(self.title, True, self._text_color)
            screen.blit(title_surf, (title_x, title_y))
            
        # 3. Draw Message (BLUE Zone)
        if self.message and self.font_message:
            message_x = box_rect.x + content_margin_x
            message_y = box_rect.y + 100
            max_w = box_rect.width - (content_margin_x * 2)
            self._draw_text_with_shadow(screen, self.message, (message_x, message_y), self._text_color, self.font_message, max_w)
            
        # 4. Draw Next Arrow (GREEN Zone)
        if self.next_arrow:
            # Position: bottom-right of the text area
            arrow_x = box_rect.x + box_rect.width - content_margin_x + 10
            arrow_y = box_rect.y + 140
            screen.blit(self.next_arrow, (arrow_x, arrow_y))
