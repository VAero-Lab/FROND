from frond.domain import DesignDomain, Boundary, BoundaryType

class Benchmarks:
    @staticmethod
    def mbb_beam(L: float = 60.0, H: float = 20.0) -> DesignDomain:
        """
        Half-symmetry MBB beam. 
        Trunks emerge from bottom-right (roller support) and reach top-left (load point).
        """
        domain = DesignDomain([(0,0), (L,0), (L,H), (0,H)])
        domain.add_boundary(Boundary([(L-2, 0), (L, 0)], BoundaryType.SUPPORT, is_solid=True, thickness=1.0))
        domain.add_boundary(Boundary([(0, H-2), (0, H)], BoundaryType.LOAD, is_solid=True, thickness=1.0))
        domain.add_boundary(Boundary([(0,0), (L-2,0)], BoundaryType.GEOMETRIC, is_solid=False))
        domain.add_boundary(Boundary([(L,0), (L,H)], BoundaryType.GEOMETRIC, is_solid=False))
        domain.add_boundary(Boundary([(L,H), (0,H)], BoundaryType.GEOMETRIC, is_solid=False))
        domain.add_boundary(Boundary([(0,H), (0,H-2)], BoundaryType.GEOMETRIC, is_solid=False))
        return domain

    @staticmethod
    def l_bracket(L: float = 100.0, W: float = 40.0) -> DesignDomain:
        """
        Standard L-Bracket benchmark.
        Top edge fixed (Support), Right corner loaded (Load).
        """
        points = [(0, L), (W, L), (W, W), (L, W), (L, 0), (0, 0)]
        domain = DesignDomain(points)
        domain.add_boundary(Boundary([(0, L), (W, L)], BoundaryType.SUPPORT, is_solid=True, thickness=2.0))
        domain.add_boundary(Boundary([(L, 0), (L, int(W/2))], BoundaryType.LOAD, is_solid=True, thickness=2.0))
        
        # Case A: Solid Design Boundaries (Spines)
        domain.add_boundary(Boundary([(W, L), (W, W), (L, W)], BoundaryType.GEOMETRIC, is_solid=True, thickness=1.0))
        domain.add_boundary(Boundary([(L, int(W/2)), (L, 0), (0, 0), (0, L)], BoundaryType.GEOMETRIC, is_solid=True, thickness=1.0))
        return domain

    @staticmethod
    def cantilever(L: float = 100.0, H: float = 50.0) -> DesignDomain:
        """
        Standard Cantilever Beam. Fixed left wall, point load mid-right.
        """
        domain = DesignDomain([(0,0), (L,0), (L,H), (0,H)])
        domain.add_boundary(Boundary([(0, 0), (0, H)], BoundaryType.SUPPORT, is_solid=True, thickness=2.0))
        domain.add_boundary(Boundary([(L, H/2 - 2), (L, H/2 + 2)], BoundaryType.LOAD, is_solid=True, thickness=2.0))
        domain.add_boundary(Boundary([(0,H), (L,H), (L, H/2+2)], BoundaryType.GEOMETRIC, is_solid=True, thickness=1.0))
        domain.add_boundary(Boundary([(0,0), (L,0), (L, H/2-2)], BoundaryType.GEOMETRIC, is_solid=True, thickness=1.0))
        return domain
