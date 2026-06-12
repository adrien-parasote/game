"""
Engine-level constants — placeholder and fallback colors.
These colors appear in error/missing-asset rendering paths only (never in production UI).
Spec: game/docs/specs/code-quality-constants-i18n.md § F-QUAL-02-A
"""

# Fallback colors for missing or fallback assets (debug-visible, non-production)
COLOR_PLACEHOLDER_MAGENTA: tuple[int, int, int] = (255, 0, 255)
COLOR_PLACEHOLDER_BLUE: tuple[int, int, int] = (0, 0, 255)

# SpriteSheet fallback dimensions (used when image load fails)
SPRITESHEET_FALLBACK_SIZE: tuple[int, int] = (32, 32)
SPRITESHEET_FALLBACK_FRAME_COUNT: int = 16

# Map layer depth threshold for grass-eligible tiles
GRASS_MAX_DEPTH: int = 1

# Tiled project file path (relative to workspace root)
TILED_PROJECT_PATH: str = "assets/tiled/game.tiled-project"
