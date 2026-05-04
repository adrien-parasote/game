# src/ui/chest_constants.py
"""Chest UI constants and asset paths."""

import os

# ---------------------------------------------------------------------------
# Asset paths (relative to project root)
# ---------------------------------------------------------------------------
ASSET_CHEST_BG = os.path.join("assets", "images", "HUD", "07-chest.png")
ASSET_INV_BG = os.path.join("assets", "images", "HUD", "12-inventory.png")
ASSET_SLOT_IMG = os.path.join("assets", "images", "ui", "03-inventory_slot.png")
ASSET_SLOT_HOVER = os.path.join("assets", "images", "ui", "04-inventory_slot_hover.png")
ASSET_POINTER = os.path.join("assets", "images", "ui", "05-pointer.png")
ASSET_POINTER_SELECT = os.path.join("assets", "images", "ui", "06-pointer_select.png")
ASSET_ARROW_DOWN_HOVER = os.path.join("assets", "images", "HUD", "08-arrow_down.png")
ASSET_ARROW_UP_HOVER = os.path.join("assets", "images", "HUD", "09-arrow_up.png")
ASSET_ARROW_LEFT_HOVER = os.path.join("assets", "images", "HUD", "10-arrow_left.png")
ASSET_ARROW_RIGHT_HOVER = os.path.join("assets", "images", "HUD", "11-arrow_right.png")

# ---------------------------------------------------------------------------
# Chest panel layout constants
# ---------------------------------------------------------------------------
_TITLE_ZONE_REL = (0.29, 0.02, 0.71, 0.23)
_CONTENT_ZONE_REL = (0.11, 0.27, 0.89, 0.93)
_SLOT_COLS = 10
_SLOT_ROWS = 2
_GRID_OFFSET_Y = -23
_TITLE_OFFSET_X = 10
_TITLE_OFFSET_Y = 8
_TARGET_WIDTH = 900

# Arrow button zones (measured from 1200px source)
_ARROW_UP_ZONE_REL = (0.7233, 0.8294, 0.7625, 0.9500)
_ARROW_DOWN_ZONE_REL = (0.7942, 0.8294, 0.8333, 0.9500)
_ARROW_OFFSET_X = 1
_ARROW_OFFSET_Y = 1

# ---------------------------------------------------------------------------
# Player inventory panel layout constants
# ---------------------------------------------------------------------------
_INV_TARGET_WIDTH = 1280  # Full screen width
_INV_SLOT_COLS = 18  # Slots visible at once
_INV_SLOT_ROWS = 1
_INV_SLOTS_VISIBLE = _INV_SLOT_COLS * _INV_SLOT_ROWS  # 18
_INV_CONTENT_ZONE_REL = (0.05, 0.05, 0.95, 0.95)
_INV_GRID_OFFSET_X = 0  # Fine-tune escape hatch
_INV_GRID_OFFSET_Y = 15  # Fine-tune escape hatch
_INV_ARROW_ZONE_W = 60  # px — hit zone size for left/right arrows
_INV_ARROW_EDGE_OFFSET = 20  # px — inset from the panel edge
