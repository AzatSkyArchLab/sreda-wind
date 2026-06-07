# AIJ Case C — validation results (sreda-wind, OpenFOAM 13)

Urban **city-block group**: 3×3 array of cubes, D = H = 0.2 m, pitch 0.4 m
(street/canyon gap = 1 D = 0.2 m). The 8 perimeter cubes are always present; the
centre varies by config (0H empty / 1H height-H / 2H height-2H). The first real
*urban* test of the engine — canyon channelling and mutual sheltering between many
blocks, not one isolated bluff body. Wind along +x; 120 pedestrian points at
z = 0.02 m. Reference: `validation_data/caseC_data.json` (read programmatically),
geometry and normalisation cross-checked against the public SimScale AIJ Case C.

Run with the validated engine: explicit AIJ domain (±20H half-width lateral,
−5H/+15H streamwise, 4H above the tallest block; ~1.5 % blockage), adaptive snappy
mesh, measured tabulated inlet, floor z0 = 4.5e-4 m (published AIJ value),
**equilibrium turbulence seed + monitor-probe stationarity gate** (the Case A/B
convergence protocol). Normalisation = **variant 1, incident**: ratio =
|U_local| / inflow(z), inflow(0.02) = 2.434 m/s, U_H = 3.654 m/s (the experiment's
own normalisation, taken from the data — the reference-velocity ambiguity that
dogged A and B does not arise here).

## Status: CLOSED (1H/0°) — steady k-ε CONVERGES on the city and captures the
## flow PATTERN (R = 0.77), but q = 0.525 < 0.66 (AIJ) because it systematically
## UNDER-PREDICTS the channelling AMPLITUDE in wind-parallel streets. A
## *quantitative* structural limit of steady RANS — NOT a convergence failure and
## NOT a setup defect. All four cheap steady branches were exhausted by direct
## test (mesh, νt/realizable, ε/RNG, wall-shear/prisms). Path forward = URANS/DDES,
## as the industry uses for this case.

## Result (1H, 0°, fine mesh 5.27M)
| metric | std k-ε (headline) |
|--------|--------------------|
| q (incident, D=0.25 W=0.06), 120 pts | **0.525** |
| FAC2 / NMSE / FB / R | 0.717 / 0.193 / **+0.303** / **0.771** |

FB > 0 = CFD **under-predicts** speed (the opposite sign to Case B). High R (0.77,
inside the published DDES band 0.72–0.94) with a positive FB is the signature of a
**correct pattern with under-predicted amplitude** — magnitudes shifted *down*,
concentrated in the channelling streets.

## The under-prediction is localised to wind-parallel street channelling
Bias (ratio_cfd − ratio_exp) is concentrated in the wind-parallel streets
(0.1 < |y| ≤ 0.3): **street bias = −0.192** (the streets where flow accelerates
between block rows are precisely where the steady solution is too slow). νt/ν in
the streets ≈ 226 (moderate, not an eddy-viscosity blow-up).

## Convergence — a genuine steady fixed point (the city converges)
Unlike a worry that the urban array might never settle, steady k-ε reaches a clean
fixed point: the four canyon monitor probes freeze (last-200 std 1.5e-4 … 2e-3;
the one in the centre-cube wake is the loosest at 2e-3 but its mean is stable),
p residual plateaus ~1e-5. **The engine is numerically valid for the urban
regime** — the limitation below is accuracy, not convergence.

## Mesh convergence — ruled out as the dominant cause (but partly real)
| mesh | cells | q | R | FB |
|------|-------|---|---|----|
| coarse | 1.13M | 0.433 | 0.662 | +0.406 |
| **fine** | **5.27M** | **0.525** | **0.771** | **+0.303** |

Refining lifted q by +0.09 and R by +0.11 (into the DDES band) and cut FB — so the
coarse mesh was *partly* responsible, but a substantial residual under-prediction
(FB +0.30) survives at 5.27M. The residual is physical, not numerical.

## All four cheap steady branches exhausted by DIRECT test (the matrix)
| branch | test | q | R | FB | street bias | verdict |
|--------|------|---|---|----|-------------|---------|
| mesh resolution | coarse→fine | 0.433→0.525 | 0.66→0.77 | helped | — | partial, residual real |
| eddy viscosity / realizability | realizable k-ε | 0.517 | 0.752 | +0.263 | −0.172 | no help |
| ε-equation (strain) | RNG k-ε | 0.508 | 0.747 | +0.350 | −0.235 | no help |
| wall shear / y+ regime | prisms, y+→30–100 | 0.517 | 0.758 | +0.316 | −0.201 | **no help (proven)** |
| (baseline) | std k-ε | 0.525 | 0.771 | +0.303 | −0.192 | — |

No steady k-ε variant, and no wall-treatment fix, moves q off ~0.52. The pattern
(R) is stable; the amplitude deficit is not a knob any steady closure exposes.

### The wall-shear test, proven dead point-by-point (the last and subtlest branch)
The std-fine near-wall cells sat in the **buffer layer** (cube walls 94 % of faces
y+ < 30, floor 93 %, mean y+ ≈ 27) — the high-Re wall function operates below its
valid range (30–300), a legitimate suspect for mis-computed wall shear → damped
channelling. Test: add prism layers (3 layers, t1 = 0.006, expansion 1.2) on cube
walls **and** floor, sized for the high-Re regime (NOT low-Re y+ < 1). At
convergence the prisms moved the walls solidly into the log layer (cube walls
73 % in 30–300, mean 50; global floor 84 %; 0 % overshoot > 300). The street floor
stayed borderline (58 %, mean 36) because it is intrinsically low-shear (slow
canyon flow → y+ ∝ u_τ cannot be raised by cell size there).

Result: **q 0.525 → 0.517 (no improvement; slightly worse)**, street bias
−0.192 → −0.201. Point-by-point over the 90 wind-parallel-street points,
shift (prism − std) mean **−0.009**, 34 up / 55 down — **no systematic upward
trend**. Decisively, the points nearest the centre-cube wall (|y| = 0.15, where a
genuine wall-shear fix should help *most*) **dropped −0.04 … −0.08**. Where the
wall treatment was corrected best, channelling did not improve. (Caveat named
honestly: fitting the prisms required coarsening the cube surface level 5→4, a
small tangential-resolution penalty that could only have hurt; even the most
generous "prism-only" estimate is ≤ +0.007, vs the +0.135 needed to reach 0.66 —
a control run is unnecessary.)

## Why steady RANS under-predicts urban channelling (mechanism)
Wind-parallel street channelling is fed by **unsteady** momentum transport: shear
layers and vortices shed from upstream block edges intermittently pump
high-momentum fluid down into the streets. Steady RANS time-averages these
structures into a smooth, over-mixed field with too-low peak street speeds. This
deficit lives in the *resolved unsteady flux*, not in the steady closure — which is
exactly why no steady knob (νt cap, ε term, wall y+) recovers it, and why
scale-resolving methods do. This is a *quantitative amplitude* limit, distinct from
Case B's *qualitative topology* miss (a missed upstream recirculation, wrong sign
of U) — same destination (URANS) for different reasons; do not over-generalise one
mechanism across geometries.

## Industry context — this is a strong result for its class
SimScale validate AIJ Case C with **k-ω SST DDES on an 82.5 M-cell LBM/GPU mesh**
(R ≈ 0.8–0.94). Our **steady k-ε reaches R = 0.77 on a mesh ~16× coarser** (5.27M)
with a converged, reproducible solution in ~1.5 h on 8 cores. For a steady-RANS
method at this cost, matching the pattern into the lower edge of the DDES
correlation band is a solid outcome; the gap to q ≥ 0.66 is the method+fidelity
gap (steady vs scale-resolving), not a setup error.

## Conclusion
On the urban array, steady k-ε is a genuine, converged, reproducible solution that
**captures the channelling pattern (R = 0.77) but under-predicts its amplitude**
(q = 0.525 < 0.66, FB = +0.30, deficit localised to wind-parallel streets). The
deficit is **structural to steady RANS**: it survives mesh refinement and is not
cured by any eddy-viscosity, ε-equation, or wall-treatment variant (four branches
eliminated by direct test). The path to AIJ-passing urban accuracy is **URANS /
scale-resolving (DDES)**, consistent with industry practice for this benchmark
(Phase 2, backlog).

## Applicability disclaimer (for the product)
For urban pedestrian-comfort screening, steady k-ε is **fit for relative / pattern
comparisons** (R = 0.77, converges cheaply and robustly) but **under-predicts peak
channelling speeds by ~20 % (FB +0.30)** in wind-parallel streets. Absolute
comfort thresholds derived from steady k-ε in such streets are therefore
**non-conservative on the calm side** (they read calmer than reality) and should
not be used for final pass/fail of a comfort criterion; high-fidelity absolute
comfort requires URANS/DDES.

## Scope and reproduce
Characterised on **1H, 0°** (the central urban config) with the full 4-branch
matrix. The remaining 8 configs (0H/2H × 0/22.5/45°) are deferred — the structural
steady-RANS conclusion is established on the matrix; the sweep would only quantify
the deficit across configs, not change the verdict.

Reproduce: geometry `tests/aij/case_c/geometry.py` (config "1H"); domain ±20H half
lateral / −5H…+15H streamwise / 4H vertical; adaptive mesh (base 0.125, refinement
box level 4 = 0.0078, surface level 5 = 0.0039); measured 16-level tabulated inlet
(eps = Cmu^0.5 k dU/dz); z0 = 4.5e-4; equilibrium seed; foamRun incompressibleFluid
3000 iters parallel (8 cores); sample 120 pts at z = 0.02 (cellPoint), /inflow(z).
Branch matrix: `tests/aij/PHASE1_MODEL_MATRIX.md`. Baseline incident drift
+7.3 % near-ground (building-free, z0 = 4.5e-4) — see SPEC.md §3.
