"""
TDD tests for off_position support on InteractiveEntity.

Spec:
- off_position=-1 → no column switch (default, backward-compat)
- off_position=N  → col_index=N when is_on=False, col_index=on_position when True
- interact() toggles is_on and updates col_index accordingly
- restore_state({'is_on': bool}) also updates col_index
"""

from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.entities.interactive import InteractiveEntity


def _make_entity(**kwargs) -> InteractiveEntity:
    """Helper: build an InteractiveEntity with sensible defaults."""
    defaults = dict(
        pos=(100, 100),
        groups=[],
        sub_type="animated_decor",
        sprite_sheet="",
        position=0,
        is_on=True,
        is_animated=True,
        off_position=-1,
    )
    defaults.update(kwargs)
    return InteractiveEntity(**defaults)  # type: ignore


# ── Initialization ──────────────────────────────────────────────────────────


class TestOffPositionInit:
    def test_no_off_position_col_index_equals_position(self):
        """off_position=-1 → col_index stays at on_position (backward compat)."""
        entity = _make_entity(position=0, off_position=-1, is_on=True)
        assert entity.col_index == 0

    def test_is_on_true_col_index_equals_on_position(self):
        """When is_on=True and off_position set, col_index = on_position."""
        entity = _make_entity(position=0, off_position=1, is_on=True)
        assert entity.col_index == 0

    def test_is_on_false_col_index_equals_off_position(self):
        """When is_on=False and off_position=1, col_index = 1."""
        entity = _make_entity(position=0, off_position=1, is_on=False)
        assert entity.col_index == 1

    def test_off_position_stored(self):
        """Entity stores both on_position and off_position."""
        entity = _make_entity(position=0, off_position=1)
        assert entity.on_position == 0
        assert entity.off_position == 1

    def test_no_off_position_defaults_minus_one(self):
        """Default off_position is -1 when not passed."""
        entity = _make_entity()
        assert entity.off_position == -1


# ── Toggling via interact() ─────────────────────────────────────────────────


class TestOffPositionToggle:
    def test_interact_on_to_off_switches_col(self):
        """interact() when ON → OFF should set col_index to off_position."""
        entity = _make_entity(position=0, off_position=1, is_on=True, is_animated=True)
        entity.interact(MagicMock())
        assert entity.is_on is False
        assert entity.col_index == 1

    def test_interact_off_to_on_restores_col(self):
        """interact() when OFF → ON should restore col_index to on_position."""
        entity = _make_entity(position=0, off_position=1, is_on=False, is_animated=True)
        entity.interact(MagicMock())
        assert entity.is_on is True
        assert entity.col_index == 0

    def test_interact_no_off_position_col_unchanged(self):
        """When off_position=-1, col_index never changes on toggle."""
        entity = _make_entity(position=0, off_position=-1, is_on=True, is_animated=True)
        entity.interact(MagicMock())
        assert entity.col_index == 0

    def test_interact_double_toggle_returns_to_on(self):
        """Two interact() calls cycle back to ON with correct col."""
        entity = _make_entity(position=0, off_position=1, is_on=True, is_animated=True)
        entity.interact(MagicMock())  # → OFF
        entity.interact(MagicMock())  # → ON
        assert entity.is_on is True
        assert entity.col_index == 0


# ── State restore ───────────────────────────────────────────────────────────


class TestOffPositionRestoreState:
    def test_restore_on_sets_on_col(self):
        """restore_state({'is_on': True}) → col_index = on_position."""
        entity = _make_entity(position=0, off_position=1, is_on=False)
        entity.restore_state({"is_on": True})
        assert entity.col_index == 0

    def test_restore_off_sets_off_col(self):
        """restore_state({'is_on': False}) → col_index = off_position."""
        entity = _make_entity(position=0, off_position=1, is_on=True)
        entity.restore_state({"is_on": False})
        assert entity.col_index == 1

    def test_restore_off_no_off_position_keeps_on_col(self):
        """restore_state OFF with off_position=-1 keeps col_index = on_position."""
        entity = _make_entity(position=0, off_position=-1, is_on=True)
        entity.restore_state({"is_on": False})
        assert entity.col_index == 0


# ── Frame rendering ─────────────────────────────────────────────────────────


class TestOffPositionFrameRendering:
    def test_get_frame_uses_off_col_when_off(self):
        """_get_frame picks the correct column based on col_index when OFF."""
        # Build entity with 2-col sheet (simulated with 8 frames: 4 rows × 2 cols)
        entity = _make_entity(position=0, off_position=1, is_on=False, is_animated=True)
        # Manually inject a 2-col frame grid so index arithmetic is predictable
        entity._sheet_cols = 2
        entity.frames = [pygame.Surface((32, 32)) for _ in range(8)]
        # row 0, col 1 → index = 0*2 + 1 = 1
        frame = entity._get_frame(0)
        assert frame is entity.frames[1]

    def test_get_frame_uses_on_col_when_on(self):
        """_get_frame picks col 0 (on_position) when entity is ON."""
        entity = _make_entity(position=0, off_position=1, is_on=True, is_animated=True)
        entity._sheet_cols = 2
        entity.frames = [pygame.Surface((32, 32)) for _ in range(8)]
        # row 0, col 0 → index = 0
        frame = entity._get_frame(0)
        assert frame is entity.frames[0]
