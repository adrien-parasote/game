import os

_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"

OVERLAY_ALPHA = 160

# Panel — 02-panel_background.png (600x600 → 480x480)
PANEL_W = 480
PANEL_H = 480

# Inner content area offsets from panel edges (gear decorations)
INNER_TOP = 60  # px from panel top to inner stone area
INNER_BOTTOM = 60  # px from panel bottom to inner stone area

# Layout offsets from panel top
PAUSE_TITLE_OFFSET = 105  # y offset of the title from the top of the panel
ITEM_Y_START_OFFSET = 170  # y offset of the first item from the top of the panel
ITEM_SPACING = 60  # vertical spacing between items

# Font sizes
PAUSE_TITLE_FONT_SIZE = 42
PAUSE_ITEM_FONT_SIZE = 32

# Colors — identical to TitleScreen
ENGRAVE_TEXT = (45, 65, 75)
ENGRAVE_SHADOW = (12, 20, 23)
ENGRAVE_LIGHT = (90, 120, 130)
HOVER_COLOR = (255, 235, 180)
TITLE_COLOR = (220, 195, 140)

_BUTTON_KEYS = ["pause_menu.main_menu", "pause_menu.resume", "pause_menu.save"]
_BUTTON_DEFAULTS = ["Menu Principal", "Reprendre", "Sauvegarder"]

# Cursor source image raw dimensions (px) — used to compute scaled ratio
CURSOR_RAW_H: int = 535
CURSOR_RAW_W: int = 309

# Fallback surface size for error placeholders
FALLBACK_SURF_SIZE: int = 32

# Panel fallback colors (used when panel PNG fails to load)
PANEL_FALLBACK_FILL: tuple[int, int, int, int] = (10, 18, 22, 210)
PANEL_FALLBACK_BORDER: tuple[int, int, int] = (60, 80, 85)

# Font sizes
PAUSE_SUCCESS_FONT_SIZE: int = 26

# Button click zone dimensions
PAUSE_BTN_W: int = 280
PAUSE_BTN_H: int = 50

# Menu item hover colors
HOVER_TEXT_COLOR: tuple[int, int, int] = (180, 230, 255)
HOVER_HALO_COLOR: tuple[int, int, int] = (40, 120, 255)

# Save confirmation feedback colors and timing
SUCCESS_COLOR: tuple[int, int, int] = (180, 220, 150)
CONFIRM_DISPLAY_SECONDS: float = 2.0
CONFIRM_MSG_MARGIN_BOTTOM: int = 40

# Halo blur parameters
HALO_BLUR_PADDING: int = 24
HALO_BLUR_RADIUS: int = 8
