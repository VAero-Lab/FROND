from typing import List
import numpy as np
from frond.domain import Boundary, BoundaryType
from frond.graph import BranchGraph, Node

class ForestGenerator:
    """Handles seeding trunks on support boundaries."""
    
    @staticmethod
    def generate_seeds(boundary: Boundary, num_seeds: int, graph: BranchGraph) -> List[Node]:
        """
        Distribute num_seeds evenly along the support boundary line.
        """
        if boundary.b_type != BoundaryType.SUPPORT:
            raise ValueError("Seeds can only be generated on SUPPORT boundaries.")
            
        line = boundary.geometry
        length = line.length
        
        seeds = []
        if num_seeds == 1:
            # Place in the middle
            pt = line.interpolate(length / 2.0)
            seeds.append(graph.add_node(pt.x, pt.y))
        else:
            # Distribute evenly
            distances = np.linspace(0, length, num_seeds)
            for d in distances:
                pt = line.interpolate(d)
                seeds.append(graph.add_node(pt.x, pt.y))
                
        return seeds
