import os

# ── Asset constants ────────────────────────────────────────────────────────────
_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

# Logo composite: 5 separate alpha-transparent PNGs assembled at runtime
LOGO_MAIN_W = 640          # main title scaled width
LOGO_ACCENT_H = 58         # moon/gear icon height
LOGO_SEP_W = 380           # separator width
LOGO_SUB_W = 380           # subtitle width
LOGO_Y = 30                # top of logo block on screen
LOGO_GAP = 6               # vertical gap between elements
LOGO_ZONE_W = 720          # left panel width — logo is centered within this zone

# Fine-tune moon/gear position (px, relative to default centred placement)
MOON_OFFSET_X = 25         # >0 → right,  <0 → left
MOON_OFFSET_Y = 55         # >0 → down,   <0 → up
GEAR_OFFSET_X = -25        # >0 → right,  <0 → left
GEAR_OFFSET_Y = 55         # >0 → down,   <0 → up

# Save slot spritesheet (04-save_slot.png 1024x1024, 2 states stacked)
SLOT_H_SRC = 512
SLOT_W_DST = 800
SLOT_H_DST = 120
SLOT_SPACING = 140
SLOT_PANEL_Y_START = 140   # inside the load panel overlay

# Semi-transparent overlay for load screen
OVERLAY_ALPHA = 180

# Right panel scroll banner
SCROLL_TITLE_X = 1000      # centre-x of the scroll text zone (pixels)
SCROLL_TITLE_Y = 80       # centre-y of the scroll text zone (pixels)
SCROLL_TITLE_OFFSET_X = 0  # fine-tune x  (>0 right, <0 left)
SCROLL_TITLE_OFFSET_Y = 0  # fine-tune y  (>0 down,  <0 up)
SCROLL_TITLE_FONT_SIZE = 50  # menu title font size (px)
SCROLL_TITLE_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"  # scroll title font
SCROLL_TITLE_COLOR = (72, 40, 12)   # sepia ink

# Right panel — menu items
MENU_ITEM_X = 1005          # centre-x of items (centre of text zone)
MENU_ITEM_Y_START = 360     # y of the first item
MENU_ITEM_SPACING = 80      # vertical spacing between items
MENU_ITEM_FONT_SIZE = 38    # item font size (px)
MENU_ITEM_COLOR = (220, 195, 140)        # warm gold on hover
MENU_ITEM_HOVER_COLOR = (255, 235, 180)  # bright gold on hover
MENU_ITEM_OFFSET_X = 0      # fine-tune x offset
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
