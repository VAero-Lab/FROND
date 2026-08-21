import numpy as np
from numba import njit
import scipy.sparse as sps
import scipy.sparse.linalg as spla
from frond.graph import BranchGraph
from frond.domain import DesignDomain
import shapely.geometry as sg

@njit
def element_stiffness_matrix(E: float, A: float, I: float, L: float, c: float, s: float):
    """Computes the 6x6 local stiffness matrix for a 2D frame element and transforms it to global."""
    k_local = np.zeros((6, 6))
    L2 = L * L
    L3 = L2 * L
    
    k_a = E * A / L
    k_local[0, 0] = k_a; k_local[0, 3] = -k_a
    k_local[3, 0] = -k_a; k_local[3, 3] = k_a
    
    k_12 = 12 * E * I / L3
    k_6 = 6 * E * I / L2
    k_4 = 4 * E * I / L
    k_2 = 2 * E * I / L
    
    k_local[1, 1] = k_12; k_local[1, 2] = k_6; k_local[1, 4] = -k_12; k_local[1, 5] = k_6
    k_local[2, 1] = k_6; k_local[2, 2] = k_4; k_local[2, 4] = -k_6; k_local[2, 5] = k_2
    k_local[4, 1] = -k_12; k_local[4, 2] = -k_6; k_local[4, 4] = k_12; k_local[4, 5] = -k_6
    k_local[5, 1] = k_6; k_local[5, 2] = k_2; k_local[5, 4] = -k_6; k_local[5, 5] = k_4
    
    T = np.zeros((6, 6))
    T[0, 0] = c; T[0, 1] = s; T[1, 0] = -s; T[1, 1] = c; T[2, 2] = 1.0
    T[3, 3] = c; T[3, 4] = s; T[4, 3] = -s; T[4, 4] = c; T[5, 5] = 1.0
    
    return T.T @ k_local @ T

class FEAMesh:
    """Internal 2D FEA mesh representation independent of the generative graph."""
    def __init__(self):
        self.nodes = [] # List of np.array([x, y])
        self.elements = [] # List of (n1_idx, n2_idx, thickness, length, c, s)
        self.node_id_map = {} # Maps BranchGraph node.id -> FEAMesh node index

class FEASolver:
    def __init__(self, graph: BranchGraph, domain: DesignDomain, E: float = 1.0, elements_per_branch: int = 1):
        self.graph = graph
        self.domain = domain
        self.E = E
        self.elements_per_branch = elements_per_branch
        self.mesh = FEAMesh()
        self._build_mesh()
        
    def _build_mesh(self):
        for node in self.graph.nodes.values():
            idx = len(self.mesh.nodes)
            self.mesh.nodes.append(node.coords)
            self.mesh.node_id_map[node.id] = idx
            
        for branch in self.graph.branches.values():
            n1_idx = self.mesh.node_id_map[branch.start_node.id]
            n2_idx = self.mesh.node_id_map[branch.end_node.id]
            
            p1 = self.mesh.nodes[n1_idx]
            p2 = self.mesh.nodes[n2_idx]
            
            vec = p2 - p1
            total_L = np.linalg.norm(vec)
            if total_L < 1e-12:
                continue
                
            c = vec[0] / total_L
            s = vec[1] / total_L
            elem_L = total_L / self.elements_per_branch
            thickness = branch.thickness
            
            curr_idx = n1_idx
            for i in range(1, self.elements_per_branch):
                inter_pt = p1 + (i / self.elements_per_branch) * vec
                new_idx = len(self.mesh.nodes)
                self.mesh.nodes.append(inter_pt)
                
                self.mesh.elements.append((curr_idx, new_idx, thickness, elem_L, c, s))
                curr_idx = new_idx
                
            self.mesh.elements.append((curr_idx, n2_idx, thickness, elem_L, c, s))
            
    def compute_compliance_and_mass(self, load_vector: np.ndarray = None) -> tuple[float, float]:
        """
        Solves the system and returns (Compliance, Volume).
        Assumes rectangular cross section: Area = thickness, I = thickness^3 / 12 (depth = 1.0).
        """
        N_nodes = len(self.mesh.nodes)
        N_dof = 3 * N_nodes
        
        I_idx, J_idx, V_val = [], [], []
        volume = 0.0
        
        for n1, n2, t, L, c, s in self.mesh.elements:
            A = t
            I_mom = (t**3) / 12.0
            volume += A * L
            
            k_glob = element_stiffness_matrix(self.E, A, I_mom, L, c, s)
            dof_map = [3*n1, 3*n1+1, 3*n1+2, 3*n2, 3*n2+1, 3*n2+2]
            
            for i in range(6):
                for j in range(6):
                    I_idx.append(dof_map[i])
                    J_idx.append(dof_map[j])
                    V_val.append(k_glob[i, j])
                    
        K = sps.coo_matrix((V_val, (I_idx, J_idx)), shape=(N_dof, N_dof)).tocsr()
        
        fixed_dofs = []
        support_boundaries = self.domain.get_support_boundaries()
        
        for n_id, idx in self.mesh.node_id_map.items():
            pt = sg.Point(self.mesh.nodes[idx])
            is_support = any(pt.distance(sb.geometry) < 1e-6 for sb in support_boundaries)
            if is_support:
                fixed_dofs.extend([3*idx, 3*idx+1, 3*idx+2]) # Fully fixed (clamp)
                
        free_dofs = np.setdiff1d(np.arange(N_dof), fixed_dofs)
        if len(free_dofs) == 0:
            return 0.0, volume
            
        F = np.zeros(N_dof)
        
        if load_vector is None:
            load_boundaries = self.domain.get_load_boundaries()
            load_nodes = []
            for n_id, idx in self.mesh.node_id_map.items():
                pt = sg.Point(self.mesh.nodes[idx])
                if any(pt.distance(lb.geometry) < 1e-6 for lb in load_boundaries):
                    load_nodes.append(idx)
            
            if load_nodes:
                f_per_node = -1.0 / len(load_nodes) # Distribute 1N downward load
                for idx in load_nodes:
                    F[3*idx + 1] = f_per_node
        else:
            F = load_vector
            
        F_free = F[free_dofs]
        K_free = K[free_dofs, :][:, free_dofs]
        
        try:
            U_free = spla.spsolve(K_free, F_free)
        except Exception:
            return float('inf'), volume # Ill-conditioned/Mechanism
            
        U = np.zeros(N_dof)
        U[free_dofs] = U_free
        
        compliance = float(np.dot(F, U))
        return compliance, volume
