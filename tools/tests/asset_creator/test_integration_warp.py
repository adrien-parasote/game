"""Integration tests for terrain domain warping functionality."""

from __future__ import annotations

from pathlib import Path

import pytest
from asset_creator.core.palette import Palette, PaletteRole, RampConfig
from asset_creator.core.texture import TextureParams
from asset_creator.core.tile_assembler import assemble_tileset
from asset_creator.gui.state import AppState

# Shared test palette
TEST_PALETTE = Palette(
    name="test",
    colors=(
        (45, 90, 30),
        (62, 124, 39),
        (90, 158, 58),
        (123, 192, 79),
    ),
    roles={
        PaletteRole.SHADOW: 0,
        PaletteRole.BASE: 1,
        PaletteRole.HIGHLIGHT: 2,
        PaletteRole.ACCENT: 3,
    },
    ramp_config=RampConfig(
        base_color=(62, 124, 39),
        steps=9,
        shadow_hue_shift=-15.0,
        highlight_hue_shift=10.0,
        lightness_range=0.25,
    ),
)


class TestPipelineWarp:
    """Integration tests for Domain Warping (IT-001 to IT-003)."""

    @pytest.mark.tc("IT-001")
    def test_full_pipeline_with_warp(self) -> None:
        """IT-001: Generate 49 tiles with warp_strength = 20 without crashing."""
        params = TextureParams(warp_strength=20.0, warp_scale=0.1)

        # Generate a full tileset image (which internally calls generate_noise_texture_v2
        # via pipeline or manually assembled if needed, but generate_tileset_image expects raw inputs)
        # Actually generate_tileset_image doesn't take TextureParams directly, it takes the assembled base/detail images.
        # But this tests the general integration.
        # Let's generate a single tile first via the pipeline.

        # Let's mock a pipeline run by just generating a 32x32 noise and running tile_assembler
        from asset_creator.core.subtile import generate_subtiles
        from asset_creator.core.texture import generate_noise_texture_v2

        base_img = generate_noise_texture_v2(32, 32, TEST_PALETTE, params, seed=42)
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(base_img, edge_config, seed=42)
        tileset = assemble_tileset(subtiles)

        # All 49 tile slots should generate without crashing
        assert tileset is not None
        assert tileset.size == (32 * 47, 32)  # 47 tiles side by side

    @pytest.mark.tc("IT-002")
    def test_gui_state_conversion(self) -> None:
        """IT-002: AppState.to_texture_config() correctly maps warp parameters."""
        state = AppState()
        # AppState is frozen, use replace
        import dataclasses
        state = dataclasses.replace(state, texture_warp_scale=0.15, texture_warp_strength=25.5)

        config = state.to_texture_config()
        assert getattr(config, "warp_scale", None) == 0.15
        assert getattr(config, "warp_strength", None) == 25.5

    @pytest.mark.tc("IT-003")
    def test_preset_loading_with_warp(self, tmp_path: Path) -> None:
        """IT-003: AppState parses and applies warp parameters from YAML correctly."""
        yaml_path = tmp_path / "test_preset_warp.yaml"
        yaml_content = """
terrains:
  warp_test:
    palette: forest_grass
    texture:
      type: noise
      scale: 0.1
      octaves: 3
      warp_scale: 0.12
      warp_strength: 30.0
    colors:
      base: [100, 100, 100]
        """
        yaml_path.write_text(yaml_content)

        from asset_creator.core.terrain import load_terrain_presets
        from asset_creator.gui.state import state_from_preset

        presets = load_terrain_presets(yaml_path)
        state = state_from_preset("warp_test", presets)

        assert state.texture_warp_scale == 0.12
        assert state.texture_warp_strength == 30.0
