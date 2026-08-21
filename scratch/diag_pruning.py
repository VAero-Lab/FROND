import sys, os, copy
sys.path.append("/home/victor-alulema/PhD Program/FROND")

from frond.benchmarks import Benchmarks
from frond.parameters import GrowthParameters
from frond.graph import BranchGraph
from frond.forest import ForestGenerator
from frond.growth import GrowthEngine
from frond.spines import SpineManager
from frond.cleaning import GraphCleaner
from frond.plot import FrondPlotter
import numpy as np
import shapely.geometry as sg
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
    
    for _ in range(500):
        if len(engine.attractors) == 0:
            break
        engine.grow_step()
        
    engine.apply_murrays_law()
    SpineManager.materialize_spines(domain, graph)
    
    n_nodes_before = len(graph.nodes)
    n_branches_before = len(graph.branches)
    
    # Examine leaf nodes BEFORE pruning
    adj = defaultdict(set)
    for b_id, b in graph.branches.items():
        adj[b.start_node.id].add(b_id)
        adj[b.end_node.id].add(b_id)
    
    leaves = [n_id for n_id, branches in adj.items() if len(branches) == 1]
    anchored_leaves = 0
    unanchored_leaves = 0
    for leaf_id in leaves:
        node = graph.nodes[leaf_id]
        pt = sg.Point(node.coords)
        is_anchored = False
        for lb in domain.boundaries:
            d = pt.distance(lb.geometry)
            if d < 1e-2:
                is_anchored = True
                break
        if is_anchored:
            anchored_leaves += 1
        else:
            unanchored_leaves += 1
    
    print(f"=== BEFORE PRUNING ===")
    print(f"Nodes: {n_nodes_before}, Branches: {n_branches_before}")
    print(f"Total leaf nodes (degree 1): {len(leaves)}")
    print(f"  Anchored to boundary (distance < 1e-2): {anchored_leaves}")
    print(f"  Unanchored (will be pruned): {unanchored_leaves}")
    
    # Now check distances of unanchored leaves to boundaries
    for leaf_id in leaves:
        node = graph.nodes[leaf_id]
        pt = sg.Point(node.coords)
        min_dist = float('inf')
        for lb in domain.boundaries:
            d = pt.distance(lb.geometry)
            if d < min_dist:
                min_dist = d
        if min_dist >= 1e-2 and min_dist < 5.0:
            print(f"  Near-miss leaf node {leaf_id} at {node.coords}, min distance to boundary: {min_dist:.4f}")
    
    # Run pruning
    cleaner = GraphCleaner(graph, domain)
    cleaner.prune_dangling()
    
    n_nodes_after = len(graph.nodes)
    n_branches_after = len(graph.branches)
    
    print(f"\n=== AFTER PRUNING ===")
    print(f"Nodes: {n_nodes_after}, Branches: {n_branches_after}")
    print(f"Nodes removed: {n_nodes_before - n_nodes_after}")
    print(f"Branches removed: {n_branches_before - n_branches_after}")
    print(f"Fraction of nodes remaining: {n_nodes_after / n_nodes_before:.2%}")
    print(f"Fraction of branches remaining: {n_branches_after / n_branches_before:.2%}")

if __name__ == "__main__":
    main()
