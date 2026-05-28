"""
SaveMenu UI constants — layout, colors, dimensions.
Spec: docs/game/specs/perf-constants-spec.md#feature-p-const-01e--save-menu-constants-new-file
"""

from src.ui.pause_screen_constants import ENGRAVE_LIGHT, ENGRAVE_SHADOW, ENGRAVE_TEXT
from src.ui.ui_colors import COLOR_TEXT_STONE

# ---------------------------------------------------------------------------
# SaveSlotUI — slot background card (source asset: 427×200 px)
# ---------------------------------------------------------------------------
SAVE_SLOT_BG_W: int = 427
SAVE_SLOT_BG_H: int = 200

# Hover halo radius on gem corners
SAVE_SLOT_HALO_RADIUS: int = 45
SAVE_SLOT_GEM_COORDS: list[tuple[int, int]] = [
    (26, 27),
    (413, 27),
    (26, 170),
    (414, 171),
]

# Thumbnail sub-rect within the 427×200 card (px from card origin)
SAVE_THUMB_X: int = 56
SAVE_THUMB_Y: int = 59
SAVE_THUMB_SIZE: int = 82

# Fallback draw colors (when background PNG is unavailable)
SAVE_THUMB_BG_COLOR: tuple[int, int, int] = (20, 20, 20)
SAVE_THUMB_BORDER_COLOR: tuple[int, int, int] = (80, 80, 80)
SAVE_SLOT_FALLBACK_BG: tuple[int, int, int, int] = (30, 30, 30, 200)
SAVE_SLOT_FALLBACK_BORDER: tuple[int, int, int] = (100, 100, 100)

# Text colors
SAVE_TITLE_COLOR: tuple[int, int, int] = (220, 200, 150)
SAVE_DETAIL_COLOR: tuple[int, int, int] = COLOR_TEXT_STONE  # (60, 40, 30) — from ui_colors.py

# Detail text layout (px from card origin)
SAVE_DETAIL_TEXT_X_OFFSET: int = 180
SAVE_DETAIL_TEXT_Y_OFFSET: int = 70
SAVE_DETAIL_LINE_SPACING: int = 30

# ---------------------------------------------------------------------------
# SaveMenuOverlay — full-screen panel
# ---------------------------------------------------------------------------
SAVE_PANEL_W: int = 600
SAVE_PANEL_H: int = 800
SAVE_PANEL_FILL: tuple[int, int, int, int] = (10, 18, 22, 220)
SAVE_PANEL_Y_OFFSET: int = 30   # shift from vertical center
SAVE_SLOT_SPACING: int = 20     # px gap between slot cards

# ---------------------------------------------------------------------------
# Back button
# ---------------------------------------------------------------------------
BACK_ICON_W: int = 28
BACK_ICON_H: int = 25
BACK_ICON_HOVER_W: int = 32
BACK_ICON_HOVER_H: int = 29
BACK_BTN_W: int = 140
BACK_BTN_H: int = 40
BACK_FONT_SIZE: int = 22
BACK_FONT_PATH: str = "assets/fonts/cormorant-garamond-regular.ttf"
BACK_TEXT_COLOR: tuple[int, int, int] = (150, 255, 220)
BACK_HALO_COLOR: tuple[int, int, int] = (0, 180, 150)
BACK_LABEL_GAP: int = 8   # px between icon and label

# Engraving colors (re-exported from pause_screen_constants — canonical source)
__all__ = [
    "ENGRAVE_TEXT",
    "ENGRAVE_SHADOW",
    "ENGRAVE_LIGHT",
]

# Halo blur parameters for back button
SAVE_HALO_BLUR_PADDING: int = 20
SAVE_HALO_BLUR_RADIUS: int = 6

# Font fallback size
SAVE_FONT_TITLE_FALLBACK_SIZE: int = 48
