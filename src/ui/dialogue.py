import pygame
import os
import logging
from src.config import Settings
from src.engine.asset_manager import AssetManager

class DialogueManager:
    """
    Handles dialogue box rendering, text wrapping, and state management.
    Optimized for performance by pre-calculating text wrapping.
    """
    
    def __init__(self):
        self.is_active = False
        self.message = ""
        self.title = ""
        self.displayed_text = ""
        
        # Settings.TEXT_SPEED is delay per character (seconds); convert to chars per second
        self.typewriter_speed = 1.0 / getattr(Settings, "TEXT_SPEED", 0.05)
        
        # Paginated text state
        self._pages: list[list[str]] = []  # List of pages, each page is a list of lines
        self._page_surfaces: list[pygame.Surface] = [] # Pre-rendered surface for each page
        self._current_page_index = 0
        self._page_char_index = 0.0
        self._is_page_complete = False
        
        # UI Assets
        self.dialogue_box = None
        self.next_arrow = None
        
        # Scaling (based on HUD scale 0.5)
        self.scale = 0.5
        
        # Style
        self._shadow_color = (180, 170, 150) # Light shadow for parchment
        self._shadow_offset = 1
        self._text_color = (60, 40, 30)      # Dark brown for high contrast on parchment
        
        # Fonts
        self.font_title = None
        self.font_message = None
        
        self._load_assets()

    def _load_assets(self):
        """Load HUD assets and prepare fonts."""
        try:
            hud_dir = os.path.join("assets", "images", "hud")
            
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
            am = AssetManager()
            self.font_message = am.get_font(Settings.FONT_NARRATIVE, int(Settings.FONT_SIZE_NARRATIVE * 1.5)) # Larger for dialogue
            self.font_title = am.get_font(Settings.FONT_NOBLE, int(Settings.FONT_SIZE_NOBLE * 1.5)) # Larger for dialogue
            
        except Exception as e:
            logging.error(f"Failed to load dialogue assets: {e}")

    def _paginate(self, text: str):
        """Split text into pages based on font metrics and box size."""
        if not self.font_message or not self.dialogue_box:
            self._pages = [[text]] if text else []
            return

        # Fixed layout metrics
        content_margin_x = 140
        max_w = self.dialogue_box.get_width() - (content_margin_x * 2)
        
        # Available height calculation
        message_y_offset = 90 if self.title else 42
        available_h = self.dialogue_box.get_height() - message_y_offset - 40 
        
        line_spacing = 1.2
        line_height = self.font_message.get_linesize() * line_spacing
        max_lines = max(1, int(available_h // line_height))
        
        # 1. Wrap all text into lines
        all_lines = []
        words = text.split(' ')
        current_line_words = []
        
        for word in words:
            test_line = ' '.join(current_line_words + [word]) if current_line_words else word
            if self.font_message.size(test_line)[0] <= max_w:
                current_line_words.append(word)
            else:
                all_lines.append(' '.join(current_line_words))
                current_line_words = [word]
        if current_line_words:
            all_lines.append(' '.join(current_line_words))
            
        # 2. Group lines into pages and pre-render them
        self._pages = []
        self._page_surfaces = []
        for i in range(0, len(all_lines), max_lines):
            page_lines = all_lines[i:i + max_lines]
            self._pages.append(page_lines)
            
            # Pre-render the full page to a transparent surface
            surf_h = int(len(page_lines) * line_height)
            page_surf = pygame.Surface((max_w, surf_h), pygame.SRCALPHA)
            
            y_offset = 0
            for line in page_lines:
                # Shadow
                shadow_surf = self.font_message.render(line, True, self._shadow_color)
                page_surf.blit(shadow_surf, (self._shadow_offset, y_offset + self._shadow_offset))
                # Main text
                line_surf = self.font_message.render(line, True, self._text_color)
                page_surf.blit(line_surf, (0, y_offset))
                y_offset += line_height
            
            self._page_surfaces.append(page_surf)

    def start_dialogue(self, text: str, title: str = ""):
        """Activate the dialogue system with a message and optional title."""
        if not text:
            self.is_active = False
            return

        self.message = text
        self.title = title
        self.is_active = True
        self.displayed_text = ""
        self._current_page_index = 0
        self._page_char_index = 0.0
        self._is_page_complete = False
        
        self._paginate(text)
        
        if not self._pages:
            self.is_active = False
            return
            
        logging.info(f"Dialogue started: [{title}] {text[:30]}... ({len(self._pages)} pages)")

    def advance(self):
        """Handle dialogue progression: skip typing, next page, or close."""
        if not self.is_active:
            return

        # 1. If currently typing, skip to end of page
        if not self._is_page_complete:
            current_page_text = " ".join(self._pages[self._current_page_index])
            self._page_char_index = float(len(current_page_text))
            self.displayed_text = current_page_text
            self._is_page_complete = True
            return

        # 2. If page is complete, check if there are more pages
        if self._current_page_index < len(self._pages) - 1:
            self._current_page_index += 1
            self._page_char_index = 0.0
            self._is_page_complete = False
            self.displayed_text = ""
        else:
            # 3. Last page finished, close dialogue
            self.is_active = False
            self.message = ""
            self.title = ""
            self._pages = []
            self._page_surfaces = []

    def update(self, dt: float):
        """Update typewriter animation for the current page."""
        if not self.is_active or self._is_page_complete:
            return
            
        current_page_text = " ".join(self._pages[self._current_page_index])
        
        if self._page_char_index < len(current_page_text):
            self._page_char_index += self.typewriter_speed * dt
            current_len = int(self._page_char_index)
            if current_len >= len(current_page_text):
                current_len = len(current_page_text)
                self._is_page_complete = True
            self.displayed_text = current_page_text[:current_len]
        else:
            self._is_page_complete = True

    def draw(self, screen):
        """Draw the dialogue box and paginated text."""
        if not self.is_active or not self.dialogue_box:
            return
            
        # 1. Position box at bottom
        box_rect = self.dialogue_box.get_rect(midbottom=(Settings.WINDOW_WIDTH // 2, Settings.WINDOW_HEIGHT - 20))
        screen.blit(self.dialogue_box, box_rect)
        
        content_margin_x = 140

        # 2. Draw Title
        if self.title and self.font_title:
            title_x = box_rect.x + content_margin_x
            title_y = box_rect.y + 42
            # Shadow
            s_surf = self.font_title.render(self.title, True, self._shadow_color)
            screen.blit(s_surf, (title_x + self._shadow_offset, title_y + self._shadow_offset))
            # Title
            title_surf = self.font_title.render(self.title, True, self._text_color)
            screen.blit(title_surf, (title_x, title_y))
            message_y = box_rect.y + 90
        else:
            message_y = box_rect.y + 42

        # 3. Draw Message Lines for Current Page (Optimized)
        if self.font_message and self._page_surfaces:
            message_x = box_rect.x + content_margin_x
            
            page_surf = self._page_surfaces[self._current_page_index]
            
            if self._is_page_complete:
                screen.blit(page_surf, (message_x, message_y))
            else:
                # Typewriter effect: Use a clipping rectangle to only reveal characters typed so far
                # Wait, clipping by width won't work perfectly for multi-line text because we need to reveal
                # line by line. Let's do it by rendering only the visible lines from the page_surf,
                # plus the currently typing line.
                
                line_spacing = 1.2
                line_height = self.font_message.get_linesize() * line_spacing
                current_page_lines = self._pages[self._current_page_index]
                chars_to_show = len(self.displayed_text)
                accumulated_chars = 0
                
                y_offset = 0
                for line in current_page_lines:
                    if accumulated_chars >= chars_to_show:
                        break
                    
                    line_len_with_space = len(line) + 1
                    
                    if accumulated_chars + len(line) <= chars_to_show:
                        # Full line is visible: blit this horizontal strip from the pre-rendered page_surf
                        strip_rect = pygame.Rect(0, int(y_offset), page_surf.get_width(), int(line_height))
                        screen.blit(page_surf, (message_x, message_y + y_offset), strip_rect)
                        accumulated_chars += line_len_with_space
                    else:
                        # Partial line: render dynamically just for this line
                        chars_in_this_line = chars_to_show - accumulated_chars
                        text_to_draw = line[:chars_in_this_line]
                        if text_to_draw:
                            shadow_surf = self.font_message.render(text_to_draw, True, self._shadow_color)
                            screen.blit(shadow_surf, (message_x + self._shadow_offset, message_y + y_offset + self._shadow_offset))
                            line_surf = self.font_message.render(text_to_draw, True, self._text_color)
                            screen.blit(line_surf, (message_x, message_y + y_offset))
                        accumulated_chars = chars_to_show
                    
                    y_offset += line_height

        # 4. Draw Next Arrow when page is complete
        if self.next_arrow and self._is_page_complete:
            arrow_x = box_rect.x + box_rect.width - content_margin_x + 10
            arrow_y = box_rect.y + 140
            screen.blit(self.next_arrow, (arrow_x, arrow_y))
