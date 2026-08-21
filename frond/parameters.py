from dataclasses import dataclass

@dataclass
class GrowthParameters:
    # Space Colonization Algorithm (SCA) Parameters
    num_attractors: int = 1000
    radius_of_influence: float = 50.0
    kill_distance: float = 5.0
    step_size: float = 2.0
    anastomosis_radius: float = 4.0
    
    # Thickness / Vascular (Murray's Law)
    base_thickness: float = 1.0
    murray_exponent: float = 2.0
    
    # Toggle for Straight vs Curved mode
    # If False, paths are naturally curved via small steps.
    # If True, step size is typically set larger or a post-process simplification is used.
    straight_webs: bool = False
