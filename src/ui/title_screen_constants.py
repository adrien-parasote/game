import os

# ── Asset constants ────────────────────────────────────────────────────────────
_MENU_DIR = os.path.join("assets", "images", "menu")
_UI_DIR = os.path.join("assets", "images", "ui")

# Logo composite: 3 separate alpha-transparent PNGs assembled at runtime
LOGO_MAIN_W = 640  # main title scaled width
LOGO_SEP_W = 380  # separator width
LOGO_SUB_W = 380  # subtitle width
LOGO_Y = 80  # center y of title text on screen
LOGO_GAP = 6  # vertical gap between elements
LOGO_ZONE_W = 1280  # full screen width to center the title
LOGO_MAIN_FONT_SIZE = 90
LOGO_MAIN_COLOR = (150, 255, 220)
LOGO_MAIN_HALO = (0, 180, 150)

# Save slot spritesheet (04-save_slot.png 1024x1024, 2 states stacked)
SLOT_H_SRC = 512
SLOT_W_DST = 800
SLOT_H_DST = 120
SLOT_SPACING = 140
SLOT_PANEL_Y_START = 140  # inside the load panel overlay

# Background animated lights — calibrated interactively via tools/calibrate_halos.py
# Each entry: (x, y, halo_radius)  — 45=lantern, 28=window, 18=small window
BACKGROUND_LIGHTS = [
    (443, 378, 45),  # lantern
    (546, 500, 45),  # lantern
    (790, 287, 45),  # lantern
    (861, 406, 45),  # lantern
    (458, 570, 28),  # window
    (752, 554, 28),  # window
    (831, 559, 28),  # window
    (787, 583, 28),  # window
    (390, 514, 28),  # window
    (230, 406, 18),  # small window
    (415, 456, 18),  # small window
    (444, 458, 18),  # small window
    (455, 511, 18),  # small window
    (403, 475, 18),  # small window
    (393, 583, 18),  # small window
    (427, 576, 18),  # small window
    (399, 557, 18),  # small window
    (490, 630, 28),  # window
    (482, 533, 18),  # small window
    (504, 575, 18),  # small window
    (785, 459, 18),  # small window
    (744, 363, 18),  # small window
    (770, 363, 18),  # small window
    (818, 456, 18),  # small window
    (827, 509, 18),  # small window
    (871, 484, 18),  # small window
    (858, 520, 18),  # small window
    (900, 496, 18),  # small window
    (1049, 367, 18),  # small window
    (1052, 408, 18),  # small window
    (1035, 538, 18),  # small window
    (856, 460, 18),  # small window
    (822, 607, 18),  # small window
]
BG_LIGHT_COLOR = (255, 120, 20)
HALO_DEBUG = False  # Set to True to re-enable calibration crosshairs

# Mushroom bioluminescent glows — filled by scripts/apply_calibration.py
# Format: (x, y, radius, (R, G, B))  — coords in logical 1280×720 space
MUSHROOM_LIGHTS = [
    (196, 520, 22, (70, 220, 200)),  # cyan large
    (217, 528, 22, (70, 220, 200)),  # cyan large
    (226, 546, 22, (70, 220, 200)),  # cyan large
    (207, 232, 22, (70, 220, 200)),  # cyan large
    (218, 251, 22, (70, 220, 200)),  # cyan large
    (354, 102, 22, (70, 220, 200)),  # cyan large
    (379, 84, 22, (70, 220, 200)),  # cyan large
    (1094, 495, 22, (70, 220, 200)),  # cyan large
    (1071, 518, 22, (70, 220, 200)),  # cyan large
    (1097, 516, 22, (70, 220, 200)),  # cyan large
    (1099, 237, 22, (70, 220, 200)),  # cyan large
    (1081, 255, 22, (70, 220, 200)),  # cyan large
    (1005, 37, 22, (70, 220, 200)),  # cyan large
    (822, 54, 16, (70, 220, 200)),  # cyan medium
    (839, 60, 16, (70, 220, 200)),  # cyan medium
    (849, 68, 16, (70, 220, 200)),  # cyan medium
    (1118, 524, 16, (70, 220, 200)),  # cyan medium
    (212, 452, 16, (70, 220, 200)),  # cyan medium
    (214, 435, 16, (70, 220, 200)),  # cyan medium
    (193, 441, 11, (70, 220, 200)),  # cyan small
    (295, 345, 11, (70, 220, 200)),  # cyan small
    (299, 350, 11, (70, 220, 200)),  # cyan small
    (323, 353, 11, (70, 220, 200)),  # cyan small
    (331, 347, 11, (70, 220, 200)),  # cyan small
    (332, 354, 11, (70, 220, 200)),  # cyan small
]

# Semi-transparent overlay for load screen
OVERLAY_ALPHA = 180

MENU_FONT_PATH = "assets/fonts/cormorant-garamond-regular.ttf"  # general menu font

# Right panel — menu items
MENU_ITEM_X = 1005  # centre-x of items (centre of text zone)
MENU_ITEM_Y_START = 360  # y of the first item
MENU_ITEM_SPACING = 80  # vertical spacing between items
MENU_ITEM_FONT_SIZE = 38  # item font size (px)
MENU_HOVER_COLOR = (150, 255, 220)  # bright cyan on hover
MENU_HOVER_HALO = (0, 180, 150)  # cyan glow on hover
MENU_ITEM_OFFSET_X = 50  # fine-tune x offset
MENU_ITEM_OFFSET_Y = 0  # fine-tune y offset

# "Engraved in stone" effect for idle state
MENU_ENGRAVE_TEXT = (45, 65, 75)  # text: slightly lighter than stone
MENU_ENGRAVE_SHADOW = (12, 20, 23)  # shadow (top-left -1,-1): engraving depth
MENU_ENGRAVE_LIGHT = (90, 120, 130)  # highlight (bottom-right +1,+1): lit edge

_MENU_ITEM_KEYS = ["menu.new_game", "menu.load", "menu.options", "menu.quit"]
_MENU_ITEM_DEFAULTS = ["Nouvelle Partie", "Charger", "Options", "Quitter"]

# Options back button
BACK_BTN_W = 28  # render width (1/2 native)
BACK_BTN_H = 25  # render height (1/2 native)
BACK_BTN_X = 1005  # centre-x (same axis as items)
BACK_BTN_Y = 620  # centre-y (bottom of the panel)
BACK_BTN_OFFSET_X = -50  # fine-tune x (centred on text+icon)
BACK_BTN_OFFSET_Y = 0  # fine-tune y
BACK_BTN_GAP = 6  # space between the text and the icon
BACK_BTN_FONT_SIZE = 22  # label size
BACK_BTN_LABEL_KEY = "menu.back"  # i18n key
BACK_BTN_LABEL_DEFAULT = "Retour"  # default value
