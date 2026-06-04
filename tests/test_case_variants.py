"""Tests for the structured-mesh and equilibrium-inlet case variants.

These assert that the generated OpenFOAM dictionaries are correct at the file
level (no OpenFOAM run needed): the structured blockMeshDict carries the right
resolution and vertical grading, and the equilibrium inlet writes
atmBoundaryLayerInlet* patches plus a matching include/ABLConditions.
"""
import os
import types

import pytest

from sreda_wind.case import Building, CaseSettings, generate_case
from sreda_wind.case.boundary import InletContext, abl_conditions
from sreda_wind.case.mesh_dicts import structured_block_mesh_dict
from sreda_wind.core import Domain

_CUBE = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
_DOMAIN = Domain(-5.0, 8.0, -5.0, 5.0, 0.0, 5.0, "x")


def _read(case_dir, rel):
    with open(os.path.join(case_dir, rel)) as f:
        return f.read()


def _model_settings(**kw):
    """CaseSettings tuned for a small model-scale cube case."""
    base = dict(turbulence_model="kEpsilon", iterations=10,
                min_base_cell=0.2, target_facade_cell=0.1, min_building_area=1e-6)
    base.update(kw)
    return CaseSettings(**base)


# --- pure builder unit tests -----------------------------------------------

def test_structured_block_mesh_dict_grading_and_resolution():
    # 1.0 x 0.8 domain, 0.01 base cell -> 100 x 80 horizontal cells, nz vertical.
    domain = types.SimpleNamespace(xmin=-0.4, xmax=0.6, ymin=-0.4, ymax=0.4,
                                   zmin=0.0, zmax=0.8)
    text = structured_block_mesh_dict(domain, base_cell=0.01, nz=50,
                                      vertical_grading=12.0)
    assert "hex (0 1 2 3 4 5 6 7) (100 80 50) simpleGrading (1 1 12.0)" in text
    assert "convertToMeters 1;" in text
    # the six named patches are present
    for name in ("xMin", "xMax", "yMin", "yMax", "ground", "top"):
        assert name in text


def test_structured_block_mesh_dict_respects_boundary_types():
    domain = types.SimpleNamespace(xmin=0.0, xmax=1.0, ymin=0.0, ymax=1.0,
                                   zmin=0.0, zmax=1.0)
    text = structured_block_mesh_dict(domain, base_cell=0.1, nz=20,
                                      vertical_grading=5.0,
                                      boundary_types={"yMin": "symmetry", "yMax": "symmetry"})
    assert "(10 10 20)" in text
    assert text.count("type symmetry;") == 2


def test_abl_conditions_carries_uref_zref_z0():
    ctx = InletContext(ux=2.935, uy=0.0, flow_x=1.0, flow_y=0.0, speed=2.935,
                       z_ref=0.01, z0=1.8e-4, k=0.1, epsilon=0.1, omega=1.0,
                       inlet_mode="equilibrium")
    text = abl_conditions(ctx)
    assert "Uref            2.935;" in text
    assert "Zref            0.01;" in text
    assert "z0              uniform 0.00018;" in text
    assert "flowDir         (1.000000 0.000000 0);" in text
    assert "zDir            (0 0 1);" in text


# --- generated-case tests (full wiring through generate_case) ---------------

def test_generate_case_structured_blockmesh(tmp_path):
    case = str(tmp_path / "struct")
    settings = _model_settings(structured_base_cell=0.05, structured_nz=50,
                               structured_grading=12.0, structured_surface_level=1)
    generate_case(case, [Building(_CUBE, 2.0)], 270.0, 5.0, _DOMAIN,
                  settings=settings, mesh_type="structured")
    block = _read(case, "system/blockMeshDict")
    # structured grading and vertical cell count come straight from settings
    assert "simpleGrading (1 1 12.0)" in block
    assert " 50) simpleGrading" in block   # nz = structured_nz


def test_monitor_points_write_probes_in_controldict(tmp_path):
    # The stationarity-gate monitor: when monitor_points is set, controlDict
    # carries a probes functionObject sampling them every iteration.
    case = str(tmp_path / "mon")
    settings = _model_settings(monitor_points=((0.12, 0.0, 0.01), (0.16, 0.0, 0.01)))
    generate_case(case, [Building(_CUBE, 2.0)], 270.0, 5.0, _DOMAIN,
                  settings=settings, mesh_type="structured")
    control = _read(case, "system/controlDict")
    assert "type            probes;" in control
    assert "(0.12 0.0 0.01)" in control
    assert "writeInterval   1;" in control   # every iteration


def test_no_monitor_points_no_probes(tmp_path):
    case = str(tmp_path / "nomon")
    generate_case(case, [Building(_CUBE, 2.0)], 270.0, 5.0, _DOMAIN,
                  settings=_model_settings())
    assert "type            probes;" not in _read(case, "system/controlDict")


def test_structured_snappy_is_nobox(tmp_path):
    # The structured path carries its OWN snappy recipe: building snapped at the
    # explicit structured_surface_level, and NO refinement region ("nobox") --
    # it does not inherit the adaptive mesh_spec's level/region (canon Case A).
    case = str(tmp_path / "struct_snappy")
    settings = _model_settings(structured_surface_level=1)
    generate_case(case, [Building(_CUBE, 2.0)], 270.0, 5.0, _DOMAIN,
                  settings=settings, mesh_type="structured")
    snappy = _read(case, "system/snappyHexMeshDict")
    assert "level (1 1);" in snappy                 # structured_surface_level
    # nobox: the refinementRegions block is empty (no refinementBox inside it)
    regions = snappy.split("refinementRegions", 1)[1].split("}", 1)[0]
    assert "refinementBox" not in regions
    assert "mode" not in regions


def test_generate_case_equilibrium_inlet(tmp_path):
    case = str(tmp_path / "equil")
    settings = _model_settings(z_ref=0.01, z0=1.8e-4, ground_z0=1.8e-4,
                               side_top_symmetry=True)
    generate_case(case, [Building(_CUBE, 2.0)], 270.0, 2.935, _DOMAIN,
                  settings=settings, inlet_type="equilibrium")

    # 270 deg meteorological -> flow toward +x -> inlet at xMin.
    u = _read(case, "0/U")
    assert "atmBoundaryLayerInletVelocity" in u
    assert '#include        "include/ABLConditions"' in u
    k = _read(case, "0/k")
    assert "atmBoundaryLayerInletK" in k
    eps = _read(case, "0/epsilon")
    assert "atmBoundaryLayerInletEpsilon" in eps

    # the shared include exists and carries the inlet parameters
    abl = _read(case, "0/include/ABLConditions")
    assert "Uref            2.935;" in abl
    assert "Zref            0.01;" in abl
    assert "z0              uniform 0.00018;" in abl

    # the atmospheric models library is loaded (rough wall + atm inlet need it)
    control = _read(case, "system/controlDict")
    assert "libatmosphericModels.so" in control


def test_generate_case_equilibrium_rejects_omega(tmp_path):
    case = str(tmp_path / "bad")
    settings = _model_settings(turbulence_model="kOmegaSST", ground_z0=1.8e-4)
    with pytest.raises(ValueError):
        generate_case(case, [Building(_CUBE, 2.0)], 270.0, 2.935, _DOMAIN,
                      settings=settings, inlet_type="equilibrium")


def test_generate_case_default_inlet_is_coded(tmp_path):
    # Regression: the default (coded) inlet is unchanged by the new variants.
    case = str(tmp_path / "coded")
    generate_case(case, [Building(_CUBE, 2.0)], 270.0, 5.0, _DOMAIN,
                  settings=_model_settings())
    u = _read(case, "0/U")
    assert "codedFixedValue" in u
    assert "atmBoundaryLayerInlet" not in u
    assert not os.path.exists(os.path.join(case, "0/include/ABLConditions"))
