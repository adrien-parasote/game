"""
Shared UI color palette — used across inventory, chest, dialogue and pause screens.

All colors are (R, G, B) tuples intended for pygame font.render / draw calls.
Do not add layout values here — per-module _constants.py files own those.
"""

# Text colors
COLOR_TEXT_STONE: tuple = (60, 40, 30)         # Parchment/stone engraved text (inventory, chest, dialogue)
COLOR_TEXT_EMPTY: tuple = (140, 120, 100)       # Dimmed label for empty slots

# Selection and highlight
COLOR_HIGHLIGHT_GOLD: tuple = (255, 215, 0)    # Gold border for active drag-selected slot
COLOR_HIGHLIGHT_GOLD_HALO: tuple = (255, 160, 40)  # Golden/orange halo glow center

# Slot borders
COLOR_SLOT_BORDER: tuple = (200, 200, 200)     # Idle slot border
COLOR_SLOT_BORDER_HOVER: tuple = (180, 180, 180)   # Hovered slot border

# Debug / fallback
COLOR_DEBUG_MISSING: tuple = (255, 0, 255)     # Magenta placeholder for missing assets
COLOR_DEBUG_RECT: tuple = (255, 0, 0)          # Red debug rect overlay
