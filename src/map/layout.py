from abc import ABC, abstractmethod
from typing import Tuple
from src.config import Settings

class LayoutStrategy(ABC):
    """Abstract base class for map layout coordinate transformations."""
    
    @abstractmethod
    def to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world/tile coordinates to screen pixel coordinates."""
        pass

    def to_world(self, px: float, py: float) -> Tuple[float, float]:
        """Convert screen pixel coordinates to world/tile coordinates."""
        raise NotImplementedError("to_world must be implemented by subclass")

class OrthogonalLayout(LayoutStrategy):
    """Standard top-down or side-view orthogonal layout."""
    
    def __init__(self, tile_size: int = Settings.TILE_SIZE):
        self.tile_size = tile_size

    def to_screen(self, x: float, y: float) -> Tuple[float, float]:
        return x * self.tile_size, y * self.tile_size

    def to_world(self, px: float, py: float) -> Tuple[float, float]:
        return px / self.tile_size, py / self.tile_size

# IsometricLayout is deferred per user request.
# The interface LayoutStrategy is preserved for future implementation.
