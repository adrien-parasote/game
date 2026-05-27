"""
Engine-level constants — placeholder and fallback colors.
These colors appear in error/missing-asset rendering paths only (never in production UI).
Spec: docs/specs/code-quality-constants-i18n.md § F-QUAL-02-A
"""

# Fallback colors for missing or fallback assets (debug-visible, non-production)
COLOR_PLACEHOLDER_MAGENTA: tuple[int, int, int] = (255, 0, 255)
COLOR_PLACEHOLDER_BLUE: tuple[int, int, int] = (0, 0, 255)
