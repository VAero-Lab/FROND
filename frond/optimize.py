import numpy as np
from typing import Callable, List
from frond.domain import DesignDomain
from frond.parameters import GrowthParameters
from frond.graph import BranchGraph
from frond.forest import ForestGenerator
from frond.growth import GrowthEngine
from frond.interactions import InteractionEngine
from frond.spines import SpineManager
from frond.cleaning import GraphCleaner
from frond.fea import FEASolver

class FrondOptimizer:
    """Wraps the entire FROND pipeline into a clean objective function for optimization."""
    def __init__(self, domain_builder: Callable[[], DesignDomain]):
        self.domain_builder = domain_builder
        
    def evaluate(self, x: List[float], max_volume: float) -> float:
        """
        Evaluates a design vector x.
        x[0]: num_attractors (integer, e.g. 100 to 5000)
        x[1]: radius_of_influence (float)
        x[2]: kill_distance (float)
        x[3]: step_size (float)
        x[4]: murray_exponent (float, e.g. 1.0 to 3.0)
        x[5]: anastomosis_radius (float)
        """
        # 1. Setup Parameters
        params = GrowthParameters(
            num_attractors=int(x[0]),
            radius_of_influence=x[1],
            kill_distance=x[2],
            step_size=x[3],
            murray_exponent=x[4],
            anastomosis_radius=x[5]
        )
        
        domain = self.domain_builder()
        graph = BranchGraph()
        
        # 2. Phase 1: Growth
        seeds = []
        directions = []
        for bound in domain.get_support_boundaries():
            bound_seeds = ForestGenerator.generate_seeds(bound, num_seeds=3, graph=graph)
            seeds.extend(bound_seeds)
            directions.extend([np.array([0.0, -1.0]) for _ in bound_seeds]) # Default direction
            
        engine = GrowthEngine(domain, graph, params)
        engine.grow_forest(seeds, directions)
        
        # Grow until attractors are consumed or max iterations reached
        for _ in range(500):
            if len(engine.attractors) == 0:
                break
            engine.grow_step()
            
        # Apply Murray's Law retroactively
        engine.apply_murrays_law()
            
        # 3. Phase 2: Interactions & Cleaning
        InteractionEngine.resolve_intersections(graph)
        SpineManager.materialize_spines(domain, graph)
        
        cleaner = GraphCleaner(graph, domain)
        cleaner.prune_dangling()
        
        # 4. Phase 3: FEA
        solver = FEASolver(graph, domain, E=2.1e5, elements_per_branch=1)
        compliance, volume = solver.compute_compliance_and_mass()
        
        # 5. Penalize if volume exceeds constraint
        if volume > max_volume:
            penalty = 1e6 * (volume - max_volume)
            return compliance + penalty
            
        return compliance
