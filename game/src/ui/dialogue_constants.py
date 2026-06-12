"""
DialogueManager layout constants — box margins and text positioning.
Spec: game/docs/specs/dialogue-spec.md
"""

# Horizontal text margin inside the dialogue box (px from the box left edge)
DIALOGUE_CONTENT_MARGIN_X: int = 140

# Vertical offset of the message text from the top of the dialogue box
DIALOGUE_MSG_Y_OFFSET_TITLED: int = 90  # When a title/speaker label is present
DIALOGUE_MSG_Y_OFFSET_PLAIN: int = 42  # Without a title

# Y offset of the "next page" arrow from the top of the dialogue box
DIALOGUE_ARROW_Y_OFFSET: int = 140

# Text rendering colors (parchment theme)
DIALOGUE_SHADOW_COLOR: tuple[int, int, int] = (180, 170, 150)  # Light shadow on parchment
DIALOGUE_TEXT_COLOR: tuple[int, int, int] = (60, 40, 30)  # Dark brown, high contrast

# Layout and display
DIALOGUE_SCALE: float = 0.5  # scale factor for dialogue panel relative to screen
DIALOGUE_FONT_SCALE: float = 1.5  # multiplier applied to narrative/noble font sizes
DIALOGUE_BOTTOM_MARGIN: int = 40  # px margin from bottom of available height
DIALOGUE_LINE_SPACING: float = 1.2  # line spacing multiplier
DIALOGUE_BOX_BOTTOM_INSET: int = 20  # px inset from WINDOW_HEIGHT for box bottom edge
DIALOGUE_SHADOW_OFFSET: int = 1  # text shadow offset in pixels
DIALOGUE_ARROW_X_INSET: int = 10  # px inset for continue arrow from right margin
