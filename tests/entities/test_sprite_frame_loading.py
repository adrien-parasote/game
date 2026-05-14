"""
TDD — RED tests for sprite frame height bug.

Symptom: Torches and animated sprites do not display correctly.
Root cause: _load_assets computes real_frame_h = sheet_h // (end_row + 1),
            which is wrong when the spritesheet has more rows than end_row + 1.
            The correct value is sprite_height (declared frame height).

Bug file: src/entities/interactive.py — _load_assets()
"""

import os
from unittest.mock import MagicMock, patch, PropertyMock

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.entities.interactive import InteractiveEntity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sheet_mock(sheet_width: int, sheet_height: int) -> MagicMock:
    """Simulate a valid SpriteSheet with a real pygame surface of given size."""
    mock = MagicMock()
    mock.valid = True
    mock.sheet = pygame.Surface((sheet_width, sheet_height))
    mock.last_cols = sheet_width // 32
    return mock


def _make_interactive_with_real_sheet(
    sheet_mock: MagicMock,
    sprite_width: int = 32,
    sprite_height: int = 32,
    start_row: int = 0,
    end_row: int = 3,
    is_animated: bool = True,
    is_on: bool = True,
) -> InteractiveEntity:
    """Instantiate InteractiveEntity with a mocked-but-valid SpriteSheet."""
    group = pygame.sprite.Group()

    # We capture the args passed to load_grid_by_size to assert correctness
    captured = {}

    def capture_load_grid_by_size(frame_w, frame_h, transparent=False):
        captured["frame_w"] = frame_w
        captured["frame_h"] = frame_h
        cols = sheet_mock.sheet.get_width() // frame_w
        rows = sheet_mock.sheet.get_height() // frame_h
        sheet_mock.last_cols = cols
        return [pygame.Surface((frame_w, frame_h)) for _ in range(cols * rows)]

    sheet_mock.load_grid_by_size.side_effect = capture_load_grid_by_size

    with patch("src.entities.interactive.SpriteSheet", return_value=sheet_mock):
        entity = InteractiveEntity(
            pos=(100, 100),
            groups=[group],
            sub_type="torch",
            sprite_sheet="fake_torch.png",
            position=0,
            depth=1,
            start_row=start_row,
            end_row=end_row,
            width=sprite_width,
            height=sprite_height,
            tiled_width=32,
            tiled_height=32,
            obstacles_group=None,
            is_passable=False,
            is_animated=is_animated,
            is_on=is_on,
            halo_size=0,
            element_id="torch_1",
        )

    entity._captured = captured
    return entity


# ---------------------------------------------------------------------------
# RED tests — these MUST FAIL before the fix
# ---------------------------------------------------------------------------


class TestSpriteFrameHeightCalculation:
    """
    Verify that _load_assets passes sprite_height (not sheet_h // (end_row+1))
    as the frame_h to load_grid_by_size.
    """

    @pytest.mark.tc("SPRITE-U-01")
    def test_torch_frame_height_uses_sprite_height(self):
        """
        A torch spritesheet 32×256 with sprite_height=32 and end_row=3
        must call load_grid_by_size with frame_h=32, NOT frame_h=64.

        Bug: end_row+1 = 4, sheet_h // 4 = 64 → wrong frame slicing.
        Fix: use sprite_height=32 directly.
        """
        # Sheet is 32px wide × 256px tall → 8 real rows of 32px each
        sheet = _make_sheet_mock(sheet_width=32, sheet_height=256)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,
            end_row=3,
        )
        assert entity._captured["frame_h"] == 32, (
            f"Expected frame_h=32 (sprite_height), "
            f"got frame_h={entity._captured['frame_h']} (sheet_h // (end_row+1))"
        )

    @pytest.mark.tc("SPRITE-U-02")
    def test_frame_count_matches_real_sheet_layout(self):
        """
        A 128×128 sheet with 32×32 frames must produce 16 frames (4 cols × 4 rows),
        regardless of end_row.

        Bug: end_row+1=4 → frame_h=128//4=32 → luck! only works when end_row+1 == real rows.
        But with a 32×256 sheet and end_row=3: frame_h=64 → only 4 frames instead of 8×4=32.
        """
        sheet = _make_sheet_mock(sheet_width=128, sheet_height=128)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,
            end_row=3,  # 4 rows expected, matches sheet → would pass even with bug
        )
        # 128 // 32 = 4 cols, 128 // 32 = 4 rows → 16 frames
        assert len(entity.frames) == 16, (
            f"Expected 16 frames (4×4), got {len(entity.frames)}"
        )

    @pytest.mark.tc("SPRITE-U-03")
    def test_multidirectional_sheet_correct_frame_count(self):
        """
        A 128×256 sheet (4 cols × 8 rows of 32px) with end_row=3 must produce
        32 frames, not 16.

        Bug: end_row+1=4 → frame_h=256//4=64 → 4 rows detected → 16 frames (WRONG).
        Fix: sprite_height=32 → 8 rows → 32 frames (CORRECT).
        """
        sheet = _make_sheet_mock(sheet_width=128, sheet_height=256)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,
            end_row=3,
        )
        # 128 // 32 = 4 cols, 256 // 32 = 8 rows → 32 frames
        assert len(entity.frames) == 32, (
            f"Expected 32 frames (4×8 real rows), got {len(entity.frames)} "
            f"(frame_h was likely {entity._captured.get('frame_h', '?')} instead of 32)"
        )

    @pytest.mark.tc("SPRITE-U-04")
    def test_get_frame_returns_non_default_image_after_load(self):
        """
        After loading a valid sheet, _get_frame(0) must return a Surface with the
        correct declared dimensions (sprite_width × sprite_height), not arbitrary.

        Proves that the frames array was sliced at the right height.
        """
        sheet = _make_sheet_mock(sheet_width=32, sheet_height=256)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,
            end_row=3,
        )
        frame = entity._get_frame(0)
        assert frame.get_width() == 32
        assert frame.get_height() == 32, (
            f"Expected frame height=32, got {frame.get_height()}. "
            f"Slicing was done with frame_h={entity._captured.get('frame_h', '?')}"
        )
