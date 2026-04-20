"""
GameHUD — Fixed overlay HUD for in-game time, day and season display.

Layout constants are relative to the 00-clock.png top-left corner.
All text positions are center-anchored.
"""
import os
import json
import logging
import pygame
from src.engine.time_system import TimeSystem, Season

# ------------------------------------------------------------------
# Layout constants (pixels relative to clock image top-left)
# ------------------------------------------------------------------
SEASON_ICON_CENTER: tuple = (33, 36)   # Center of season circle icon
TIME_ANCHOR: tuple = (75, 22)           # Center of time text zone (top-right)
SEASON_DAY_ANCHOR: tuple = (88, 52)    # Center of season/day text zone (bottom)

SEASON_ICON_SIZE: int = 50             # Scaled size of season icon in the circle

HUD_MARGIN_X: int = 20                 # Pixels from right edge
HUD_MARGIN_Y: int = 20                 # Pixels from top edge

TEXT_COLOR: tuple = (240, 235, 210)    # Warm off-white
SHADOW_COLOR: tuple = (0, 0, 0)
SHADOW_OFFSET: int = 1
FONT_SIZE: int = 14

# Map Season enum to lang key and filename
_SEASON_FILES: dict = {
    Season.SPRING: "01-spring.png",
    Season.SUMMER: "02-summer.png",
    Season.AUTUMN: "03-autumn.png",
    Season.WINTER: "04-winter.png",
}

_SEASON_LANG_KEYS: dict = {
    Season.SPRING: "SPRING",
    Season.SUMMER: "SUMMER",
    Season.AUTUMN: "AUTUMN",
    Season.WINTER: "WINTER",
}


class GameHUD:
    """
    Renders a fixed top-right HUD overlay showing time, season, and day.

    Usage:
        hud = GameHUD(time_system, lang="fr")
        # In render loop (last draw call):
        hud.draw(screen)
    """

    def __init__(self, time_system: TimeSystem, lang: str = "fr") -> None:
        self.time_system = time_system
        self._lang = self._load_lang(lang)
        self._clock_surf = self._load_image("00-clock.png")
        self._season_surfs = self._load_season_icons()
        self._font = self._load_font()

    # ------------------------------------------------------------------
    # Asset loading helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hud_asset_path(filename: str) -> str:
        base = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "images", "HUD"
        )
        return os.path.normpath(os.path.join(base, filename))

    @staticmethod
    def _lang_path(lang: str) -> str:
        base = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "langs"
        )
        return os.path.normpath(os.path.join(base, f"{lang}.json"))

    def _load_lang(self, lang: str) -> dict:
        """Load the language file, falling back to empty defaults on error."""
        path = self._lang_path(lang)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"GameHUD: Could not load lang '{lang}': {e}. Using defaults.")
            return {"seasons": {}, "day_label": "Day"}

    def _load_image(self, filename: str) -> pygame.Surface:
        """Load a HUD image, returning a blank surface on failure."""
        path = self._hud_asset_path(filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            logging.error(f"GameHUD: Could not load image '{filename}': {e}")
            return pygame.Surface((390, 350), pygame.SRCALPHA)

    def _load_season_icons(self) -> dict:
        """Load and pre-scale all season icons."""
        icons = {}
        for season, filename in _SEASON_FILES.items():
            raw = self._load_image(filename)
            icons[season] = pygame.transform.smoothscale(
                raw, (SEASON_ICON_SIZE, SEASON_ICON_SIZE)
            )
        return icons

    @staticmethod
    def _load_font() -> pygame.font.Font:
        """Load the best available pixel-friendly font."""
        for name in ("freesansbold", "dejavusans", "sans-serif", None):
            try:
                return pygame.font.SysFont(name, FONT_SIZE, bold=True)
            except Exception:
                continue
        return pygame.font.Font(None, FONT_SIZE)

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_text_centered(
        self, surface: pygame.Surface, text: str, center: tuple
    ) -> None:
        """Draw text centered on `center` with a 1px black drop shadow."""
        shadow_surf = self._font.render(text, True, SHADOW_COLOR)
        shadow_rect = shadow_surf.get_rect(
            center=(center[0] + SHADOW_OFFSET, center[1] + SHADOW_OFFSET)
        )
        surface.blit(shadow_surf, shadow_rect)

        main_surf = self._font.render(text, True, TEXT_COLOR)
        main_rect = main_surf.get_rect(center=center)
        surface.blit(main_surf, main_rect)

    def _season_label(self) -> str:
        """Return localised season name."""
        key = _SEASON_LANG_KEYS[self.time_system.current_season]
        return self._lang.get("seasons", {}).get(key, key.capitalize())

    # ------------------------------------------------------------------
    # Public draw API
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        """Render the full HUD on `screen` (no camera offset applied)."""
        clock_w = self._clock_surf.get_width()
        hud_x = screen.get_width() - clock_w - HUD_MARGIN_X
        hud_y = HUD_MARGIN_Y

        # Base frame
        screen.blit(self._clock_surf, (hud_x, hud_y))

        # Season icon centred in the circular zone
        icon = self._season_surfs[self.time_system.current_season]
        icon_x = hud_x + SEASON_ICON_CENTER[0] - icon.get_width() // 2
        icon_y = hud_y + SEASON_ICON_CENTER[1] - icon.get_height() // 2
        screen.blit(icon, (icon_x, icon_y))

        # Time label — top-right zone
        self._render_text_centered(
            screen,
            self.time_system.time_label,
            (hud_x + TIME_ANCHOR[0], hud_y + TIME_ANCHOR[1]),
        )

        # Season / Day label — bottom zone (single line)
        wt = self.time_system.world_time
        day_label = self._lang.get("day_label", "Day")
        season_day_text = f"{self._season_label()} - {day_label} {wt.day + 1}"
        self._render_text_centered(
            screen,
            season_day_text,
            (hud_x + SEASON_DAY_ANCHOR[0], hud_y + SEASON_DAY_ANCHOR[1]),
        )
