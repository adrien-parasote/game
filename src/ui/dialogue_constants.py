"""
DialogueManager layout constants — box margins and text positioning.
Spec: docs/specs/dialogue-spec.md
"""

# Horizontal text margin inside the dialogue box (px from the box left edge)
DIALOGUE_CONTENT_MARGIN_X: int = 140

# Vertical offset of the message text from the top of the dialogue box
DIALOGUE_MSG_Y_OFFSET_TITLED: int = 90   # When a title/speaker label is present
DIALOGUE_MSG_Y_OFFSET_PLAIN: int = 42    # Without a title

# Y offset of the "next page" arrow from the top of the dialogue box
DIALOGUE_ARROW_Y_OFFSET: int = 140
