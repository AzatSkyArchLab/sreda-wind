"""Tests for solver/runner: pure config tests (green) + a gated real smoke."""
import json
import os
import shutil

import pytest

from sreda_wind.solver import runner as runner_mod
from sreda_wind.solver.runner import RunConfig, run, _inject_coeffs
from sreda_wind.case import Building
from sreda_wind.core import Domain

_CUBE = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
_DOMAIN = Domain(-5.0, 8.0, -5.0, 5.0, 0.0, 5.0, "x")


# --- pure RunConfig tests (no OpenFOAM) ------------------------------------

def test_runconfig_to_dict_and_hash_deterministic():
    a = RunConfig(name="c1", buildings=[Building(_CUBE, 2.0)], coeffs={"sigmaEps": 1.167})
    d = a.to_dict()
    assert d["turbulence_model"] == "kEpsilon"
    assert d["coeffs"]["sigmaEps"] == 1.167
    # same config -> same hash
    b = RunConfig(name="c1", buildings=[Building(_CUBE, 2.0)], coeffs={"sigmaEps": 1.167})
    assert a.config_hash() == b.config_hash()
    assert len(a.config_hash()) == 64


def test_runconfig_hash_changes_with_config():
    a = RunConfig(name="c", buildings=[Building(_CUBE, 2.0)])
    b = RunConfig(name="c", buildings=[Building(_CUBE, 2.0)], turbulence_model="kOmegaSST")
    assert a.config_hash() != b.config_hash()


def test_nonzero_returncode_is_failed(tmp_path, monkeypatch):
    # A stage that exits non-zero with NO "FATAL" line in the log (segfault /
    # OOM / not-found) must still fail the run -- never solve on a broken stage.
    def fake_stage(stage, command, case_dir, timeout, foam_bashrc):
        return (False, 139, "starting...\nSegmentation fault (core dumped)\n")
    monkeypatch.setattr(runner_mod, "_run_stage", fake_stage)
    config = RunConfig(name="seg", buildings=[Building(_CUBE, 2.0)], domain=_DOMAIN,
                       target_facade_cell=0.5, min_base_cell=1.0, min_building_area=1e-6)
    result = run(config, str(tmp_path), foam_bashrc=None)
    assert result.status == "failed"
    assert result.stages.get("blockMesh") == "failed"
    with open(result.manifest_path) as f:
        manifest = json.load(f)
    assert manifest["stages"]["blockMesh"]["returncode"] == 139
    assert "foamRun" not in manifest["stages"]   # pipeline stopped, no solve


def test_monitor_stationarity_reads_frozen_probe(tmp_path):
    # A frozen probe (|U| flat) -> stationary True, tiny band. Synthesises the
    # OpenFOAM probes output layout the runner reads after foamRun.
    base = tmp_path / "postProcessing" / "monitorProbes" / "0"
    base.mkdir(parents=True)
    lines = ["# Probe 0 (0.12 0 0.01)\n"]
    i = 0
    while i < 40:
        lines.append("{}   (1.4005 0.0038 -0.012)\n".format(2000 + i))
        i += 1
    (base / "U").write_text("".join(lines))
    stat, band = runner_mod._monitor_stationarity(str(tmp_path))
    assert stat is True
    assert band < 1e-6


def test_monitor_stationarity_detects_oscillation(tmp_path):
    base = tmp_path / "postProcessing" / "monitorProbes" / "0"
    base.mkdir(parents=True)
    lines = ["# Probe 0\n"]
    i = 0
    while i < 40:
        ux = 1.30 if i % 2 == 0 else 1.27   # 2.3% swing -> not frozen
        lines.append("{}   ({} 0.0 0.0)\n".format(2000 + i, ux))
        i += 1
    (base / "U").write_text("".join(lines))
    stat, band = runner_mod._monitor_stationarity(str(tmp_path))
    assert stat is False
    assert band > 0.01


def test_monitor_stationarity_none_without_probe(tmp_path):
    stat, band = runner_mod._monitor_stationarity(str(tmp_path))
    assert stat is None and band == 0.0


def test_inject_coeffs_raises_on_format_mismatch(tmp_path):
    const = tmp_path / "case" / "constant"
    const.mkdir(parents=True)
    # momentumTransport WITHOUT the expected "printCoeffs on;\n}" marker.
    (const / "momentumTransport").write_text(
        "FoamFile {}\nsimulationType RAS;\nRAS { model kEpsilon; turbulence on; }\n")
    with pytest.raises(RuntimeError):
        _inject_coeffs(str(tmp_path / "case"), "kEpsilon", {"sigmaEps": 1.167})


def test_build_case_structured_equilibrium(tmp_path):
    # build_case must wire structured mesh + equilibrium inlet without raising
    # (the old NotImplementedError is gone); check the produced dicts.
    config = RunConfig(
        name="se", buildings=[Building(_CUBE, 2.0)], domain=_DOMAIN,
        turbulence_model="kEpsilon", mesh_type="structured", inlet_type="equilibrium",
        z_ref=0.01, ground_z0=1.8e-4, side_top_symmetry=True,
        structured_base_cell=0.05, structured_nz=50, structured_grading=12.0,
        coeffs={"sigmaEps": 1.167},
        target_facade_cell=0.1, min_base_cell=0.2, min_building_area=1e-6)
    case_dir = str(tmp_path / config.name)
    os.makedirs(case_dir)
    runner_mod.build_case(config, case_dir)

    with open(os.path.join(case_dir, "system/blockMeshDict")) as f:
        assert "simpleGrading (1 1 12.0)" in f.read()
    with open(os.path.join(case_dir, "0/U")) as f:
        assert "atmBoundaryLayerInletVelocity" in f.read()
    assert os.path.exists(os.path.join(case_dir, "0/include/ABLConditions"))
    # coeffs were injected (no silent no-op)
    with open(os.path.join(case_dir, "constant/momentumTransport")) as f:
        assert "sigmaEps" in f.read()


def test_equilibrium_inlet_and_ground_z0_match(tmp_path):
    # A self-consistent equilibrium ABL needs the inlet roughness and the ground
    # rough-wall roughness to be the same z0 (canon Case A: both 1.8e-4). The
    # single config z0 must drive both -- regression for the inlet-z0 bug where
    # the inlet silently used the default 0.5 while the ground used ground_z0.
    config = RunConfig(
        name="z0", buildings=[Building(_CUBE, 2.0)], domain=_DOMAIN,
        turbulence_model="kEpsilon", mesh_type="structured", inlet_type="equilibrium",
        z_ref=0.01, z0=1.8e-4, ground_z0=0.0,   # ground_z0 left unset on purpose
        side_top_symmetry=True, min_building_area=1e-6,
        target_facade_cell=0.1, min_base_cell=0.2)
    case_dir = str(tmp_path / config.name)
    os.makedirs(case_dir)
    runner_mod.build_case(config, case_dir)
    with open(os.path.join(case_dir, "0/include/ABLConditions")) as f:
        assert "z0              uniform 0.00018;" in f.read()
    with open(os.path.join(case_dir, "0/nut")) as f:
        nut = f.read()
    assert "nutkAtmRoughWallFunction" in nut
    assert "z0              uniform 0.00018;" in nut   # matched, not smooth/default


# --- real smoke test (gated on OpenFOAM 13) --------------------------------

_HAS_OF = shutil.which("foamRun") is not None and shutil.which("blockMesh") is not None


@pytest.mark.skipif(not _HAS_OF, reason="OpenFOAM 13 (foamRun) not on PATH")
def test_runner_smoke_real_case(tmp_path):
    # Smallest/fastest real run: a 2 m cube, coarse mesh, 30 iterations, loose
    # residual target so it converges quickly. Asserts a real RunResult and a
    # valid manifest.json with the config hash written.
    config = RunConfig(
        name="smoke",
        buildings=[Building(_CUBE, 2.0)], domain=_DOMAIN,
        direction_deg=270.0, speed=5.0,
        turbulence_model="kEpsilon",
        iterations=30, residual_target=1e-2,
        target_facade_cell=0.5, min_base_cell=1.0, min_building_area=1e-6,
        cell_budget=100_000)
    result = run(config, str(tmp_path))

    assert result.status in ("converged", "not_converged")   # a real verdict
    assert result.cells > 0
    assert result.stages.get("blockMesh") == "ok"
    assert result.stages.get("snappyHexMesh") == "ok"
    assert result.stages.get("foamRun") in ("converged", "not_converged")

    # manifest is valid and carries the config + hash (early-write provenance).
    with open(result.manifest_path) as f:
        manifest = json.load(f)
    assert manifest["config_hash"] == config.config_hash()
    assert manifest["openfoam_version"] == "13"
    assert manifest["config"]["turbulence_model"] == "kEpsilon"
    assert "result" in manifest and manifest["result"]["cells"] > 0
