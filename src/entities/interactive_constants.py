"""
InteractiveEntity animation and physics constants.
Spec: docs/specs/entity-spec.md (interactive entities section)
"""

# Sprite sheet layout
INTERACTIVE_SHEET_COLS: int = 4         # Default columns per spritesheet row
INTERACTIVE_DUMMY_FRAME_COUNT: int = 16  # Fallback frame count for invisible/missing sprites
INTERACTIVE_POS_Y_OFFSET: int = 16     # Vertical offset from rect.bottom for world position

# Light mask pre-generation
LIGHT_MASK_CACHE_COUNT: int = 10        # Number of pre-scaled halo entries in light_mask_cache
LIGHT_MASK_SCALE_BASE: float = 0.97    # Base scale factor for the first bucket
LIGHT_MASK_SCALE_STEP: float = 0.0066  # Incremental scale per bucket step

# Animation speeds
ANIM_SPEED_LIGHT_SOURCE: float = 1.5   # Frame/s for animated light sources (torches, etc.)
ANIM_SPEED_OBJECT: float = 10.0        # Frame/s for non-light animated objects (doors, levers, etc.)

# Halo flicker — alpha (brightness) oscillation
FLICKER_ALPHA_AMPLITUDE: float = 0.12  # Main flicker brightness swing (±)
FLICKER_ALPHA_JITTER_SCALE: float = 0.3   # Secondary jitter wave scale
FLICKER_ALPHA_JITTER_AMP: float = 0.02    # Jitter random noise amplitude (animated entity)
FLICKER_ALPHA_NOISE_AMP: float = 0.01     # Random noise amplitude (static entity)

# Halo flicker — scale (size) oscillation
FLICKER_SCALE_AMPLITUDE: float = 0.03  # Halo size oscillation amplitude (±)

# Flicker wave frequencies (multipliers on time_sec in radians/s)
FLICKER_MAIN_FREQ: float = 1.5         # Primary candle flicker frequency (× π rad/s)
FLICKER_JITTER_FREQ: float = 4.2       # Secondary jitter frequency (× π rad/s)
FLICKER_SCALE_FREQ: float = 1.2        # Halo scale oscillation frequency (× π rad/s)
FLICKER_SCALE_PHASE_OFFSET: float = 0.5  # Phase offset for scale vs alpha waves

# Halo default fallback color when parsing fails
HALO_DEFAULT_COLOR: tuple = (255, 255, 255)

# Default halo opacity (0-255)
HALO_DEFAULT_ALPHA: int = 130
