"""Run OpenFOAM 13 for a configuration and report a trustworthy result.

This is the only solver module that touches the shell / OpenFOAM. It is
parameterised by a RunConfig (turbulence model, mesh type, inlet type, model
coeffs, iterations) and builds the case from it — it does not hardcode one set-up.

Robustness (load-bearing for batch runs):
- manifest.json is written EARLY, before any heavy stage, holding the config and
  its hash, so a crash/timeout still leaves a record of what was being run.
- a stage timeout writes status "timed_out" into the manifest (and which stage),
  it does not just kill the process silently.
- every stage's log is parsed (logparse) so a FATAL/divergence is caught and the
  run is marked failed/diverged rather than reported as fine.

Requires the OpenFOAM 13 environment (foamRun etc. on PATH).
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field

from ..case import generate_case, CaseSettings
from . import logparse, convergence

OPENFOAM_VERSION = "13"

# OpenFOAM 13 environment is loaded by sourcing this bashrc inside each stage's
# shell — a bare subprocess does NOT inherit OpenFOAM on PATH (the env only comes
# from ~/.bashrc in interactive shells). Override via run(foam_bashrc=...).
DEFAULT_FOAM_BASHRC = os.environ.get("FOAM_BASHRC", "/opt/openfoam13/etc/bashrc")

# Default per-stage wall-clock limits [s].
DEFAULT_TIMEOUTS = {
    "blockMesh": 300,
    "snappyHexMesh": 1800,
    "checkMesh": 300,
    "foamRun": 7200,
}


@dataclass
class RunConfig:
    """Everything needed to build and run one case."""
    name: str
    buildings: list                       # list of Building
    direction_deg: float = 270.0
    speed: float = 5.0
    turbulence_model: str = "kEpsilon"
    mesh_type: str = "box"                # box | structured
    inlet_type: str = "measured"          # measured | equilibrium
    inlet_profile: tuple = None           # ((z, u, k, eps), ...) for measured
    u_ref: float = 5.0                    # equilibrium Uref
    z_ref: float = 10.0                   # equilibrium Zref
    ground_z0: float = 0.0
    side_top_symmetry: bool = False
    surface_layers: int = 0
    ground_layers: int = 0
    coeffs: dict = field(default_factory=dict)   # e.g. {"sigmaEps": 1.167}
    iterations: int = 500
    residual_target: float = 1.0e-4
    target_facade_cell: float = 2.0
    min_base_cell: float = 4.0
    min_building_area: float = 1.0
    cell_budget: int = 3_000_000

    def to_dict(self):
        out = {}
        out["name"] = self.name
        out["n_buildings"] = len(self.buildings)
        out["direction_deg"] = self.direction_deg
        out["speed"] = self.speed
        out["turbulence_model"] = self.turbulence_model
        out["mesh_type"] = self.mesh_type
        out["inlet_type"] = self.inlet_type
        out["u_ref"] = self.u_ref
        out["z_ref"] = self.z_ref
        out["ground_z0"] = self.ground_z0
        out["side_top_symmetry"] = self.side_top_symmetry
        out["surface_layers"] = self.surface_layers
        out["ground_layers"] = self.ground_layers
        out["coeffs"] = dict(self.coeffs)
        out["iterations"] = self.iterations
        out["residual_target"] = self.residual_target
        out["target_facade_cell"] = self.target_facade_cell
        out["cell_budget"] = self.cell_budget
        return out

    def config_hash(self):
        canonical = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class RunResult:
    """Outcome of a run."""
    status: str = "failed"   # converged | not_converged | diverged | failed | timed_out
    converged: bool = False
    n_iterations: int = 0
    final_residuals: dict = field(default_factory=dict)
    cells: int = 0
    manifest_path: str = ""
    stages: dict = field(default_factory=dict)   # stage -> status
    message: str = ""


def _settings(config):
    """Build a CaseSettings from the config (box/adaptive defaults)."""
    return CaseSettings(
        turbulence_model=config.turbulence_model,
        iterations=config.iterations,
        residual_control=config.residual_target,
        ground_z0=config.ground_z0,
        side_top_symmetry=config.side_top_symmetry,
        surface_layers=config.surface_layers,
        ground_layers=config.ground_layers,
        target_facade_cell=config.target_facade_cell,
        min_base_cell=config.min_base_cell,
        min_building_area=config.min_building_area,
        cell_budget=config.cell_budget,
        z_ref=config.z_ref)


_COEFF_MARKER = "    printCoeffs     on;\n}"


def _inject_coeffs(case_dir, model, coeffs):
    """Inject RAS model coefficients into constant/momentumTransport.

    Raises RuntimeError if the expected marker is not found, so a format drift
    can never silently no-op (which would run with the default coefficients —
    e.g. sigmaEps 1.3 instead of a requested 1.167).
    """
    if not coeffs:
        return
    path = os.path.join(case_dir, "constant", "momentumTransport")
    text = open(path).read()
    if _COEFF_MARKER not in text:
        raise RuntimeError(
            "cannot inject {}Coeffs: marker not found in momentumTransport "
            "(format drift) — refusing to run with wrong coefficients".format(model))
    block = []
    block.append("    {}Coeffs".format(model))
    block.append("    {")
    for key in sorted(coeffs):
        block.append("        {}    {};".format(key, coeffs[key]))
    block.append("    }")
    inject = "    printCoeffs     on;\n" + "\n".join(block) + "\n}"
    new_text = text.replace(_COEFF_MARKER, inject, 1)
    if new_text == text:
        raise RuntimeError("coefficient injection was a no-op")
    open(path, "w").write(new_text)


def build_case(config, case_dir):
    """Build the case directory from the config (box+measured implemented).

    mesh_type=structured and inlet_type=equilibrium reuse the recipes validated
    in the Case A study; box+measured uses case/ directly. Returns nothing; the
    case is on disk.
    """
    settings = _settings(config)
    profile = config.inlet_profile if config.inlet_type == "measured" else None
    generate_case(case_dir, config.buildings, config.direction_deg, config.speed,
                  settings=settings, inlet_profile=profile)
    _inject_coeffs(case_dir, config.turbulence_model, config.coeffs)
    if config.mesh_type != "box" or config.inlet_type != "measured":
        # Structured-mesh / equilibrium-inlet variants are folded in here (the
        # /tmp recipes from the Case A study). Not needed for box+measured.
        raise NotImplementedError(
            "mesh_type={}, inlet_type={} not yet wired into the runner".format(
                config.mesh_type, config.inlet_type))


def _has_geometry(config):
    return len(config.buildings) > 0


def _write_manifest(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _kill_group(proc):
    """SIGKILL the whole process group (snappy/foamRun spawn children)."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def _run_stage(stage, command, case_dir, timeout, foam_bashrc):
    """Run one OpenFOAM command in a sourced shell, with a hard timeout.

    The command runs in its own process session so a timeout kills the whole
    tree (no zombies). Returns (timed_out, returncode, log_text); returncode is
    None on timeout.
    """
    log_path = os.path.join(case_dir, "log.{}".format(stage))
    if foam_bashrc and os.path.exists(foam_bashrc):
        shell_cmd = "source {} && {}".format(foam_bashrc, command)
    else:
        shell_cmd = command
    log_file = open(log_path, "w")
    proc = subprocess.Popen(
        ["bash", "-c", shell_cmd], cwd=case_dir,
        stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        log_file.close()
        return True, None, _read(log_path)
    log_file.close()
    return False, proc.returncode, _read(log_path)


def _read(path):
    if not os.path.exists(path):
        return ""
    return open(path, errors="ignore").read()


def run(config, work_dir, timeouts=None, foam_bashrc=DEFAULT_FOAM_BASHRC, clock=time.time):
    """Build and run the case; return a RunResult and write manifest.json."""
    if timeouts is None:
        timeouts = DEFAULT_TIMEOUTS
    case_dir = os.path.join(work_dir, config.name)
    os.makedirs(case_dir, exist_ok=True)
    manifest_path = os.path.join(case_dir, "manifest.json")

    # (a) Early manifest: config + hash + version, BEFORE any heavy stage.
    manifest = {
        "name": config.name,
        "openfoam_version": OPENFOAM_VERSION,
        "config": config.to_dict(),
        "config_hash": config.config_hash(),
        "status": "started",
        "stages": {},
        "started_at": clock(),
    }
    _write_manifest(manifest_path, manifest)

    result = RunResult(manifest_path=manifest_path)

    def finish(status, message=""):
        result.status = status
        result.message = message
        manifest["status"] = status
        manifest["message"] = message
        manifest["finished_at"] = clock()
        manifest["result"] = {
            "status": status, "converged": result.converged,
            "n_iterations": result.n_iterations, "cells": result.cells,
            "final_residuals": result.final_residuals,
        }
        _write_manifest(manifest_path, manifest)
        return result

    build_case(config, case_dir)

    # Stage pipeline (commands are shell strings, sourced into the OF13 env).
    stages = [("blockMesh", "blockMesh", "command")]
    if _has_geometry(config):
        stages.append(("snappyHexMesh", "snappyHexMesh -overwrite", "command"))
    stages.append(("checkMesh", "checkMesh", "command"))
    stages.append(("foamRun", "foamRun", "solver"))

    si = 0
    while si < len(stages):
        stage, command, kind = stages[si]
        t0 = clock()
        timed_out, returncode, log_text = _run_stage(
            stage, command, case_dir, timeouts.get(stage, 1800), foam_bashrc)
        elapsed = clock() - t0

        if timed_out:
            # (b) timeout -> recorded in the manifest, not a silent kill.
            manifest["stages"][stage] = {"status": "timed_out", "seconds": elapsed}
            result.stages[stage] = "timed_out"
            return finish("timed_out", "{} exceeded {} s".format(stage, timeouts.get(stage)))

        # (c) a non-zero exit (segfault 139 / OOM 137 / not-found 127) is a
        # failure even without a FATAL line in the log — never solve on a broken
        # stage.
        cl = logparse.parse_command_log(log_text)
        if returncode != 0:
            msg = cl.fatal_message if cl.fatal_message else "exit code {}".format(returncode)
            manifest["stages"][stage] = {"status": "failed", "seconds": elapsed,
                                         "returncode": returncode, "message": msg}
            result.stages[stage] = "failed"
            return finish("failed", "{}: {}".format(stage, msg[:160]))
        if not cl.ok:
            manifest["stages"][stage] = {"status": "failed", "seconds": elapsed,
                                         "message": cl.fatal_message}
            result.stages[stage] = "failed"
            return finish("failed", "{}: {}".format(stage, cl.fatal_message[:160]))

        if kind == "command":
            if cl.cells > 0:
                result.cells = cl.cells
            manifest["stages"][stage] = {"status": "ok", "seconds": elapsed, "cells": cl.cells}
            result.stages[stage] = "ok"
        else:
            log = logparse.parse_solver_log(log_text)
            rep = convergence.evaluate(log, config.residual_target)
            result.n_iterations = log.n_steps
            result.final_residuals = dict(log.final_residuals)
            result.converged = rep.converged
            manifest["stages"][stage] = {
                "status": rep.status, "seconds": elapsed,
                "n_iterations": log.n_steps, "diverged": log.diverged, "fatal": log.fatal}
            result.stages[stage] = rep.status
            if rep.status in ("failed", "diverged"):
                return finish(rep.status, "foamRun {}: {}".format(rep.status, log.divergence_reason))
            return finish(rep.status)
        si += 1

    return finish("failed", "pipeline ended without foamRun")
