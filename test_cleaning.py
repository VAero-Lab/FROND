import sys
import os
sys.path.append(os.path.dirname(__file__))

from frond.benchmarks import Benchmarks
from frond.parameters import GrowthParameters
from frond.graph import BranchGraph
from frond.forest import ForestGenerator
from frond.growth import GrowthEngine
from frond.interactions import InteractionEngine
from frond.spines import SpineManager
from frond.cleaning import GraphCleaner
from frond.plot import FrondPlotter
import numpy as np

def main():
    domain = Benchmarks.l_bracket()
    graph = BranchGraph()
    
    # Large step size to create straight webs (structural truss look)
    params = GrowthParameters(
        num_attractors=1000,
        radius_of_influence=80.0,
        kill_distance=5.0,
        step_size=8.0,
        murray_exponent=2.0,
        anastomosis_radius=10.0
    )
    
    seeds = []
    directions = []
    for bound in domain.get_support_boundaries():
        bound_seeds = ForestGenerator.generate_seeds(bound, num_seeds=3, graph=graph)
        seeds.extend(bound_seeds)
        directions.extend([np.array([0.0, -1.0]) for _ in bound_seeds])
        
    engine = GrowthEngine(domain, graph, params)
    engine.grow_forest(seeds, directions)
    
    for _ in range(500):
        if len(engine.attractors) == 0:
            break
        engine.grow_step()
        
    engine.apply_murrays_law()
        
    print("Applying interactions and pruning...")
    InteractionEngine.resolve_intersections(graph)
    SpineManager.materialize_spines(domain, graph)
    
    cleaner = GraphCleaner(graph, domain)
    cleaner.prune_dangling()
    
    print("Saving pruned structure plot to test_pruned.png ...")
    FrondPlotter.plot_snapshot(domain, graph, title="Pruned SCA Structure (Straight Webs)", filename="test_pruned.png")
    
if __name__ == "__main__":
    main()
