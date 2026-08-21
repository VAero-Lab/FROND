import numpy as np
from typing import List
import shapely.geometry as sg
import shapely.ops
from scipy.spatial import cKDTree
from collections import defaultdict

from frond.graph import BranchGraph, Node, Branch
from frond.domain import DesignDomain
from frond.parameters import GrowthParameters

class GrowthEngine:
    def __init__(self, domain: DesignDomain, graph: BranchGraph, params: GrowthParameters):
        self.domain = domain
        self.graph = graph
        self.params = params
        self.attractors = np.array([])
        self.attractor_is_load = np.array([], dtype=bool)
        self.inactive_nodes = set()   # nodes that can no longer grow or pull attractors
        self.tip_nodes = set()        # current active growth tips
        
    def _generate_attractors(self):
        """Seeds attractors in the domain and densely along all boundaries."""
        attractors_list = []
        is_load_list = []
        minx, miny, maxx, maxy = self.domain.polygon.bounds
        points_needed = self.params.num_attractors
        
        # 70% in domain, 30% strongly clustered on boundaries
        domain_pts = int(points_needed * 0.7)
        boundary_pts = points_needed - domain_pts
        
        # Domain points
        pts_found = 0
        while pts_found < domain_pts:
            x = np.random.uniform(minx, maxx)
            y = np.random.uniform(miny, maxy)
            pt = sg.Point(x, y)
            if self.domain.polygon.contains(pt):
                attractors_list.append(np.array([x, y]))
                is_load_list.append(False)
                pts_found += 1
                
        # Boundary points (act as snapping targets)
        all_boundaries = self.domain.boundaries
        if all_boundaries and boundary_pts > 0:
            pts_per_boundary = boundary_pts // len(all_boundaries)
            for lb in all_boundaries:
                length = lb.geometry.length
                distances = np.random.uniform(0, length, pts_per_boundary)
                for d in distances:
                    pt = lb.geometry.interpolate(d)
                    attractors_list.append(np.array([pt.x, pt.y]))
                    is_load_list.append(True)
                    
        self.attractors = np.array(attractors_list)
        self.attractor_is_load = np.array(is_load_list, dtype=bool)

    def _is_on_boundary(self, coords, tol=1e-3):
        """Check if a coordinate is on any boundary."""
        pt = sg.Point(coords)
        for lb in self.domain.boundaries:
            if pt.distance(lb.geometry) < tol:
                return True
        return False

    def _snap_to_nearest_boundary(self, coords):
        """Find the nearest point on any boundary and return the snapped coords."""
        pt = sg.Point(coords)
        min_dist = float('inf')
        best_snap = None
        for lb in self.domain.boundaries:
            _, p2 = shapely.ops.nearest_points(pt, lb.geometry)
            d = pt.distance(lb.geometry)
            if d < min_dist:
                min_dist = d
                best_snap = np.array([p2.x, p2.y])
        return best_snap, min_dist

    def grow_forest(self, seeds: List[Node], initial_directions: List[np.ndarray]):
        """Initialize the first generation from seeds."""
        self._generate_attractors()
        self.inactive_nodes = set()
        self.tip_nodes = set()
        
        for seed, direction in zip(seeds, initial_directions):
            norm = np.linalg.norm(direction)
            if norm > 1e-12:
                direction = direction / norm
            
            new_coords = seed.coords + direction * self.params.step_size
            
            pt = sg.Point(new_coords)
            if self.domain.polygon.buffer(1e-4).contains(pt):
                new_node = self.graph.add_node(new_coords[0], new_coords[1])
                self.graph.add_branch(seed, new_node, self.params.base_thickness, 0)
                self.tip_nodes.add(new_node.id)
                
        # Deactivate seed nodes — they sit on the support boundary and don't grow
        for seed in seeds:
            self.inactive_nodes.add(seed.id)

    def grow_step(self):
        """
        Executes one step of the Space Colonization Algorithm.
        
        Key invariant: only tip_nodes grow. When a tip grows, the tip itself 
        becomes an interior node, and the NEW node becomes the tip. This prevents 
        the hub-and-spoke pattern where a single node spawns hundreds of branches.
        """
        if len(self.attractors) == 0 or not self.tip_nodes:
            return
            
        node_ids = list(self.graph.nodes.keys())
        all_node_coords = np.array([self.graph.nodes[nid].coords for nid in node_ids])
        
        # Only tips can grow
        tip_ids = list(self.tip_nodes)
        tip_coords = np.array([self.graph.nodes[nid].coords for nid in tip_ids])
        
        # Build spatial trees
        all_tree = cKDTree(all_node_coords)
        tip_tree = cKDTree(tip_coords)
        
        # ─── Phase 1: Kill attractors near ANY node (active or inactive) ───
        distances_to_all, indices_to_all = all_tree.query(self.attractors, k=1)
        distances_to_all = np.atleast_1d(distances_to_all)
        indices_to_all = np.atleast_1d(indices_to_all)
        
        attractors_to_delete = set()
        nodes_to_snap = {}  # tip_id -> snap coords
        
        for i, (dist, idx) in enumerate(zip(distances_to_all, indices_to_all)):
            if dist < self.params.kill_distance:
                attractors_to_delete.add(i)
                # If boundary attractor is killed near an active tip, trigger snap
                if self.attractor_is_load[i]:
                    closest_node_id = node_ids[idx]
                    if closest_node_id in self.tip_nodes:
                        snap_coords, _ = self._snap_to_nearest_boundary(all_node_coords[idx])
                        if snap_coords is not None:
                            nodes_to_snap[closest_node_id] = snap_coords
        
        # ─── Phase 2: Remaining attractors pull only tips ───
        remaining_mask = np.array([i not in attractors_to_delete for i in range(len(self.attractors))])
        node_dirs = defaultdict(list)
        
        if remaining_mask.any():
            remaining_attractors = self.attractors[remaining_mask]
            
            distances_tip, indices_tip = tip_tree.query(remaining_attractors, k=1)
            distances_tip = np.atleast_1d(distances_tip)
            indices_tip = np.atleast_1d(indices_tip)
            
            for i, (dist, idx) in enumerate(zip(distances_tip, indices_tip)):
                if dist <= self.params.radius_of_influence:
                    tip_id = tip_ids[idx]
                    vec = remaining_attractors[i] - tip_coords[idx]
                    norm = np.linalg.norm(vec)
                    if norm > 1e-12:
                        vec = vec / norm
                    node_dirs[tip_id].append(vec)
        
        # ─── Phase 3: Delete consumed attractors ───
        if attractors_to_delete:
            keep_mask = np.array([i not in attractors_to_delete for i in range(len(self.attractors))])
            self.attractors = self.attractors[keep_mask]
            self.attractor_is_load = self.attractor_is_load[keep_mask]
        
        # ─── Phase 4: Grow, Snap, or Anastomose ───
        existing_connections = set()
        for b in self.graph.branches.values():
            existing_connections.add(frozenset([b.start_node.id, b.end_node.id]))
        
        new_tips = set()
        tips_to_retire = set()
        
        processed_nodes = set(node_dirs.keys()) | set(nodes_to_snap.keys())
        for tip_id in processed_nodes:
            parent_node = self.graph.nodes[tip_id]
            
            # (A) Boundary Snapping — tip reached a boundary, snap and deactivate
            if tip_id in nodes_to_snap:
                snap_coords = nodes_to_snap[tip_id]
                new_node = self.graph.add_node(snap_coords[0], snap_coords[1])
                self.graph.add_branch(parent_node, new_node, self.params.base_thickness, 0)
                self.inactive_nodes.add(new_node.id)
                tips_to_retire.add(tip_id)
                continue
            
            # (B) Normal growth
            vecs = node_dirs[tip_id]
            if not vecs:
                continue
                
            avg_vec = np.sum(vecs, axis=0)
            norm = np.linalg.norm(avg_vec)
            if norm > 1e-12:
                avg_vec = avg_vec / norm
                
            new_coords = parent_node.coords + avg_vec * self.params.step_size
            
            pt = sg.Point(new_coords)
            if not self.domain.polygon.buffer(1e-4).contains(pt):
                continue
            
            # (C) Anastomosis check — try to fuse to an existing nearby node
            dists_to_existing, idxs_existing = all_tree.query(new_coords, k=10)
            dists_to_existing = np.atleast_1d(dists_to_existing)
            idxs_existing = np.atleast_1d(idxs_existing)
            
            fused = False
            for d_ext, i_ext in zip(dists_to_existing, idxs_existing):
                if d_ext > self.params.anastomosis_radius:
                    break
                    
                existing_node_id = node_ids[i_ext]
                
                # Don't fuse to self
                if existing_node_id == parent_node.id:
                    continue
                    
                conn = frozenset([parent_node.id, existing_node_id])
                if conn not in existing_connections:
                    existing_node = self.graph.nodes[existing_node_id]
                    self.graph.add_branch(parent_node, existing_node, self.params.base_thickness, 0)
                    existing_connections.add(conn)
                    fused = True
                    # Tip stays active — it formed a loop but can still branch
                    break
                    
            if not fused:
                new_node = self.graph.add_node(new_coords[0], new_coords[1])
                self.graph.add_branch(parent_node, new_node, self.params.base_thickness, 0)
                
                # Check if the new node landed on a boundary
                if self._is_on_boundary(new_coords):
                    self.inactive_nodes.add(new_node.id)
                    tips_to_retire.add(tip_id)
                else:
                    # The new node becomes a tip. The old tip also stays a tip
                    # (it may branch again next step from attractors in other directions).
                    new_tips.add(new_node.id)
        
        # Update tip set: retire old tips, add new tips.
        # Tips that had no attractors pulling them this step are retired.
        idle_tips = self.tip_nodes - processed_nodes - tips_to_retire
        self.tip_nodes -= tips_to_retire
        self.tip_nodes -= idle_tips
        self.tip_nodes |= new_tips
                
    def apply_murrays_law(self):
        """Retroactively calculates branch thickness from tips back to roots using Murray's Law, conserving flow in loops."""
        alpha = self.params.murray_exponent
        base_flow = self.params.base_thickness ** alpha
        
        # Build adjacency
        children_branches = defaultdict(list)
        parent_branches = defaultdict(list)
        for b in self.graph.branches.values():
            children_branches[b.start_node.id].append(b)
            parent_branches[b.end_node.id].append(b)
            
        memo_node_flow = {}
        visited = set()
        
        def get_node_flow(node_id):
            if node_id in memo_node_flow:
                return memo_node_flow[node_id]
                
            if node_id in visited:
                return base_flow
                
            visited.add(node_id)
            
            child_brs = children_branches[node_id]
            if not child_brs:
                flow = base_flow
            else:
                flow = 0.0
                for cb in child_brs:
                    end_node_id = cb.end_node.id
                    end_node_flow = get_node_flow(end_node_id)
                    num_parents = len(parent_branches[end_node_id])
                    cb_flow = end_node_flow / max(1, num_parents)
                    flow += cb_flow
                    
            memo_node_flow[node_id] = flow
            visited.remove(node_id)
            return flow
            
        # Set thickness of all branches
        for b in self.graph.branches.values():
            end_node_id = b.end_node.id
            end_node_flow = get_node_flow(end_node_id)
            num_parents = len(parent_branches[end_node_id])
            b_flow = end_node_flow / max(1, num_parents)
            b.thickness = max(self.params.base_thickness, b_flow ** (1.0 / alpha))
