from typing import Set, List
import numpy as np
from frond.graph import BranchGraph
from frond.domain import DesignDomain
from collections import defaultdict
import shapely.geometry as sg

class GraphCleaner:
    """Handles structural pruning to eliminate dead weight."""
    def __init__(self, graph: BranchGraph, domain: DesignDomain):
        self.graph = graph
        self.domain = domain
        
    def prune_dangling(self):
        """
        Recursively trims dangling branches that do not connect to any boundary 
        or form a closed loop.
        """
        pruning = True
        while pruning:
            pruning = False
            
            # 1. Build adjacency mapping: node_id -> set of branch_ids
            adj = defaultdict(set)
            for b_id, b in self.graph.branches.items():
                adj[b.start_node.id].add(b_id)
                adj[b.end_node.id].add(b_id)
                
            # 2. Identify leaf nodes
            leaves = [n_id for n_id, branches in adj.items() if len(branches) == 1]
            
            for leaf_id in leaves:
                node = self.graph.nodes[leaf_id]
                pt = sg.Point(node.coords)
                
                # Check if this leaf node is anchored to ANY boundary
                is_anchored = False
                for lb in self.domain.boundaries:
                    if pt.distance(lb.geometry) < 2.0:
                        is_anchored = True
                        break
                        
                # If it is a leaf and NOT anchored, it is a dangling branch
                if not is_anchored:
                    # Delete the single branch connected to it
                    b_id = next(iter(adj[leaf_id]))
                    del self.graph.branches[b_id]
                    del self.graph.nodes[leaf_id]
                    pruning = True
                    break # Restart loop to rebuild adjacency
                    
        # 3. Clean up any completely disconnected degree-0 nodes
        adj = defaultdict(set)
        for b in self.graph.branches.values():
            adj[b.start_node.id].add(b.id)
            adj[b.end_node.id].add(b.id)
            
        all_node_ids = list(self.graph.nodes.keys())
        for n_id in all_node_ids:
            if len(adj[n_id]) == 0:
                del self.graph.nodes[n_id]
