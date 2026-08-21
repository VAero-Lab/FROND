import sys
import os
sys.path.append("/home/victor-alulema/PhD Program/FROND")

from frond.benchmarks import Benchmarks
from frond.parameters import GrowthParameters
from frond.graph import BranchGraph
from frond.forest import ForestGenerator
from frond.growth import GrowthEngine
from frond.interactions import InteractionEngine
from frond.spines import SpineManager
from frond.cleaning import GraphCleaner
import numpy as np

def main():
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
    
    for _ in range(500):
        if len(engine.attractors) == 0:
            break
        engine.grow_step()
        
    engine.apply_murrays_law()
    
    print("Before materialize_spines:")
    thicknesses = [b.thickness for b in graph.branches.values()]
    print(f"Max thickness: {max(thicknesses)}, Mean thickness: {np.mean(thicknesses)}, Min thickness: {min(thicknesses)}")
    
    SpineManager.materialize_spines(domain, graph)
    
    cleaner = GraphCleaner(graph, domain)
    cleaner.prune_dangling()
    
    print("After prune_dangling:")
    thicknesses = [b.thickness for b in graph.branches.values()]
    print(f"Max thickness: {max(thicknesses)}, Mean thickness: {np.mean(thicknesses)}, Min thickness: {min(thicknesses)}")
    
    # Print the branches with very large thickness
    for b_id, b in graph.branches.items():
        if b.thickness > 50:
            print(f"Branch {b_id}: {b.start_node.coords} -> {b.end_node.coords}, thickness={b.thickness}")

if __name__ == "__main__":
    main()
