from typing import List, Dict
import numpy as np

class Node:
    def __init__(self, node_id: int, x: float, y: float):
        self.id = node_id
        self.coords = np.array([x, y], dtype=float)

    @property
    def x(self) -> float:
        return self.coords[0]
        
    @property
    def y(self) -> float:
        return self.coords[1]

class Branch:
    def __init__(self, branch_id: int, start_node: Node, end_node: Node, 
                 thickness: float, generation: int, is_active: bool = True):
        self.id = branch_id
        self.start_node = start_node
        self.end_node = end_node
        self.thickness = thickness
        self.generation = generation
        self.is_active = is_active  # True if it is an active growth tip
        
    def length(self) -> float:
        return np.linalg.norm(self.end_node.coords - self.start_node.coords)
        
    def direction(self) -> np.ndarray:
        vec = self.end_node.coords - self.start_node.coords
        norm = np.linalg.norm(vec)
        if norm < 1e-12:
            return np.array([0.0, 0.0])
        return vec / norm

class BranchGraph:
    """Holds the topological and geometrical graph of the structure."""
    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.branches: Dict[int, Branch] = {}
        self._next_node_id = 0
        self._next_branch_id = 0
        
    def add_node(self, x: float, y: float) -> Node:
        node = Node(self._next_node_id, x, y)
        self.nodes[self._next_node_id] = node
        self._next_node_id += 1
        return node
        
    def add_branch(self, start_node: Node, end_node: Node, thickness: float, generation: int) -> Branch:
        branch = Branch(self._next_branch_id, start_node, end_node, thickness, generation)
        self.branches[self._next_branch_id] = branch
        self._next_branch_id += 1
        return branch
        
    def get_active_branches(self) -> List[Branch]:
        return [b for b in self.branches.values() if b.is_active]
