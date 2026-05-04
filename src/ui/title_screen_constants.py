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

# Background animated lights — calibrated interactively via tools/calibrate_halos.py
# Each entry: (x, y, halo_radius)  — 45=lanterne, 28=fenêtre, 18=petite fenêtre
BACKGROUND_LIGHTS = [
    ( 443,  378, 45),  # lanterne
    ( 546,  500, 45),  # lanterne
    ( 790,  287, 45),  # lanterne
    ( 861,  406, 45),  # lanterne
    ( 458,  570, 28),  # fenêtre
    ( 752,  554, 28),  # fenêtre
    ( 831,  559, 28),  # fenêtre
    ( 787,  583, 28),  # fenêtre
    ( 390,  514, 28),  # fenêtre
    ( 230,  406, 18),  # petite fenêtre
    ( 415,  456, 18),  # petite fenêtre
    ( 444,  458, 18),  # petite fenêtre
    ( 455,  511, 18),  # petite fenêtre
    ( 403,  475, 18),  # petite fenêtre
    ( 393,  583, 18),  # petite fenêtre
    ( 427,  576, 18),  # petite fenêtre
    ( 399,  557, 18),  # petite fenêtre
    ( 490,  630, 28),  # fenêtre
    ( 482,  533, 18),  # petite fenêtre
    ( 504,  575, 18),  # petite fenêtre
    ( 785,  459, 18),  # petite fenêtre
    ( 744,  363, 18),  # petite fenêtre
    ( 770,  363, 18),  # petite fenêtre
    ( 818,  456, 18),  # petite fenêtre
    ( 827,  509, 18),  # petite fenêtre
    ( 871,  484, 18),  # petite fenêtre
    ( 858,  520, 18),  # petite fenêtre
    ( 900,  496, 18),  # petite fenêtre
    (1049,  367, 18),  # petite fenêtre
    (1052,  408, 18),  # petite fenêtre
    (1035,  538, 18),  # petite fenêtre
    ( 856,  460, 18),  # petite fenêtre
    ( 822,  607, 18),  # petite fenêtre
]
BG_LIGHT_COLOR = (255, 120, 20)
HALO_DEBUG = False  # Set to True to re-enable calibration crosshairs

# Mushroom bioluminescent glows — filled by scripts/apply_calibration.py
# Format: (x, y, radius, (R, G, B))  — coords in logical 1280×720 space
MUSHROOM_LIGHTS = [
    (1087,  513, 40, ( 70, 220, 200)),  # cyan large
    (1006,   40, 20, ( 70, 220, 200)),  # cyan petit
    ( 297,  350, 20, ( 70, 220, 200)),  # cyan petit
    ( 326,  351, 20, ( 70, 220, 200)),  # cyan petit
    ( 207,  534, 40, ( 70, 220, 200)),  # cyan large
    ( 208,  247, 40, ( 70, 220, 200)),  # cyan large
    ( 206,  446, 40, ( 70, 220, 200)),  # cyan large
    (1104,  242, 28, ( 70, 220, 200)),  # cyan medium
    (1081,  255, 28, ( 70, 220, 200)),  # cyan medium
    ( 816,   51, 20, ( 70, 220, 200)),  # cyan petit
    ( 838,   60, 20, ( 70, 220, 200)),  # cyan petit
    ( 851,   70, 20, ( 70, 220, 200)),  # cyan petit
    ( 386,   85, 40, ( 70, 220, 200)),  # cyan large
    ( 352,  106, 40, ( 70, 220, 200)),  # cyan large
]

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