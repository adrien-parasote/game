"""
GameStateManager constants — save thumbnail sizing and audio fade timings.
Spec: docs/specs/game-flow-spec.md
"""

# Save thumbnail generation
THUMBNAIL_CROP_SIZE: int = 246   # Square world-space crop centered on player (px), ~3× zoom-out
THUMBNAIL_SIZE: int = 82         # Final thumbnail size written to disk and shown in save slot (px)

# BGM transition
SAVE_BGM_FADE_MS: int = 500      # BGM fade-out duration when returning to title (ms)

# Player stat defaults — used when restoring a save file that lacks these fields
PLAYER_DEFAULT_HP: int = 100
PLAYER_DEFAULT_MAX_HP: int = 100
PLAYER_DEFAULT_LEVEL: int = 1
PLAYER_DEFAULT_GOLD: int = 0
