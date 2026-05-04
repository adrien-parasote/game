import pygame
import os
import json
import logging
from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.i18n import I18nManager
from src.ui.inventory_constants import *
from src.ui.ui_colors import (
    COLOR_TEXT_STONE, COLOR_HIGHLIGHT_GOLD, COLOR_DEBUG_MISSING,
)

class InventoryUI:
    """
    RPG Inventory UI management.
    Handles rendering of the inventory background, slots, tabs, and character preview.
    """
    
    def __init__(self, player):
        self.player = player
        self.is_open = False
        self.active_tab = 0 # 0: Inventory, 1-3: Other
        
        am = AssetManager()
        self.noble_font = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        self.narrative_font = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        self.tech_font = am.get_font(Settings.FONT_TECH, Settings.FONT_SIZE_TECH)
        
        self.icon_cache = {}
        
        # Load and Scale Assets
        self.bg = self._load_asset(INV_ASSET_BG)
        self.slot_img = self._load_asset(INV_ASSET_SLOT)
        self.active_tab_img = self._load_asset(INV_ASSET_TAB)
        self.hover_img = self._load_asset(INV_ASSET_HOVER)
        self.pointer_img = self._load_asset(INV_ASSET_POINTER)
        self.pointer_select_img = self._load_asset(INV_ASSET_POINTER_SELECT)
        
        # Urbanization: Scale down to fit 1280px screen (1344 -> 1200)
        original_width = self.bg.get_width()
        self.scale_factor = INV_TARGET_WIDTH / original_width
        
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
        ratio = target_h / INV_ORIGINAL_CURSOR_HEIGHT
        target_w = int(INV_ORIGINAL_CURSOR_WIDTH * ratio)
        
        self.pointer_img = pygame.transform.smoothscale(self.pointer_img, (target_w, target_h))
        self.pointer_select_img = pygame.transform.smoothscale(self.pointer_select_img, (target_w, target_h))
        
        # UI Layout Constants
        s = self.scale_factor
        
        # Tabs positions (RED zone)
        self.tab_rects = [
            self.active_tab_img.get_rect(center=(self.bg_rect.x + int(x * s), self.bg_rect.y + int(INV_TAB_Y * s)))
            for x in INV_TAB_X_POSITIONS
        ]
        
        # Equipment Slots (MAGENTA zone - Left)
        self.equip_rect_side = int(INV_EQUIP_RECT_SIDE * s)
        self.equipment_slots = {
            k: (self.bg_rect.x + int(v[0] * s), self.bg_rect.y + int(v[1] * s))
            for k, v in INV_EQUIPMENT_SLOTS.items()
        }
        
        # Inventory Grid (BLUE zone - Right)
        self.grid_start = (self.bg_rect.x + int(INV_GRID_START[0] * s), self.bg_rect.y + int(INV_GRID_START[1] * s))
        self.grid_cols = INV_GRID_COLS
        self.grid_rows = INV_GRID_ROWS
        self.grid_spacing_x = int(INV_GRID_SPACING_X * s)
        self.grid_spacing_y = int(INV_GRID_SPACING_Y * s)
        
        # Character Preview (ORANGE zone - Center Left)
        self.char_preview_pos = (self.bg_rect.x + int(INV_CHAR_PREVIEW_POS[0] * s), self.bg_rect.y + int(INV_CHAR_PREVIEW_POS[1] * s))
        self.char_name_pos = (self.bg_rect.x + int(INV_CHAR_NAME_POS[0] * s), self.bg_rect.y + int(INV_CHAR_NAME_POS[1] * s))
        
        self.anim_timer = 0
        self.anim_frame = 0
        self.preview_state = 'down'
        self.hovered_slot = None # None, ('equipment', name), or ('grid', index)
        
        # Drag & Drop State
        self._dragging_item = None
        self._drag_pos = (0, 0)

    def _load_asset(self, filename):
        path = os.path.join("assets", "images", "ui", filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"InventoryUI: Could not load {filename}: {e}")
            surf = pygame.Surface((INV_PLACEHOLDER_SIZE, INV_PLACEHOLDER_SIZE))
            surf.fill(COLOR_DEBUG_MISSING)
            return surf

    def toggle(self):
        self.is_open = not self.is_open
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
                    if rect.collidepoint(mouse_pos):
                        logging.info(f"Tab {i} selected")
                        self.set_tab(i)
                        return
                
                # Drag Start
                if self.hovered_slot:
                    slot_type, value = self.hovered_slot
                    if slot_type == "equipment":
                        item = self.player.inventory.equipment.get(value)
                        if item:
                            self._dragging_item = {
                                "source": "equipment",
                                "name": value,
                                "item_id": item.id,
                                "quantity": item.quantity,
                                "icon": item.icon if item.icon else f"{item.id}.png"
                            }
                            self._drag_pos = mouse_pos
                            return
                    elif slot_type == "grid":
                        item = self.player.inventory.get_item_at(value)
                        if item:
                            self._dragging_item = {
                                "source": "grid",
                                "index": value,
                                "item_id": item.id,
                                "quantity": item.quantity,
                                "icon": item.icon if item.icon else f"{item.id}.png"
                            }
                            self._drag_pos = mouse_pos
                            return
                                
        elif event.type == pygame.MOUSEMOTION:
            if self._dragging_item:
                self._drag_pos = event.pos
                
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._dragging_item:
                self.update_hover(event.pos) # ensure accurate drop target
                if self.hovered_slot:
                    slot_type, value = self.hovered_slot
                    if slot_type == "equipment":
                        self._transfer_dragged_to_equipment(value)
                    elif slot_type == "grid":
                        self._transfer_dragged_to_grid(value)
                self._dragging_item = None
                
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

    def _transfer_dragged_to_equipment(self, target_name: str) -> None:
        """Transfer dragged item to the equipment slot."""
        if not self._dragging_item or not self.player:
            return
            
        source = self._dragging_item["source"]
        inv = self.player.inventory
        
        if source == "equipment":
            src_name = self._dragging_item["name"]
            if src_name == target_name:
                return
            
            src_item = inv.unequip_item(src_name)
            if not src_item: return
            
            swapped = inv.equip_item(target_name, src_item)
            if swapped == src_item:
                # Failed to equip, put back
                inv.equip_item(src_name, src_item)
            elif swapped is not None:
                # Put swapped item back in source slot if possible
                swapped_back = inv.equip_item(src_name, swapped)
                if swapped_back == swapped:
                    # Couldn't swap back, add to grid as fallback
                    inv.add_item(swapped.id, swapped.quantity)
        else:
            # Source is grid
            src_idx = self._dragging_item["index"]
            src_item = inv.slots[src_idx]
            if not src_item: return
            
            inv.slots[src_idx] = None
            
            swapped = inv.equip_item(target_name, src_item)
            if swapped == src_item:
                # Failed to equip, return to grid
                inv.slots[src_idx] = src_item
            elif swapped is not None:
                # Equip successful, we got a swapped item. Put it in grid
                inv.slots[src_idx] = swapped

    def _transfer_dragged_to_grid(self, target_idx: int) -> None:
        """Transfer dragged item to a grid slot."""
        if not self._dragging_item or not self.player:
            return
            
        item_id = self._dragging_item["item_id"]
        qty = self._dragging_item["quantity"]
        source = self._dragging_item["source"]
        
        inv = self.player.inventory
        target_slot = inv.slots[target_idx]
        
        if source == "grid":
            src_idx = self._dragging_item["index"]
            if src_idx == target_idx:
                return
                
            if target_slot is None:
                inv.slots[target_idx] = inv.slots[src_idx]
                inv.slots[src_idx] = None
            elif target_slot.id == item_id:
                can_add = min(qty, target_slot.stack_max - target_slot.quantity)
                target_slot.quantity += can_add
                inv.slots[src_idx].quantity -= can_add
                if inv.slots[src_idx].quantity <= 0:
                    inv.slots[src_idx] = None
            else:
                inv.slots[target_idx], inv.slots[src_idx] = inv.slots[src_idx], inv.slots[target_idx]
        else:
            # Source is equipment
            src_name = self._dragging_item["name"]
            src_item = inv.equipment.get(src_name)
            if not src_item: return
            
            if target_slot is None:
                inv.slots[target_idx] = src_item
                inv.equipment[src_name] = None
            elif target_slot.id == item_id:
                can_add = min(qty, target_slot.stack_max - target_slot.quantity)
                target_slot.quantity += can_add
                src_item.quantity -= can_add
                if src_item.quantity <= 0:
                    inv.equipment[src_name] = None
            else:
                # Swap target into equipment
                inv.slots[target_idx] = None
                swapped = inv.equip_item(src_name, target_slot)
                if swapped == target_slot:
                    # Failed to equip target item to this slot, abort transfer
                    inv.slots[target_idx] = target_slot
                else:
                    # Put the previously equipped item into the grid
                    inv.slots[target_idx] = src_item

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
        screen.blit(self.bg, self.bg_rect)
        screen.blit(self.active_tab_img, self.tab_rects[self.active_tab])

        # Character preview
        row_offsets = {'down': 0, 'left': 4, 'right': 8, 'up': 12}
        offset = row_offsets.get(self.preview_state, 0)
        try:
            char_image = self.player.frames[offset + self.anim_frame]
            screen.blit(char_image, char_image.get_rect(center=self.char_preview_pos))
        except Exception as e:
            logging.error(f"InventoryUI: Character preview failed: {e}")

        name_text = self.noble_font.render("Player", True, COLOR_TEXT_STONE)
        screen.blit(name_text, name_text.get_rect(midbottom=self.char_name_pos))

        if self.active_tab == 0:
            self._draw_grid(screen, s)

        self._draw_equipment_slots(screen, s)
        self._draw_info_zone(screen)
        self._draw_dragged_item(screen)
        self._draw_cursor(screen)

    def _draw_grid(self, screen, s):
        """Draw inventory grid slots and item icons for the active tab."""
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = self.grid_start[0] + (col * self.grid_spacing_x)
                y = self.grid_start[1] + (row * self.grid_spacing_y)
                slot_rect = self.slot_img.get_rect(center=(x, y))
                screen.blit(self.slot_img, slot_rect)

                index = row * self.grid_cols + col
                item = self.player.inventory.get_item_at(index)
                if not item:
                    continue
                # Skip if dragged
                if self._dragging_item and self._dragging_item["source"] == "grid" and self._dragging_item["index"] == index:
                    continue
                icon = self._get_item_icon(item.icon if item.icon else f"{item.id}.png")
                if icon:
                    screen.blit(icon, icon.get_rect(center=(x, y)))
                if item.quantity > 1:
                    qty_text = self.tech_font.render(f"x{item.quantity}", True, COLOR_TEXT_STONE)
                    margin = int(8 * s)
                    screen.blit(qty_text, qty_text.get_rect(bottomright=(slot_rect.right - margin, slot_rect.bottom - margin)))

        if self.hovered_slot and self.hovered_slot[0] == "grid":
            _, value = self.hovered_slot
            col, row = value % self.grid_cols, value // self.grid_cols
            pos = (self.grid_start[0] + col * self.grid_spacing_x,
                   self.grid_start[1] + row * self.grid_spacing_y)
            screen.blit(self.hover_img, self.hover_img.get_rect(center=pos))

    def _draw_equipment_slots(self, screen, s):
        """Draw equipped items and gold border on hovered equipment slot."""
        for name, pos in self.equipment_slots.items():
            item = self.player.inventory.equipment.get(name)
            rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
            rect.center = pos
            
            # Draw item if equipped
            if item and not (self._dragging_item and self._dragging_item["source"] == "equipment" and self._dragging_item["name"] == name):
                icon = self._get_item_icon(item.icon if item.icon else f"{item.id}.png")
                if icon:
                    screen.blit(icon, icon.get_rect(center=pos))
                if item.quantity > 1:
                    qty_text = self.tech_font.render(f"x{item.quantity}", True, COLOR_TEXT_STONE)
                    margin = int(8 * s)
                    screen.blit(qty_text, qty_text.get_rect(bottomright=(rect.right - margin, rect.bottom - margin)))
        
        if not self.hovered_slot or self.hovered_slot[0] != "equipment":
            return
        _, name = self.hovered_slot
        pos = self.equipment_slots[name]
        rect = pygame.Rect(0, 0, self.equip_rect_side, self.equip_rect_side)
        rect.center = pos
        pygame.draw.rect(screen, COLOR_HIGHLIGHT_GOLD, rect, INV_DRAG_HIGHLIGHT_BORDER, border_radius=int(INV_DRAG_BORDER_RADIUS_BASE * s))

    def _draw_dragged_item(self, screen):
        """Draw the item currently being dragged."""
        if not self._dragging_item:
            return
            
        icon = self._get_item_icon(self._dragging_item["icon"])
        if icon:
            rect = icon.get_rect(center=self._drag_pos)
            screen.blit(icon, rect)
            
        qty = self._dragging_item["quantity"]
        if qty > 1:
            qty_text = self.tech_font.render(f"x{qty}", True, COLOR_TEXT_STONE)
            # align to bottom right of the icon rect
            margin = int(8 * self.scale_factor)
            screen.blit(qty_text, qty_text.get_rect(bottomright=(rect.right - margin, rect.bottom - margin)))

    def _draw_cursor(self, screen):
        """Draw custom cursor on top of all UI elements."""
        mouse_pos = pygame.mouse.get_pos()
        cursor_img = self.pointer_select_img if pygame.mouse.get_pressed()[0] else self.pointer_img
        screen.blit(cursor_img, mouse_pos)

    def _draw_info_zone(self, screen):
        """Draw either character stats or hovered item info in the green bar."""
        s = self.scale_factor
        stats_x = self.bg_rect.x + int(INV_STATS_X * s)
        stats_y = self.bg_rect.y + int(INV_STATS_Y * s)
        
        # Check if we should show item info instead of stats
        if self.hovered_slot:
            slot_type, value = self.hovered_slot
            if slot_type == "grid":
                item = self.player.inventory.get_item_at(value)
                if item:
                    # Draw Item Info (Localized)
                    item_data = I18nManager().get_item(item.id)
                    name = item_data["name"]
                    description = item_data["description"]
                    
                    name_text = self.noble_font.render(name, True, COLOR_TEXT_STONE)
                    screen.blit(name_text, (stats_x, stats_y - int(INV_STAT_NAME_OFFSET_Y * s)))
                    
                    # Draw Wrapped Description (More compact)
                    max_w = self.bg_rect.width - int(INV_INFO_MAX_W_OFFSET * s) 
                    words = description.split(' ')
                    lines = []
                    current_line = []
                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        if self.narrative_font.size(test_line)[0] < max_w:
                            current_line.append(word)
                        else:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                    lines.append(' '.join(current_line))
                    
                    for i, line in enumerate(lines[:3]): # Max 3 lines
                        desc_surf = self.narrative_font.render(line, True, COLOR_TEXT_STONE)
                        screen.blit(desc_surf, (stats_x, stats_y + int(5 * s) + i * int(18 * s)))
                    return

        # Default: Draw Stats
        # LVL (Left part of green bar)
        lvl_text = self.noble_font.render(f"LVL {self.player.level}", True, COLOR_TEXT_STONE)
        lvl_rect = lvl_text.get_rect(midleft=(stats_x, stats_y))
        screen.blit(lvl_text, lvl_rect)

        # HP (Center)
        hp_text = self.noble_font.render(f"HP {self.player.hp}/{self.player.max_hp}", True, COLOR_TEXT_STONE)
        hp_rect = hp_text.get_rect(center=(self.bg_rect.x + int(INV_HP_X * s), stats_y))
        screen.blit(hp_text, hp_rect)

        # GOLD (Right)
        gold_text = self.noble_font.render(f"GOLD {self.player.gold}", True, COLOR_TEXT_STONE)
        gold_rect = gold_text.get_rect(midright=(self.bg_rect.x + int(INV_GOLD_X * s), stats_y))
        screen.blit(gold_text, gold_rect)

    def _get_item_icon(self, icon_filename):
        """Load and cache item icon."""
        if icon_filename in self.icon_cache:
            return self.icon_cache[icon_filename]
        
        path = os.path.join("assets", "images", "icons", icon_filename)
        # Ensure .png extension if missing
        if not path.endswith(".png"):
            path += ".png"
            icon_filename += ".png"
            
        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                # Scale icon to fit slot (approx 48x48 base, scaled by s)
                target_size = int(48 * self.scale_factor)
                img = pygame.transform.smoothscale(img, (target_size, target_size))
                self.icon_cache[icon_filename] = img
                return img
        except Exception as e:
            logging.error(f"InventoryUI: Could not load icon {icon_filename}: {e}")
        
        return None
