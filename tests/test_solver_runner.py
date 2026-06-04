"""Tests for solver/runner: pure config tests (green) + a gated real smoke."""
import json
import os
import shutil

import pytest

from sreda_wind.solver import runner as runner_mod
from sreda_wind.solver.runner import RunConfig, run, _inject_coeffs
from sreda_wind.case import Building

_CUBE = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]


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
    config = RunConfig(name="seg", buildings=[Building(_CUBE, 2.0)],
                       target_facade_cell=0.5, min_base_cell=1.0, min_building_area=1e-6)
    result = run(config, str(tmp_path), foam_bashrc=None)
    assert result.status == "failed"
    assert result.stages.get("blockMesh") == "failed"
    with open(result.manifest_path) as f:
        manifest = json.load(f)
    assert manifest["stages"]["blockMesh"]["returncode"] == 139
    assert "foamRun" not in manifest["stages"]   # pipeline stopped, no solve


def test_inject_coeffs_raises_on_format_mismatch(tmp_path):
    const = tmp_path / "case" / "constant"
    const.mkdir(parents=True)
    # momentumTransport WITHOUT the expected "printCoeffs on;\n}" marker.
    (const / "momentumTransport").write_text(
        "FoamFile {}\nsimulationType RAS;\nRAS { model kEpsilon; turbulence on; }\n")
    with pytest.raises(RuntimeError):
        _inject_coeffs(str(tmp_path / "case"), "kEpsilon", {"sigmaEps": 1.167})


# --- real smoke test (gated on OpenFOAM 13) --------------------------------

_HAS_OF = shutil.which("foamRun") is not None and shutil.which("blockMesh") is not None


@pytest.mark.skipif(not _HAS_OF, reason="OpenFOAM 13 (foamRun) not on PATH")
def test_runner_smoke_real_case(tmp_path):
    # Smallest/fastest real run: a 2 m cube, coarse mesh, 30 iterations, loose
    # residual target so it converges quickly. Asserts a real RunResult and a
    # valid manifest.json with the config hash written.
    config = RunConfig(
        name="smoke",
        buildings=[Building(_CUBE, 2.0)],
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
