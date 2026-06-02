# AIJ Case A — validation spec for sreda-wind (v3)

Spec for `tests/aij/case_a/`. Read with repo-root `CLAUDE.md`. Conventions:
English comments, no list comprehensions, layer-by-layer commits, `pytest -q`
green before commit.

Approach: reproduce the AIJ-2016 benchmark, guided by its own sensitivity
study. AIJ (Section 2.1.5) showed which conditions matter and which do not, so
we are strict where it matters and practical where it does not. Source: AIJ
Benchmarks 2016, Section 2.1 (experiment: Meng & Hibi 1998).

Exact point coordinates, reference ratios and the measured inflow profile come
from `CaseA(1_1_2).xls` -> delivered as `reference_data.json`. Do not hardcode.

## 1. Goal and acceptance
Two complementary checks (both reported):
- A. Pedestrian wind speed ratio hit rate at z/b = 0.125: q >= 0.66.
- B. Reattachment lengths vs the benchmark table (Section 7).

For standard k-epsilon (step 1) "success" means landing in the published
family, NOT beating the experiment.

## 2. Scale and geometry
Wind-tunnel (model) scale: b = 0.08 m, h = 2b = 0.16 m. Building centred on the
origin in plan (x,y in [-0.04, +0.04]), base at z=0, top at z=0.16. Re_b ~
2.4e4 > critical -> Reynolds-independent, ratios scale-free. Wind along +x
(direction 270). Build via geometry.extrude_footprint + write_binary; bbox
0.08 x 0.08 x 0.16.

## 3. STRICT vs FLEXIBLE (from AIJ 2.1.5 sensitivity study)
STRICT (high impact on the result):
- Inflow k(z) profile — must be the measured profile. Wrong k breaks it badly.
- Floor roughness — rough-wall log law, z0 = 1.8e-4 m.
- Advection scheme — QUICK / 2nd-order bounded. No pure first-order upwind.
- Convergence — tight. Benchmark used STED = 1e-6 (eq 2.1.7). Drive residuals
  ~1e-5..1e-6 and confirm probe stationarity.

FLEXIBLE (AIJ showed near-zero impact):
- Domain size — compact (11b x 5.56b x 4.35b) ~ basic (21b x 13.75b x 11.25b).
  Keep outlet well past x/b=3.25.
- Top/side BC — tunnel walls ~ free/symmetry. Use symmetry on sides + top.
- Inflow eps form — eps = Cmu^.5 k dU/dz ~ Richards-Hoxey. Use the former.
- Upper-region inflow profile — negligible.

## 4. Boundary conditions
- Building walls: smooth-wall log law.
- Side + top: symmetry.
- Floor: rough-wall log law, z0 = 1.8e-4 m (atmNutkWallFunction with z0).
- Inflow: tabulated measured U(z), k(z) (profile ~ z^0.27), eps(z) = Cmu^(1/2)
  k(z) dU/dz.
- Outflow: zero-gradient.

## 5. Mesh
snappyHexMesh + surface (prism) layers is sanctioned (AIJ 2.1.7).
- Target facade cell ~ b/14; roof ~ b/20 (grid-converged per 2.1.5.2).
- A few prism/inflation layers at the building walls.
- Use core/mesh.py with target_facade_cell = b/14.

## 6. Numerics and model
- Solver: foamRun -solver incompressibleFluid (OpenFOAM 13), steady RANS.
- Convection: QUICK / linearUpwind (2nd order).
- Turbulence (parameter): step 1 standard k-epsilon (reproduce KE1-KE5 base).
- Baseline (recommended): **k-omega SST** — best reattachment of the OF13
  Foundation models actually tested (X_F/b=1.00; see VALIDATION_RESULTS.md).
  Realizable k-epsilon was tested but is NOT recommended (q=0.183, worse than
  base; no production limiter, so it does not cure the stagnation-k anomaly).
  Reproducing the AIJ "modified k-eps" family would need a production-limited
  model (Kato-Launder / MMK / Durbin), absent in OF13 Foundation by default.

## 7. Reattachment-length validation (AIJ Table 2-1-3)
Extract by linear interpolation to the sign reversal of the wall-adjacent
streamwise velocity:
- X_R : reattachment length on the roof.
- X_F : reattachment length behind the building (floor).
Report X_R/b, X_F/b. Targets:
- Experiment:                 X_R/b = 0.52   X_F/b = 1.42
- Standard k-eps (KE1-KE5):   X_R = none     X_F = 1.98-2.70
- Modified k-eps:             X_R = 0.52-0.87 X_F = 2.70-3.34
- DSM:                        X_R > 1.0      X_F = 4.22
- LES:                        X_R = 0.92     X_F = 2.05

Pass step 1 (std k-eps): no roof reverse flow (X_R absent) AND X_F ~ 2.0-2.7.
Tested result (OF13): X_R none (correct), X_F/b ~ 0.6-1.0 across kEpsilon /
realizableKE / kOmegaSST — all under the family; kOmegaSST closest (1.00). The
short bubble is the genuine model solution (mesh-refinement makes it shorter),
driven by the std-k-eps stagnation-k over-production. See VALIDATION_RESULTS.md.

## 8. Comparison quantity and normalisation
Pedestrian wind speed ratio = local scalar speed / inflow speed at same height.
At z/b = 0.125 the reference speed is **2.935 m/s** (Meng & Hibi Table 1, the
primary source; the AIJ guidebook text rounds this to 2.75). For z/b = 1.25 use
4.021 m/s (Table 1). Quantity = horizontal speed sqrt(U^2+V^2) (AIJ near-ground
convention) -> compare ratio_horizontal.
CFD side: ratio(point) = speed_CFD(point) / U_inflow_CFD(z_of_plane).

**Normalisation for the milestone (strict):** the Case A Level-1 milestone is
q >= 0.66 on the DIRECT normalisation by the tabulated incident u_ref(z) from
Table 1 (2.935 at z/b=0.125). This requires the CFD incident profile to be
maintained (~2.935 at the building). Normalising CFD by its own building-free
incident U(x) is a valid FALLBACK method (equivalent to how the experiment
normalised by the maintained tunnel incident) and is reported, but it is NOT the
milestone metric.

## 9. Measurement points
- Vertical centre plane (y/b=0): 66 points.
  x/b: -0.75,-0.5,-0.25,0,0.5,0.75,1.25,2,3.25 ;
  z/b: 0.125,0.5,1,1.5,1.75,2,2.125,2.375,2.75,3.5
- Horizontal z/b=0.125 (PRIMARY): 60 points.
- Horizontal z/b=1.25 (secondary): 60 points.
  Both: x/b as above; y/b: 0,-0.25,-0.5,-0.625,-0.875,-1.125,-1.5,-2
- Symmetry: only y <= 0 measured; probe CFD at measured points (or mirror).
- Coordinates in metres = normalised * b (b = 0.08).

## 10. Metrics (tests/aij/metrics.py)
q, FAC2, NMSE, FB, R as defined in metrics.py (D=0.25, W=0.06).

## 11. reference_data.json schema (actual — Meng & Hibi 1998, Tables 1-4)
```
{
  "case": "A", "b": 0.08, "h": 0.16, "wind_direction_deg": 270,
  "reynolds_number": 24000.0,
  "u_ref": { "z_over_b_0125": 2.935, "z_over_b_125": 4.021 },
  "reattachment_targets": { "experiment": {...}, "per_case": {KE1..LES} },
  "inflow_profile": { "points": [ {"z_over_b":.., "z":.., "u":.., "k":..}, ... ] },  // 24 levels, measured k
  "pedestrian_ratios_z0125": { "points": [
      {"id":1,"x_over_b":..,"y_over_b":..,"x":..,"y":..,"z":0.01,
       "U":..,"V":..,"W":..,"speed_horizontal":..,"ratio_horizontal":..,"speed_3d":..,"ratio_3d":..}, ... ] },  // 60
  "secondary_ratios_z125": { "points": [ ...60... ] },
  "vertical_y0": { "points": [ {"id":1,"U":..,"V":..,"W":..,"speed_3d":..}, ... ] }  // 66, coords pending
}
```
Coordinates in metres. ratio_horizontal = sqrt(U^2+V^2)/u_ref (milestone
quantity); ratio_3d = |U|/u_ref. Inflow k is the measured 0.5*(su^2+sv^2+sw^2);
eps for the inlet is derived (inlet.py). The §11 placeholder (u=2.75, k=0.30,
flat vertical/horizontal arrays) is superseded by this real structure.

## 12. Harness layout
```
tests/aij/
  metrics.py / test_metrics.py
  case_a/
    SPEC.md
    geometry.py    # 0.08x0.08x0.16 box -> STL
    conditions.py  # domain, BCs, mesh targets, scheme, model
    inlet.py       # tabulated U(z),k(z) -> field + eps=Cmu^.5 k dU/dz
    reattachment.py# extract X_R, X_F from the field
    reference.py   # loader/validator for reference_data.json
    reference_data.json
    test_case_a.py
    run_validation.py
```
run_validation: build STL -> assemble case (conditions + tabulated inlet) ->
solve -> probe pedestrian points (primary) -> q/FAC2/NMSE/FB/R -> extract
X_R,X_F -> PASS/FAIL. Write manifest.json (provenance).

## 13. Build order
1. metrics.py + test (pure math).
2. geometry.py + bbox test.
3. conditions/inlet/reattachment/reference + placeholder json + tests.
4. run_validation.py wiring; full run needs case/solver/post + real data.
Commit 1-3 once green (no OpenFOAM). Step 4 results analysed off-repo.

## 14. Expected discrepancies (AIJ figures, not bugs)
- Standard k-eps: overestimates k at the upwind roof corner -> no roof reverse
  flow -> X_R absent. Modified models reproduce it but over-predict X_F.
- Wake (x/b > 0.5, y/b ~ 0): U under-predicted; X_F over-predicted by all RANS.
- z/b=1.25 plane: side velocity too gradual vs experiment.
- z/b=0.125 (pedestrian): good agreement; this is the primary hit-rate target.
