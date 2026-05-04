"""
inventory_constants.py — Layout coordinates, dimensions, and asset paths for the Inventory UI.
"""

# ── Asset Paths ──────────────────────────────────────────────────────────────
INV_ASSET_BG = "01-inventory.png"
INV_ASSET_SLOT = "03-inventory_slot.png"
INV_ASSET_TAB = "02-active_tab.png"
INV_ASSET_HOVER = "04-inventory_slot_hover.png"
INV_ASSET_POINTER = "05-pointer.png"
INV_ASSET_POINTER_SELECT = "06-pointer_select.png"

# ── Dimensions & Scaling ─────────────────────────────────────────────────────
INV_TARGET_WIDTH = 1200
INV_ORIGINAL_CURSOR_HEIGHT = 535
INV_ORIGINAL_CURSOR_WIDTH = 309

# ── Layout Coordinates (Native 1344x704 scale) ───────────────────────────────
# These coordinates are scaled dynamically by the UI based on INV_TARGET_WIDTH.

# Tabs positions (RED zone)
INV_TAB_X_POSITIONS = [733, 863, 992, 1121]
INV_TAB_Y = 130

# Equipment Slots (MAGENTA zone - Left)
INV_EQUIP_RECT_SIDE = 78
INV_EQUIPMENT_SLOTS = {
    "HEAD": (354, 160),
    "BAG": (212, 290),
    "BELT": (211, 405),
    "LEFT_HAND": (242, 529),
    "UPPER_BODY": (499, 291),
    "LOWER_BODY": (498, 406),
    "RIGHT_HAND": (469, 529),
    "SHOES": (354, 549)
}

# Inventory Grid (BLUE zone - Right)
INV_GRID_START = (713, 219)
INV_GRID_COLS = 7
INV_GRID_ROWS = 4
INV_GRID_SPACING_X = 72
INV_GRID_SPACING_Y = 72

# Character Preview (ORANGE zone - Center Left)
INV_CHAR_PREVIEW_POS = (358, 311)
INV_CHAR_NAME_POS = (358, 410)

# Info Zone
INV_STATS_X = 695
INV_STATS_Y = 551
INV_INFO_MAX_W_OFFSET = 780
INV_HP_X = 929
INV_GOLD_X = 1160

# Drag-and-drop highlight
INV_DRAG_HIGHLIGHT_BORDER: int = 3      # Border width for drag-selected slot (px)
INV_DRAG_BORDER_RADIUS_BASE: int = 12   # Base border radius for drag highlight (before scale)
INV_STAT_NAME_OFFSET_Y: int = 16        # Item name label Y-offset in the stats panel (px)

# Fallback placeholder
INV_PLACEHOLDER_SIZE: int = 32          # Fallback surface size for missing assets (px)
