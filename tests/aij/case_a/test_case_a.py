"""Unit tests for the AIJ Case A harness (pure Python, no OpenFOAM)."""
import os

import pytest

from aij.case_a import geometry


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
