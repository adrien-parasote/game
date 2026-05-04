"""
Save Menu UI Components.
Spec: docs/specs/save-system.md
"""

import logging
import os

import pygame

from src.config import Settings
from src.engine.i18n import I18nManager
from src.engine.save_manager import SaveManager, SlotInfo


class SaveSlotUI:
    """Renders a single save slot: background, thumbnail, text, and hover glow."""

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
        self._halo.fill((0, 0, 0))  # Black: invisible in BLEND_RGB_ADD mode
        for r in range(radius, 0, -1):
            # Non-linear (quadratic) gradient for a soft light falloff
            intensity = (1.0 - (r / radius)) ** 2
            # Golden/orange hue
            color = (int(255 * intensity), int(160 * intensity), int(40 * intensity))
            pygame.draw.circle(self._halo, color, (radius, radius), r)

        # Approximate gem coordinates in 427x200 space
        self._gem_coords = [(26, 27), (413, 27), (26, 170), (414, 171)]

    def get_size(self) -> tuple[int, int]:
        return self._bg.get_size()

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        slot_id: int,
        info: SlotInfo | None,
        thumbnail: pygame.Surface | None,
        is_hovered: bool,
    ) -> None:
        """Render the slot background, thumbnail, text and hover effect."""
        surface.blit(self._bg, rect)

        if info is None:
            pass
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

            # Title: Map Name (Centered in the top ribbon)
            display_name = info.map_display_name if info.map_display_name else ""
            if display_name:
                display_name = self._i18n.get(display_name, display_name)
            title_text = self._font_title.render(display_name, True, (220, 200, 150))
            title_rect = title_text.get_rect(center=(rect.x + rect.w // 2, rect.y + 22))
            surface.blit(title_text, title_rect)

            # Details: Level, Time
            text_x = rect.x + 180
            details_y = rect.y + 70

            level_str = self._i18n.get("save_menu.level", "Niveau: {level}").format(
                level=info.level
            )
            level_text = self._font_small.render(level_str, True, (60, 40, 30))
            surface.blit(level_text, (text_x, details_y))

            # Formatted playtime (e.g. 02h 15m)
            hours = int(info.playtime_seconds // 3600)
            minutes = int((info.playtime_seconds % 3600) // 60)
            time_str = self._i18n.get(
                "save_menu.time", "Temps: {hours:02d}h {minutes:02d}m"
            ).format(hours=hours, minutes=minutes)
            time_text = self._font_small.render(time_str, True, (60, 40, 30))
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
        self._i18n = I18nManager()
        self._slots_info: list[SlotInfo | None] = [None, None, None]
        self._thumbnails: list[pygame.Surface | None] = [None, None, None]
        self._hovered_slot: int | None = None

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

        self._slot_ui = SaveSlotUI(am) if am else None  # Fallback logic can be added if needed

        # Semi-transparent background panel
        self._panel = pygame.Surface((600, 800), pygame.SRCALPHA)
        self._panel.fill((10, 18, 22, 220))

        # Back button assets
        self._back_hovered = False
        self._back_offset_x = 10  # Default padding from left
        self._back_offset_y = 10  # Default padding from bottom
        self._load_back_assets()

        self._compute_layout()

    def _load_back_assets(self) -> None:
        """Load icon and font for the Back button."""
        path = os.path.join("assets", "images", "menu", "01-menu_back_cursor.png")
        try:
            raw = pygame.image.load(path).convert_alpha()
            # Standard back icon size (matches TitleScreen)
            self._back_btn_icon = pygame.transform.smoothscale(raw, (28, 25))
            self._back_btn_icon_hover = pygame.transform.smoothscale(raw, (32, 29))
        except pygame.error:
            self._back_btn_icon = pygame.Surface((28, 25), pygame.SRCALPHA)
            self._back_btn_icon_hover = pygame.Surface((32, 29), pygame.SRCALPHA)

        try:
            font_path = "assets/fonts/cormorant-garamond-regular.ttf"
            self._font_back = pygame.font.Font(font_path, 22)
        except OSError:
            self._font_back = pygame.font.SysFont(None, 22)

    def _compute_layout(self) -> None:
        if not self._slot_ui:
            self.slot_rects = []
            self.back_btn_rect = pygame.Rect(0, 0, 0, 0)
            return

        slot_w, slot_h = self._slot_ui.get_size()
        spacing = 20
        total_h = (slot_h * 3) + (spacing * 2)

        start_y = (self._sh - total_h) // 2 + 30
        start_x = (self._sw - slot_w) // 2

        self.slot_rects = [
            pygame.Rect(start_x, start_y + i * (slot_h + spacing), slot_w, slot_h) for i in range(3)
        ]

        # Panel rect (shared with draw)
        self._panel_rect = pygame.Rect(
            self._sw // 2 - 300,
            max(0, self.slot_rects[0].y - 80),
            600,
            (self.slot_rects[-1].bottom - self.slot_rects[0].y + 120),
        )

        # Back button at bottom left of the panel
        # total_w estimate: icon (28) + gap (10) + text (~70) = ~110
        bw, bh = 140, 40
        self.back_btn_rect = pygame.Rect(
            self._panel_rect.left + self._back_offset_x,
            self._panel_rect.bottom - bh - self._back_offset_y,
            bw,
            bh,
        )

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

        self._back_hovered = self.back_btn_rect.collidepoint(mouse_pos)

    def draw(self) -> None:
        # Draw background panel
        self._screen.blit(self._panel, self._panel_rect)

        # Draw title
        title_surf = self._font_title.render(self._title_text, True, (220, 200, 150))
        self._screen.blit(
            title_surf, title_surf.get_rect(midtop=(self._sw // 2, self._panel_rect.y + 20))
        )

        # Draw slots
        if self._slot_ui:
            for i, rect in enumerate(self.slot_rects):
                self._slot_ui.draw(
                    surface=self._screen,
                    rect=rect,
                    slot_id=i + 1,
                    info=self._slots_info[i],
                    thumbnail=self._thumbnails[i],
                    is_hovered=(self._hovered_slot == i),
                )

        # Draw Back Button
        self._draw_back_button()

    def _draw_back_button(self) -> None:
        """Render the Back button at the bottom left of the panel."""
        label = self._i18n.get("menu.back", "Retour")

        # Center of the button area for alignment
        cx = self.back_btn_rect.centerx
        cy = self.back_btn_rect.centery

        # Render icon (hover = slightly larger)
        icon = self._back_btn_icon_hover if self._back_hovered else self._back_btn_icon
        icon_w = icon.get_width()

        # Measure label width
        label_surf_measure = self._font_back.render(label, True, (0, 0, 0))
        label_w = label_surf_measure.get_width()
        gap = 8

        total_w = icon_w + gap + label_w
        start_x = cx - total_w // 2

        # Draw icon
        icon_r = icon.get_rect(midleft=(start_x, cy))
        self._screen.blit(icon, icon_r)

        # Draw text
        text_cx = start_x + icon_w + gap + label_w // 2
        if self._back_hovered:
            self._blit_halo_text(
                label, text_cx, cy, self._font_back, (150, 255, 220), (0, 180, 150)
            )
        else:
            self._blit_engraved(label, text_cx, cy, self._font_back)

    def _blit_halo_text(
        self,
        label: str,
        cx: int,
        cy: int,
        font: pygame.font.Font,
        text_color: tuple[int, int, int],
        halo_color: tuple[int, int, int],
    ) -> None:
        """Draw text with a soft, spreading glowing halo effect."""
        base_surf = font.render(label, True, halo_color)
        w, h = base_surf.get_size()
        pad = 20
        padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        padded.blit(base_surf, (pad, pad))
        try:
            blurred = pygame.transform.gaussian_blur(padded, 6)
            rect = blurred.get_rect(center=(cx, cy))
            self._screen.blit(blurred, rect)
            self._screen.blit(blurred, rect)
        except AttributeError:
            pass

        main_surf = font.render(label, True, text_color)
        self._screen.blit(main_surf, main_surf.get_rect(center=(cx, cy)))

    def _blit_engraved(self, label: str, cx: int, cy: int, font: pygame.font.Font) -> None:
        """3-pass stone engraving: shadow | light | text."""
        # Engraving colors consistent with TitleScreen
        ENGRAVE_TEXT = (45, 65, 75)
        ENGRAVE_SHADOW = (12, 20, 23)
        ENGRAVE_LIGHT = (90, 120, 130)

        shadow = font.render(label, True, ENGRAVE_SHADOW)
        light = font.render(label, True, ENGRAVE_LIGHT)
        text = font.render(label, True, ENGRAVE_TEXT)
        r = text.get_rect(center=(cx, cy))
        self._screen.blit(shadow, r.move(-1, -1))
        self._screen.blit(light, r.move(1, 1))
        self._screen.blit(text, r)

    def is_back_clicked(self, event: pygame.Event) -> bool:
        """Return True if the Back button was clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn_rect.collidepoint(event.pos):
                return True
        return False

    def get_clicked_slot(self, event: pygame.Event) -> int | None:
        """Return slot index (0, 1, 2) if clicked, else None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos):
                    return i
        return None
