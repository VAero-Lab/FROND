import sys, os
sys.path.append("/home/victor-alulema/PhD Program/FROND")

from frond.benchmarks import Benchmarks
from frond.parameters import GrowthParameters
from frond.graph import BranchGraph
from frond.forest import ForestGenerator
from frond.growth import GrowthEngine
import numpy as np
from collections import defaultdict

def main():
    np.random.seed(42)
    domain = Benchmarks.l_bracket()
    graph = BranchGraph()
    
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
    
    for step in range(500):
        if len(engine.attractors) == 0:
            break
        n_tips = len(engine.tip_nodes)
        n_attractors = len(engine.attractors)
        engine.grow_step()
        if step < 20 or step % 50 == 0:
            print(f"Step {step}: tips={n_tips}, attractors={n_attractors}, nodes={len(graph.nodes)}, branches={len(graph.branches)}")
    
    print(f"\nFinal: nodes={len(graph.nodes)}, branches={len(graph.branches)}")
    print(f"Remaining tips: {len(engine.tip_nodes)}")
    print(f"Remaining attractors: {len(engine.attractors)}")
    print(f"Inactive nodes: {len(engine.inactive_nodes)}")

if __name__ == "__main__":
    main()
