"""
Tests — sprite frame height calculation in _load_assets.

The authoritative frame height is sheet_h // (end_row + 1).
The Tiled-declared `height` property is a fallback for when no sheet is available.

Commit 73c8f8c incorrectly switched to using sprite_height (Tiled value) directly,
breaking chests (128×172 sheet → 32px instead of 43px) and leviers (32×128 → 32px
instead of 64px). This file validates the correct sheet-based calculation.
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
# Tests — sheet-based frame height calculation
# ---------------------------------------------------------------------------


class TestSpriteFrameHeightCalculation:
    """
    Verify that _load_assets derives frame_h from the sheet (sheet_h // (end_row+1)),
    not from the Tiled-declared sprite_height.

    The spritesheet is the authoritative source for frame dimensions.
    """

    @pytest.mark.tc("SPRITE-U-01")
    def test_torch_frame_height_computed_from_sheet(self):
        """
        A torch spritesheet 32×256 with end_row=3 must call load_grid_by_size
        with frame_h = 256 // (3+1) = 64, NOT the Tiled-declared sprite_height=32.

        The sheet is the authoritative source for frame dimensions.
        end_row+1 = 4 animation rows → each row = 256 // 4 = 64px.
        """
        # Sheet is 32px wide × 256px tall → 4 rows of 64px each
        sheet = _make_sheet_mock(sheet_width=32, sheet_height=256)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,  # Tiled declares 32px, but sheet overrides
            end_row=3,
        )
        assert entity._captured["frame_h"] == 64, (
            f"Expected frame_h=64 (sheet_h // (end_row+1)), "
            f"got frame_h={entity._captured['frame_h']}"
        )

    @pytest.mark.tc("SPRITE-U-02")
    def test_frame_count_matches_real_sheet_layout(self):
        """
        A 128×128 sheet with 32×32 frames must produce 16 frames (4 cols × 4 rows),
        regardless of end_row.

        This case is neutral: sheet_h // (end_row+1) = 128 // 4 = 32 = sprite_height.
        Both logics give the same result, so this test still passes.
        """
        sheet = _make_sheet_mock(sheet_width=128, sheet_height=128)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,
            end_row=3,  # 4 rows expected, matches sheet exactly
        )
        # 128 // 32 = 4 cols, 128 // 32 = 4 rows → 16 frames
        assert len(entity.frames) == 16, (
            f"Expected 16 frames (4×4), got {len(entity.frames)}"
        )

    @pytest.mark.tc("SPRITE-U-03")
    def test_chest_sheet_correct_frame_height(self):
        """
        A chest spritesheet 128×172 with end_row=3 must produce frames of
        height 43px (172 // 4), not 32px.

        This was the visual centering regression: with frame_h=32, the coffre sprite
        was sliced incorrectly and appeared misaligned on the grid.
        """
        sheet = _make_sheet_mock(sheet_width=128, sheet_height=172)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,  # Tiled declares 32, sheet overrides to 43
            end_row=3,
        )
        assert entity._captured["frame_h"] == 43, (
            f"Expected frame_h=43 (172 // 4), got {entity._captured.get('frame_h', '?')}"
        )

    @pytest.mark.tc("SPRITE-U-04")
    def test_get_frame_returns_sheet_height_not_tiled_height(self):
        """
        After loading a valid sheet (128×172, end_row=3), _get_frame(0) must return
        a Surface with the computed frame height (43px), not the Tiled-declared 32px.

        Validates that self.sprite_height is updated from the sheet, and that
        _setup_physics uses the correct rect size for centering.
        """
        sheet = _make_sheet_mock(sheet_width=128, sheet_height=172)
        entity = _make_interactive_with_real_sheet(
            sheet_mock=sheet,
            sprite_width=32,
            sprite_height=32,  # Tiled declares 32, but sheet overrides to 43
            end_row=3,
        )
        frame = entity._get_frame(0)
        assert frame.get_width() == 32
        assert frame.get_height() == 43, (
            f"Expected frame height=43 (172 // 4), got {frame.get_height()}. "
            f"self.sprite_height should have been updated from the sheet."
        )
