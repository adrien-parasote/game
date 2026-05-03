"""
Save Menu UI Components.
Spec: docs/specs/save-system.md
"""
import os
import pygame
import logging
from typing import Optional
from src.engine.save_manager import SaveManager, SlotInfo
from src.config import Settings
from src.engine.i18n import I18nManager


class SaveSlotUI:
    """Composant responsable du rendu d'un emplacement de sauvegarde unique."""
    
    def __init__(self, am):
        self._font_title = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        self._font_small = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        self._i18n = I18nManager()
        
        # Load the slot background
        path = os.path.join("assets", "images", "menu", "03-save_slot.png")
        try:
            raw = pygame.image.load(path).convert_alpha()
            self._bg = pygame.transform.smoothscale(raw, (427, 200))
        except pygame.error as e:
            logging.error(f"SaveSlotUI: Could not load 03-save_slot.png: {e}")
            self._bg = pygame.Surface((427, 200), pygame.SRCALPHA)
            self._bg.fill((30, 30, 30, 200))
            pygame.draw.rect(self._bg, (100, 100, 100), self._bg.get_rect(), 2)

        # Pre-calculate halo for hover effect (using additive blending)
        radius = 45
        self._halo = pygame.Surface((radius * 2, radius * 2))
        self._halo.fill((0, 0, 0)) # Noir: invisible en mode ADD
        for r in range(radius, 0, -1):
            # Dégradé non-linéaire (quadratique) pour un effet de lumière doux
            intensity = (1.0 - (r / radius)) ** 2
            # Couleur dorée/orangée
            color = (int(255 * intensity), int(160 * intensity), int(40 * intensity))
            pygame.draw.circle(self._halo, color, (radius, radius), r)
        
        # Approximate gem coordinates in 427x200 space
        self._gem_coords = [
            (26, 27),
            (413, 27),
            (26, 170),
            (414, 171)
        ]

    def get_size(self) -> tuple[int, int]:
        return self._bg.get_size()

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, slot_id: int, info: Optional[SlotInfo], thumbnail: Optional[pygame.Surface], is_hovered: bool) -> None:
        """Render the slot background, thumbnail, text and hover effect."""
        surface.blit(self._bg, rect)
        
        if info is None:
            empty_text = self._i18n.get("save_menu.slot_empty", "Emplacement {slot_id} — Vide").format(slot_id=slot_id)
            text = self._font_title.render(empty_text, True, (140, 120, 100))
            surface.blit(text, text.get_rect(center=(rect.x + rect.w // 2, rect.centery)))
        else:
            # Thumbnail area in 03-save_slot.png starts around x=56, y=59 and is ~82x82 pixels
            thumb_rect = pygame.Rect(rect.x + 56, rect.y + 59, 82, 82)
            if thumbnail:
                # Scale thumbnail to fit 82x82 just in case
                if thumbnail.get_size() != (82, 82):
                    thumbnail = pygame.transform.smoothscale(thumbnail, (82, 82))
                surface.blit(thumbnail, thumb_rect)
            else:
                pygame.draw.rect(surface, (20, 20, 20), thumb_rect)
                pygame.draw.rect(surface, (80, 80, 80), thumb_rect, 1)

            # Texts on the right side
            text_x = rect.x + 180
            text_y = rect.y + 30
            
            # Title: Map Name
            title_text = self._font_title.render(info.map_name, True, (220, 200, 150))
            surface.blit(title_text, (text_x, text_y))
            
            # Details: Level, Time
            details_y = text_y + 40
            level_str = self._i18n.get("save_menu.level", "Niveau: {level}").format(level=info.level)
            level_text = self._font_small.render(level_str, True, (180, 180, 180))
            surface.blit(level_text, (text_x, details_y))
            
            # Formatted playtime (e.g. 02h 15m)
            hours = int(info.playtime_seconds // 3600)
            minutes = int((info.playtime_seconds % 3600) // 60)
            time_str = self._i18n.get("save_menu.time", "Temps: {hours:02d}h {minutes:02d}m").format(hours=hours, minutes=minutes)
            time_text = self._font_small.render(time_str, True, (180, 180, 180))
            surface.blit(time_text, (text_x, details_y + 30))

        # Hover Effect: Draw true additive light glow over the 4 gems
        if is_hovered:
            halo_r = self._halo.get_width() // 2
            for gx, gy in self._gem_coords:
                hx = rect.x + gx - halo_r
                hy = rect.y + gy - halo_r
                surface.blit(self._halo, (hx, hy), special_flags=pygame.BLEND_RGB_ADD)


class SaveMenuOverlay:
    """
    Overlay menu managing 3 save slots. 
    Can be used for both Loading (TitleScreen) and Saving (PauseScreen).
    """

    def __init__(self, screen: pygame.Surface, save_manager: SaveManager, title: str):
        self._screen = screen
        self._save_manager = save_manager
        self._title_text = title
        self._slots_info: list[Optional[SlotInfo]] = [None, None, None]
        self._thumbnails: list[Optional[pygame.Surface]] = [None, None, None]
        self._hovered_slot: Optional[int] = None
        
        self._sw, self._sh = screen.get_size()
        
        # Load asset manager fonts
        try:
            am = __import__("src.engine.asset_manager", fromlist=["AssetManager"]).AssetManager()
        except Exception:
            am = None
            
        if am:
            self._font_title = am.get_font(Settings.FONT_NOBLE, int(Settings.FONT_SIZE_NOBLE * 1.5))
        else:
            self._font_title = pygame.font.SysFont(None, 48)

        self._slot_ui = SaveSlotUI(am) if am else None # Fallback logic can be added if needed
        
        # Semi-transparent background panel
        self._panel = pygame.Surface((600, 800), pygame.SRCALPHA)
        self._panel.fill((10, 18, 22, 220))
        
        self._compute_layout()

    def _compute_layout(self) -> None:
        if not self._slot_ui:
            self.slot_rects = []
            return
            
        slot_w, slot_h = self._slot_ui.get_size()
        spacing = 20
        total_h = (slot_h * 3) + (spacing * 2)
        
        start_y = (self._sh - total_h) // 2 + 30
        start_x = (self._sw - slot_w) // 2
        
        self.slot_rects = [
            pygame.Rect(start_x, start_y + i * (slot_h + spacing), slot_w, slot_h)
            for i in range(3)
        ]

    def refresh(self) -> None:
        """Re-read slot metadata and thumbnails from disk."""
        self._slots_info = self._save_manager.list_slots()
        for i in range(3):
            if self._slots_info[i] is not None:
                self._thumbnails[i] = self._save_manager.load_thumbnail(i + 1)
            else:
                self._thumbnails[i] = None

    def update(self, dt: float) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self._hovered_slot = None
        for i, rect in enumerate(self.slot_rects):
            if rect.collidepoint(mouse_pos):
                self._hovered_slot = i
                break

    def draw(self) -> None:
        # Draw background panel
        panel_rect = pygame.Rect(
            self._sw // 2 - 300,
            max(0, self.slot_rects[0].y - 80) if self.slot_rects else 0,
            600,
            (self.slot_rects[-1].bottom - self.slot_rects[0].y + 120) if self.slot_rects else 800
        )
        self._screen.blit(self._panel, panel_rect)
        
        # Draw title
        title_surf = self._font_title.render(self._title_text, True, (220, 200, 150))
        self._screen.blit(title_surf, title_surf.get_rect(midtop=(self._sw // 2, panel_rect.y + 20)))

        # Draw slots
        if self._slot_ui:
            for i, rect in enumerate(self.slot_rects):
                self._slot_ui.draw(
                    surface=self._screen,
                    rect=rect,
                    slot_id=i + 1,
                    info=self._slots_info[i],
                    thumbnail=self._thumbnails[i],
                    is_hovered=(self._hovered_slot == i)
                )

    def get_clicked_slot(self, event: pygame.Event) -> Optional[int]:
        """Return slot index (0, 1, 2) if clicked, else None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos):
                    return i
        return None
