"""Tests for PNG and TSX exporters (TC-017 through TC-019)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from tools.asset_creator.exporters.png_exporter import export_png, validate_tileset
from tools.asset_creator.exporters.tsx_exporter import (
    compute_relative_path,
    export_tsx,
)


# ── TC-017: PNG export ────────────────────────────────────────────────────────


class TestPngExport:
    """TC-017: PNG export creates file with correct dimensions, readable."""

    def test_export_creates_file(self, tmp_path: Path) -> None:
        """Valid tileset image is exported as PNG file."""
        image = Image.new("RGBA", (47 * 32, 32), (100, 200, 50, 255))
        output = tmp_path / "test_tileset.png"
        result = export_png(image, output)
        assert result == output
        assert output.exists()

    def test_exported_file_is_readable(self, tmp_path: Path) -> None:
        """Exported PNG can be read back by Pillow with correct dimensions."""
        image = Image.new("RGBA", (47 * 32, 32), (100, 200, 50, 255))
        output = tmp_path / "test_tileset.png"
        export_png(image, output)

        loaded = Image.open(output)
        assert loaded.size == (47 * 32, 32)
        assert loaded.mode == "RGBA"

    def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Export creates parent directories if they don't exist."""
        image = Image.new("RGBA", (47 * 32, 32), (100, 200, 50, 255))
        output = tmp_path / "deep" / "nested" / "dir" / "tileset.png"
        export_png(image, output)
        assert output.exists()

    def test_export_rejects_invalid_tileset(self, tmp_path: Path) -> None:
        """Export raises ValueError for invalid tileset."""
        image = Image.new("RGBA", (100, 50), (100, 200, 50, 255))
        output = tmp_path / "bad.png"
        with pytest.raises(ValueError, match="validation failed"):
            export_png(image, output)


class TestValidateTileset:
    """Validation checks for tileset images."""

    def test_valid_tileset_returns_empty(self) -> None:
        """A properly sized tileset with opaque tiles passes validation."""
        image = Image.new("RGBA", (47 * 32, 32), (100, 200, 50, 255))
        assert validate_tileset(image) == []

    def test_wrong_height_detected(self) -> None:
        """Height not matching tile_size is detected."""
        image = Image.new("RGBA", (47 * 32, 64), (100, 200, 50, 255))
        errors = validate_tileset(image)
        assert any("height" in e.lower() for e in errors)

    def test_wrong_width_detected(self) -> None:
        """Width not a multiple of tile_size is detected."""
        image = Image.new("RGBA", (100, 32), (100, 200, 50, 255))
        errors = validate_tileset(image)
        assert any("width" in e.lower() for e in errors)

    def test_transparent_tile_detected(self) -> None:
        """Fully transparent tile triggers L-MAP-003 error."""
        image = Image.new("RGBA", (3 * 32, 32), (100, 200, 50, 255))
        # Make tile 1 fully transparent
        for x in range(32, 64):
            for y in range(32):
                image.putpixel((x, y), (0, 0, 0, 0))
        errors = validate_tileset(image)
        assert any("tile 1" in e.lower() and "transparent" in e.lower() for e in errors)


# ── TC-018: TSX export ────────────────────────────────────────────────────────


class TestTsxExport:
    """TC-018: TSX export creates valid XML with correct structure."""

    def test_export_creates_file(self, tmp_path: Path) -> None:
        """TSX file is created at the specified path."""
        tsx_path = tmp_path / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")
        assert tsx_path.exists()

    def test_valid_xml_structure(self, tmp_path: Path) -> None:
        """TSX has correct root element and attributes."""
        tsx_path = tmp_path / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")

        tree = ET.parse(tsx_path)
        root = tree.getroot()
        assert root.tag == "tileset"
        assert root.attrib["name"] == "test_terrain"
        assert root.attrib["tilewidth"] == "32"
        assert root.attrib["tileheight"] == "32"
        assert root.attrib["tilecount"] == "47"

    def test_image_element(self, tmp_path: Path) -> None:
        """TSX contains image element with correct source path."""
        tsx_path = tmp_path / "tiled" / "test.tsx"
        png_path = tmp_path / "images" / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")

        tree = ET.parse(tsx_path)
        image_el = tree.getroot().find("image")
        assert image_el is not None
        assert image_el.attrib["source"] == "../images/test.png"
        assert image_el.attrib["width"] == str(47 * 32)
        assert image_el.attrib["height"] == "32"

    def test_wangset_structure(self, tmp_path: Path) -> None:
        """TSX contains wangset with type=mixed and wangcolor."""
        tsx_path = tmp_path / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")

        tree = ET.parse(tsx_path)
        wangset = tree.getroot().find(".//wangset")
        assert wangset is not None
        assert wangset.attrib["type"] == "mixed"
        assert wangset.attrib["name"] == "test_terrain"

        wangcolor = wangset.find("wangcolor")
        assert wangcolor is not None
        assert wangcolor.attrib["name"] == "test_terrain"

    def test_47_wangtile_entries(self, tmp_path: Path) -> None:
        """TSX contains exactly 47 wangtile entries."""
        tsx_path = tmp_path / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")

        tree = ET.parse(tsx_path)
        wangtiles = tree.getroot().findall(".//wangtile")
        assert len(wangtiles) == 47

    def test_first_wangtile_bitmask_0(self, tmp_path: Path) -> None:
        """First wangtile (bitmask 0) has wangid=0,0,0,0,0,0,0,0."""
        tsx_path = tmp_path / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")

        tree = ET.parse(tsx_path)
        wangtiles = tree.getroot().findall(".//wangtile")
        first = wangtiles[0]
        assert first.attrib["tileid"] == "0"
        assert first.attrib["wangid"] == "0,0,0,0,0,0,0,0"

    def test_last_wangtile_bitmask_255(self, tmp_path: Path) -> None:
        """Last wangtile (bitmask 255) has wangid=1,1,1,1,1,1,1,1."""
        tsx_path = tmp_path / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")

        tree = ET.parse(tsx_path)
        wangtiles = tree.getroot().findall(".//wangtile")
        last = wangtiles[-1]
        assert last.attrib["tileid"] == "46"
        assert last.attrib["wangid"] == "1,1,1,1,1,1,1,1"

    def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
        """TSX export creates parent directories."""
        tsx_path = tmp_path / "deep" / "nested" / "test.tsx"
        png_path = tmp_path / "test.png"
        export_tsx(tsx_path, png_path, "test_terrain")
        assert tsx_path.exists()


# ── TC-019: Relative path computation ─────────────────────────────────────────


class TestRelativePath:
    """TC-019: Relative path computation."""

    def test_same_directory(self) -> None:
        """PNG and TSX in the same directory."""
        result = compute_relative_path(
            Path("/a/b/img.png"), Path("/a/b/out.tsx")
        )
        assert result == "img.png"

    def test_sibling_directories(self) -> None:
        """PNG in sibling images/ dir, TSX in tiled/ dir."""
        result = compute_relative_path(
            Path("/a/images/img.png"), Path("/a/tiled/out.tsx")
        )
        assert result == "../images/img.png"

    def test_deeper_nesting(self) -> None:
        """PNG deeper than TSX."""
        result = compute_relative_path(
            Path("/project/assets/images/autotiles/grass.png"),
            Path("/project/assets/tiled/autotiles/grass.tsx"),
        )
        assert result == "../../images/autotiles/grass.png"
