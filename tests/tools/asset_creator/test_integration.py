"""Integration tests for the Asset Creator Tool.

Tests the full pipeline end-to-end:
  Palette YAML → Texture → SubTiles → 47-tile Assembly → PNG/TSX Export

Also covers:
  - CLI generate command (end-to-end)
  - Seed reproducibility across the full pipeline
  - Cross-terrain consistency (all builtin presets produce valid output)
  - TSX XML structure validation against Tiled schema
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from tools.asset_creator.core.palette import Palette, PaletteRole, load_palette
from tools.asset_creator.core.subtile import (
    Quadrant,
    SubTileType,
    generate_subtiles,
)
from tools.asset_creator.core.terrain import TerrainConfig, get_builtin_presets
from tools.asset_creator.core.texture import (
    TextureParams,
    generate_noise_texture_v2,
    generate_pattern_texture,
)
from tools.asset_creator.core.tile_assembler import (
    BLOB_BITMASKS,
    assemble_tile,
    assemble_tileset,
    blob_wang_id,
)
from tools.asset_creator.exporters.png_exporter import export_png, validate_tileset
from tools.asset_creator.exporters.tsx_exporter import export_tsx

PALETTE_DIR = Path(__file__).parents[3] / "tools" / "asset_creator" / "config" / "palettes"
TILE_SIZE = 32
EXPECTED_TILE_COUNT = 47


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def grass_palette() -> Palette:
    """Load the forest_grass palette from disk."""
    return load_palette(PALETTE_DIR / "forest_grass.yaml")


@pytest.fixture()
def tmp_output(tmp_path: Path) -> dict[str, Path]:
    """Provide temp directories for PNG and TSX output."""
    png_dir = tmp_path / "png"
    tsx_dir = tmp_path / "tsx"
    png_dir.mkdir()
    tsx_dir.mkdir()
    return {"png": png_dir, "tsx": tsx_dir, "root": tmp_path}


# ---------------------------------------------------------------------------
# IT-001: Full pipeline — palette → texture → subtiles → tileset → PNG
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """Integration: complete pipeline from palette YAML to exported files."""

    def test_grass_pipeline_produces_valid_png(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """grass preset produces a valid 47-tile PNG strip."""
        params = TextureParams(
            texture_type="noise", scale=0.15, octaves=3,
            persistence=0.5,
        )
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=42,
        )

        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=42)
        tileset = assemble_tileset(subtiles)

        # Validate tileset geometry
        assert tileset.size == (EXPECTED_TILE_COUNT * TILE_SIZE, TILE_SIZE)
        assert tileset.mode == "RGBA"

        # Export and verify file is written
        png_path = tmp_output["png"] / "grass.png"
        result_path = export_png(tileset, png_path)
        assert result_path.exists()
        assert result_path.stat().st_size > 0

        # Re-read and verify it matches
        reloaded = Image.open(result_path).convert("RGBA")
        assert reloaded.size == tileset.size

    def test_grass_pipeline_produces_valid_tsx(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """grass preset produces a valid TSX with Wang set."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=42,
        )

        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=42)
        tileset = assemble_tileset(subtiles)

        png_path = tmp_output["png"] / "grass.png"
        tsx_path = tmp_output["tsx"] / "grass.tsx"

        export_png(tileset, png_path)
        result_path = export_tsx(tsx_path, png_path, "grass")

        assert result_path.exists()
        assert result_path.stat().st_size > 0

        # Parse and verify TSX XML structure
        tree = ET.parse(result_path)
        root = tree.getroot()
        assert root.tag == "tileset"
        assert root.attrib["name"] == "grass"
        assert root.attrib["tilewidth"] == str(TILE_SIZE)
        assert root.attrib["tileheight"] == str(TILE_SIZE)
        assert root.attrib["tilecount"] == str(EXPECTED_TILE_COUNT)

    def test_pipeline_no_fully_transparent_tile(
        self, grass_palette: Palette,
    ) -> None:
        """no tile in the assembled tileset is fully transparent (L-MAP-003)."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=42,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=42)
        tileset = assemble_tileset(subtiles)

        errors = validate_tileset(tileset, TILE_SIZE)
        assert errors == [], f"Validation errors: {errors}"


# ---------------------------------------------------------------------------
# IT-002: Seed reproducibility
# ---------------------------------------------------------------------------

class TestSeedReproducibility:
    """Integration: same seed produces identical output."""

    def test_same_seed_identical_tileset(self, grass_palette: Palette) -> None:
        """two runs with the same seed produce pixel-identical tilesets."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}

        results = []
        for _ in range(2):
            texture = generate_noise_texture_v2(
                TILE_SIZE, TILE_SIZE, grass_palette, params, seed=99,
            )
            subtiles = generate_subtiles(texture, edge_config, seed=99)
            tileset = assemble_tileset(subtiles)
            results.append(tileset.tobytes())

        assert results[0] == results[1], "Same seed must produce identical output"

    def test_different_seed_different_tileset(self, grass_palette: Palette) -> None:
        """different seeds produce different tilesets."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}

        results = []
        for seed in (1, 2):
            texture = generate_noise_texture_v2(
                TILE_SIZE, TILE_SIZE, grass_palette, params, seed=seed,
            )
            subtiles = generate_subtiles(texture, edge_config, seed=seed)
            tileset = assemble_tileset(subtiles)
            results.append(tileset.tobytes())

        assert results[0] != results[1], "Different seeds must produce different output"


# ---------------------------------------------------------------------------
# IT-003: Cross-terrain — all builtin presets produce valid output
# ---------------------------------------------------------------------------

class TestAllTerrains:
    """Integration: every builtin terrain preset produces a valid tileset."""

    @pytest.fixture()
    def all_presets(self) -> dict[str, TerrainConfig]:
        return get_builtin_presets()

    def test_all_presets_are_loaded(self, all_presets: dict[str, TerrainConfig]) -> None:
        """builtin presets file loads all 6 terrains."""
        expected = {"grass", "dirt", "paving_stone", "sand", "snow", "water"}
        assert set(all_presets.keys()) == expected

    @pytest.mark.parametrize("terrain_name", [
        "grass", "dirt", "paving_stone", "sand", "snow", "water",
    ])
    def test_terrain_generates_valid_tileset(
        self, terrain_name: str, all_presets: dict[str, TerrainConfig],
        tmp_output: dict[str, Path],
    ) -> None:
        """each terrain produces a valid 47-tile PNG + TSX."""
        config = all_presets[terrain_name]
        palette = load_palette(PALETTE_DIR / f"{config.palette_name}.yaml")

        params = TextureParams(
            texture_type=config.texture.texture_type,
            scale=config.texture.scale,
            octaves=config.texture.octaves,
            persistence=config.texture.persistence,
            lacunarity=config.texture.lacunarity,
            density=config.texture.density,
        )

        if config.texture.texture_type == "noise":
            texture = generate_noise_texture_v2(
                TILE_SIZE, TILE_SIZE, palette, params, seed=0,
            )
        else:
            texture = generate_pattern_texture(
                TILE_SIZE, TILE_SIZE, palette,
                config.texture.texture_type, params, seed=0,
            )

        edge_config = {
            "style": config.edge.style,
            "width": config.edge.width,
            "noise_scale": config.edge.noise_scale,
        }
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        # Geometry check
        assert tileset.size == (EXPECTED_TILE_COUNT * TILE_SIZE, TILE_SIZE)

        # No fully transparent tiles
        errors = validate_tileset(tileset, TILE_SIZE)
        assert errors == [], (
            f"{terrain_name} validation errors: {errors}"
        )

        # Export both files
        png_path = tmp_output["png"] / f"{terrain_name}.png"
        tsx_path = tmp_output["tsx"] / f"{terrain_name}.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, terrain_name)
        assert png_path.exists()
        assert tsx_path.exists()


# ---------------------------------------------------------------------------
# IT-004: TSX XML structure — Tiled compatibility
# ---------------------------------------------------------------------------

class TestTsxStructure:
    """Integration: TSX files are valid for Tiled Map Editor."""

    def test_tsx_has_correct_wang_tile_count(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """TSX contains exactly 47 wangtile entries."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        png_path = tmp_output["png"] / "test.png"
        tsx_path = tmp_output["tsx"] / "test.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, "test")

        tree = ET.parse(tsx_path)
        root = tree.getroot()

        wangtiles = root.findall(".//wangtile")
        assert len(wangtiles) == EXPECTED_TILE_COUNT

    def test_tsx_wang_ids_are_valid(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """every wangid uses only 0 or 1 values (single-terrain blob)."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        png_path = tmp_output["png"] / "test.png"
        tsx_path = tmp_output["tsx"] / "test.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, "test")

        tree = ET.parse(tsx_path)
        wangtiles = tree.getroot().findall(".//wangtile")

        for wt in wangtiles:
            wangid = wt.attrib["wangid"]
            values = wangid.split(",")
            assert len(values) == 8, f"wangid must have 8 components: {wangid}"
            for v in values:
                assert v in ("0", "1"), f"wangid value must be 0 or 1: {wangid}"

    def test_tsx_tile_ids_are_sequential(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """tileid values are 0..46 (sequential)."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        png_path = tmp_output["png"] / "test.png"
        tsx_path = tmp_output["tsx"] / "test.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, "test")

        tree = ET.parse(tsx_path)
        wangtiles = tree.getroot().findall(".//wangtile")
        tile_ids = sorted(int(wt.attrib["tileid"]) for wt in wangtiles)
        assert tile_ids == list(range(EXPECTED_TILE_COUNT))

    def test_tsx_image_source_relative(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """image source is a relative path from TSX to PNG."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        png_path = tmp_output["png"] / "test.png"
        tsx_path = tmp_output["tsx"] / "test.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, "test")

        tree = ET.parse(tsx_path)
        image_el = tree.getroot().find("image")
        assert image_el is not None
        source = image_el.attrib["source"]
        # Must be relative (no leading /)
        assert not source.startswith("/"), f"Image source must be relative: {source}"
        # Must point to a file that exists relative to the TSX
        resolved = (tsx_path.parent / source).resolve()
        assert resolved.exists(), f"Image not found at resolved path: {resolved}"

    def test_tsx_wangset_type_is_mixed(
        self, grass_palette: Palette, tmp_output: dict[str, Path],
    ) -> None:
        """wangset type is 'mixed' for blob tileset."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        png_path = tmp_output["png"] / "test.png"
        tsx_path = tmp_output["tsx"] / "test.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, "test")

        tree = ET.parse(tsx_path)
        wangset = tree.getroot().find(".//wangset")
        assert wangset is not None
        assert wangset.attrib["type"] == "mixed"


# ---------------------------------------------------------------------------
# IT-005: CLI end-to-end via cmd_generate
# ---------------------------------------------------------------------------

class TestCliGenerate:
    """Integration: CLI generate command produces files on disk."""

    def test_cli_generate_single_terrain(self, tmp_output: dict[str, Path]) -> None:
        """cmd_generate produces PNG + TSX for a single terrain."""
        import argparse

        from tools.asset_creator.cli import cmd_generate

        args = argparse.Namespace(
            terrain="grass",
            output_dir=tmp_output["png"],
            tsx_dir=tmp_output["tsx"],
            seed=42,
            variants=1,
            preview=False,
            name=None,
        )

        cmd_generate(args)

        png_path = tmp_output["png"] / "grass.png"
        tsx_path = tmp_output["tsx"] / "grass.tsx"
        assert png_path.exists(), "PNG not generated"
        assert tsx_path.exists(), "TSX not generated"

        # Verify PNG is a valid tileset
        img = Image.open(png_path).convert("RGBA")
        assert img.size == (EXPECTED_TILE_COUNT * TILE_SIZE, TILE_SIZE)

    def test_cli_generate_multiple_variants(self, tmp_output: dict[str, Path]) -> None:
        """cmd_generate with --variants produces N files."""
        import argparse

        from tools.asset_creator.cli import cmd_generate

        args = argparse.Namespace(
            terrain="grass",
            output_dir=tmp_output["png"],
            tsx_dir=tmp_output["tsx"],
            seed=0,
            variants=3,
            preview=False,
            name=None,
        )

        cmd_generate(args)

        for i in range(1, 4):
            png = tmp_output["png"] / f"grass-v{i}.png"
            tsx = tmp_output["tsx"] / f"grass-v{i}.tsx"
            assert png.exists(), f"Variant {i} PNG missing"
            assert tsx.exists(), f"Variant {i} TSX missing"

    def test_cli_generate_custom_name(self, tmp_output: dict[str, Path]) -> None:
        """cmd_generate with --name uses custom filename stem."""
        import argparse

        from tools.asset_creator.cli import cmd_generate

        args = argparse.Namespace(
            terrain="dirt",
            output_dir=tmp_output["png"],
            tsx_dir=tmp_output["tsx"],
            seed=0,
            variants=1,
            preview=False,
            name="my_dirt_tileset",
        )

        cmd_generate(args)

        assert (tmp_output["png"] / "my_dirt_tileset.png").exists()
        assert (tmp_output["tsx"] / "my_dirt_tileset.tsx").exists()


# ---------------------------------------------------------------------------
# IT-006: Variant uniqueness — variants differ from each other
# ---------------------------------------------------------------------------

class TestVariantUniqueness:
    """Integration: multiple variants from sequential seeds are unique."""

    def test_variants_are_unique(self, grass_palette: Palette) -> None:
        """3 sequential seeds produce 3 distinct tilesets."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}

        pixel_data = []
        for seed in range(3):
            texture = generate_noise_texture_v2(
                TILE_SIZE, TILE_SIZE, grass_palette, params, seed=seed,
            )
            subtiles = generate_subtiles(texture, edge_config, seed=seed)
            tileset = assemble_tileset(subtiles)
            pixel_data.append(tileset.tobytes())

        # All 3 must be distinct
        assert pixel_data[0] != pixel_data[1]
        assert pixel_data[1] != pixel_data[2]
        assert pixel_data[0] != pixel_data[2]


# ---------------------------------------------------------------------------
# IT-007: Pattern textures through the full pipeline
# ---------------------------------------------------------------------------

class TestPatternPipeline:
    """Integration: non-noise texture types work through the full pipeline."""

    @pytest.mark.parametrize("pattern_type", ["solid", "dithered", "stippled", "striped"])
    def test_pattern_produces_valid_tileset(
        self, pattern_type: str, grass_palette: Palette,
        tmp_output: dict[str, Path],
    ) -> None:
        """each pattern type produces a valid exportable tileset."""
        params = TextureParams(texture_type=pattern_type, density=0.3)
        texture = generate_pattern_texture(
            TILE_SIZE, TILE_SIZE, grass_palette, pattern_type, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        assert tileset.size == (EXPECTED_TILE_COUNT * TILE_SIZE, TILE_SIZE)

        errors = validate_tileset(tileset, TILE_SIZE)
        assert errors == [], f"{pattern_type} validation errors: {errors}"

        png_path = tmp_output["png"] / f"{pattern_type}.png"
        tsx_path = tmp_output["tsx"] / f"{pattern_type}.tsx"
        export_png(tileset, png_path)
        export_tsx(tsx_path, png_path, pattern_type)
        assert png_path.exists()
        assert tsx_path.exists()


# ---------------------------------------------------------------------------
# IT-008: Edge styles through the full pipeline
# ---------------------------------------------------------------------------

class TestEdgeStylePipeline:
    """Integration: each edge style produces a valid tileset."""

    @pytest.mark.parametrize("edge_style", ["organic", "straight", "dithered"])
    def test_edge_style_produces_valid_tileset(
        self, edge_style: str, grass_palette: Palette,
    ) -> None:
        """each edge style assembles into a valid tileset."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": edge_style, "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)
        tileset = assemble_tileset(subtiles)

        assert tileset.size == (EXPECTED_TILE_COUNT * TILE_SIZE, TILE_SIZE)
        errors = validate_tileset(tileset, TILE_SIZE)
        assert errors == [], f"{edge_style} validation errors: {errors}"


# ---------------------------------------------------------------------------
# IT-009: Bitmask 255 (all neighbors) is fully opaque center tile
# ---------------------------------------------------------------------------

class TestBitmaskExtremes:
    """Integration: extreme bitmask values produce expected tile properties."""

    def test_bitmask_255_is_fully_opaque(self, grass_palette: Palette) -> None:
        """bitmask 255 (all neighbors present) produces a fully opaque tile."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)

        tile = assemble_tile(subtiles, 255)
        assert tile.size == (TILE_SIZE, TILE_SIZE)
        assert tile.mode == "RGBA"

        # Every pixel should be fully opaque
        alpha = tile.getchannel("A")
        min_alpha, max_alpha = alpha.getextrema()
        assert min_alpha == 255, (
            f"Bitmask 255 tile has transparent pixels (min alpha={min_alpha})"
        )

    def test_bitmask_0_has_partial_transparency(self, grass_palette: Palette) -> None:
        """bitmask 0 (no neighbors) has some transparent pixels."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)

        tile = assemble_tile(subtiles, 0)
        alpha = tile.getchannel("A")
        min_alpha, _max_alpha = alpha.getextrema()
        # Bitmask 0 = isolated tile with outer corners — must have some transparency
        assert min_alpha == 0, "Bitmask 0 should have transparent corner pixels"

    def test_all_47_bitmasks_produce_non_empty_tiles(
        self, grass_palette: Palette,
    ) -> None:
        """every one of the 47 blob bitmasks produces a tile with visible pixels."""
        params = TextureParams(texture_type="noise", scale=0.15, octaves=3)
        texture = generate_noise_texture_v2(
            TILE_SIZE, TILE_SIZE, grass_palette, params, seed=0,
        )
        edge_config = {"style": "organic", "width": 3, "noise_scale": 0.3}
        subtiles = generate_subtiles(texture, edge_config, seed=0)

        for bitmask in BLOB_BITMASKS:
            tile = assemble_tile(subtiles, bitmask)
            alpha = tile.getchannel("A")
            max_alpha = alpha.getextrema()[1]
            assert max_alpha > 0, (
                f"Bitmask {bitmask} produced a fully transparent tile"
            )
