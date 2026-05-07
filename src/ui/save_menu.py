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
from src.ui.save_menu_constants import (
    BACK_BTN_H,
    BACK_BTN_W,
    BACK_FONT_PATH,
    BACK_FONT_SIZE,
    BACK_HALO_COLOR,
    BACK_ICON_H,
    BACK_ICON_HOVER_H,
    BACK_ICON_HOVER_W,
    BACK_ICON_W,
    BACK_LABEL_GAP,
    BACK_TEXT_COLOR,
    ENGRAVE_LIGHT,
    ENGRAVE_SHADOW,
    ENGRAVE_TEXT,
    SAVE_DETAIL_COLOR,
    SAVE_DETAIL_LINE_SPACING,
    SAVE_DETAIL_TEXT_X_OFFSET,
    SAVE_DETAIL_TEXT_Y_OFFSET,
    SAVE_FONT_TITLE_FALLBACK_SIZE,
    SAVE_HALO_BLUR_PADDING,
    SAVE_HALO_BLUR_RADIUS,
    SAVE_PANEL_FILL,
    SAVE_PANEL_H,
    SAVE_PANEL_W,
    SAVE_PANEL_Y_OFFSET,
    SAVE_SLOT_BG_H,
    SAVE_SLOT_BG_W,
    SAVE_SLOT_FALLBACK_BG,
    SAVE_SLOT_FALLBACK_BORDER,
    SAVE_SLOT_GEM_COORDS,
    SAVE_SLOT_HALO_RADIUS,
    SAVE_SLOT_SPACING,
    SAVE_THUMB_BG_COLOR,
    SAVE_THUMB_BORDER_COLOR,
    SAVE_THUMB_SIZE,
    SAVE_THUMB_X,
    SAVE_THUMB_Y,
    SAVE_TITLE_COLOR,
)


class SaveSlotUI:
    """Renders a single save slot: background, thumbnail, text, and hover glow."""

    def __init__(self, am):
        self._font_title = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        self._font_small = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        self._i18n = I18nManager()

        # Load the slot background — scaled to SAVE_SLOT_BG_W x SAVE_SLOT_BG_H
        path = os.path.join("assets", "images", "menu", "03-save_slot.png")
        try:
            raw = pygame.image.load(path).convert_alpha()
            self._bg = pygame.transform.smoothscale(raw, (SAVE_SLOT_BG_W, SAVE_SLOT_BG_H))
        except pygame.error as e:
            logging.error(f"SaveSlotUI: Could not load 03-save_slot.png: {e}")
            self._bg = pygame.Surface((SAVE_SLOT_BG_W, SAVE_SLOT_BG_H), pygame.SRCALPHA)
            self._bg.fill(SAVE_SLOT_FALLBACK_BG)
            pygame.draw.rect(self._bg, SAVE_SLOT_FALLBACK_BORDER, self._bg.get_rect(), 2)

        # Pre-calculate halo for hover effect (using additive blending)
        radius = SAVE_SLOT_HALO_RADIUS
        self._halo = pygame.Surface((radius * 2, radius * 2))
        self._halo.fill((0, 0, 0))
        for r in range(radius, 0, -1):
            # Non-linear (quadratic) gradient for a soft light falloff
            intensity = (1.0 - (r / radius)) ** 2
            # Golden/orange hue
            color = (int(255 * intensity), int(160 * intensity), int(40 * intensity))
            pygame.draw.circle(self._halo, color, (radius, radius), r)

        self._gem_coords = SAVE_SLOT_GEM_COORDS

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
            # Thumbnail area in 03-save_slot.png
            thumb_rect = pygame.Rect(
                rect.x + SAVE_THUMB_X, rect.y + SAVE_THUMB_Y, SAVE_THUMB_SIZE, SAVE_THUMB_SIZE
            )
            if thumbnail:
                if thumbnail.get_size() != (SAVE_THUMB_SIZE, SAVE_THUMB_SIZE):
                    thumbnail = pygame.transform.smoothscale(
                        thumbnail, (SAVE_THUMB_SIZE, SAVE_THUMB_SIZE)
                    )
                surface.blit(thumbnail, thumb_rect)
            else:
                pygame.draw.rect(surface, SAVE_THUMB_BG_COLOR, thumb_rect)
                pygame.draw.rect(surface, SAVE_THUMB_BORDER_COLOR, thumb_rect, 1)

            # Title: Map Name (centered in the top ribbon)
            display_name = info.map_display_name if info.map_display_name else ""
            if display_name:
                display_name = self._i18n.get(display_name, display_name)
            title_text = self._font_title.render(display_name, True, SAVE_TITLE_COLOR)
            title_rect = title_text.get_rect(center=(rect.x + rect.w // 2, rect.y + 22))
            surface.blit(title_text, title_rect)

            # Details: Level, Time
            text_x = rect.x + SAVE_DETAIL_TEXT_X_OFFSET
            details_y = rect.y + SAVE_DETAIL_TEXT_Y_OFFSET

            level_str = self._i18n.get("save_menu.level", "Niveau: {level}").format(
                level=info.level
            )
            level_text = self._font_small.render(level_str, True, SAVE_DETAIL_COLOR)
            surface.blit(level_text, (text_x, details_y))

            hours = int(info.playtime_seconds // 3600)
            minutes = int((info.playtime_seconds % 3600) // 60)
            time_str = self._i18n.get(
                "save_menu.time", "Temps: {hours:02d}h {minutes:02d}m"
            ).format(hours=hours, minutes=minutes)
            time_text = self._font_small.render(time_str, True, SAVE_DETAIL_COLOR)
            surface.blit(time_text, (text_x, details_y + SAVE_DETAIL_LINE_SPACING))

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
            self._font_title = am.get_font(
                Settings.FONT_NOBLE, int(Settings.FONT_SIZE_NOBLE * 1.5)
            )
        else:
            self._font_title = pygame.font.SysFont(None, SAVE_FONT_TITLE_FALLBACK_SIZE)

        self._slot_ui = SaveSlotUI(am) if am else None

        # Semi-transparent background panel
        self._panel = pygame.Surface((SAVE_PANEL_W, SAVE_PANEL_H), pygame.SRCALPHA)
        self._panel.fill(SAVE_PANEL_FILL)

        # Cached title surfaces — populated in refresh(), one per slot
        self._cached_title_surfs: list[pygame.Surface | None] = [None, None, None]

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
            self._back_btn_icon = pygame.transform.smoothscale(
                raw, (BACK_ICON_W, BACK_ICON_H)
            )
            self._back_btn_icon_hover = pygame.transform.smoothscale(
                raw, (BACK_ICON_HOVER_W, BACK_ICON_HOVER_H)
            )
        except pygame.error:
            self._back_btn_icon = pygame.Surface((BACK_ICON_W, BACK_ICON_H), pygame.SRCALPHA)
            self._back_btn_icon_hover = pygame.Surface(
                (BACK_ICON_HOVER_W, BACK_ICON_HOVER_H), pygame.SRCALPHA
            )

        try:
            self._font_back = pygame.font.Font(BACK_FONT_PATH, BACK_FONT_SIZE)
        except OSError:
            self._font_back = pygame.font.SysFont(None, BACK_FONT_SIZE)

    def _compute_layout(self) -> None:
        if not self._slot_ui:
            self.slot_rects = []
            self.back_btn_rect = pygame.Rect(0, 0, 0, 0)
            return

        slot_w, slot_h = self._slot_ui.get_size()
        spacing = SAVE_SLOT_SPACING
        total_h = (slot_h * 3) + (spacing * 2)

        start_y = (self._sh - total_h) // 2 + SAVE_PANEL_Y_OFFSET
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
        self.back_btn_rect = pygame.Rect(
            self._panel_rect.left + self._back_offset_x,
            self._panel_rect.bottom - BACK_BTN_H - self._back_offset_y,
            BACK_BTN_W,
            BACK_BTN_H,
        )

    def refresh(self) -> None:
        """Re-read slot metadata and thumbnails from disk; pre-cache title surfaces."""
        self._slots_info = self._save_manager.list_slots()
        self._cached_title_surfs = []
        for i in range(3):
            if self._slots_info[i] is not None:
                self._thumbnails[i] = self._save_manager.load_thumbnail(i + 1)
                # Pre-render the overlay title — no render() calls in draw()
                display_name = self._slots_info[i].map_display_name or ""
                title_surf = self._font_title.render(display_name, True, SAVE_TITLE_COLOR)
                self._cached_title_surfs.append(title_surf)
            else:
                self._thumbnails[i] = None
                self._cached_title_surfs.append(None)

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

        # Measure label width — use font.size() to avoid allocating a surface
        label_w = self._font_back.size(label)[0]
        gap = BACK_LABEL_GAP

        total_w = icon_w + gap + label_w
        start_x = cx - total_w // 2

        # Draw icon
        icon_r = icon.get_rect(midleft=(start_x, cy))
        self._screen.blit(icon, icon_r)

        # Draw text
        text_cx = start_x + icon_w + gap + label_w // 2
        if self._back_hovered:
            self._blit_halo_text(
                label, text_cx, cy, self._font_back, BACK_TEXT_COLOR, BACK_HALO_COLOR
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
        pad = SAVE_HALO_BLUR_PADDING
        padded = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        padded.blit(base_surf, (pad, pad))
        try:
            blurred = pygame.transform.gaussian_blur(padded, SAVE_HALO_BLUR_RADIUS)
            rect = blurred.get_rect(center=(cx, cy))
            self._screen.blit(blurred, rect)
            self._screen.blit(blurred, rect)
        except AttributeError:
            pass

        main_surf = font.render(label, True, text_color)
        self._screen.blit(main_surf, main_surf.get_rect(center=(cx, cy)))

    def _blit_engraved(self, label: str, cx: int, cy: int, font: pygame.font.Font) -> None:
        """3-pass stone engraving: shadow | light | text."""
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
