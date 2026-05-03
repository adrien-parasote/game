import os

TILE_SIZE: int = 32
MIN_BUBBLE_SIZE: int = 2 * TILE_SIZE  # Minimum size to fit corners (64x64)
ASSET_DIR: str = os.path.join("assets", "images", "HUD")

_ARROW_OFFSET_X = 8
_ARROW_OFFSET_Y = -13
_PADDING_TOP = 20
_PADDING_BOTTOM = 0
_PADDING_X = 30
_TAIL_GAP = 20
_NAME_PLATE_OFFSET_X = 18
_NAME_PLATE_OFFSET_Y = -15

TILES: dict = {
    "bottom_right": "13-bubble_bottom_right.png",
    "bottom":       "14-bubble_bottom.png",
    "bottom_left":  "15-bubble_bottom_left.png",
    "left":         "17-bubble_left.png",
    "right":        "16-bubble_right.png",
    "top_right":    "18-bubble_top_right.png",
    "top":          "19-bubble_top.png",
    "top_left":     "20-bubble_top_left.png",
    "queue":        "21-bubble_queue.png",
    "arrow":        "22-bubble_arrow.png",
    "name_plate":   "23-bubble_name.png",
}
