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
        self.displayed_text = ""
        self.text_index = 0.0
        # Settings.TEXT_SPEED is delay per character (seconds); convert to chars per second
        self.typewriter_speed = 1.0 / getattr(Settings, "TEXT_SPEED", 0.05)
        # Rolling text state
        self._wrapped_lines: list[str] = []  # lines currently visible
        self._max_lines: int = 0  # will be computed during draw

        
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
            self.font_title = pygame.font.SysFont("Arial", font_size_title)
            
        except Exception as e:
            logging.error(f"Failed to load dialogue assets: {e}")

    def start_dialogue(self, text: str, title: str = ""):
        """Activate the dialogue system with a message and optional title."""
        self.message = text
        self.title = title
        self.is_active = True
        self.displayed_text = ""
        self.text_index = 0.0
        self._wrapped_lines = []
        logging.info(f"Dialogue started: [{title}] {text[:30]}...")

    def advance(self):
        """Close the dialogue when the user interacts, or skip typewriter."""
        if self.text_index < len(self.message):
            # Skip to end of text
            self.text_index = float(len(self.message))
            self.displayed_text = self.message
        else:
            self.is_active = False
            self.message = ""
            self.title = ""
            self.displayed_text = ""

    def update(self, dt: float):
        """Update typewriter animation and manage rolling lines."""
        if self.is_active and self.text_index < len(self.message):
            # Advance typing
            self.text_index += self.typewriter_speed * dt
            current_len = int(self.text_index)
            if current_len > len(self.message):
                current_len = len(self.message)
            self.displayed_text = self.message[:current_len]
        # Store dt for possible future use
        self._last_dt = dt

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

        if self.title and self.font_title:
            title_x = box_rect.x + content_margin_x
            title_y = box_rect.y + 42

            # Shadow
            s_surf = self.font_title.render(self.title, True, self._shadow_color)
            screen.blit(s_surf, (title_x + self._shadow_offset, title_y + self._shadow_offset))
            # Title
            title_surf = self.font_title.render(self.title, True, self._text_color)
            screen.blit(title_surf, (title_x, title_y))

            # Message starts below title
            message_y = box_rect.y + 90
        else:
            # No title, message takes full height starting from title's y-position
            message_y = box_rect.y + 42

        # 3. Draw Message
        message_x = box_rect.x + content_margin_x
        max_w = box_rect.width - (content_margin_x * 2)
        # Compute available vertical space for text
        available_h = box_rect.height - (message_y - box_rect.y) - 40 # 40px bottom margin
        
        if self.font_message:
            line_spacing = 1.2
            line_height = self.font_message.get_linesize() * line_spacing
            max_lines = int(available_h // line_height)
            
            # Wrap displayed text
            words = self.displayed_text.split(' ')
            lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word]) if current_line else word
                if self.font_message.size(test_line)[0] <= max_w:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            # Rolling effect: keep only the last N lines that fit
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
            
            # Draw lines
            y_offset = 0
            for line in lines:
                # Shadow
                shadow_surf = self.font_message.render(line, True, self._shadow_color)
                screen.blit(shadow_surf, (message_x + self._shadow_offset, message_y + y_offset + self._shadow_offset))
                # Main text
                line_surf = self.font_message.render(line, True, self._text_color)
                screen.blit(line_surf, (message_x, message_y + y_offset))
                y_offset += line_height

        # 4. Draw Next Arrow
        if self.next_arrow and self.text_index >= len(self.message):
            arrow_x = box_rect.x + box_rect.width - content_margin_x + 10
            arrow_y = box_rect.y + 140
            screen.blit(self.next_arrow, (arrow_x, arrow_y))
