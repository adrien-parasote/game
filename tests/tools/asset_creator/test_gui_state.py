"""Tests for GUI application state (TC-009 → TC-014).

Verifies AppState creation from presets, conversion to core configs,
and frozen immutability.
"""
from __future__ import annotations

import dataclasses

import pytest

from tools.asset_creator.core.terrain import (
    DetailConfig,
    EdgeConfig,
    TextureConfig,
    get_builtin_presets,
)
from tools.asset_creator.gui.state import AppState, state_from_preset


@pytest.fixture()
def presets() -> dict:
    """Load the builtin terrain presets."""
    return get_builtin_presets()


class TestStateFromPreset:
    """TC-009: state_from_preset loads correct values from grass preset."""

    def test_grass_preset_scale(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.scale == pytest.approx(0.12)

    def test_grass_preset_detail_type(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.detail_type == "grass_blades"

    def test_grass_preset_edge_style(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.edge_style == "organic"

    def test_grass_preset_terrain_name(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.terrain_name == "grass"

    def test_grass_preset_texture_type(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.texture_type == "noise"

    def test_grass_preset_use_smooth_ramp(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.use_smooth_ramp is True

    def test_grass_preset_use_dithering(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.use_dithering is True

    def test_grass_preset_edge_width(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.edge_width == 3

    def test_grass_preset_edge_noise_scale(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.edge_noise_scale == pytest.approx(0.3)

    def test_grass_preset_name_field(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        assert state.name == "grass"


class TestToTextureConfig:
    """TC-010: to_texture_config produces valid TextureConfig."""

    def test_returns_texture_config_type(self) -> None:
        state = AppState()
        result = state.to_texture_config()
        assert isinstance(result, TextureConfig)

    def test_texture_type_matches(self) -> None:
        state = AppState(texture_type="noise")
        result = state.to_texture_config()
        assert result.texture_type == "noise"

    def test_scale_matches(self) -> None:
        state = AppState(scale=0.25)
        result = state.to_texture_config()
        assert result.scale == pytest.approx(0.25)

    def test_octaves_matches(self) -> None:
        state = AppState(octaves=4)
        result = state.to_texture_config()
        assert result.octaves == 4

    def test_persistence_matches(self) -> None:
        state = AppState(persistence=0.7)
        result = state.to_texture_config()
        assert result.persistence == pytest.approx(0.7)

    def test_lacunarity_matches(self) -> None:
        state = AppState(lacunarity=3.0)
        result = state.to_texture_config()
        assert result.lacunarity == pytest.approx(3.0)

    def test_v2_smooth_ramp_on(self) -> None:
        state = AppState(use_smooth_ramp=True)
        result = state.to_texture_config()
        assert result.use_smooth_ramp is True

    def test_v2_dithering_on(self) -> None:
        state = AppState(use_dithering=True)
        result = state.to_texture_config()
        assert result.use_dithering is True

    def test_detail_scale_matches(self) -> None:
        state = AppState(detail_scale=0.8)
        result = state.to_texture_config()
        assert result.detail_scale == pytest.approx(0.8)

    def test_detail_strength_matches(self) -> None:
        state = AppState(detail_strength=0.1)
        result = state.to_texture_config()
        assert result.detail_strength == pytest.approx(0.1)

    def test_dither_matrix_size_matches(self) -> None:
        state = AppState(dither_matrix_size=8)
        result = state.to_texture_config()
        assert result.dither_matrix_size == 8


class TestToDetailConfig:
    """TC-011: to_detail_config produces valid DetailConfig."""

    def test_returns_detail_config_type(self) -> None:
        state = AppState()
        result = state.to_detail_config()
        assert isinstance(result, DetailConfig)

    def test_detail_type_matches(self) -> None:
        state = AppState(detail_type="dirt_specks")
        result = state.to_detail_config()
        assert result.detail_type == "dirt_specks"

    def test_density_matches(self) -> None:
        state = AppState(detail_density=0.2)
        result = state.to_detail_config()
        assert result.density == pytest.approx(0.2)

    def test_max_height_matches(self) -> None:
        state = AppState(detail_max_height=6)
        result = state.to_detail_config()
        assert result.max_height == 6

    def test_max_length_matches(self) -> None:
        state = AppState(detail_max_length=8)
        result = state.to_detail_config()
        assert result.max_length == 8


class TestToEdgeConfig:
    """TC-012: to_edge_config produces valid EdgeConfig."""

    def test_returns_edge_config_type(self) -> None:
        state = AppState()
        result = state.to_edge_config()
        assert isinstance(result, EdgeConfig)

    def test_style_matches(self) -> None:
        state = AppState(edge_style="straight")
        result = state.to_edge_config()
        assert result.style == "straight"

    def test_width_matches(self) -> None:
        state = AppState(edge_width=5)
        result = state.to_edge_config()
        assert result.width == 5

    def test_noise_scale_matches(self) -> None:
        state = AppState(edge_noise_scale=0.5)
        result = state.to_edge_config()
        assert result.noise_scale == pytest.approx(0.5)


class TestAppStateFrozen:
    """TC-013: AppState is frozen — assigning raises FrozenInstanceError."""

    def test_cannot_assign_scale(self) -> None:
        state = AppState()
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.scale = 0.5  # type: ignore[misc]

    def test_cannot_assign_terrain_name(self) -> None:
        state = AppState()
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.terrain_name = "dirt"  # type: ignore[misc]

    def test_cannot_assign_seed(self) -> None:
        state = AppState()
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.seed = 42  # type: ignore[misc]


class TestAllPresets:
    """TC-014: state_from_preset works for all 6 presets without exceptions."""

    ALL_PRESET_NAMES = ["grass", "dirt", "paving_stone", "sand", "snow", "water"]

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_preset_loads_without_exception(
        self, preset_name: str, presets: dict
    ) -> None:
        state = state_from_preset(preset_name, presets)
        assert isinstance(state, AppState)
        assert state.terrain_name == preset_name

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_preset_name_matches(self, preset_name: str, presets: dict) -> None:
        state = state_from_preset(preset_name, presets)
        assert state.name == preset_name
