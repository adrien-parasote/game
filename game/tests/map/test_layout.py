
import pytest
from src.config import Settings
from src.map.layout import OrthogonalLayout


class TestOrthogonalLayout:
    def test_to_screen_converts_tile_to_pixels(self):
        """to_screen(x, y) → (x * tile_size, y * tile_size)."""
        layout = OrthogonalLayout(tile_size=32)
        sx, sy = layout.to_screen(3, 5)
        assert sx == 96
        assert sy == 160

    def test_to_screen_fractional(self):
        """Ligne 27 : to_screen avec coordonnées décimales."""
        layout = OrthogonalLayout(tile_size=32)
        sx, sy = layout.to_screen(1.5, 2.5)
        assert sx == pytest.approx(48.0)
        assert sy == pytest.approx(80.0)

    def test_to_world_converts_pixels_to_tiles(self):
        """Ligne 17 : to_world(px, py) → (px / tile_size, py / tile_size)."""
        layout = OrthogonalLayout(tile_size=32)
        tx, ty = layout.to_world(64, 96)
        assert tx == pytest.approx(2.0)
        assert ty == pytest.approx(3.0)

    def test_to_world_fractional(self):
        """to_world arrondit correctement les positions sub-tile."""
        layout = OrthogonalLayout(tile_size=32)
        tx, ty = layout.to_world(48, 16)
        assert tx == pytest.approx(1.5)
        assert ty == pytest.approx(0.5)

    def test_default_tile_size_is_settings(self):
        """OrthogonalLayout() sans argument utilise Settings.TILE_SIZE."""
        layout = OrthogonalLayout()
        assert layout.tile_size == Settings.TILE_SIZE

    def test_roundtrip(self):
        """to_world(to_screen(x, y)) == (x, y) pour tout x, y entier."""
        layout = OrthogonalLayout(tile_size=32)
        for x, y in [(0, 0), (5, 3), (10, 20)]:
            sx, sy = layout.to_screen(x, y)
            tx, ty = layout.to_world(sx, sy)
            assert tx == pytest.approx(x)
            assert ty == pytest.approx(y)
