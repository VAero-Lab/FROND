from enum import Enum, auto
from typing import List, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, LineString, Point

class BoundaryType(Enum):
    SUPPORT = auto()
    LOAD = auto()
    GEOMETRIC = auto()

class Boundary:
    """Base class representing a boundary in the design domain."""
    def __init__(self, coordinates: List[Tuple[float, float]], b_type: BoundaryType, is_solid: bool = False, thickness: float = 0.0):
        """
        Args:
            coordinates: List of (x, y) defining the boundary line/polygon segment.
            b_type: The type of boundary (SUPPORT, LOAD, GEOMETRIC).
            is_solid: If True, this boundary acts as a 'spine' and material is optimized.
            thickness: Initial thickness of the solid web/spine.
        """
        self.coordinates = coordinates
        self.b_type = b_type
        self.is_solid = is_solid
        self.thickness = thickness
        self.geometry = LineString(coordinates)

class DesignDomain:
    """Represents the 2D spatial domain where the structure grows."""
    def __init__(self, boundary_points: List[Tuple[float, float]]):
        """
        Args:
            boundary_points: List of (x, y) defining the closed outer polygon.
        """
        self.polygon = Polygon(boundary_points)
        self.boundaries: List[Boundary] = []

    def add_boundary(self, boundary: Boundary):
        self.boundaries.append(boundary)

    def is_inside(self, point: Tuple[float, float]) -> bool:
        """Check if a point is strictly inside or on the boundary of the domain."""
        return self.polygon.contains(Point(point)) or self.polygon.touches(Point(point))

    def get_load_boundaries(self) -> List[Boundary]:
        return [b for b in self.boundaries if b.b_type == BoundaryType.LOAD]

    def get_support_boundaries(self) -> List[Boundary]:
        return [b for b in self.boundaries if b.b_type == BoundaryType.SUPPORT]
