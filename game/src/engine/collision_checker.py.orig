"""CollisionChecker: tile + entity collision detection.

Extracted from InteractionManager.is_collidable (L364-L390).
Used by InteractionManager via a thin wrapper preserving the public API.

Deep links:
  - Origin: src/engine/interaction.py#L364-L390
  - Spec: game/docs/specs/phase-1.5-interaction-refactoring.md
"""

from typing import Any


class CollisionChecker:
    """Checks whether a pixel position is blocked by map tiles or entities.

    Args:
        game: Game context (Any — ADR-004 pattern).
    """

    def __init__(self, game: Any) -> None:
        self.game = game

    def check(  # noqa: C901
        self,
        px_center: float,
        py_center: float,
        requester=None,
    ) -> bool:
        """Return True if (px_center, py_center) is blocked.

        Checks in order:
          1. Map tile collidability via layout + map_manager
          2. Dynamic obstacles (doors, etc.)
          3. NPCs
          4. Player (when requester is not the player)

        Args:
            px_center: X pixel coordinate of the target position.
            py_center: Y pixel coordinate of the target position.
            requester: Entity requesting the check — skipped in all group checks.
        """
        # 0. Walkable overrides (passable bridges/drawbridges open above non-walkable tiles)
        tile_overridden = False
        for entity in getattr(self.game, "walkable_override_entities", ()):
            if entity.rect and entity.rect.collidepoint(px_center, py_center):  # noqa: SIM102
                # Only override if not animating (drawbridges and doors block while animating)
                if not getattr(entity, "is_animating", False):
                    tile_overridden = True
                    break

        # 1. Map tiles
        if not tile_overridden:
            wx, wy = self.game.layout.to_world(px_center, py_center)
            if not self.game.map_manager.is_walkable(int(wx), int(wy)):
                return True

        # 2. Dynamic obstacles (doors, etc.)
        for obj in self.game.obstacles_group:
            if obj == requester:
                continue
            if obj.rect and obj.rect.collidepoint(px_center, py_center):
                return True

        # 3. NPCs
        for npc in self.game.npcs:
            if npc == requester:
                continue
            if npc.rect and npc.rect.collidepoint(px_center, py_center):
                return True

        # 4. Player (only blocks entities other than themselves)
        if self.game.player != requester:
            player_rect = getattr(self.game.player, "rect", None)
            if player_rect and player_rect.collidepoint(px_center, py_center):
                return True

        return False
