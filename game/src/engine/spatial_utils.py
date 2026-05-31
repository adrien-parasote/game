"""Pure spatial/geometry utility functions extracted from InteractionManager.

These functions have no state and no dependency on `game` context.
Extracted from src/engine/interaction.py as part of Phase 1.5 refactoring.

Deep links:
  - Origin: src/engine/interaction.py#L265-L320
  - Spec: game/docs/specs/phase-1.5-interaction-refactoring.md
"""

import pygame

# ── Facing vector ────────────────────────────────────────────────────────────


def get_facing_vector(state: str) -> pygame.math.Vector2:
    """Return unit vector for the given player facing state.

    Args:
        state: Player direction string ('up', 'down', 'left', 'right').

    Returns:
        Corresponding unit Vector2. Zero vector for unknown states.
    """
    if state == "down":
        return pygame.math.Vector2(0, 1)
    if state == "up":
        return pygame.math.Vector2(0, -1)
    if state == "left":
        return pygame.math.Vector2(-1, 0)
    if state == "right":
        return pygame.math.Vector2(1, 0)
    return pygame.math.Vector2(0, 0)


# ── Facing toward ────────────────────────────────────────────────────────────


def facing_toward(
    player_pos: pygame.math.Vector2,
    facing: str,
    obj_pos: pygame.math.Vector2,
) -> bool:
    """Return True if the player looks toward obj_pos from player_pos.

    Uses dominant axis: horizontal takes priority over vertical when
    |dx| >= |dy|. Extracted from InteractionManager._facing_toward (L277-L286).

    Args:
        player_pos: Player world position.
        facing: Player facing string ('up', 'down', 'left', 'right').
        obj_pos: Target object world position.
    """
    dx = obj_pos.x - player_pos.x
    dy = obj_pos.y - player_pos.y
    if abs(dx) >= abs(dy):  # horizontal dominant axis
        return (facing == "right" and dx > 0) or (facing == "left" and dx < 0)
    # vertical dominant axis
    return (facing == "down" and dy > 0) or (facing == "up" and dy < 0)


def _is_front_facing(o_dir: str, p_state: str, dx: float, dy: float, x_aligned: bool, y_aligned: bool) -> bool:
    if x_aligned:
        if o_dir == "up" and p_state == "down" and dy < 0:
            return True
        if o_dir == "down" and p_state == "up" and dy > 0:
            return True
    if y_aligned:
        if o_dir == "left" and p_state == "right" and dx < 0:
            return True
        if o_dir == "right" and p_state == "left" and dx > 0:
            return True
    return False


def _is_back_facing(o_dir: str, p_state: str, dx: float, dy: float, x_aligned: bool, y_aligned: bool) -> bool:
    if x_aligned:
        if o_dir == "up" and p_state == "up" and dy > 0:
            return True
        if o_dir == "down" and p_state == "down" and dy < 0:
            return True
    if y_aligned:
        if o_dir == "left" and p_state == "left" and dx > 0:
            return True
        if o_dir == "right" and p_state == "right" and dx < 0:
            return True
    return False


def verify_orientation(
    obj,
    p_state: str,
    p_pos: pygame.math.Vector2,
) -> bool:
    """Verify if the player is correctly oriented toward an object to interact.

    The player must stand at the object's front side, facing it.
    Open doors allow interaction from both sides (relaxation rule).

    Extracted from InteractionManager._verify_orientation (L288-L320).
    Alignment threshold: 20px on the orthogonal axis.

    Args:
        obj: Interactive entity with `direction_str`, `pos`, `sub_type`, `is_on`.
        p_state: Player current facing state string.
        p_pos: Player world position Vector2.

    Returns:
        True if the player can interact, False otherwise.
    """
    o_dir = getattr(obj, "direction_str", "down")
    o_pos = obj.pos

    x_aligned = abs(p_pos.x - o_pos.x) < 20
    y_aligned = abs(p_pos.y - o_pos.y) < 20
    dx = p_pos.x - o_pos.x
    dy = p_pos.y - o_pos.y

    if _is_front_facing(o_dir, p_state, dx, dy, x_aligned, y_aligned):
        return True

    if obj.sub_type == "door" and getattr(obj, "is_on", False):
        return _is_back_facing(o_dir, p_state, dx, dy, x_aligned, y_aligned)

    return False
