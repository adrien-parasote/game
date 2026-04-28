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
        self.item_font = pygame.font.SysFont("arial", 16, bold=True)
        self.icon_cache = {}
        
        # Load and Scale Assets
        self.bg = self._load_asset("01-inventory.png")
        self.slot_img = self._load_asset("03-inventory_slot.png")
        self.active_tab_img = self._load_asset("02-active_tab.png")
        self.hover_img = self._load_asset("04-inventory_slot_hover.png")
        self.pointer_img = self._load_asset("05-pointer.png")
        self.pointer_select_img = self._load_asset("06-pointer_select.png")
        
        # Urbanization: Scale down to fit 1280px screen (1344 -> 1200)
        target_width = 1200
        original_width = self.bg.get_width()
        self.scale_factor = target_width / original_width
        
        # Rescale all visual assets
        new_bg_size = (int(self.bg.get_width() * self.scale_factor), int(self.bg.get_height() * self.scale_factor))
        self.bg = pygame.transform.smoothscale(self.bg, new_bg_size)
        self.bg_rect = self.bg.get_rect(center=(Settings.WINDOW_WIDTH // 2, Settings.WINDOW_HEIGHT // 2))
        
        self.slot_img = pygame.transform.smoothscale(self.slot_img, 
            (int(self.slot_img.get_width() * self.scale_factor), int(self.slot_img.get_height() * self.scale_factor)))
        self.active_tab_img = pygame.transform.smoothscale(self.active_tab_img, 
            (int(self.active_tab_img.get_width() * self.scale_factor), int(self.active_tab_img.get_height() * self.scale_factor)))
        self.hover_img = pygame.transform.smoothscale(self.hover_img, 
            (int(self.hover_img.get_width() * self.scale_factor), int(self.hover_img.get_height() * self.scale_factor)))
        # Scale cursors while preserving aspect ratio
        target_h = Settings.CURSOR_SIZE
        ratio = target_h / 535 # 535 is original height
        target_w = int(309 * ratio) # 309 is original width
        
        self.pointer_img = pygame.transform.smoothscale(self.pointer_img, (target_w, target_h))
        self.pointer_select_img = pygame.transform.smoothscale(self.pointer_select_img, (target_w, target_h))
        
        # UI Layout Constants (Scaled from original 1344x704 coordinates)
        s = self.scale_factor
        
        # Tabs positions (RED zone)
        self.tab_rects = [
            self.active_tab_img.get_rect(center=(self.bg_rect.x + int(x * s), self.bg_rect.y + int(130 * s)))
            for x in [733, 863, 992, 1121]
        ]
        
        # Equipment Slots (MAGENTA zone - Left)
        self.equip_rect_side = int(78 * s)
        self.equipment_slots = {
            "HEAD": (self.bg_rect.x + int(354 * s), self.bg_rect.y + int(160 * s)),
            "BAG": (self.bg_rect.x + int(212 * s), self.bg_rect.y + int(290 * s)),
            "BELT": (self.bg_rect.x + int(211 * s), self.bg_rect.y + int(405 * s)),
            "LEFT_HAND": (self.bg_rect.x + int(242 * s), self.bg_rect.y + int(529 * s)),
            "UPPER_BODY": (self.bg_rect.x + int(499 * s), self.bg_rect.y + int(291 * s)),
            "LOWER_BODY": (self.bg_rect.x + int(498 * s), self.bg_rect.y + int(406 * s)),
            "RIGHT_HAND": (self.bg_rect.x + int(469 * s), self.bg_rect.y + int(529 * s)),
            "SHOES": (self.bg_rect.x + int(354 * s), self.bg_rect.y + int(549 * s))
        }
        
        # Inventory Grid (BLUE zone - Right)
        self.grid_start = (self.bg_rect.x + int(713 * s), self.bg_rect.y + int(219 * s))
        self.grid_cols = 7
        self.grid_rows = 4
        self.grid_spacing_x = int(72 * s)
        self.grid_spacing_y = int(72 * s)
        
        # Character Preview (ORANGE zone - Center Left)
        self.char_preview_pos = (self.bg_rect.x + int(358 * s), self.bg_rect.y + int(311 * s))
        self.char_name_pos = (self.bg_rect.x + int(358 * s), self.bg_rect.y + int(410 * s))
        
        self.anim_timer = 0
        self.anim_frame = 0
        self.preview_state = 'down'
        self.hovered_slot = None # None, ('equipment', name), or ('grid', index)

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
        # Custom pointer replaces system cursor
        pygame.mouse.set_visible(not self.is_open)
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
                    rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
                    rect.center = pos
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
                                
        elif event.type == pygame.KEYDOWN:
            # Change character preview direction
            if event.key == Settings.MOVE_UP:
                self.preview_state = 'up'
            elif event.key == Settings.MOVE_DOWN:
                self.preview_state = 'down'
            elif event.key == Settings.MOVE_LEFT:
                self.preview_state = 'left'
            elif event.key == Settings.MOVE_RIGHT:
                self.preview_state = 'right'

    def update_hover(self, mouse_pos):
        """Detect which slot is under the mouse."""
        self.hovered_slot = None
        
        # Check Equipment Slots
        for name, pos in self.equipment_slots.items():
            rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
            rect.center = pos
            if rect.collidepoint(mouse_pos):
                self.hovered_slot = ("equipment", name)
                return
        
        # Check Grid Slots (only if Tab 0)
        if self.active_tab == 0:
            for row in range(self.grid_rows):
                for col in range(self.grid_cols):
                    x = self.grid_start[0] + (col * self.grid_spacing_x)
                    y = self.grid_start[1] + (row * self.grid_spacing_y)
                    rect = self.slot_img.get_rect(center=(x, y))
                    if rect.collidepoint(mouse_pos):
                        self.hovered_slot = ("grid", row * self.grid_cols + col)
                        return

    def update(self, dt):
        if not self.is_open:
            return
            
        # Update character preview animation (Idle)
        self.anim_timer += dt
        if self.anim_timer >= 0.15: # 150ms per frame
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4
            
        # Update hover state
        self.update_hover(pygame.mouse.get_pos())

    def draw(self, screen):
        if not self.is_open:
            return
            
        s = self.scale_factor
        # 1. Draw Background
        screen.blit(self.bg, self.bg_rect)
        
        # 2. Draw Active Tab Highlight
        screen.blit(self.active_tab_img, self.tab_rects[self.active_tab])
        
        # 3. Draw Character Preview
        # Selecting row based on preview state (down: 0, left: 4, right: 8, up: 12)
        row_offsets = {'down': 0, 'left': 4, 'right': 8, 'up': 12}
        offset = row_offsets.get(self.preview_state, 0)
        
        try:
            char_image = self.player.frames[offset + self.anim_frame]
            # Base size preview (no scaling)
            preview_rect = char_image.get_rect(center=self.char_preview_pos)
            screen.blit(char_image, preview_rect)
        except Exception as e:
            logging.error(f"InventoryUI: Character preview failed: {e}")

        # Draw Player Name (Bottom of Orange zone)
        name_text = self.font.render("Player", True, (60, 40, 30)) # Dark brown for parchment style
        name_rect = name_text.get_rect(midbottom=self.char_name_pos)
        screen.blit(name_text, name_rect)

        # 4. Equipment Zones (Interaction only, no image as per request)
        # 5. Draw Inventory Grid (only if tab 0 is active)
        if self.active_tab == 0:
            for row in range(self.grid_rows):
                for col in range(self.grid_cols):
                    x = self.grid_start[0] + (col * self.grid_spacing_x)
                    y = self.grid_start[1] + (row * self.grid_spacing_y)
                    # Center slot image on the calculated grid point
                    slot_rect = self.slot_img.get_rect(center=(x, y))
                    screen.blit(self.slot_img, slot_rect)
                    
                    # Draw Item Icon if slot is occupied
                    index = row * self.grid_cols + col
                    item = self.player.inventory.get_item_at(index)
                    if item:
                        icon = self._get_item_icon(item.id)
                        if icon:
                            icon_rect = icon.get_rect(center=(x, y))
                            screen.blit(icon, icon_rect)
                        
                        # Draw Quantity if > 1
                        if item.quantity > 1:
                            qty_text = self.item_font.render(str(item.quantity), True, (255, 255, 255))
                            # Position: bottom right of slot
                            qty_rect = qty_text.get_rect(bottomright=(slot_rect.right - int(5 * s), slot_rect.bottom - int(5 * s)))
                            # Draw small background for legibility
                            bg_rect = qty_rect.inflate(4, 2)
                            pygame.draw.rect(screen, (30, 30, 30), bg_rect, border_radius=3)
                            screen.blit(qty_text, qty_rect)

        # 6. Draw Hover Highlight
        if self.hovered_slot:
            slot_type, value = self.hovered_slot
            if slot_type == "equipment":
                pos = self.equipment_slots[value]
                rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
                rect.center = pos
                # Gold border (brightening effect) with rounded corners
                pygame.draw.rect(screen, (255, 215, 0), rect, 3, border_radius=int(12 * s))
            elif slot_type == "grid":
                row = value // self.grid_cols
                col = value % self.grid_cols
                pos = (self.grid_start[0] + (col * self.grid_spacing_x),
                       self.grid_start[1] + (row * self.grid_spacing_y))
                hover_rect = self.hover_img.get_rect(center=pos)
                screen.blit(self.hover_img, hover_rect)

        # 7. Draw Stats or Item Info (Info Zone - Bottom Right)
        self._draw_info_zone(screen)

        # 8. Draw Custom Cursor (Always on top - must be last)
        mouse_pos = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            cursor_img = self.pointer_select_img
        else:
            cursor_img = self.pointer_img
        
        # Offset cursor slightly so tip is at mouse position
        screen.blit(cursor_img, mouse_pos)

    def _draw_info_zone(self, screen):
        """Draw either character stats or hovered item info in the green bar."""
        s = self.scale_factor
        stats_x = self.bg_rect.x + int(695 * s)
        stats_y = self.bg_rect.y + int(551 * s)
        
        # Check if we should show item info instead of stats
        if self.hovered_slot:
            slot_type, value = self.hovered_slot
            if slot_type == "grid":
                item = self.player.inventory.get_item_at(value)
                if item:
                    # Draw Item Name and Description
                    name_text = self.font.render(item.name, True, (30, 30, 30))
                    desc_text = self.item_font.render(item.description, True, (60, 60, 60))
                    
                    screen.blit(name_text, (stats_x, stats_y - int(10 * s)))
                    screen.blit(desc_text, (stats_x, stats_y + int(12 * s)))
                    return

        # Default: Draw Stats
        # LVL (Left part of green bar)
        lvl_text = self.font.render(f"LVL {self.player.level}", True, (30, 30, 30))
        lvl_rect = lvl_text.get_rect(midleft=(stats_x, stats_y))
        screen.blit(lvl_text, lvl_rect)
        
        # HP (Center)
        hp_text = self.font.render(f"HP {self.player.hp}/{self.player.max_hp}", True, (30, 30, 30))
        hp_rect = hp_text.get_rect(center=(self.bg_rect.x + int(929 * s), stats_y))
        screen.blit(hp_text, hp_rect)
        
        # GOLD (Right)
        gold_text = self.font.render(f"GOLD {self.player.gold}", True, (30, 30, 30))
        gold_rect = gold_text.get_rect(midright=(self.bg_rect.x + int(1160 * s), stats_y))
        screen.blit(gold_text, gold_rect)

    def _get_item_icon(self, item_id):
        """Load and cache item icon."""
        if item_id in self.icon_cache:
            return self.icon_cache[item_id]
        
        filename = f"{item_id}.png"
        path = os.path.join("assets", "images", "icons", filename)
        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                # Scale icon to fit slot (approx 48x48 base, scaled by s)
                target_size = int(48 * self.scale_factor)
                img = pygame.transform.smoothscale(img, (target_size, target_size))
                self.icon_cache[item_id] = img
                return img
        except Exception as e:
            logging.error(f"InventoryUI: Could not load icon {filename}: {e}")
        
        return None
