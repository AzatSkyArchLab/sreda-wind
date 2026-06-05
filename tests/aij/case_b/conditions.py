"""Assemble the OpenFOAM Case B run configuration, reusing the solver layer.

Produces a solver.RunConfig (NOT a new builder): explicit AIJ tunnel domain,
structured mesh + measured tabulated inlet, std k-epsilon, the generator's
equilibrium seed and the monitor-probe stationarity gate. The domain is the
full-span (no y=0 symmetry) box widened to keep the frontal blockage < 3%.
"""
from __future__ import annotations

from sreda_wind.solver.runner import RunConfig
from sreda_wind.case import Building
from sreda_wind.core import Domain

from . import geometry, reference
from ..case_a.inlet import build_inlet_profile

WIND_DIRECTION_DEG = 270.0     # wind along +x
U_H = 5.133                    # reference velocity at building height (z=200 mm)
Z_REF = geometry.H             # 0.20 m
# Floor roughness DERIVED from the inflow near-wall log fit (z<=50 mm, R^2=0.96);
# poorly constrained because the profile is power-law. Only sets floor shear (the
# inlet imposes the profile directly). See SPEC.md §6.
GROUND_Z0 = 3.1e-6


def case_b_domain():
    """Full-span AIJ Case B tunnel box (no y=0 symmetry; widened to <3% blockage).

    x in [-0.30, 1.00] (-6b..+20b), y in [-1.50, 1.50] (+-30b), z in [0, 1.00]
    (5H = top of the measured inflow). FULL span so the wake is free to shed (a
    symmetry plane would force a false freeze). See SPEC.md §5.
    """
    return Domain(xmin=-0.30, xmax=1.00, ymin=-1.50, ymax=1.50,
                  zmin=0.0, zmax=1.00, streamwise_axis="x")


def frontal_blockage(domain=None):
    """Plate frontal area / domain cross-section [-] (AIJ best practice < 0.03)."""
    if domain is None:
        domain = case_b_domain()
    frontal = geometry.WIDTH_CROSS * geometry.H          # 0.20 x 0.20
    cross = (domain.ymax - domain.ymin) * (domain.zmax - domain.zmin)
    return frontal / cross


def case_b_inflow_profile(data=None):
    """Measured tabulated inlet ((z, u, k, eps), ...); eps = Cmu^0.5 k dU/dz."""
    if data is None:
        data = reference.load_reference()
    return build_inlet_profile(reference.inflow_points(data))


def case_b_config(data=None, model="kEpsilon", iterations=4000, name="caseB"):
    """Return the solver.RunConfig for Case B (reuses the committed runner)."""
    if data is None:
        data = reference.load_reference()
    profile = case_b_inflow_profile(data)
    return RunConfig(
        name=name,
        buildings=[Building(footprint=geometry.footprint(), height=geometry.H)],
        domain=case_b_domain(),
        direction_deg=WIND_DIRECTION_DEG,
        speed=U_H,
        z_ref=Z_REF,
        turbulence_model=model,
        mesh_type="structured",
        inlet_type="measured",
        inlet_profile=profile,
        z0=GROUND_Z0,
        ground_z0=GROUND_Z0,
        side_top_symmetry=True,           # far-field side/top patches
        structured_base_cell=0.01,
        structured_nz=50,
        structured_grading=12.0,
        structured_surface_level=2,
        surface_layers=4,
        ground_layers=0,
        # off-centre +-y probes to detect anti-symmetric shedding (none found)
        monitor_points=((0.10, 0.0, 0.0125),
                        (0.20, 0.05, 0.0125),
                        (0.20, -0.05, 0.0125)),
        iterations=iterations,
        residual_target=1.0e-6,
        coeffs={},                        # standard k-epsilon, no coefficient override
        min_building_area=1.0e-8)
