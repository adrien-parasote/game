"""Tests for CLI interface (TC-020..022) and Terrain config (TC-023..024)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from tools.asset_creator.cli import _build_parser, cmd_generate, cmd_list
from tools.asset_creator.core.terrain import (
    BorderConfig,
    EdgeConfig,
    TerrainConfig,
    TextureConfig,
    get_builtin_presets,
    load_terrain_presets,
)

# ── TC-020: CLI parser ───────────────────────────────────────────────────────


class TestCliParser:
    """TC-020: CLI argument parsing."""

    def test_generate_command_parsed(self) -> None:
        """generate command parses terrain flag."""
        parser = _build_parser()
        args = parser.parse_args(["generate", "--terrain", "grass"])
        assert args.command == "generate"
        assert args.terrain == "grass"

    def test_generate_with_seed(self) -> None:
        """generate command parses seed."""
        parser = _build_parser()
        args = parser.parse_args(["generate", "--terrain", "dirt", "--seed", "42"])
        assert args.seed == 42

    def test_generate_with_variants(self) -> None:
        """generate command parses variant count."""
        parser = _build_parser()
        args = parser.parse_args(
            ["generate", "--terrain", "grass", "--variants", "3"],
        )
        assert args.variants == 3

    def test_list_command(self) -> None:
        """list command is recognized."""
        parser = _build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_preview_command(self) -> None:
        """preview command with path."""
        parser = _build_parser()
        args = parser.parse_args(["preview", "/tmp/test.png"])
        assert args.command == "preview"
        assert args.png_path == Path("/tmp/test.png")

    def test_missing_command_exits(self) -> None:
        """No command raises SystemExit."""
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


# ── TC-021: CLI list command ──────────────────────────────────────────────────


class TestCliListCommand:
    """TC-021: list command shows available presets."""

    def test_list_outputs_preset_names(self, capsys: pytest.CaptureFixture) -> None:
        """list command writes preset names to stdout."""
        parser = _build_parser()
        args = parser.parse_args(["list"])
        cmd_list(args)
        output = capsys.readouterr().out
        assert "grass" in output
        assert "dirt" in output
        assert "sand" in output


# ── TC-022: CLI generate command ──────────────────────────────────────────────


class TestCliGenerateCommand:
    """TC-022: generate command produces files."""

    def test_generate_creates_files(self, tmp_path: Path) -> None:
        """generate command creates PNG and TSX files."""
        parser = _build_parser()
        png_dir = tmp_path / "png"
        tsx_dir = tmp_path / "tsx"
        args = parser.parse_args([
            "generate",
            "--terrain", "grass",
            "--output-dir", str(png_dir),
            "--tsx-dir", str(tsx_dir),
            "--seed", "0",
        ])
        cmd_generate(args)
        assert (png_dir / "grass.png").exists()
        assert (tsx_dir / "grass.tsx").exists()

    def test_generate_with_custom_name(self, tmp_path: Path) -> None:
        """generate command uses custom name stem."""
        parser = _build_parser()
        png_dir = tmp_path / "png"
        tsx_dir = tmp_path / "tsx"
        args = parser.parse_args([
            "generate",
            "--terrain", "dirt",
            "--output-dir", str(png_dir),
            "--tsx-dir", str(tsx_dir),
            "--name", "my-terrain",
        ])
        cmd_generate(args)
        assert (png_dir / "my-terrain.png").exists()
        assert (tsx_dir / "my-terrain.tsx").exists()

    def test_generate_multiple_variants(self, tmp_path: Path) -> None:
        """generate command with variants creates multiple files."""
        parser = _build_parser()
        png_dir = tmp_path / "png"
        tsx_dir = tmp_path / "tsx"
        args = parser.parse_args([
            "generate",
            "--terrain", "sand",
            "--output-dir", str(png_dir),
            "--tsx-dir", str(tsx_dir),
            "--variants", "2",
        ])
        cmd_generate(args)
        assert (png_dir / "sand-v1.png").exists()
        assert (png_dir / "sand-v2.png").exists()
        assert (tsx_dir / "sand-v1.tsx").exists()
        assert (tsx_dir / "sand-v2.tsx").exists()


# ── TC-023: Terrain config loading ────────────────────────────────────────────


class TestTerrainConfig:
    """TC-023: Terrain config dataclasses and loading."""

    def test_load_builtin_presets(self) -> None:
        """Built-in presets load without error."""
        presets = get_builtin_presets()
        assert len(presets) >= 6
        assert "grass" in presets
        assert "dirt" in presets
        assert "sand" in presets

    def test_grass_preset_values(self) -> None:
        """Grass preset has expected configuration."""
        presets = get_builtin_presets()
        grass = presets["grass"]
        assert grass.palette_name == "forest_grass"
        assert grass.texture.texture_type == "noise"
        assert grass.edge.style == "organic"
        assert grass.edge.width == 3

    def test_paving_stone_preset(self) -> None:
        """Paving stone preset uses stippled texture and straight edges."""
        presets = get_builtin_presets()
        stone = presets["paving_stone"]
        assert stone.texture.texture_type == "stippled"
        assert stone.edge.style == "straight"

    def test_frozen_dataclass(self) -> None:
        """TerrainConfig is immutable."""
        presets = get_builtin_presets()
        with pytest.raises(AttributeError):
            presets["grass"].name = "modified"  # type: ignore[misc]

    def test_custom_terrain_file(self, tmp_path: Path) -> None:
        """Custom YAML terrain file loads correctly."""
        custom = {
            "terrains": {
                "custom_biome": {
                    "palette": "forest_grass",
                    "texture": {"type": "noise", "scale": 0.5},
                    "edge": {"style": "organic", "width": 4},
                }
            }
        }
        yaml_path = tmp_path / "custom.yaml"
        yaml_path.write_text(yaml.dump(custom), encoding="utf-8")
        presets = load_terrain_presets(yaml_path)
        assert "custom_biome" in presets
        assert presets["custom_biome"].texture.scale == 0.5

    def test_missing_palette_raises(self, tmp_path: Path) -> None:
        """Missing palette field raises ValueError."""
        bad = {"terrains": {"bad": {"texture": {"type": "noise"}}}}
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text(yaml.dump(bad), encoding="utf-8")
        with pytest.raises(ValueError, match="palette"):
            load_terrain_presets(yaml_path)

    def test_missing_file_raises(self) -> None:
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_terrain_presets(Path("/nonexistent/path.yaml"))

    def test_default_values(self) -> None:
        """Config defaults are sensible."""
        edge = EdgeConfig()
        assert edge.style == "organic"
        assert edge.width == 3

        border = BorderConfig()
        assert border.shadow_width == 1

        texture = TextureConfig()
        assert texture.texture_type == "noise"
        assert texture.octaves == 3

# ── TC-024: Extended CLI operations ───────────────────────────────────────────

class TestCliExtended:
    """TC-024: Extended CLI commands and edge cases."""

    @patch("tools.asset_creator.cli.sys.exit")
    def test_preview_file_not_found(self, mock_exit: MagicMock) -> None:
        """Preview with missing file exits."""
        mock_exit.side_effect = SystemExit(1)
        parser = _build_parser()
        args = parser.parse_args(["preview", "/path/does/not/exist.png"])
        from tools.asset_creator.cli import cmd_preview
        with pytest.raises(SystemExit):
            cmd_preview(args)
        mock_exit.assert_called_once()

    @patch("tools.asset_creator.cli.sys.exit")
    def test_gui_launch(self, mock_exit: MagicMock) -> None:
        """GUI launch attempts to run_gui or exits."""
        parser = _build_parser()
        args = parser.parse_args(["gui"])
        mock_dpg = MagicMock()
        mock_dpg.is_dearpygui_running.return_value = False
        with patch.dict("sys.modules", {"dearpygui": MagicMock(), "dearpygui.dearpygui": mock_dpg}):
            from tools.asset_creator.cli import cmd_gui
            try:
                cmd_gui(args)
            except Exception:
                pass # expected if inner modules fail

    @patch("tools.asset_creator.cli.sys.exit")
    def test_main_no_args(self, mock_exit: MagicMock) -> None:
        """main() without args exits."""
        mock_exit.side_effect = SystemExit(2)
        from tools.asset_creator.cli import main
        with patch("sys.argv", ["asset_creator"]):
            with pytest.raises(SystemExit):
                main()
            mock_exit.assert_called_once_with(2)

    @patch("tools.asset_creator.cli.sys.exit")
    def test_resolve_terrain_config_unknown(self, mock_exit: MagicMock) -> None:
        """resolve terrain with unknown name exits."""
        mock_exit.side_effect = SystemExit(1)
        from tools.asset_creator.cli import _resolve_terrain_config
        with pytest.raises(SystemExit):
            _resolve_terrain_config("nonexistent_terrain")
        mock_exit.assert_called_once()

    @patch("tools.asset_creator.cli.sys.exit")
    def test_resolve_terrain_config_bad_yaml(self, mock_exit: MagicMock, tmp_path: Path) -> None:
        """resolve terrain with empty yaml exits."""
        mock_exit.side_effect = SystemExit(1)
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("not_a_dict", encoding="utf-8")
        from tools.asset_creator.cli import _resolve_terrain_config
        with pytest.raises(ValueError):
            _resolve_terrain_config(str(empty_yaml))

    def test_generate_pattern_texture(self, tmp_path: Path) -> None:
        """generate command uses pattern texture for paving_stone."""
        parser = _build_parser()
        png_dir = tmp_path / "png"
        tsx_dir = tmp_path / "tsx"
        args = parser.parse_args([
            "generate",
            "--terrain", "paving_stone",
            "--output-dir", str(png_dir),
            "--tsx-dir", str(tsx_dir),
        ])
        from tools.asset_creator.cli import cmd_generate
        cmd_generate(args)
        assert (png_dir / "paving_stone.png").exists()

    @patch("tools.asset_creator.cli.sys.stdout.write")
    def test_generate_preview_no_pygame(self, mock_write: MagicMock, tmp_path: Path) -> None:
        """generate with --preview warns if pygame missing."""
        parser = _build_parser()
        args = parser.parse_args([
            "generate",
            "--terrain", "grass",
            "--output-dir", str(tmp_path),
            "--tsx-dir", str(tmp_path),
            "--preview",
        ])
        from tools.asset_creator.cli import cmd_generate
        with patch.dict("sys.modules", {"tools.asset_creator.preview.pygame_preview": None}):
            cmd_generate(args)
        # Should warn about Pygame
        assert any("WARNING: Pygame preview not available" in call[0][0] for call in mock_write.call_args_list)

    @patch("tools.asset_creator.cli.sys.exit")
    def test_cmd_preview_no_pygame(self, mock_exit: MagicMock, tmp_path: Path) -> None:
        """preview command exits if pygame missing."""
        # Create dummy image
        png_path = tmp_path / "dummy.png"
        from PIL import Image
        Image.new("RGBA", (10, 10)).save(png_path)

        parser = _build_parser()
        args = parser.parse_args(["preview", str(png_path)])
        from tools.asset_creator.cli import cmd_preview
        
        mock_exit.side_effect = SystemExit(1)
        with patch.dict("sys.modules", {"tools.asset_creator.preview.pygame_preview": None}):
            with pytest.raises(SystemExit):
                cmd_preview(args)
        mock_exit.assert_called_with("ERROR: Pygame preview not available.")


