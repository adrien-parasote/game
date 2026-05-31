from src.engine.time_system import Season

HUD_SCALE: float = 0.4  # Scale factor for the large original HUD asset

SEASON_ICON_CENTER: tuple = (int(313 * HUD_SCALE), int(279 * HUD_SCALE))
TIME_ANCHOR: tuple = (int(255 * HUD_SCALE), int(98 * HUD_SCALE))
SEASON_DAY_ANCHOR: tuple = (int(155 * HUD_SCALE), int(284 * HUD_SCALE))  # Slightly adjusted

SEASON_ICON_SIZE: int = int(147 * HUD_SCALE)  # Circular icon native size is ~147px

HUD_MARGIN_X: int = 20  # Pixels from right edge
HUD_MARGIN_Y: int = 20  # Pixels from top edge

TEXT_COLOR: tuple = (240, 235, 210)  # Warm off-white
SHADOW_COLOR: tuple = (0, 0, 0)
SHADOW_OFFSET: int = 1
FONT_SIZE: int = 12  # Technical data size

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
