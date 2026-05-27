from pathlib import Path

import pygame

from src.config import Settings
from src.engine.i18n import I18nManager
from src.engine.save_manager import SlotInfo
from src.ui.save_menu_constants import (
    SAVE_DETAIL_COLOR,
    SAVE_DETAIL_LINE_SPACING,
    SAVE_DETAIL_TEXT_X_OFFSET,
    SAVE_DETAIL_TEXT_Y_OFFSET,
    SAVE_SLOT_BG_H,
    SAVE_SLOT_BG_W,
    SAVE_SLOT_FALLBACK_BG,
    SAVE_SLOT_FALLBACK_BORDER,
    SAVE_SLOT_GEM_COORDS,
    SAVE_SLOT_HALO_RADIUS,
    SAVE_THUMB_BG_COLOR,
    SAVE_THUMB_BORDER_COLOR,
    SAVE_THUMB_SIZE,
    SAVE_THUMB_X,
    SAVE_THUMB_Y,
    SAVE_TITLE_COLOR,
)
from src.ui.ui_colors import COLOR_BLACK


class SaveSlotUI:
    """Renders a single save slot: background, thumbnail, text, and hover glow."""

    def __init__(self, am):
        self._font_title = am.get_font(Settings.FONT_NOBLE, Settings.FONT_SIZE_NOBLE)
        self._font_small = am.get_font(Settings.FONT_NARRATIVE, Settings.FONT_SIZE_NARRATIVE)
        self._i18n = I18nManager()

        # Load the slot background — scaled to SAVE_SLOT_BG_W x SAVE_SLOT_BG_H
        path = str(Path("assets") / "images" / "menu" / "03-save_slot.png")
        raw = am.get_image(path, fallback=True)
        if raw.get_size() == (32, 32):  # fallback placeholder from AssetManager
            self._bg = pygame.Surface((SAVE_SLOT_BG_W, SAVE_SLOT_BG_H), pygame.SRCALPHA)
            self._bg.fill(SAVE_SLOT_FALLBACK_BG)
            pygame.draw.rect(self._bg, SAVE_SLOT_FALLBACK_BORDER, self._bg.get_rect(), 2)
        else:
            self._bg = pygame.transform.smoothscale(raw, (SAVE_SLOT_BG_W, SAVE_SLOT_BG_H))

        # Pre-calculate halo for hover effect (using additive blending)
        radius = SAVE_SLOT_HALO_RADIUS
        self._halo = pygame.Surface((radius * 2, radius * 2))
        self._halo.fill(COLOR_BLACK)
        for r in range(radius, 0, -1):
            # Non-linear (quadratic) gradient for a soft light falloff
            intensity = (1.0 - (r / radius)) ** 2
            # Golden/orange hue
            color = (int(255 * intensity), int(160 * intensity), int(40 * intensity))
            pygame.draw.circle(self._halo, color, (radius, radius), r)

        self._gem_coords = SAVE_SLOT_GEM_COORDS

    def get_size(self) -> tuple[int, int]:
        return self._bg.get_size()

    def _draw_thumbnail(self, surface: pygame.Surface, rect: pygame.Rect, thumbnail: pygame.Surface | None) -> None:
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

    def _draw_title(self, surface: pygame.Surface, rect: pygame.Rect, info: "SlotInfo") -> None:
        display_name = info.map_display_name if info.map_display_name else ""
        if display_name:
            display_name = self._i18n.get(display_name, display_name)
        title_text = self._font_title.render(display_name, True, SAVE_TITLE_COLOR)
        title_rect = title_text.get_rect(center=(rect.x + rect.w // 2, rect.y + 22))
        surface.blit(title_text, title_rect)

    def _draw_details(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        info: "SlotInfo",
        cached_level_surf: pygame.Surface | None,
        cached_time_surf: pygame.Surface | None,
    ) -> None:
        text_x = rect.x + SAVE_DETAIL_TEXT_X_OFFSET
        details_y = rect.y + SAVE_DETAIL_TEXT_Y_OFFSET

        if cached_level_surf is not None:
            surface.blit(cached_level_surf, (text_x, details_y))
        else:
            level_str = self._i18n.get("save_menu.level", "Level: {level}").format(level=info.level)
            level_text = self._font_small.render(level_str, True, SAVE_DETAIL_COLOR)
            surface.blit(level_text, (text_x, details_y))

        if cached_time_surf is not None:
            surface.blit(cached_time_surf, (text_x, details_y + SAVE_DETAIL_LINE_SPACING))
        else:
            hours = int(info.playtime_seconds // 3600)
            minutes = int((info.playtime_seconds % 3600) // 60)
            time_str = self._i18n.get(
                "save_menu.time", "Time: {hours:02d}h {minutes:02d}m"
            ).format(hours=hours, minutes=minutes)
            time_text = self._font_small.render(time_str, True, SAVE_DETAIL_COLOR)
            surface.blit(time_text, (text_x, details_y + SAVE_DETAIL_LINE_SPACING))

    def _draw_hover(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        halo_r = self._halo.get_width() // 2
        for gx, gy in self._gem_coords:
            hx = rect.x + gx - halo_r
            hy = rect.y + gy - halo_r
            surface.blit(self._halo, (hx, hy), special_flags=pygame.BLEND_RGB_ADD)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        slot_id: int,
        info: "SlotInfo | None",
        thumbnail: pygame.Surface | None,
        is_hovered: bool,
        cached_level_surf: pygame.Surface | None = None,
        cached_time_surf: pygame.Surface | None = None,
    ) -> None:
        """Render the slot background, thumbnail, text and hover effect."""
        surface.blit(self._bg, rect)

        if info is not None:
            self._draw_thumbnail(surface, rect, thumbnail)
            self._draw_title(surface, rect, info)
            self._draw_details(surface, rect, info, cached_level_surf, cached_time_surf)

        if is_hovered:
            self._draw_hover(surface, rect)
