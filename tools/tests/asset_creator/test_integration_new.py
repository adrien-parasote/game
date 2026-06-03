import pytest
import os
from asset_creator.core.generator import generate
from asset_creator.core.quantizer import quantize
from asset_creator.exporters.exporter import export

def test_it_002_end_to_end_pipeline(tmp_path):
    """IT-002: End-to-end pipeline."""
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        arr = generate("stone", 42, 4.0)
        pico8_palette = [(0,0,0), (255,255,255)]
        img = quantize(arr, pico8_palette)
        export(img, "stone_42")
        
        assert os.path.exists("output/stone_42.tsx")
        assert os.path.exists("output/stone_42.png")
        
        from PIL import Image
        saved_img = Image.open("output/stone_42.png")
        assert saved_img.size == (32, 32)
    finally:
        os.chdir(orig_dir)
        
def test_it_003_write_failure_handling(tmp_path, monkeypatch):
    """IT-003: Write failure handling."""
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        def mock_makedirs(*args, **kwargs):
            raise PermissionError("Mock permission error")
            
        monkeypatch.setattr(os, "makedirs", mock_makedirs)
        
        img = __import__("PIL").Image.new("RGB", (32, 32))
        
        # It should raise PermissionError and let the GUI catch it
        with pytest.raises(PermissionError):
            export(img, "stone_42")
    finally:
        os.chdir(orig_dir)
