import os

_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"

OVERLAY_ALPHA = 160

# Panel — 02-panel_background.png (600x600 → 480x480)
PANEL_W = 480
PANEL_H = 480

# Inner content area offsets from panel edges (gear decorations)
INNER_TOP = 60        # px from panel top to inner stone area
INNER_BOTTOM = 60     # px from panel bottom to inner stone area

# Layout offsets from panel top
PAUSE_TITLE_OFFSET = 105    # y offset of the title from the top of the panel
ITEM_Y_START_OFFSET = 170  # y offset of the first item from the top of the panel
ITEM_SPACING = 60          # vertical spacing between items

# Font sizes
PAUSE_TITLE_FONT_SIZE = 42
PAUSE_ITEM_FONT_SIZE = 32

# Colors — identical to TitleScreen
ENGRAVE_TEXT   = (45, 65, 75)
ENGRAVE_SHADOW = (12, 20, 23)
ENGRAVE_LIGHT  = (90, 120, 130)
HOVER_COLOR    = (255, 235, 180)
TITLE_COLOR    = (220, 195, 140)

_BUTTON_KEYS = ["pause_menu.main_menu", "pause_menu.resume", "pause_menu.save"]
_BUTTON_DEFAULTS = ["Menu Principal", "Reprendre", "Sauvegarder"]
