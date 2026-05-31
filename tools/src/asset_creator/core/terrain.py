"""Terrain configuration data structures and YAML loader.

Defines the configuration hierarchy for terrain generation:
TerrainConfig -> TextureConfig, EdgeConfig, BorderConfig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class EdgeConfig:
    """Edge rendering configuration for terrain borders."""

    style: str = "organic"  # organic | straight | dithered
    width: int = 3
    noise_scale: float = 0.3


@dataclass(frozen=True)
class BorderConfig:
    """Border effect configuration (shadow/highlight on edges)."""

    shadow_width: int = 1
    highlight_width: int = 1


@dataclass(frozen=True)
class TextureConfig:
    """Procedural texture generation configuration."""

    texture_type: str = "noise"
    scale: float = 0.15
    octaves: int = 3
    persistence: float = 0.5
    lacunarity: float = 2.0
    thresholds: tuple[float, ...] = (-0.2, 0.4, 0.8)
    density: float = 0.3
    # V2 additions
    use_smooth_ramp: bool = False
    detail_scale: float = 0.5
    detail_strength: float = 0.06
    use_dithering: bool = False
    dither_matrix_size: int = 4


@dataclass(frozen=True)
class DetailConfig:
    """V2 detail overlay configuration."""

    detail_type: str = "none"  # grass_blades | dirt_specks | stone_cracks | sand_grains | none
    density: float = 0.12
    max_height: int = 4
    max_length: int = 4


@dataclass(frozen=True)
class TerrainConfig:
    """Complete terrain definition combining palette, texture, and edge settings."""

    name: str
    palette_name: str
    texture: TextureConfig = field(default_factory=TextureConfig)
    edge: EdgeConfig = field(default_factory=EdgeConfig)
    border: BorderConfig = field(default_factory=BorderConfig)
    detail: DetailConfig = field(default_factory=DetailConfig)


def _parse_texture_config(data: dict) -> TextureConfig:
    """Parse texture config from YAML dict."""
    thresholds = data.get("thresholds", (-0.2, 0.4, 0.8))
    if isinstance(thresholds, list):
        thresholds = tuple(thresholds)

    return TextureConfig(
        texture_type=data.get("type", "noise"),
        scale=data.get("scale", 0.15),
        octaves=data.get("octaves", 3),
        persistence=data.get("persistence", 0.5),
        lacunarity=data.get("lacunarity", 2.0),
        thresholds=thresholds,
        density=data.get("density", 0.3),
        # V2 fields
        use_smooth_ramp=data.get("use_smooth_ramp", False),
        detail_scale=data.get("detail_scale", 0.5),
        detail_strength=data.get("detail_strength", 0.06),
        use_dithering=data.get("use_dithering", False),
        dither_matrix_size=data.get("dither_matrix_size", 4),
    )


def _parse_detail_config(data: dict) -> DetailConfig:
    """Parse detail overlay config from YAML dict."""
    return DetailConfig(
        detail_type=data.get("type", "none"),
        density=data.get("density", 0.12),
        max_height=data.get("max_height", 4),
        max_length=data.get("max_length", 4),
    )


def _parse_edge_config(data: dict) -> EdgeConfig:
    """Parse edge config from YAML dict."""
    return EdgeConfig(
        style=data.get("style", "organic"),
        width=data.get("width", 3),
        noise_scale=data.get("noise_scale", 0.3),
    )


def _parse_border_config(data: dict) -> BorderConfig:
    """Parse border config from YAML dict."""
    return BorderConfig(
        shadow_width=data.get("shadow_width", 1),
        highlight_width=data.get("highlight_width", 1),
    )


def load_terrain_presets(path: Path) -> dict[str, TerrainConfig]:
    """Load terrain presets from YAML file.

    Args:
        path: Path to the terrain presets YAML file.

    Returns:
        Dict mapping terrain name to TerrainConfig.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the YAML structure is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Terrain presets file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict) or "terrains" not in raw:
        raise ValueError(f"Invalid terrain presets file: expected 'terrains' key in {path}")

    result: dict[str, TerrainConfig] = {}
    for name, config_data in raw["terrains"].items():
        if not isinstance(config_data, dict):
            raise ValueError(f"Invalid terrain config for '{name}': expected a dict")

        palette_name = config_data.get("palette")
        if not palette_name:
            raise ValueError(f"Terrain '{name}' is missing required 'palette' field")

        texture = _parse_texture_config(config_data.get("texture", {}))
        edge = _parse_edge_config(config_data.get("edge", {}))
        border = _parse_border_config(config_data.get("border", {}))
        detail = _parse_detail_config(config_data.get("detail", {}))

        result[name] = TerrainConfig(
            name=name,
            palette_name=palette_name,
            texture=texture,
            edge=edge,
            border=border,
            detail=detail,
        )

    return result


def get_builtin_presets() -> dict[str, TerrainConfig]:
    """Load the bundled terrain presets shipped with the tool."""
    presets_path = Path(__file__).parent.parent / "config" / "terrain_presets.yaml"
    return load_terrain_presets(presets_path)
