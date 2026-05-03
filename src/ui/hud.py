import os
import json
import logging
import pygame
from src.engine.time_system import TimeSystem, Season
from src.engine.asset_manager import AssetManager
from src.engine.i18n import I18nManager
from src.config import Settings
from src.ui.hud_constants import *
from src.ui.hud_constants import _SEASON_FILES, _SEASON_LANG_KEYS

class GameHUD:
    """
    Renders a fixed top-right HUD overlay showing time, season, and day.
    """

    def __init__(self, time_system: TimeSystem) -> None:
        self.time_system = time_system
        self._clock_surf = self._load_scaled_clock()
        self._season_surfs = self._load_season_icons()
        self._font = self._load_font()

    @staticmethod
    def _hud_asset_path(filename: str) -> str:
        base = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "HUD")
        return os.path.normpath(os.path.join(base, filename))

    def _load_image(self, filename: str) -> pygame.Surface:
        path = self._hud_asset_path(filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"GameHUD: Could not load image '{filename}': {e}")
            return pygame.Surface((10, 10), pygame.SRCALPHA)

    def _load_scaled_clock(self) -> pygame.Surface:
        raw = self._load_image("00-clock.png")
        return pygame.transform.smoothscale(
            raw, (int(raw.get_width() * HUD_SCALE), int(raw.get_height() * HUD_SCALE))
        )

    def _load_season_icons(self) -> dict:
        icons = {}
        for season, filename in _SEASON_FILES.items():
            raw = self._load_image(filename)
            icons[season] = pygame.transform.smoothscale(raw, (SEASON_ICON_SIZE, SEASON_ICON_SIZE))
        return icons

    @staticmethod
    def _load_font() -> pygame.font.Font:
        am = AssetManager()
        return am.get_font(Settings.FONT_TECH, FONT_SIZE)

    def _render_text_centered(self, surface: pygame.Surface, text: str, center: tuple) -> None:
        shadow_surf = self._font.render(text, True, SHADOW_COLOR)
        shadow_rect = shadow_surf.get_rect(center=(center[0] + SHADOW_OFFSET, center[1] + SHADOW_OFFSET))
        surface.blit(shadow_surf, shadow_rect)
        main_surf = self._font.render(text, True, TEXT_COLOR)
        main_rect = main_surf.get_rect(center=center)
        surface.blit(main_surf, main_rect)

    def draw(self, screen: pygame.Surface) -> None:
        clock_w = self._clock_surf.get_width()
        hud_x = screen.get_width() - clock_w - HUD_MARGIN_X
        hud_y = HUD_MARGIN_Y

        screen.blit(self._clock_surf, (hud_x, hud_y))

        icon = self._season_surfs[self.time_system.current_season]
        icon_x = hud_x + SEASON_ICON_CENTER[0] - icon.get_width() // 2
        icon_y = hud_y + SEASON_ICON_CENTER[1] - icon.get_height() // 2
        screen.blit(icon, (icon_x, icon_y))

        self._render_text_centered(
            screen,
            self.time_system.time_label,
            (hud_x + TIME_ANCHOR[0], hud_y + TIME_ANCHOR[1]),
        )

        wt = self.time_system.world_time
        day_label = I18nManager().get("day_label", "Day").upper()
        season_day_text = f"{day_label} {wt.day + 1}"
        
        self._render_text_centered(
            screen,
            season_day_text,
            (hud_x + SEASON_DAY_ANCHOR[0], hud_y + SEASON_DAY_ANCHOR[1]),
        )
