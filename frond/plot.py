import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.collections import LineCollection
from frond.domain import DesignDomain, BoundaryType
from frond.graph import BranchGraph
import numpy as np
from typing import List, Tuple

class FrondPlotter:
    @staticmethod
    def plot_domain(ax, domain: DesignDomain):
        # Plot Polygon
        x, y = domain.polygon.exterior.xy
        ax.plot(x, y, color='black', linewidth=2, linestyle='-', zorder=1)
        
        # Plot Boundaries
        for b in domain.boundaries:
            coords = np.array(b.geometry.coords)
            if b.b_type == BoundaryType.SUPPORT:
                ax.plot(coords[:,0], coords[:,1], color='red', linewidth=3, zorder=2)
            elif b.b_type == BoundaryType.LOAD:
                ax.plot(coords[:,0], coords[:,1], color='blue', linewidth=3, zorder=2)
            else:
                # Geometric
                if b.is_solid:
                    ax.plot(coords[:,0], coords[:,1], color='orange', linewidth=2, zorder=2)

    @staticmethod
    def plot_graph(ax, graph: BranchGraph, color='black', alpha=1.0):
        lines = []
        linewidths = []
        for branch in graph.branches.values():
            p1 = branch.start_node.coords
            p2 = branch.end_node.coords
            lines.append([p1, p2])
            # Scale thickness slightly for visual appeal
            linewidths.append(max(0.5, branch.thickness))
            
        lc = LineCollection(lines, linewidths=linewidths, colors=color, alpha=alpha, zorder=3)
        ax.add_collection(lc)

    @staticmethod
    def plot_snapshot(domain: DesignDomain, graph: BranchGraph, title: str = "FROND Structure", filename: str = None):
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_aspect('equal')
        FrondPlotter.plot_domain(ax, domain)
        FrondPlotter.plot_graph(ax, graph)
        ax.set_title(title)
        ax.axis('off')
        plt.tight_layout()
        if filename:
            plt.savefig(filename, dpi=300)
        else:
            plt.show()
        plt.close()

    @staticmethod
    def animate_history(domain: DesignDomain, history: List[Tuple[BranchGraph, float, float]], 
                        filename: str = 'optimization_history.gif'):
        """
        Generates an animation showing the structure evolving alongside the compliance.
        history: List of (BranchGraph, compliance, volume) for each iteration
        """
        fig = plt.figure(figsize=(15, 6))
        gs = fig.add_gridspec(1, 3)
        ax_struct = fig.add_subplot(gs[0, 0:2])
        ax_obj = fig.add_subplot(gs[0, 2])
        
        comp_history = [h[1] for h in history]
        
        def update(frame):
            graph, comp, vol = history[frame]
            
            ax_struct.clear()
            ax_struct.set_aspect('equal')
            ax_struct.axis('off')
            FrondPlotter.plot_domain(ax_struct, domain)
            FrondPlotter.plot_graph(ax_struct, graph)
            ax_struct.set_title(f"Optimization Iteration {frame}\nVolume: {vol:.2f}")
            
            ax_obj.clear()
            ax_obj.plot(range(frame+1), comp_history[:frame+1], color='blue', marker='o', markersize=4)
            ax_obj.set_ylabel('Compliance')
            ax_obj.set_xlabel('Iteration')
            ax_obj.set_title("Objective Evolution")
            ax_obj.grid(True)
            
            # Keep bounds fixed for smoother animation
            ax_obj.set_xlim(0, max(1, len(history)-1))
            
            valid_comps = [c for c in comp_history if c != float('inf')]
            if valid_comps:
                ax_obj.set_ylim(min(valid_comps)*0.9, max(valid_comps)*1.1)
            
        anim = animation.FuncAnimation(fig, update, frames=len(history), interval=300)
        anim.save(filename, writer='pillow')
        plt.close()
