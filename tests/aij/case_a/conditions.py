"""Assemble the OpenFOAM case configuration for AIJ Case A.

Turns the reference data + a turbulence-model choice into the inputs for
case.generate_case: the building, the wind, the explicit wind-tunnel domain, a
CaseSettings tuned to the AIJ sensitivity study (Section 3), and the tabulated
inflow profile. The STRICT conditions (measured inflow, rough floor z0,
2nd-order advection, tight convergence) are honoured; the FLEXIBLE ones use
practical choices (symmetry sides/top). The domain is the Meng & Hibi tunnel
geometry, supplied explicitly -- there is no generic COST 732 sizing here.
"""
from __future__ import annotations

from sreda_wind.case import Building, CaseSettings
from sreda_wind.core import Domain

from . import geometry, inlet, reference

# Case A conditions (Section 2-4 of SPEC.md).
B = geometry.B                 # 0.08 m
H = geometry.H                 # 0.16 m
GROUND_Z0 = 1.8e-4             # rough-wall log-law roughness length [m]
WIND_DIRECTION_DEG = 270.0     # wind along +x


def case_a_domain():
    """Meng & Hibi wind-tunnel domain for Case A (the canonical 100x80x50 box).

    x in [-0.4, 0.6], y in [-0.4, 0.4], z in [0, 0.8] m -> with a 0.01 m base
    cell and nz=50 this is exactly the validated 100x80x50 blockMesh. The domain
    is a property OF THE CASE (Case B/C/D each carry their own tunnel geometry),
    not a generic formula.
    """
    return Domain(xmin=-0.4, xmax=0.6, ymin=-0.4, ymax=0.4,
                  zmin=0.0, zmax=0.8, streamwise_axis="x")


def case_a_settings(model="kEpsilon", iterations=2000):
    """CaseSettings for Case A. Step 1: model="kEpsilon"; step 2: "realizableKE"."""
    return CaseSettings(
        turbulence_model=model,
        iterations=iterations,
        residual_control=1e-6,            # STRICT: tight convergence (eq 2.1.7)
        side_top_symmetry=True,           # FLEXIBLE: confinement ~ tunnel walls
        ground_z0=GROUND_Z0,              # STRICT: rough floor
        surface_layers=3,                 # prism layers at the building walls
        target_facade_cell=B / 14.0,      # grid-converged facade cell (2.1.5.2)
        min_base_cell=B / 16.0,           # model-scale background-cell floor
        min_building_area=1e-6,           # model-scale footprints are sub-m2
        vertical_grading=1.0,
        cell_budget=3_000_000,
        sample_height=0.125 * B,          # pedestrian plane z/b = 0.125
    )


def _reference_speed(profile, z_ref):
    """Pick the inflow speed nearest z_ref to seed the internal field."""
    best_u = profile[0][1]
    best_dz = abs(profile[0][0] - z_ref)
    i = 1
    while i < len(profile):
        dz = abs(profile[i][0] - z_ref)
        if dz < best_dz:
            best_dz = dz
            best_u = profile[i][1]
        i += 1
    return best_u


def case_a_inputs(data=None, model="kEpsilon", iterations=2000):
    """Return the kwargs for case.generate_case for Case A.

    data: parsed reference dict (loaded if None).
    """
    if data is None:
        data = reference.load_reference()

    profile = inlet.build_inlet_profile(reference.inflow_points(data))
    settings = case_a_settings(model=model, iterations=iterations)
    settings.z_ref = H
    speed = _reference_speed(profile, H)

    return {
        "buildings": [Building(footprint=geometry.footprint(B), height=H)],
        "direction_deg": WIND_DIRECTION_DEG,
        "speed": speed,
        "domain": case_a_domain(),
        "settings": settings,
        "inlet_profile": profile,
    }
