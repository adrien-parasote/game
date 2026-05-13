from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from src.map.manager import MapManager

class AnimationMapManager:
    """Handles the resolution of animated map tiles."""

    def __init__(self, map_manager: "MapManager"):
        self.map_manager = map_manager

    def update(self, dt_ms: int):
        """Update any internal animation clocks if necessary.
        Currently relying on absolute pygame time for tile cycles."""
        pass

    def get_current_frame_image(self, tile_id: int) -> pygame.Surface:
        """Resolves the current frame's image for a given animated tile_id based on absolute time."""
        tile_data = self.map_manager.tiles.get(tile_id)
        if not tile_data or not tile_data.frames:
            # Fallback to base image if not animated
            return tile_data.image if tile_data else None

        current_time = pygame.time.get_ticks()
        total_duration = sum(dur for _, dur in tile_data.frames)

        if total_duration <= 0:
            frame_gid = tile_data.frames[0][0]
        else:
            time_in_cycle = current_time % total_duration
            accumulated = 0
            frame_gid = tile_data.frames[0][0]
            for f_gid, dur in tile_data.frames:
                accumulated += dur
                if time_in_cycle < accumulated:
                    frame_gid = f_gid
                    break

        frame_data = self.map_manager.tiles.get(frame_gid)
        if frame_data:
            return frame_data.image

        # Fallback to the base image if frame_gid is missing
        return tile_data.image
