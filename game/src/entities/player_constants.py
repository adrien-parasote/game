"""
Player entity constants.
Spec: game/docs/specs/entities-system.md
"""

# Spritesheet layout
PLAYER_SPRITESHEET_COLS: int = 4
PLAYER_SPRITESHEET_ROWS: int = 4

# Animation
PLAYER_ANIM_FRAME_DURATION: float = 0.15  # seconds per frame
PLAYER_FRAMES_PER_ROW: int = 4

# Direction row offsets in spritesheet
PLAYER_ROW_OFFSETS: dict[str, int] = {"down": 0, "left": 4, "right": 8, "up": 12}

# Audio
PLAYER_FOOTSTEP_FRAMES: tuple[int, int] = (1, 3)  # animation frame indices that trigger footstep
PLAYER_FOOTSTEP_VOLUME: float = 0.15

# Starting stats
PLAYER_INITIAL_LEVEL: int = 1
PLAYER_INITIAL_HP: int = 100
PLAYER_INITIAL_GOLD: int = 0
