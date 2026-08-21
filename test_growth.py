import sys
import os
sys.path.append(os.path.dirname(__file__))

from frond.benchmarks import Benchmarks
from frond.parameters import GrowthParameters
from frond.graph import BranchGraph
from frond.forest import ForestGenerator
from frond.growth import GrowthEngine
from frond.plot import FrondPlotter
import numpy as np

def main():
    domain = Benchmarks.l_bracket()
    graph = BranchGraph()
    
    # SCA Parameters (Curved/Organic mode by default)
    params = GrowthParameters(
        num_attractors=2000,
        radius_of_influence=60.0,
        kill_distance=3.0,
        step_size=3.0,
        murray_exponent=3.0,
        anastomosis_radius=4.0
    )
    
    seeds = []
    directions = []
    for bound in domain.get_support_boundaries():
        bound_seeds = ForestGenerator.generate_seeds(bound, num_seeds=3, graph=graph)
        seeds.extend(bound_seeds)
        directions.extend([np.array([0.0, -1.0]) for _ in bound_seeds])
        
    engine = GrowthEngine(domain, graph, params)
    engine.grow_forest(seeds, directions)
    
    # Grow until attractors are consumed
    for _ in range(500):
        if len(engine.attractors) == 0:
            break
        engine.grow_step()
        
    # Apply thickness via Murray's law retroactively
    engine.apply_murrays_law()
        
    print("Saving SCA growth plot to test_raw_growth.png ...")
    FrondPlotter.plot_snapshot(domain, graph, title="SCA Growth", filename="test_raw_growth.png")
    
if __name__ == "__main__":
    main()
