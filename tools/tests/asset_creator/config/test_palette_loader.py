import json
from src.asset_creator.config.palette_loader import load_palettes

def test_tc006_palette_loader(tmp_path):
    """TC-006: palettes.json is parsed from hex strings to RGB tuples."""
    fake_json = tmp_path / "palettes.json"
    fake_json.write_text(json.dumps({
        "TestPalette": ["#000000", "#1D2B53", "#008751", "#ABFC4C"]
    }))
    palettes = load_palettes(str(fake_json))
    assert "TestPalette" in palettes
    assert palettes["TestPalette"] == [(0,0,0), (29,43,83), (0,135,81), (171,252,76)]
