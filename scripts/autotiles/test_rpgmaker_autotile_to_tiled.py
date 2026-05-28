"""
TDD tests for scripts/rpgmaker_autotile_to_tiled.py

Tests derived directly from scripts/docs/game/specs/autotile-pipeline-spec.md
Test IDs: UT-001..UT-009, IT-001..IT-003
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Path to the script's directory so we can import it directly.
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from rpgmaker_autotile_to_tiled import (  # noqa: E402
    _Q,
    TILE_COUNT,
    TILE_SIZE,
    _quarter_source,
    _wang_id,
    convert,
)


def _make_autotile(width: int = 96, height: int = 128, color: tuple = (0, 200, 0, 255)) -> Image.Image:
    """Create a synthetic RGBA autotile image filled with a solid color."""
    img = Image.new("RGBA", (width, height), color)
    return img


def _save_autotile(tmp_path: Path, **kwargs) -> Path:
    """Save a synthetic autotile PNG and return the path."""
    img = _make_autotile(**kwargs)
    p = tmp_path / "test_autotile.png"
    img.save(p)
    return p


# ---------------------------------------------------------------------------
# UT-001 — No CLI args → sys.exit with usage message
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut001_no_args_exits_with_usage(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["rpgmaker_autotile_to_tiled.py"])
    from rpgmaker_autotile_to_tiled import main  # noqa: PLC0415

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# UT-002 — Nonexistent input file → sys.exit with file-not-found message
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut002_missing_file_exits(monkeypatch, tmp_path):
    missing = tmp_path / "nonexistent.png"
    monkeypatch.setattr(sys, "argv", ["rpgmaker_autotile_to_tiled.py", str(missing)])
    from rpgmaker_autotile_to_tiled import main  # noqa: PLC0415

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# UT-003 — Wrong image size → sys.exit with size mismatch message
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut003_wrong_size_exits(tmp_path):
    wrong = _make_autotile(width=64, height=64)
    src = tmp_path / "wrong.png"
    wrong.save(src)
    tsx = tmp_path / "out.tsx"
    png = tmp_path / "out.png"

    with pytest.raises(SystemExit) as exc:
        convert(src, tsx, png)
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# UT-004 — _wang_id(0) → all-zero edge Wang ID
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut004_wang_id_zero():
    assert _wang_id(0) == "0,0,0,0,0,0,0,0"


# ---------------------------------------------------------------------------
# UT-005 — _wang_id(15) → all-one edge Wang ID (all edges active)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut005_wang_id_full():
    assert _wang_id(15) == "1,0,1,0,1,0,1,0"


# ---------------------------------------------------------------------------
# UT-006 — _wang_id(1) → only top edge active
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut006_wang_id_top_only():
    # bit0 = Top
    assert _wang_id(1) == "1,0,0,0,0,0,0,0"


# ---------------------------------------------------------------------------
# UT-007 — _wang_id(8) → only left edge active
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut007_wang_id_left_only():
    # bit3 = Left
    assert _wang_id(8) == "0,0,0,0,0,0,1,0"


# ---------------------------------------------------------------------------
# UT-008 — _quarter_source: top-only → top-edge source for tl corner
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut008_quarter_source_top_only_tl():
    # only top neighbour present, corner tl
    # → left side is the BORDER, top connects
    # → use left-edge tile's TL quadrant (lft_tl) because it shows "left=border, top=connects"
    result = _quarter_source(top=True, right=False, bottom=False, left=False, corner="tl")
    assert result == _Q["lft_tl"], f"Expected lft_tl={_Q['lft_tl']!r}, got {result!r}"


# ---------------------------------------------------------------------------
# UT-009 — _quarter_source: top+left → inner center source for tl corner
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut009_quarter_source_top_and_left_tl():
    result = _quarter_source(top=True, right=False, bottom=False, left=True, corner="tl")
    assert result == _Q["inn_tl"], f"Expected inn_tl={_Q['inn_tl']!r}, got {result!r}"


# ---------------------------------------------------------------------------
# IT-001 — Full pipeline: produces 512×32 PNG and valid TSX with 16 wangtile elements
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it001_full_pipeline_produces_correct_outputs(tmp_path):
    src = _save_autotile(tmp_path)
    tsx = tmp_path / "out" / "tileset.tsx"
    png = tmp_path / "img" / "tileset.png"

    convert(src, tsx, png)

    # PNG dimensions
    result_img = Image.open(png)
    assert result_img.size == (TILE_SIZE * TILE_COUNT, TILE_SIZE), (
        f"Expected {TILE_SIZE * TILE_COUNT}×{TILE_SIZE}, got {result_img.size}"
    )

    # TSX is valid XML with 16 wangtile elements
    tree = ET.parse(tsx)
    root = tree.getroot()
    wangtiles = root.findall(".//wangtile")
    assert len(wangtiles) == TILE_COUNT, f"Expected {TILE_COUNT} wangtiles, got {len(wangtiles)}"


# ---------------------------------------------------------------------------
# IT-002 — TSX <image source> is a relative path (not absolute)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it002_tsx_image_source_is_relative(tmp_path):
    src = _save_autotile(tmp_path)
    tsx = tmp_path / "tilesets" / "tileset.tsx"
    png = tmp_path / "images" / "tileset.png"

    convert(src, tsx, png)

    tree = ET.parse(tsx)
    root = tree.getroot()
    image_el = root.find("image")
    assert image_el is not None
    source = image_el.get("source", "")
    assert not Path(source).is_absolute(), f"Expected relative path, got: {source!r}"


# ---------------------------------------------------------------------------
# IT-003 — TSX wangid for tile 15 is "1,0,1,0,1,0,1,0"
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it003_tsx_wangid_tile_15(tmp_path):
    src = _save_autotile(tmp_path)
    tsx = tmp_path / "tileset.tsx"
    png = tmp_path / "tileset.png"

    convert(src, tsx, png)

    tree = ET.parse(tsx)
    root = tree.getroot()
    wangtiles = {wt.get("tileid"): wt.get("wangid") for wt in root.findall(".//wangtile")}
    assert wangtiles.get("15") == "1,0,1,0,1,0,1,0", (
        f"Expected '1,0,1,0,1,0,1,0' for tileid=15, got {wangtiles.get('15')!r}"
    )
