"""Unit tests for the case layer (no OpenFOAM, no solver run)."""
import json
import os

import pytest

from sreda_wind.case import (
    CaseSettings, Building, PorousZone, generate_case,
    classify_patches, turbulence_family, KE_MODELS, KOMEGA_MODELS,
)
from sreda_wind.case import boundary, fields, mesh_dicts, system_dicts, constant_dicts, porous
from sreda_wind.case.boundary import InletContext
from sreda_wind.core import compute_domain, compute_mesh_spec, BBox

# A 32 m cube footprint (AIJ Case A scale: H = 64).
SQUARE = [(0.0, 0.0), (32.0, 0.0), (32.0, 32.0), (0.0, 32.0)]


def _ctx():
    return InletContext(
        ux=5.0, uy=0.0, flow_x=1.0, flow_y=0.0, speed=5.0,
        z_ref=10.0, z0=0.5, k=0.3, epsilon=0.01, omega=0.4)


# --- patch classification ---------------------------------------------------

def test_classify_west_wind_inlet_xmin():
    # Wind FROM 270 deg blows toward +x: inlet at xMin, outlet at xMax.
    types = classify_patches(1.0, 0.0)
    assert types["xMin"] == "inlet"
    assert types["xMax"] == "outlet"
    assert types["yMin"] == "outlet"
    assert types["yMax"] == "outlet"


def test_classify_north_wind_inlet_ymax():
    # Wind FROM 0 deg (north) blows toward -y: inlet at yMax.
    types = classify_patches(0.0, -1.0)
    assert types["yMax"] == "inlet"
    assert types["yMin"] == "outlet"
    assert types["xMin"] == "outlet"
    assert types["xMax"] == "outlet"


def test_classify_diagonal_two_inlets():
    # Diagonal wind: both upwind faces become inlets.
    fx = fy = -(0.5 ** 0.5)
    types = classify_patches(fx, fy)
    assert types["xMax"] == "inlet"
    assert types["yMax"] == "inlet"


# --- turbulence families ----------------------------------------------------

def test_turbulence_family():
    for m in KE_MODELS:
        assert turbulence_family(m) == "epsilon"
    for m in KOMEGA_MODELS:
        assert turbulence_family(m) == "omega"
    with pytest.raises(ValueError):
        turbulence_family("spalartAllmaras")


# --- field builders ---------------------------------------------------------

def test_velocity_field_has_coded_abl_inlet():
    types = {"xMin": "inlet", "xMax": "outlet", "yMin": "outlet", "yMax": "outlet"}
    text = fields.velocity_field(types, _ctx())
    assert "codedFixedValue" in text
    assert "ABLInletVelocity" in text
    # outlet uses inletOutlet, walls noSlip / slip top
    assert "inletOutlet" in text
    assert "noSlip" in text
    assert "slip" in text
    assert "class       volVectorField" in text


def test_all_fields_ke_vs_komega():
    types = {"xMin": "inlet", "xMax": "outlet", "yMin": "outlet", "yMax": "outlet"}
    ke = fields.all_fields(types, _ctx(), "realizableKE")
    assert set(ke) == {"U", "p", "k", "epsilon", "nut"}
    assert "epsilonWallFunction" in ke["epsilon"]

    kw = fields.all_fields(types, _ctx(), "kOmegaSST")
    assert set(kw) == {"U", "p", "k", "omega", "nut"}
    assert "omegaWallFunction" in kw["omega"]


# --- mesh dicts -------------------------------------------------------------

def test_block_mesh_dict_dimensions():
    bbox = BBox(0.0, 32.0, 0.0, 32.0)
    domain = compute_domain(bbox, 64.0, 270.0)
    spec = compute_mesh_spec(domain, bbox, 64.0)
    text = mesh_dicts.block_mesh_dict(domain, spec, vertical_grading=2.0)
    assert "hex (0 1 2 3 4 5 6 7)" in text
    assert "simpleGrading (1 1 2.0)" in text
    # all six named patches present
    for name in ("xMin", "xMax", "yMin", "yMax", "ground", "top"):
        assert name in text
    assert "type wall;" in text   # ground


def test_snappy_region_omitted_when_region_level_zero():
    bbox = BBox(0.0, 32.0, 0.0, 32.0)
    domain = compute_domain(bbox, 64.0, 270.0)
    spec = compute_mesh_spec(domain, bbox, 64.0)
    text = mesh_dicts.snappy_hex_mesh_dict(spec, (0.0, 0.0, 70.0), 3_000_000)
    assert "triSurface" in text
    assert "insidePoint (0.0 0.0 70.0)" in text
    assert ("refinementBox\n        {" in text) == (spec.region_level > 0)


# --- porous zones -----------------------------------------------------------

def test_porous_dicts():
    zones = [PorousZone(id="t0", center_x=5.0, center_y=5.0, z_min=2.5,
                        z_max=7.5, radius=3.0, lad=1.0, cd=0.2)]
    topo = porous.topo_set_dict(zones)
    assert "cylinderToCell" in topo
    assert "treeZone_0" in topo
    fv = porous.fv_options(zones)
    assert "DarcyForchheimer" in fv
    # f = LAD * Cd = 0.2
    assert "0.2000 0.2000 0.2000" in fv


# --- system / constant dicts ------------------------------------------------

def test_control_dict_solver_inline():
    text = system_dicts.control_dict(CaseSettings(iterations=300))
    assert "solver          incompressibleFluid;" in text
    assert "endTime         300;" in text
    assert "application" not in text   # OF13: no application entry


def test_momentum_transport_model():
    text = constant_dicts.momentum_transport("realizableKE")
    assert "simulationType  RAS;" in text
    assert "model           realizableKE;" in text
    assert "RASProperties" in text


def test_physical_properties_nu():
    text = constant_dicts.physical_properties(1.5e-05)
    assert "viscosityModel  constant;" in text
    assert "1.5e-05" in text


# --- full case generation ---------------------------------------------------

def test_generate_case_writes_all_files(tmp_path):
    case_dir = str(tmp_path / "case")
    result = generate_case(
        case_dir,
        buildings=[Building(footprint=SQUARE, height=64.0)],
        direction_deg=270.0, speed=5.0,
        settings=CaseSettings(iterations=100))

    expected = [
        "constant/triSurface/buildings.stl",
        "system/blockMeshDict", "system/snappyHexMeshDict",
        "system/controlDict", "system/fvSchemes", "system/fvSolution",
        "system/decomposeParDict",
        "constant/physicalProperties", "constant/momentumTransport",
        "0/U", "0/p", "0/k", "0/epsilon", "0/nut",
        "manifest.json",
    ]
    for rel in expected:
        assert os.path.exists(os.path.join(case_dir, rel)), rel

    # No omega file for the default k-epsilon model.
    assert not os.path.exists(os.path.join(case_dir, "0/omega"))
    # No fvOptions for the base (no-trees) pipeline.
    assert not os.path.exists(os.path.join(case_dir, "constant/fvOptions"))

    # West wind -> inlet at xMin.
    assert result.patch_types["xMin"] == "inlet"

    # Manifest is valid and records provenance.
    with open(result.manifest_path) as f:
        manifest = json.load(f)
    assert manifest["openfoam_version"] == "13"
    assert manifest["wind"]["direction_deg"] == 270.0
    assert len(manifest["geometry_hash"]) == 64
    assert manifest["mesh"]["nx"] > 0


def test_generate_case_komega_writes_omega(tmp_path):
    case_dir = str(tmp_path / "case_kw")
    generate_case(
        case_dir,
        buildings=[Building(footprint=SQUARE, height=64.0)],
        direction_deg=270.0, speed=5.0,
        settings=CaseSettings(turbulence_model="kOmegaSST"))
    assert os.path.exists(os.path.join(case_dir, "0/omega"))
    assert not os.path.exists(os.path.join(case_dir, "0/epsilon"))


def test_generate_case_with_trees_writes_porous(tmp_path):
    case_dir = str(tmp_path / "case_trees")
    zones = [PorousZone(id="t0", center_x=16.0, center_y=16.0, z_min=2.5,
                        z_max=7.5, radius=3.0, lad=1.0, cd=0.2)]
    generate_case(
        case_dir,
        buildings=[Building(footprint=SQUARE, height=64.0)],
        direction_deg=270.0, speed=5.0,
        porous_zones=zones)
    assert os.path.exists(os.path.join(case_dir, "system/topoSetDict"))
    with open(os.path.join(case_dir, "constant/fvOptions")) as f:
        assert "DarcyForchheimer" in f.read()


def test_generate_case_rejects_empty(tmp_path):
    with pytest.raises(ValueError):
        generate_case(str(tmp_path / "empty"), buildings=[],
                      direction_deg=270.0, speed=5.0)


def test_location_moved_when_inside_building(tmp_path):
    # A footprint centred on the origin; the bbox centre lies inside it, so the
    # insidePoint must be relocated toward the domain corner.
    centred = [(-16.0, -16.0), (16.0, -16.0), (16.0, 16.0), (-16.0, 16.0)]
    case_dir = str(tmp_path / "case_centre")
    generate_case(case_dir, buildings=[Building(footprint=centred, height=64.0)],
                  direction_deg=270.0, speed=5.0)
    with open(os.path.join(case_dir, "system/snappyHexMeshDict")) as f:
        text = f.read()
    # The relocated point must not be (0 0 ...) which is inside the footprint.
    assert "insidePoint (0.0 0.0" not in text
