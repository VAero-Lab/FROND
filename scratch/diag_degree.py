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
    
    anastomosis_count = 0
    snap_count = 0
    new_node_count = 0
    
    for step in range(500):
        if len(engine.attractors) == 0:
            break
        n_before = len(graph.nodes)
        b_before = len(graph.branches)
        engine.grow_step()
        n_after = len(graph.nodes)
        b_after = len(graph.branches)
        
        new_branches = b_after - b_before
        new_nodes = n_after - n_before
        
        # If a branch was created but no node: anastomosis (reused existing node)
        # If a branch was created and a new node was created: normal growth or snap
        if new_branches > 0 and new_nodes < new_branches:
            anastomosis_count += (new_branches - new_nodes)
            
    # Analyze the final graph
    adj = defaultdict(set)
    for b_id, b in graph.branches.items():
        adj[b.start_node.id].add(b_id)
        adj[b.end_node.id].add(b_id)
    
    degree_hist = defaultdict(int)
    for n_id in graph.nodes:
        degree_hist[len(adj[n_id])] += 1
    
    print(f"Total nodes: {len(graph.nodes)}, Total branches: {len(graph.branches)}")
    print(f"Approximate anastomosis fusions: {anastomosis_count}")
    print(f"\nDegree distribution:")
    for deg in sorted(degree_hist.keys()):
        print(f"  Degree {deg}: {degree_hist[deg]} nodes ({degree_hist[deg]/len(graph.nodes)*100:.1f}%)")

if __name__ == "__main__":
    main()
