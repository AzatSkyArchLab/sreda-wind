"""Unit tests for the geometry layer (no OpenFOAM)."""
import math

import pytest

from sreda_wind.geometry import (
    TriMesh, merge,
    is_ccw, ensure_ccw, is_convex_polygon, triangulate_ear_clipping,
    extrude_footprint,
    write_ascii, write_binary, read_stl,
    polygon_area, validate_polygon,
)

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
L_SHAPE = [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0), (1.0, 2.0), (0.0, 2.0)]


# --- orientation / convexity ----------------------------------------------

def test_ccw_detection_and_fix():
    assert is_ccw(SQUARE) is True
    cw = list(reversed(SQUARE))
    assert is_ccw(cw) is False
    assert is_ccw(ensure_ccw(cw)) is True


def test_convexity():
    assert is_convex_polygon(SQUARE) is True
    assert is_convex_polygon(L_SHAPE) is False


# --- ear clipping -----------------------------------------------------------

def test_ear_clipping_triangle_count():
    # A simple polygon of n vertices triangulates into n - 2 triangles.
    assert len(triangulate_ear_clipping(SQUARE)) == len(SQUARE) - 2
    assert len(triangulate_ear_clipping(L_SHAPE)) == len(L_SHAPE) - 2


# --- extrusion --------------------------------------------------------------

def test_extrude_square_box_counts_and_bbox():
    mesh = extrude_footprint(SQUARE, height=20.0)
    # 4 walls * 2 + (4 roof + 4 floor) = 16 triangles
    assert mesh.triangle_count == 16
    xmin, ymin, zmin, xmax, ymax, zmax = mesh.bbox()
    assert (xmin, ymin, zmin) == pytest.approx((0.0, 0.0, 0.0))
    assert (xmax, ymax, zmax) == pytest.approx((10.0, 10.0, 20.0))


def test_extrude_concave_is_watertight_height():
    mesh = extrude_footprint(L_SHAPE, height=5.0)
    _, _, zmin, _, _, zmax = mesh.bbox()
    assert zmin == pytest.approx(0.0)
    assert zmax == pytest.approx(5.0)
    assert mesh.triangle_count > 0


def test_merge_concatenates():
    a = extrude_footprint(SQUARE, 10.0)
    b = extrude_footprint(SQUARE, 5.0)
    m = merge([a, b])
    assert m.triangle_count == a.triangle_count + b.triangle_count


# --- STL round trips --------------------------------------------------------

def test_stl_ascii_round_trip(tmp_path):
    mesh = extrude_footprint(SQUARE, 20.0)
    p = tmp_path / "box.stl"
    write_ascii(mesh, str(p))
    back = read_stl(str(p))
    assert back.triangle_count == mesh.triangle_count
    assert back.bbox() == pytest.approx(mesh.bbox())


def test_stl_binary_round_trip(tmp_path):
    mesh = extrude_footprint(SQUARE, 20.0)
    p = tmp_path / "box_bin.stl"
    write_binary(mesh, str(p))
    back = read_stl(str(p))
    assert back.triangle_count == mesh.triangle_count
    # binary STL is float32, so compare with tolerance
    assert back.bbox() == pytest.approx(mesh.bbox(), abs=1e-3)


def test_binary_is_smaller_than_ascii(tmp_path):
    mesh = extrude_footprint(L_SHAPE, 12.0)
    a = tmp_path / "a.stl"
    b = tmp_path / "b.stl"
    write_ascii(mesh, str(a))
    write_binary(mesh, str(b))
    assert b.stat().st_size < a.stat().st_size


# --- validation -------------------------------------------------------------

def test_polygon_area_square():
    assert polygon_area(SQUARE) == pytest.approx(100.0)


def test_validate_rejects_tiny_and_degenerate():
    assert validate_polygon([(0, 0), (0.1, 0), (0, 0.1)], 10.0, min_area=1.0) is None
    assert validate_polygon([(0, 0), (1, 1)], 10.0) is None


def test_validate_enforces_ccw_and_closure():
    cw = list(reversed(SQUARE))
    out = validate_polygon(cw, height=15.0)
    assert out is not None
    assert out["height"] == 15.0
    assert out["coords"][0] == out["coords"][-1]      # closed
    assert is_ccw(out["coords"][:-1]) is True          # CCW


# --- AIJ Case A geometry (1:1:2 box, b=32 -> 32x32x64) ----------------------

def test_aij_case_a_box():
    half = 16.0
    coords = [(-half, -half), (half, -half), (half, half), (-half, half)]
    mesh = extrude_footprint(coords, height=64.0)
    xmin, ymin, zmin, xmax, ymax, zmax = mesh.bbox()
    assert (xmax - xmin) == pytest.approx(32.0)
    assert (ymax - ymin) == pytest.approx(32.0)
    assert (zmax - zmin) == pytest.approx(64.0)
