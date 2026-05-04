"""
LightingManager constants — beam shape defaults and overlay tuning values.
Spec: docs/specs/lighting-spec.md
"""

# Window beam shape defaults (pixels).
# Per-window top widths may override BEAM_TOP_WIDTH via Tiled object properties.
BEAM_TOP_WIDTH: int = 24  # Default top width of window light trapezoid (px)
BEAM_BOTTOM_WIDTH: int = 52  # Default bottom width of window light trapezoid (px)
BEAM_HEIGHT: int = 70  # Default height of window light beam (px)

# Sun/moon slant — horizontal drift of the beam over its full height.
# Sun swings between -BEAM_MAX_SLANT (evening/west) and +BEAM_MAX_SLANT (morning/east).
BEAM_MAX_SLANT: int = 28  # Max horizontal drift over the full beam height (px)

# Night overlay alpha composition
OVERLAY_BASE_ALPHA: float = 0.25  # Minimum brightness fraction (fully night)
OVERLAY_ALPHA_RANGE: float = 0.50  # Dynamic brightness range fraction

# Cache tuning
SLANT_ROUND_STEP: int = 2  # Round beam slant to nearest N px to reduce cache churn
TORCH_ALPHA_QUANTIZE: int = 20  # Intensity quantization step for torch mask cache key
