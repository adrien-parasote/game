import os

# ── Asset constants ────────────────────────────────────────────────────────────
_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

# Logo composite: 3 separate alpha-transparent PNGs assembled at runtime
LOGO_MAIN_W = 640          # main title scaled width
LOGO_SEP_W = 380           # separator width
LOGO_SUB_W = 380           # subtitle width
LOGO_Y = 80                # center y of title text on screen
LOGO_GAP = 6               # vertical gap between elements
LOGO_ZONE_W = 1280         # full screen width to center the title
LOGO_MAIN_FONT_SIZE = 90
LOGO_MAIN_COLOR = (150, 255, 220)
LOGO_MAIN_HALO = (0, 180, 150)

# Save slot spritesheet (04-save_slot.png 1024x1024, 2 states stacked)
SLOT_H_SRC = 512
SLOT_W_DST = 800
SLOT_H_DST = 120
SLOT_SPACING = 140
SLOT_PANEL_Y_START = 140   # inside the load panel overlay

# Background animated lights — positions calibrated from image analysis
BACKGROUND_LIGHTS = [
    (443, 370),   # lantern left (hanging)
    (548, 497),   # lantern center-left (hanging)
    (789, 278),   # lantern top-right (hanging)
    (872, 455),   # lantern right (hanging)
    (416, 596),   # city window bottom-left
    (463, 582),   # city window cluster left
    (850, 430),   # castle right glow
]
BG_LIGHT_COLOR = (255, 120, 20)
BG_LIGHT_RADIUS = 45

# Semi-transparent overlay for load screen
OVERLAY_ALPHA = 180

MENU_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"  # general menu font

# Right panel — menu items
MENU_ITEM_X = 1005          # centre-x of items (centre of text zone)
MENU_ITEM_Y_START = 360     # y of the first item
MENU_ITEM_SPACING = 80      # vertical spacing between items
MENU_ITEM_FONT_SIZE = 38    # item font size (px)
MENU_HOVER_COLOR = (150, 255, 220)       # bright cyan on hover
MENU_HOVER_HALO = (0, 180, 150)          # cyan glow on hover
MENU_ITEM_OFFSET_X = 50      # fine-tune x offset
MENU_ITEM_OFFSET_Y = 0      # fine-tune y offset

# "Engraved in stone" effect for idle state
MENU_ENGRAVE_TEXT   = (58, 85, 92)   # text: slightly lighter than stone
MENU_ENGRAVE_SHADOW = (12, 20, 23)   # shadow (bottom-right +1,+2): engraving depth
MENU_ENGRAVE_LIGHT  = (75, 105, 112) # highlight (top-left -1,-1): lit edge

_MENU_ITEM_KEYS = ["menu.new_game", "menu.load", "menu.options", "menu.quit"]
_MENU_ITEM_DEFAULTS = ["Nouvelle Partie", "Charger", "Options", "Quitter"]

# Options back button
BACK_BTN_W = 28           # render width (1/2 native)
BACK_BTN_H = 25           # render height (1/2 native)
BACK_BTN_X = 1005         # centre-x (same axis as items)
BACK_BTN_Y = 620          # centre-y (bottom of the panel)
BACK_BTN_OFFSET_X = -50    # fine-tune x (centred on text+icon)
BACK_BTN_OFFSET_Y = 0     # fine-tune y
BACK_BTN_GAP = 6          # space between the text and the icon
BACK_BTN_FONT_SIZE = 22   # label size
BACK_BTN_LABEL_KEY = "menu.back"   # i18n key
BACK_BTN_LABEL_DEFAULT = "Retour"  # default value
