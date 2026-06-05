"""File-level tests for the AIJ Case B harness (no OpenFOAM run).

Mirrors the Case A harness checks: the reference loads with the right counts and
a self-consistent reference velocity, the geometry has the resolved broadside
orientation, the domain/blockage match the spec, and the generated OpenFOAM
dicts (via the committed runner, not a new builder) carry the tabulated inlet,
the far-field symmetry patches and the monitor probes.
"""
import os

import pytest

from aij.case_b import reference, geometry, conditions
from sreda_wind.solver.runner import build_case


# --- reference data ---------------------------------------------------------

def test_reference_loads_with_expected_counts():
    data = reference.load_reference()
    assert len(reference.pedestrian_points(data)) == 115
    assert len(reference.vertical_points(data)) == 109
    assert len(reference.inflow_levels(data)) == 12
    assert reference.reference_velocity(data) == pytest.approx(5.133)


def test_reference_velocity_is_self_consistent():
    # X = |Uh|_exp / ratio_UH_exp must be a single constant = U_H (5.133).
    data = reference.load_reference()
    mean_x, spread = reference.solve_reference_from_data(data)
    assert mean_x == pytest.approx(5.133, abs=0.005)
    assert spread < 0.02            # constant across all 115 points


def test_inflow_profile_monotone_and_eps_positive():
    data = reference.load_reference()
    profile = conditions.case_b_inflow_profile(data)
    assert len(profile) == 12
    # U increases with height; eps strictly positive
    i = 1
    while i < len(profile):
        assert profile[i][1] >= profile[i - 1][1]
        assert profile[i][3] > 0.0
        i += 1
    # U_H at z=200 mm = 5.133
    at_h = None
    for z, u, k, e in profile:
        if abs(z - 0.20) < 1e-9:
            at_h = u
    assert at_h == pytest.approx(5.133)


# --- geometry (orientation resolved from data) ------------------------------

def test_geometry_is_broadside():
    fp = geometry.footprint()
    xs = [p[0] for p in fp]
    ys = [p[1] for p in fp]
    width_x = max(xs) - min(xs)   # along-wind depth
    width_y = max(ys) - min(ys)   # across-wind width
    assert width_x == pytest.approx(0.05)    # 1b along-wind
    assert width_y == pytest.approx(0.20)    # 4b across-wind (broadside)
    assert width_y > width_x                 # wide face across the wind
    assert geometry.H == pytest.approx(0.20)


# --- domain / blockage ------------------------------------------------------

def test_domain_full_span_and_blockage_under_3pct():
    d = conditions.case_b_domain()
    assert (d.xmin, d.xmax) == (-0.30, 1.00)
    assert (d.ymin, d.ymax) == (-1.50, 1.50)   # full span, no y=0 symmetry
    assert (d.zmin, d.zmax) == (0.0, 1.00)
    assert conditions.frontal_blockage(d) < 0.03   # AIJ best practice
    assert conditions.frontal_blockage(d) == pytest.approx(0.04 / 3.0, rel=1e-6)


# --- generated dicts (via the committed runner; pure file generation) -------

def test_generated_dicts_carry_inlet_symmetry_probes(tmp_path):
    config = conditions.case_b_config(iterations=10)
    case_dir = str(tmp_path / "caseB")
    os.makedirs(case_dir)
    build_case(config, case_dir)

    with open(os.path.join(case_dir, "system/blockMeshDict")) as f:
        block = f.read()
    assert "simpleGrading (1 1 12.0)" in block
    # full-span Y domain extent
    assert "-1.5" in block and "1.5" in block

    with open(os.path.join(case_dir, "0/U")) as f:
        u = f.read()
    assert "tabulatedInletVelocity" in u          # measured inlet
    assert "type            symmetry;" in u        # far-field sides/top

    with open(os.path.join(case_dir, "0/nut")) as f:
        assert "z0              uniform 3.1e-06;" in f.read()

    with open(os.path.join(case_dir, "system/controlDict")) as f:
        control = f.read()
    assert "type            probes;" in control     # stationarity gate
    assert "(0.2 0.05 0.0125)" in control           # off-centre +y probe
