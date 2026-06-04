"""Pure-physics core: ABL inflow, wind vectors, domain sizing, adaptive mesh.

This subpackage has no I/O and no OpenFOAM dependency. Everything here is a
plain function or dataclass and is exercised by unit tests without a solver.
"""
from .abl import ABLParameters, abl_parameters, friction_velocity, velocity_at, dissipation_at
from .wind import flow_vector, inflow_velocity
from .box import BBox, Domain
# core/domain.py is PARKED (COST 732 generic sizing, not in the build path); its
# symbols stay importable for its own unit tests.
from .domain import DomainFactors, compute_domain
from .mesh import RefinementBox, MeshSpec, compute_mesh_spec

__all__ = [
    "ABLParameters", "abl_parameters", "friction_velocity", "velocity_at", "dissipation_at",
    "flow_vector", "inflow_velocity",
    "BBox", "Domain", "DomainFactors", "compute_domain",
    "RefinementBox", "MeshSpec", "compute_mesh_spec",
]
