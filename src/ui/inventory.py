import pygame
import os
import logging
from src.config import Settings

class InventoryUI:
    """
    RPG Inventory UI management.
    Handles rendering of the inventory background, slots, tabs, and character preview.
    """
    
    def __init__(self, player):
        self.player = player
        self.is_open = False
        self.active_tab = 0 # 0: Inventory, 1-3: Other
        self.font = self._load_font()
        
        # Load Assets
        self.bg = self._load_asset("01-inventory.png")
        self.slot_img = self._load_asset("03-inventory_slot.png")
        # User requested 08-active_tab.png but only 02 exists, using 02 as per previous correction
        self.active_tab_img = self._load_asset("02-active_tab.png")
        
        # UI Layout Constants (Detected from asset colors)
        self.bg_rect = self.bg.get_rect(center=(Settings.WINDOW_WIDTH // 2, Settings.WINDOW_HEIGHT // 2))
        
        # Tabs positions (RED zone) - Centers of the 4 red boxes
        # Moved Y from 128 to 135 to lower the highlight
        self.tab_rects = [
            self.active_tab_img.get_rect(center=(self.bg_rect.x + x, self.bg_rect.y + 135))
            for x in [734, 864, 993, 1122]
        ]
        
        # Equipment Slots (MAGENTA zone - Left) - Centers of boxes
        self.equipment_slots = {
            "HEAD": (self.bg_rect.x + 354, self.bg_rect.y + 160),
            "BAG": (self.bg_rect.x + 212, self.bg_rect.y + 290),
            "BELT": (self.bg_rect.x + 211, self.bg_rect.y + 405),
            "LEFT_HAND": (self.bg_rect.x + 242, self.bg_rect.y + 529),
            "UPPER_BODY": (self.bg_rect.x + 499, self.bg_rect.y + 291),
            "LOWER_BODY": (self.bg_rect.x + 498, self.bg_rect.y + 406),
            "RIGHT_HAND": (self.bg_rect.x + 469, self.bg_rect.y + 529),
            "SHOES": (self.bg_rect.x + 354, self.bg_rect.y + 549)
        }
        
        # Inventory Grid (BLUE zone - Right)
        # Bounds: (674, 184, 1182, 470). Spacing equalized to 72px.
        self.grid_start = (self.bg_rect.x + 715, self.bg_rect.y + 225) # Centering adjustment
        self.grid_cols = 7
        self.grid_rows = 4
        self.grid_spacing_x = 72
        self.grid_spacing_y = 72
        
        # Character Preview (ORANGE zone - Center Left)
        # avg(358, 311)
        self.char_preview_pos = (self.bg_rect.x + 358, self.bg_rect.y + 311)
        self.anim_timer = 0
        self.anim_frame = 0

    def _load_asset(self, filename):
        path = os.path.join("assets", "images", "ui", filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"InventoryUI: Could not load {filename}: {e}")
            # Return a colored surface as fallback
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255))
            return surf

    def _load_font(self):
        try:
            return pygame.font.SysFont("freesansbold", 24, bold=True)
        except:
            return pygame.font.Font(None, 24)

    def toggle(self):
        self.is_open = not self.is_open
        pygame.mouse.set_visible(self.is_open)
        logging.info(f"Inventory {'opened' if self.is_open else 'closed'}")

    def set_tab(self, index):
        if 0 <= index < 4:
            self.active_tab = index
        else:
            self.active_tab = 0

    def handle_input(self, event):
        if not self.is_open:
            return
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                mouse_pos = event.pos
                logging.debug(f"Inventory click at {mouse_pos}")
                
                # Check Tabs
                for i, rect in enumerate(self.tab_rects):
                    # Expand rect slightly for easier clicking if needed
                    if rect.collidepoint(mouse_pos):
                        logging.info(f"Tab {i} selected")
                        self.set_tab(i)
                        return
                
                # Check Equipment Slots
                for name, pos in self.equipment_slots.items():
                    rect = self.slot_img.get_rect(center=pos)
                    if rect.collidepoint(mouse_pos):
                        logging.info(f"Equipment slot clicked: {name}")
                        return
                
                # Check Grid Slots
                if self.active_tab == 0:
                    for row in range(self.grid_rows):
                        for col in range(self.grid_cols):
                            x = self.grid_start[0] + (col * self.grid_spacing_x)
                            y = self.grid_start[1] + (row * self.grid_spacing_y)
                            rect = self.slot_img.get_rect(center=(x, y))
                            if rect.collidepoint(mouse_pos):
                                index = row * self.grid_cols + col
                                logging.info(f"Inventory grid slot clicked: {index}")
                                return

    def update(self, dt):
        if not self.is_open:
            return
            
        # Update character preview animation (Idle)
        self.anim_timer += dt
        if self.anim_timer >= 0.15: # 150ms per frame
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4

    def draw(self, screen):
        if not self.is_open:
            return
            
        # 1. Draw Background
        screen.blit(self.bg, self.bg_rect)
        
        # 2. Draw Active Tab Highlight
        screen.blit(self.active_tab_img, self.tab_rects[self.active_tab])
        
        # 3. Draw Character Preview
        # Using Player's 'down' idle frames (index 0, 1, 2, 3 in row 0)
        # Assuming Player frames are loaded in Player.__init__
        try:
            char_image = self.player.frames[self.anim_frame]
            # Base size preview (no scaling)
            preview_rect = char_image.get_rect(center=self.char_preview_pos)
            screen.blit(char_image, preview_rect)
        except Exception as e:
            logging.error(f"InventoryUI: Character preview failed: {e}")

        # 4. Draw Equipment Slots
        for slot_pos in self.equipment_slots.values():
            slot_rect = self.slot_img.get_rect(center=slot_pos)
            screen.blit(self.slot_img, slot_rect)
            
        # 5. Draw Inventory Grid (only if tab 0 is active)
        if self.active_tab == 0:
            for row in range(self.grid_rows):
                for col in range(self.grid_cols):
                    x = self.grid_start[0] + (col * self.grid_spacing_x)
                    y = self.grid_start[1] + (row * self.grid_spacing_y)
                    # Center slot image on the calculated grid point
                    slot_rect = self.slot_img.get_rect(center=(x, y))
                    screen.blit(self.slot_img, slot_rect)

        # 6. Draw Stats (Info Zone - Bottom Right)
        self._draw_stats(screen)

    def _draw_stats(self, screen):
        # GREEN zone: avg(929, 551)
        stats_x = self.bg_rect.x + 695
        stats_y = self.bg_rect.y + 551
        
        # LVL (Left part of green bar)
        lvl_text = self.font.render(f"LVL {self.player.level}", True, (30, 30, 30)) # Darker text for bright green?
        lvl_rect = lvl_text.get_rect(midleft=(stats_x, stats_y))
        screen.blit(lvl_text, lvl_rect)
        
        # HP (Center)
        hp_text = self.font.render(f"HP {self.player.hp}/{self.player.max_hp}", True, (30, 30, 30))
        hp_rect = hp_text.get_rect(center=(self.bg_rect.x + 929, stats_y))
        screen.blit(hp_text, hp_rect)
        
        # GOLD (Right)
        gold_text = self.font.render(f"GOLD {self.player.gold}", True, (30, 30, 30))
        gold_rect = gold_text.get_rect(midright=(self.bg_rect.x + 1160, stats_y))
        screen.blit(gold_text, gold_rect)
