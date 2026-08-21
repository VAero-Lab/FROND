from frond.graph import BranchGraph
from frond.domain import DesignDomain
import shapely.geometry as sg

class SpineManager:
    """Handles the materialization of solid boundaries (Spines) into the graph."""
    
    @staticmethod
    def materialize_spines(domain: DesignDomain, graph: BranchGraph):
        """
        Converts boundaries with is_solid=True into actual graph edges.
        Must be run BEFORE GraphCleaner.prune_dangling() so unused parts are pruned.
        """
        for boundary in domain.boundaries:
            if boundary.is_solid:
                coords = list(boundary.geometry.coords)
                
                spine_nodes = []
                for x, y in coords:
                    pt = sg.Point(x, y)
                    existing_node = None
                    for n in graph.nodes.values():
                        if sg.Point(n.coords).distance(pt) < 1e-6:
                            existing_node = n
                            break
                            
                    if existing_node:
                        spine_nodes.append(existing_node)
                    else:
                        spine_nodes.append(graph.add_node(x, y))
                
                for i in range(len(spine_nodes) - 1):
                    n1 = spine_nodes[i]
                    n2 = spine_nodes[i+1]
                    graph.add_branch(n1, n2, thickness=boundary.thickness, generation=-1)
