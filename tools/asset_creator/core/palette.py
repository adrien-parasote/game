"""Palette system for the Asset Creator Tool.

Defines color palettes with named roles (shadow, base, highlight, accent)
loaded from YAML configuration files. V2 adds optional ramp configuration
for hue-shifted extended color ramps via OKLCh color space.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from tools.asset_creator.core.color_ramp import (
    generate_hue_shifted_ramp,
    interpolate_oklch,
)

if TYPE_CHECKING:
    pass


class PaletteRole(Enum):
    """Semantic role for a color in a palette."""

    SHADOW = "shadow"
    BASE = "base"
    HIGHLIGHT = "highlight"
    ACCENT = "accent"


@dataclass(frozen=True)
class RampConfig:
    """V2 ramp generation parameters.

    Attributes:
        base_color: Anchor RGB color for the ramp midpoint.
        steps: Number of colors in the generated ramp (typically 7-11).
        shadow_hue_shift: Hue shift in degrees for darkest shadow.
        highlight_hue_shift: Hue shift in degrees for brightest highlight.
        lightness_range: Total lightness spread around the base.
    """

    base_color: tuple[int, int, int]
    steps: int = 9
    shadow_hue_shift: float = -30.0
    highlight_hue_shift: float = 20.0
    lightness_range: float = 0.35


@dataclass(frozen=True)
class Palette:
    """Immutable color palette with named roles.

    Attributes:
        name: Human-readable palette name (e.g. 'forest_grass').
        colors: Tuple of RGB color tuples (0-255 per channel).
        roles: Mapping from PaletteRole to color index in the colors tuple.
        ramp_config: Optional V2 ramp generation parameters.
    """

    name: str
    colors: tuple[tuple[int, int, int], ...]
    roles: dict[PaletteRole, int]
    ramp_config: RampConfig | None = field(default=None)

    def get_color(self, role: PaletteRole) -> tuple[int, int, int]:
        """Return the RGB color tuple assigned to the given role.

        Args:
            role: The palette role to look up.

        Returns:
            RGB tuple (r, g, b) with values 0-255.
        """
        return self.colors[self.roles[role]]

    def get_role_colors(self) -> dict[PaletteRole, tuple[int, int, int]]:
        """Return a mapping of all roles to their RGB color tuples.

        Returns:
            Dict mapping each PaletteRole to its (r, g, b) color.
        """
        return {role: self.colors[idx] for role, idx in self.roles.items()}

    @property
    def extended_colors(self) -> tuple[tuple[int, int, int], ...]:
        """Extended color ramp (typically 7-11 colors).

        If ramp_config is present, generates a hue-shifted ramp.
        Otherwise, returns the original V1 colors.
        """
        if self.ramp_config is not None:
            return tuple(generate_hue_shifted_ramp(
                self.ramp_config.base_color,
                num_steps=self.ramp_config.steps,
                shadow_hue_shift=self.ramp_config.shadow_hue_shift,
                highlight_hue_shift=self.ramp_config.highlight_hue_shift,
                lightness_range=self.ramp_config.lightness_range,
            ))
        return self.colors

    def interpolate(self, t: float) -> tuple[int, int, int]:
        """Map a value in [0,1] to a color on the extended ramp.

        Uses OKLCh interpolation between adjacent ramp colors.

        Args:
            t: Position in the ramp. 0.0 = darkest, 1.0 = brightest.

        Returns:
            Interpolated RGB color tuple.
        """
        colors = self.extended_colors
        t = max(0.0, min(1.0, t))
        n = len(colors) - 1
        idx = t * n
        lower = int(idx)
        upper = min(lower + 1, n)
        frac = idx - lower

        if frac < 0.001:
            return colors[lower]
        return interpolate_oklch(colors[lower], colors[upper], frac)


_HEX_PATTERN = re.compile(r"^#([0-9a-fA-F]{6})$")


def _parse_hex_color(hex_str: str) -> tuple[int, int, int]:
    """Parse a hex color string like '#2d5a1e' into an RGB tuple.

    Args:
        hex_str: Color in '#RRGGBB' format.

    Returns:
        Tuple of (red, green, blue) integers 0-255.

    Raises:
        ValueError: If the string is not a valid hex color.
    """
    match = _HEX_PATTERN.match(hex_str.strip())
    if match is None:
        raise ValueError(
            f"Invalid hex color '{hex_str}'. Expected format: '#RRGGBB' "
            f"(e.g. '#2d5a1e')."
        )
    hex_digits = match.group(1)
    return (
        int(hex_digits[0:2], 16),
        int(hex_digits[2:4], 16),
        int(hex_digits[4:6], 16),
    )


def _validate_yaml_fields(data: dict) -> None:
    """Validate that required fields exist in the palette YAML data.

    Args:
        data: Parsed YAML dictionary.

    Raises:
        ValueError: If any required field is missing.
    """
    for req_field in ("name", "colors", "roles"):
        if req_field not in data:
            raise ValueError(
                f"Palette YAML is missing required field '{req_field}'. "
                f"Expected fields: name, colors, roles."
            )


def load_palette(path: Path) -> Palette:
    """Load a palette from a YAML file.

    YAML format:
        name: forest_grass
        colors:
          - "#2d5a1e"
          - "#3e7c27"
        roles:
          shadow: 0
          base: 1

    Args:
        path: Path to the YAML palette file.

    Returns:
        An immutable Palette instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the YAML content is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Palette file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Palette file must contain a YAML mapping, got: {type(raw)}")

    _validate_yaml_fields(raw)

    raw_colors = raw["colors"]
    if not isinstance(raw_colors, list) or len(raw_colors) < 2:
        raise ValueError(
            f"Palette '{raw['name']}' must have at least 2 colors, "
            f"got {len(raw_colors) if isinstance(raw_colors, list) else 0}."
        )

    colors = tuple(_parse_hex_color(c) for c in raw_colors)

    raw_roles = raw["roles"]
    if not isinstance(raw_roles, dict):
        raise ValueError(
            f"Palette '{raw['name']}' roles must be a mapping, got: {type(raw_roles)}"
        )

    roles: dict[PaletteRole, int] = {}
    for role_name, idx in raw_roles.items():
        try:
            role = PaletteRole(role_name)
        except ValueError:
            raise ValueError(
                f"Unknown role '{role_name}' in palette '{raw['name']}'. "
                f"Valid roles: {[r.value for r in PaletteRole]}."
            ) from None

        if not isinstance(idx, int) or idx < 0 or idx >= len(colors):
            raise ValueError(
                f"Role '{role_name}' has invalid color index {idx}. "
                f"Valid indices: 0-{len(colors) - 1}."
            )
        roles[role] = idx

    # V2: parse optional ramp configuration
    ramp_config = None
    if "ramp" in raw:
        ramp_data = raw["ramp"]
        ramp_base_color = _parse_hex_color(ramp_data["base_color"])
        ramp_config = RampConfig(
            base_color=ramp_base_color,
            steps=ramp_data.get("steps", 9),
            shadow_hue_shift=float(ramp_data.get("shadow_hue_shift", -30.0)),
            highlight_hue_shift=float(ramp_data.get("highlight_hue_shift", 20.0)),
            lightness_range=float(ramp_data.get("lightness_range", 0.35)),
        )

    return Palette(
        name=raw["name"], colors=colors, roles=roles, ramp_config=ramp_config,
    )
