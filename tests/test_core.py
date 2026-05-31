"""Unit tests for the pure-physics core (no OpenFOAM)."""
import math

import pytest

from sreda_wind.core import (
    abl_parameters, friction_velocity, velocity_at, dissipation_at,
    flow_vector, inflow_velocity,
    BBox, DomainFactors, compute_domain,
    compute_mesh_spec,
)


# --- ABL -------------------------------------------------------------------

def test_friction_velocity_matches_log_law():
    ustar = friction_velocity(u_ref=5.0, z_ref=10.0, z0=0.5)
    expected = 5.0 * 0.41 / math.log((10.0 + 0.5) / 0.5)
    assert ustar == pytest.approx(expected)


def test_velocity_profile_recovers_reference_speed():
    p = abl_parameters(u_ref=5.0, z_ref=10.0, z0=0.5)
    u_at_ref = velocity_at(p.z_ref, p.ustar, p.z0)
    assert u_at_ref == pytest.approx(5.0, rel=1e-9)


def test_abl_k_and_epsilon_formulas():
    p = abl_parameters(u_ref=4.491, z_ref=10.0, z0=0.029)
    assert p.k == pytest.approx(p.ustar ** 2 / math.sqrt(0.09))
    assert p.epsilon == pytest.approx(p.ustar ** 3 / (0.41 * (10.0 + 0.029)))


def test_dissipation_decreases_with_height():
    p = abl_parameters(u_ref=5.0, z_ref=10.0, z0=0.5)
    assert dissipation_at(2.0, p.ustar, p.z0) > dissipation_at(50.0, p.ustar, p.z0)


def test_zero_roughness_rejected():
    with pytest.raises(ValueError):
        friction_velocity(5.0, 10.0, 0.0)


# --- wind ------------------------------------------------------------------

def test_flow_vector_cardinal_directions():
    # North (0): blows toward -y; East (90): toward -x; West (270): toward +x
    fx, fy = flow_vector(0.0)
    assert (fx, fy) == pytest.approx((0.0, -1.0), abs=1e-9)
    fx, fy = flow_vector(90.0)
    assert (fx, fy) == pytest.approx((-1.0, 0.0), abs=1e-9)
    fx, fy = flow_vector(270.0)
    assert (fx, fy) == pytest.approx((1.0, 0.0), abs=1e-9)


def test_inflow_velocity_scales_and_keeps_w_zero():
    ux, uy, uz = inflow_velocity(270.0, 5.0)
    assert ux == pytest.approx(5.0, abs=1e-9)
    assert uy == pytest.approx(0.0, abs=1e-9)
    assert uz == 0.0


# --- domain ----------------------------------------------------------------

def test_domain_streamwise_x_for_westerly():
    bbox = BBox(0.0, 50.0, 0.0, 50.0)
    H = 20.0
    d = compute_domain(bbox, H, direction_deg=270.0)  # flow toward +x
    f = DomainFactors()
    assert d.streamwise_axis == "x"
    # inlet upstream (x_min), outlet downstream (x_max)
    assert d.xmin == pytest.approx(0.0 - f.inlet * H)
    assert d.xmax == pytest.approx(50.0 + f.outlet * H)
    # lateral symmetric on y
    assert d.ymin == pytest.approx(0.0 - f.lateral * H)
    assert d.ymax == pytest.approx(50.0 + f.lateral * H)
    assert d.zmax == pytest.approx(f.height * H)


def test_domain_lateral_symmetric():
    bbox = BBox(-10.0, 10.0, -10.0, 10.0)
    d = compute_domain(bbox, 20.0, direction_deg=270.0)
    # cross-stream (y) padding equal on both sides of the bbox
    top_pad = d.ymax - bbox.ymax
    bottom_pad = bbox.ymin - d.ymin
    assert top_pad == pytest.approx(bottom_pad)


# --- adaptive mesh ---------------------------------------------------------

def _domain_for(bbox, H):
    return compute_domain(bbox, H, direction_deg=270.0)


def test_mesh_small_scene_fits_budget():
    bbox = BBox(0.0, 100.0, 0.0, 100.0)
    H = 20.0
    spec = compute_mesh_spec(_domain_for(bbox, H), bbox, H,
                             target_facade_cell=2.0, cell_budget=3_000_000)
    assert spec.estimated_cells <= 3_000_000
    assert spec.surface_level >= 2
    assert spec.facade_cell <= 2.0 + 1e-9


def test_mesh_large_scene_stays_in_budget_and_warns():
    bbox = BBox(0.0, 3000.0, 0.0, 3000.0)
    H = 20.0
    spec = compute_mesh_spec(_domain_for(bbox, H), bbox, H,
                             target_facade_cell=2.0, cell_budget=3_000_000)
    assert spec.estimated_cells <= 3_000_000
    assert len(spec.warnings) >= 1


def test_mesh_facade_finer_than_base():
    bbox = BBox(0.0, 64.0, 0.0, 64.0)
    H = 64.0
    spec = compute_mesh_spec(_domain_for(bbox, H), bbox, H,
                             target_facade_cell=3.2, cell_budget=5_000_000)
    assert spec.facade_cell < spec.base_cell
    assert spec.region_level <= spec.surface_level


def test_mesh_scales_across_sizes():
    H = 20.0
    sizes = (100.0, 500.0, 1500.0, 3000.0)
    for s in sizes:
        bbox = BBox(0.0, s, 0.0, s)
        spec = compute_mesh_spec(_domain_for(bbox, H), bbox, H,
                                 cell_budget=3_000_000)
        assert spec.estimated_cells <= 3_000_000
        assert spec.nx >= 20 and spec.ny >= 20 and spec.nz >= 15
