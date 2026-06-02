"""Unit tests for the AIJ Case A harness (pure Python, no OpenFOAM)."""
import math
import os

import pytest

from aij.case_a import geometry, inlet, reattachment, reference, conditions


def test_geometry_bbox_is_1_1_2_at_model_scale():
    mesh = geometry.build_mesh()
    xmin, ymin, zmin, xmax, ymax, zmax = mesh.bbox()
    # 0.08 x 0.08 in plan, 0.16 tall, centred on origin, base at z=0.
    assert xmin == pytest.approx(-0.04)
    assert xmax == pytest.approx(0.04)
    assert ymin == pytest.approx(-0.04)
    assert ymax == pytest.approx(0.04)
    assert zmin == pytest.approx(0.0)
    assert zmax == pytest.approx(0.16)


def test_geometry_height_is_twice_width():
    assert geometry.H == pytest.approx(2.0 * geometry.B)


def test_write_binary_stl(tmp_path):
    path = str(tmp_path / "caseA.stl")
    mesh = geometry.write_stl(path)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0
    # 4 walls x 2 + centroid-fan roof (4) + floor (4) = 16 triangles.
    assert mesh.triangle_count == 16


# --- reference data loader --------------------------------------------------

def test_reference_loads_and_validates():
    data = reference.load_reference()
    assert data["case"] == "A"
    assert data["b"] == pytest.approx(0.08)
    pts = reference.inflow_points(data)
    assert len(pts) == 24                       # real Table 1 profile
    # sorted by z, ascending
    assert pts[0][0] < pts[-1][0]
    # Measured k now in hand: ~0.398 at z/b=0.125, ~0.653 at building height.
    z0125 = [p for p in pts if abs(p[0] - 0.01) < 1e-9][0]
    assert z0125[2] == pytest.approx(0.3977)
    # The 60 measured pedestrian ratios are now populated (q check unblocked).
    assert reference.has_pedestrian_ratios(data) is True
    assert len(reference.pedestrian_ratios(data)) == 60


def test_reference_u_ref_and_quantity():
    data = reference.load_reference()
    assert reference.u_ref(data, "pedestrian") == pytest.approx(2.935)
    assert reference.u_ref(data, "secondary") == pytest.approx(4.021)
    # ratio_horizontal is consistent with speed_horizontal / u_ref.
    p = reference.pedestrian_ratios(data)[8]   # id 9
    assert p["ratio_horizontal"] == pytest.approx(p["speed_horizontal"] / 2.935, abs=1e-3)


def test_reattachment_targets_present():
    data = reference.load_reference()
    targets = reference.reattachment_targets(data)
    assert targets["experiment"]["XR_over_b"] == pytest.approx(0.52)
    assert targets["per_case"]["KE5"]["XF"] == pytest.approx(1.98)
    # Standard k-eps predicts no roof reattachment.
    assert targets["per_case"]["KE1"]["XR"] is None


# --- inlet profile (epsilon from the local-equilibrium form) ----------------

def test_inlet_eps_linear_u_constant_k():
    # U = 2 z (so dU/dz = 2), k = 0.5 -> eps = sqrt(0.09)*0.5*2 = 0.3.
    points = [(0.0, 0.0, 0.5), (1.0, 2.0, 0.5), (2.0, 4.0, 0.5)]
    profile = inlet.build_inlet_profile(points)
    assert len(profile) == 3
    for z, u, k, eps in profile:
        assert eps == pytest.approx(math.sqrt(0.09) * 0.5 * 2.0)


def test_inlet_profile_from_reference():
    data = reference.load_reference()
    profile = inlet.build_inlet_profile(reference.inflow_points(data))
    # Every epsilon is strictly positive and the table keeps the U values.
    for z, u, k, eps in profile:
        assert eps > 0.0
    assert profile[1][1] == pytest.approx(2.935)   # u at z/b=0.125 (Table 1)


# --- reattachment extraction ------------------------------------------------

def test_reattachment_on_synthetic_reversing_profile():
    # Reverse flow up to x=2.0, reattaches (sign change) between 2.0 and 3.0.
    distances = [0.0, 1.0, 2.0, 3.0, 4.0]
    u_wall = [-1.0, -0.5, -0.25, 0.25, 1.0]
    xr = reattachment.reattachment_length(distances, u_wall)
    # Zero crossing between 2.0 (u=-0.25) and 3.0 (u=0.25) -> 2.5.
    assert xr == pytest.approx(2.5)
    assert reattachment.reattachment_over_b(distances, u_wall, b=0.5) == pytest.approx(5.0)


def test_reattachment_none_when_no_reversal():
    # Attached flow everywhere (std k-eps roof) -> no reattachment length.
    assert reattachment.reattachment_length([0.0, 1.0, 2.0], [0.5, 0.8, 1.0]) is None


# --- conditions assembly ----------------------------------------------------

def test_case_a_inputs_match_spec():
    kwargs = conditions.case_a_inputs(model="kEpsilon", iterations=1000)
    assert kwargs["direction_deg"] == pytest.approx(270.0)
    s = kwargs["settings"]
    assert s.turbulence_model == "kEpsilon"
    assert s.side_top_symmetry is True
    assert s.ground_z0 == pytest.approx(1.8e-4)
    assert s.target_facade_cell == pytest.approx(0.08 / 14.0)
    assert s.residual_control == pytest.approx(1e-6)
    # inlet profile carries (z, u, k, eps) tuples
    assert len(kwargs["inlet_profile"][0]) == 4
    # realizable variant is available for step 2
    assert conditions.case_a_inputs(model="realizableKE")["settings"].turbulence_model == "realizableKE"
