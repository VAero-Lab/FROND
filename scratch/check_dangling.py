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
import shapely.geometry as sg
import numpy as np
from collections import defaultdict

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
    
    SpineManager.materialize_spines(domain, graph)
    
    cleaner = GraphCleaner(graph, domain)
    cleaner.prune_dangling()
    
    # Check degree of all nodes
    adj = defaultdict(set)
    for b in graph.branches.values():
        adj[b.start_node.id].add(b.id)
        adj[b.end_node.id].add(b.id)
        
    dangling_count = 0
    for n_id, node in graph.nodes.items():
        deg = len(adj[n_id])
        if deg == 1:
            pt = sg.Point(node.coords)
            is_anchored = False
            for lb in domain.boundaries:
                if pt.distance(lb.geometry) < 1e-2:
                    is_anchored = True
                    break
            if not is_anchored:
                print(f"Dangling leaf node {n_id} at {node.coords} (degree 1, not anchored!)")
                dangling_count += 1
        elif deg == 0:
            print(f"Isolated node {n_id} at {node.coords} (degree 0!)")
            dangling_count += 1
            
    print(f"Total dangling/isolated nodes remaining: {dangling_count}")

if __name__ == "__main__":
    main()
