# solver/ — spec

Automation layer: run OpenFOAM 13 for a given case configuration and report a
trustworthy status (converged / diverged / failed). Replaces the manual
`blockMesh → snappyHexMesh → checkMesh → foamRun` + log-reading loop that was
done by hand throughout the Case A study. Ported from the v4.8 reference
(`_run_calculation` / `_run_command` / `_get_current_iteration`) and CLAUDE.md.

Conventions: English comments, no list comprehensions, layer-by-layer commits,
`pytest -q` green before each commit.

## Composition
- `logparse.py` — **pure** parser of OpenFOAM logs (foamRun, blockMesh,
  snappyHexMesh, checkMesh). No OpenFOAM, no I/O beyond the text it is given.
- `convergence.py` — **pure** convergence + stationarity decision from parsed
  residuals (and optional probe series).
- `runner.py` — orchestrates the mesh+solve pipeline via subprocess in the OF13
  environment; builds the case from a config; writes `manifest.json`; returns a
  structured `RunResult`. The only module that touches OpenFOAM / the shell.

## Three load-bearing requirements
1. **Parameterised runner.** `runner` takes a `RunConfig` (turbulence model,
   mesh type [box | structured], inlet type [measured | equilibrium], extra
   model coeffs [e.g. sigmaEps], plus the geometry/wind/settings) and BUILDS the
   case from it. Case A exercised many variants (kEps/realizableKE/kOmegaSST ×
   box/structured × measured/equilibrium × HW coeffs); the runner must reuse that
   space, not hardcode one path. (Case construction delegates to case/ for
   box+measured; the structured-mesh and equilibrium-inlet builders used in the
   Case A study are folded in as config-selected variants — see "Case builder".)
2. **manifest.json per run** (ML provenance, not deferred). Every run writes
   `manifest.json` next to the case: full config, config hash, OpenFOAM version,
   achieved convergence (converged?, n_iterations, final residuals per field),
   mesh cell count, per-stage status and timings, and the final RunResult status.
3. **Divergence detection in logparse**, not just convergence. logparse flags a
   run as diverged/failed on: FOAM FATAL (IO) ERROR, nan/inf in any residual,
   "Floating point exception", residuals growing instead of decaying (initial
   residual of a field rising and exceeding a ceiling), or runaway continuity
   error. (During the Parente debug k blew up to 626; batch runs will hit this
   regularly, so the solver must distinguish failed from converged and never
   return garbage silently.)

## Contracts

### logparse.py
- `parse_solver_log(text) -> SolverLog`
  - `SolverLog.timesteps`: list of `TimeStep(time, residuals, continuity)` where
    `residuals` maps field -> `(initial, final)` (first solve per field per step;
    p keeps its first corrector's initial), `continuity` is
    `(sum_local, global, cumulative)` or `None`.
  - `SolverLog.converged`: bool — the explicit "SIMPLE solution converged …"
    message is present.
  - `SolverLog.diverged`: bool, `SolverLog.divergence_reason`: str.
  - `SolverLog.fatal`: bool, `SolverLog.fatal_message`: str (first FATAL block).
  - `SolverLog.last_time`: float, `SolverLog.n_steps`: int,
    `SolverLog.final_residuals`: field -> initial residual at the last step.
- `parse_command_log(text) -> CommandLog` (blockMesh/snappy/checkMesh/topoSet):
  `ok` (no FATAL), `fatal_message`, plus a couple of extracted facts
  (e.g. cell count for checkMesh / "Mesh OK").
- Helpers: `has_fatal(text)`, `fatal_message(text)`.

### convergence.py
- `is_converged(solverlog, residual_target, fields=None) -> bool` — explicit
  converged message OR all tracked fields' last initial residual <= target.
- `is_stationary(series, rel_tol) -> bool` — probe/quantity series flat to within
  rel_tol over the last window (for "confirm probe stationarity", AIJ 2.1.7).
- `ConvergenceReport` bundling converged/diverged/stationary + the numbers.

### runner.py
- `RunConfig` (dataclass): turbulence_model, mesh_type, inlet_type, coeffs(dict),
  iterations, residual_target, + case inputs (buildings, wind, ground_z0, …).
- `run(config, work_dir) -> RunResult`:
  build case → blockMesh → (snappyHexMesh if geometry) → checkMesh → foamRun,
  each stage: subprocess in OF13 env, capture log, `parse_command_log` /
  `parse_solver_log`, stop on FATAL/divergence. Timeouts per stage. Writes
  `manifest.json`. Returns `RunResult(status, converged, n_iterations,
  final_residuals, cells, manifest_path, stage_logs)` where status ∈
  {converged, not_converged, diverged, failed}.

### Case builder (config -> case)
A thin selector used by runner: `mesh_type` ∈ {box (adaptive, core/mesh),
structured (uniform near-ground z, no box)}; `inlet_type` ∈ {measured (tabulated
Meng&Hibi), equilibrium (atmBoundaryLayer)}; `coeffs` injected into
`constant/momentumTransport` (e.g. sigmaEps). Box+measured uses case/ as-is; the
structured and equilibrium variants (validated in the Case A study) become
config-selected paths. This keeps the runner declarative.

## What is tested
- `logparse` — synthetic foamRun/blockMesh/snappy/checkMesh logs: converged run,
  diverging run (residuals growing → nan), FATAL run, residual + continuity
  extraction. Pure-Python, no OpenFOAM, in the green `pytest -q` set.
- `convergence` — synthetic residual + probe series → converged/stationary
  decisions and the divergence path. Pure-Python, green.
- `runner` — smoke test on one real generated case (needs OF13): asserts it
  reaches a converged RunResult and writes a valid manifest.json. Kept out of the
  pure green set (gated on OpenFOAM availability), run like the Case A smokes.

## Build order
1. `logparse.py` + tests (pure, green).
2. `convergence.py` + tests (pure, green).
3. `runner.py` + manifest + smoke test.
Each its own commit, `pytest -q` green before committing.
