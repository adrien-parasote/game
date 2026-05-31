"""Tests for the palette system (TC-001, TC-002, TC-003)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.asset_creator.core.palette import Palette, PaletteRole, load_palette

PALETTES_DIR = Path(__file__).resolve().parents[3] / "tools" / "asset_creator" / "config" / "palettes"


class TestLoadPalette:
    """TC-001: Load a palette from YAML, verify name, colors, roles."""

    @pytest.mark.tc("TC-001")
    def test_load_palette_from_yaml(self, tmp_path: Path) -> None:
        """Load a valid palette YAML and verify all fields are correct."""
        yaml_content = {
            "name": "test_palette",
            "colors": ["#2d5a1e", "#3e7c27", "#5a9e3a", "#7bc04f"],
            "roles": {"shadow": 0, "base": 1, "highlight": 2, "accent": 3},
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        palette = load_palette(yaml_file)

        assert palette.name == "test_palette"
        assert len(palette.colors) == 4
        assert palette.colors[0] == (0x2D, 0x5A, 0x1E)
        assert palette.colors[1] == (0x3E, 0x7C, 0x27)
        assert palette.colors[2] == (0x5A, 0x9E, 0x3A)
        assert palette.colors[3] == (0x7B, 0xC0, 0x4F)
        assert palette.roles[PaletteRole.SHADOW] == 0
        assert palette.roles[PaletteRole.BASE] == 1
        assert palette.roles[PaletteRole.HIGHLIGHT] == 2
        assert palette.roles[PaletteRole.ACCENT] == 3

    @pytest.mark.tc("TC-001")
    def test_load_palette_is_frozen(self, tmp_path: Path) -> None:
        """Palette dataclass must be frozen (immutable)."""
        yaml_content = {
            "name": "frozen_test",
            "colors": ["#112233", "#445566"],
            "roles": {"shadow": 0, "base": 1},
        }
        yaml_file = tmp_path / "frozen.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        palette = load_palette(yaml_file)

        with pytest.raises(AttributeError):
            palette.name = "mutated"  # type: ignore[misc]

    @pytest.mark.tc("TC-001")
    def test_load_real_palette_forest_grass(self) -> None:
        """Load the actual forest_grass.yaml and verify it parses correctly."""
        palette = load_palette(PALETTES_DIR / "forest_grass.yaml")

        assert palette.name == "forest_grass"
        assert len(palette.colors) == 4
        assert palette.colors[0] == (0x2D, 0x5A, 0x1E)


class TestPaletteValidation:
    """TC-002: Validate color count and format."""

    @pytest.mark.tc("TC-002")
    def test_minimum_two_colors_required(self, tmp_path: Path) -> None:
        """Palette with fewer than 2 colors must raise ValueError."""
        yaml_content = {
            "name": "one_color",
            "colors": ["#112233"],
            "roles": {"shadow": 0},
        }
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="at least 2 colors"):
            load_palette(yaml_file)

    @pytest.mark.tc("TC-002")
    def test_invalid_hex_color_format(self, tmp_path: Path) -> None:
        """Invalid hex color string must raise ValueError."""
        yaml_content = {
            "name": "bad_hex",
            "colors": ["#ZZZZZZ", "#112233"],
            "roles": {"shadow": 0, "base": 1},
        }
        yaml_file = tmp_path / "bad_hex.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="[Ii]nvalid.*color"):
            load_palette(yaml_file)

    @pytest.mark.tc("TC-002")
    def test_role_index_out_of_range(self, tmp_path: Path) -> None:
        """Role referencing an out-of-range color index must raise ValueError."""
        yaml_content = {
            "name": "bad_index",
            "colors": ["#112233", "#445566"],
            "roles": {"shadow": 0, "base": 99},
        }
        yaml_file = tmp_path / "bad_index.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="[Ii]ndex"):
            load_palette(yaml_file)

    @pytest.mark.tc("TC-002")
    def test_rgb_values_in_valid_range(self, tmp_path: Path) -> None:
        """All RGB components must be in 0-255 range."""
        yaml_content = {
            "name": "range_test",
            "colors": ["#000000", "#ffffff"],
            "roles": {"shadow": 0, "base": 1},
        }
        yaml_file = tmp_path / "range.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        palette = load_palette(yaml_file)

        for color in palette.colors:
            assert len(color) == 3
            for component in color:
                assert 0 <= component <= 255


class TestRoleMapping:
    """TC-003: Role mapping correctness."""

    @pytest.mark.tc("TC-003")
    def test_get_color_returns_correct_color(self) -> None:
        """get_color(role) must return the color at the role's index."""
        palette = Palette(
            name="test",
            colors=((10, 20, 30), (40, 50, 60), (70, 80, 90), (100, 110, 120)),
            roles={
                PaletteRole.SHADOW: 0,
                PaletteRole.BASE: 1,
                PaletteRole.HIGHLIGHT: 2,
                PaletteRole.ACCENT: 3,
            },
        )

        assert palette.get_color(PaletteRole.SHADOW) == (10, 20, 30)
        assert palette.get_color(PaletteRole.BASE) == (40, 50, 60)
        assert palette.get_color(PaletteRole.HIGHLIGHT) == (70, 80, 90)
        assert palette.get_color(PaletteRole.ACCENT) == (100, 110, 120)

    @pytest.mark.tc("TC-003")
    def test_get_role_colors_returns_all_mappings(self) -> None:
        """get_role_colors() must return a dict mapping all roles to colors."""
        palette = Palette(
            name="test",
            colors=((10, 20, 30), (40, 50, 60)),
            roles={PaletteRole.SHADOW: 0, PaletteRole.BASE: 1},
        )

        role_colors = palette.get_role_colors()

        assert role_colors == {
            PaletteRole.SHADOW: (10, 20, 30),
            PaletteRole.BASE: (40, 50, 60),
        }

    @pytest.mark.tc("TC-003")
    def test_roles_can_share_same_color_index(self) -> None:
        """Multiple roles can reference the same color index."""
        palette = Palette(
            name="shared",
            colors=((10, 20, 30), (40, 50, 60)),
            roles={PaletteRole.SHADOW: 0, PaletteRole.BASE: 0},
        )

        assert palette.get_color(PaletteRole.SHADOW) == (10, 20, 30)
        assert palette.get_color(PaletteRole.BASE) == (10, 20, 30)


class TestPaletteErrors:
    """Additional error cases for palette loading."""

    def test_file_not_found_raises_error(self) -> None:
        """Loading from a non-existent path must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_palette(Path("/nonexistent/palette.yaml"))

    def test_missing_name_field(self, tmp_path: Path) -> None:
        """YAML missing 'name' field must raise ValueError."""
        yaml_content = {
            "colors": ["#112233", "#445566"],
            "roles": {"shadow": 0, "base": 1},
        }
        yaml_file = tmp_path / "no_name.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="name"):
            load_palette(yaml_file)

    def test_missing_colors_field(self, tmp_path: Path) -> None:
        """YAML missing 'colors' field must raise ValueError."""
        yaml_content = {
            "name": "no_colors",
            "roles": {"shadow": 0},
        }
        yaml_file = tmp_path / "no_colors.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="colors"):
            load_palette(yaml_file)

    def test_missing_roles_field(self, tmp_path: Path) -> None:
        """YAML missing 'roles' field must raise ValueError."""
        yaml_content = {
            "name": "no_roles",
            "colors": ["#112233", "#445566"],
        }
        yaml_file = tmp_path / "no_roles.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="roles"):
            load_palette(yaml_file)
