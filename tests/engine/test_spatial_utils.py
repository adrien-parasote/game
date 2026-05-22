"""RED tests for Phase 1.5 — spatial_utils pure functions.

TC-SU-01..TC-SU-13 from docs/specs/phase-1.5-interaction-refactoring.md
"""

from unittest.mock import MagicMock

import pygame
import pytest

from src.engine.spatial_utils import facing_toward, get_facing_vector, verify_orientation

# ---------------------------------------------------------------------------
# TC-SU-01..05 — get_facing_vector
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-SU-01")
def test_get_facing_vector_down():
    assert get_facing_vector("down") == pygame.math.Vector2(0, 1)


@pytest.mark.tc("TC-SU-02")
def test_get_facing_vector_up():
    assert get_facing_vector("up") == pygame.math.Vector2(0, -1)


@pytest.mark.tc("TC-SU-03")
def test_get_facing_vector_left():
    assert get_facing_vector("left") == pygame.math.Vector2(-1, 0)


@pytest.mark.tc("TC-SU-04")
def test_get_facing_vector_right():
    assert get_facing_vector("right") == pygame.math.Vector2(1, 0)


@pytest.mark.tc("TC-SU-05")
def test_get_facing_vector_unknown_state():
    assert get_facing_vector("idle") == pygame.math.Vector2(0, 0)


# ---------------------------------------------------------------------------
# TC-SU-06..09 — facing_toward
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-SU-06")
def test_facing_toward_right_horizontal():
    result = facing_toward(
        pygame.math.Vector2(0, 0), "right", pygame.math.Vector2(10, 0)
    )
    assert result is True


@pytest.mark.tc("TC-SU-07")
def test_facing_toward_left_horizontal():
    result = facing_toward(
        pygame.math.Vector2(10, 0), "left", pygame.math.Vector2(0, 0)
    )
    assert result is True


@pytest.mark.tc("TC-SU-08")
def test_facing_toward_down_vertical():
    result = facing_toward(
        pygame.math.Vector2(0, 0), "down", pygame.math.Vector2(0, 10)
    )
    assert result is True


@pytest.mark.tc("TC-SU-09")
def test_facing_toward_wrong_direction():
    result = facing_toward(
        pygame.math.Vector2(0, 0), "left", pygame.math.Vector2(10, 0)
    )
    assert result is False


# ---------------------------------------------------------------------------
# TC-SU-10..13 — verify_orientation
# ---------------------------------------------------------------------------


def _make_obj(direction_str="up", pos=None, sub_type="lever", is_on=False):
    obj = MagicMock()
    obj.direction_str = direction_str
    obj.pos = pos or pygame.math.Vector2(100, 100)
    obj.sub_type = sub_type
    obj.is_on = is_on
    return obj


@pytest.mark.tc("TC-SU-10")
def test_verify_orientation_standard_up_down():
    """Object faces up, player is below (south) facing down → True."""
    obj = _make_obj(direction_str="up", pos=pygame.math.Vector2(100, 100))
    # Player is below the object (p_pos.y > o_pos.y is False since p_pos.y < o_pos.y means player is above)
    # o_dir="up" means front is up; player must be at top (p_pos.y < o_pos.y) facing down
    p_pos = pygame.math.Vector2(100, 90)  # player above object (y < o.y)
    result = verify_orientation(obj, "down", p_pos)
    assert result is True


@pytest.mark.tc("TC-SU-11")
def test_verify_orientation_not_aligned():
    """Player too far on X axis → False."""
    obj = _make_obj(direction_str="up", pos=pygame.math.Vector2(100, 100))
    p_pos = pygame.math.Vector2(200, 90)  # far away on X, not x_aligned
    result = verify_orientation(obj, "down", p_pos)
    assert result is False


@pytest.mark.tc("TC-SU-12")
def test_verify_orientation_door_relaxation():
    """Open door: player on back side, same facing as door → True (relaxation)."""
    obj = _make_obj(
        direction_str="up",
        pos=pygame.math.Vector2(100, 100),
        sub_type="door",
        is_on=True,
    )
    # Relaxation: o_dir="up", p_state="up", p_pos.y > o_pos.y (player is below = back side)
    p_pos = pygame.math.Vector2(100, 110)  # below door (back side), x_aligned
    result = verify_orientation(obj, "up", p_pos)
    assert result is True


@pytest.mark.tc("TC-SU-13")
def test_verify_orientation_default_false():
    """No matching case → False."""
    obj = _make_obj(direction_str="down", pos=pygame.math.Vector2(100, 100))
    # Player to the right, facing right — no case matches
    p_pos = pygame.math.Vector2(110, 100)
    result = verify_orientation(obj, "right", p_pos)
    assert result is False


# ---------------------------------------------------------------------------
# Extra branch coverage — _is_front_facing and _is_back_facing
# ---------------------------------------------------------------------------

def test_is_front_facing_down_branch():
    """Ligne 67 : o_dir='down', p_state='up', dy > 0 → front-facing True."""
    from src.engine.spatial_utils import _is_front_facing
    # y_aligned est inutilisé ici — seul x_aligned et la branche down importent
    result = _is_front_facing(
        o_dir="down", p_state="up",
        dx=0.0, dy=10.0,       # dy > 0 → player below, object faces down
        x_aligned=True, y_aligned=False
    )
    assert result is True


def test_is_back_facing_left_branch():
    """Ligne 84 : o_dir='left', p_state='left', dx > 0 → back-facing True (open door)."""
    from src.engine.spatial_utils import _is_back_facing
    result = _is_back_facing(
        o_dir="left", p_state="left",
        dx=5.0, dy=0.0,
        x_aligned=False, y_aligned=True
    )
    assert result is True


def test_is_back_facing_right_branch():
    """Ligne 86 : o_dir='right', p_state='right', dx < 0 → back-facing True (open door)."""
    from src.engine.spatial_utils import _is_back_facing
    result = _is_back_facing(
        o_dir="right", p_state="right",
        dx=-5.0, dy=0.0,
        x_aligned=False, y_aligned=True
    )
    assert result is True


def test_is_back_facing_returns_false_when_no_match():
    """Ligne 87 : return False quand aucune condition de back-facing n'est satisfaite."""
    from src.engine.spatial_utils import _is_back_facing
    result = _is_back_facing(
        o_dir="up", p_state="down",  # combinaison non gérée par back-facing
        dx=0.0, dy=10.0,
        x_aligned=True, y_aligned=False
    )
    assert result is False
