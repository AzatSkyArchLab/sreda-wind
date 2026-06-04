# AIJ Case A — validation results (sreda-wind, OpenFOAM 13)

First end-to-end validation of the isolated 1:1:2 building against Meng & Hibi
(1998). Model scale b=0.08, h=0.16; measured inflow (Table 1), 60 pedestrian
points (Table 3). All runs: tabulated inflow (real measured U, k), rough floor
(z0=1.8e-4, nutkAtmRoughWallFunction), symmetry sides/top, snappyHexMesh +
prism layers, steady RANS, 2nd-order convection, residualControl 1e-6, ~converged.

Reproduce: `python tests/aij/case_a/run_validation.py <case>` (needs a solved case).

## Model / mesh comparison

| run | turbulence | wake mesh | X_R/b | X_F/b | q (naive /u_ref) | FB | R |
|-----|-----------|-----------|-------|-------|------------------|----|----|
| experiment (Meng & Hibi) | — | — | 0.52 | 1.42 | — | — | — |
| AIJ std k-eps (KE1–KE5) | k-eps | — | none | 1.98–2.70 | — | — | — |
| base | kEpsilon | b/8 | none | 0.76 | 0.533 | −0.26 | 0.85 |
| wake-refined | kEpsilon | b/16 | none | 0.63 | 0.550 | −0.27 | 0.83 |
| realizableKE | realizableKE | b/8 | none | 0.72 | 0.183 | −0.42 | 0.80 |
| **kOmegaSST** | k-ω SST | b/8 | none | **1.00** | 0.367 | −0.33 | 0.86 |

## Two independent findings

### 1. Reattachment X_F (wake) — model dependent
No model reaches the AIJ std-k-eps family (X_F/b ~2). **k-ω SST is closest
(1.00)**, k-eps shortest (0.6–0.8). Single-variable elimination ruled out mesh:
refining the wake (b/8→b/16) made X_F *shorter* (0.76→0.63), not longer — so the
short bubble is the genuine model solution, not numerical diffusion. The driver
is the standard-k-eps stagnation k over-production (k spikes ~50 at the windward
face vs inlet ~0.4), over-mixing the wake; realizableKE does not cap production
(worse), k-ω SST's νt limiter helps most. Reproducing AIJ's exact std-k-eps X_F
would need a production-limited model (Kato–Launder / MMK / Durbin), not in OF13
Foundation by default. No roof reattachment (X_R none) is correct for these
models per AIJ.

### 2. Pedestrian hit rate q — normalization / inflow
Naive normalization by the measured u_ref (2.935) gives q=0.53 with a systematic
positive speed bias (FB<0) even in near-freestream points. Cause (confirmed by a
building-free run): **the incident profile is not maintained** — near-ground U at
z/b=0.125 drifts from 2.94 (inlet) to ~4.1 along the fetch (+40%):

| x/b | −9.75 (inlet) | −5.0 | −2.5 | 0 (building) | +3.25 |
|-----|------|------|------|------|------|
| incident U @ z=0.01 (5H fetch) | 2.36 | 3.36 | 3.89 | 4.12 | 4.24 |

Single-variable tests (all building-free): shorter fetch 5H→2H reduced drift
(+40%→+25%) but did not remove it; inlet ε from measured −u'w' (P=ε balance)
changed the failure mode but not the drift; advection scheme (limitedLinear vs
upwind) — no effect; **removing floor prism layers — no effect (1.25→1.23)**.
Per the strict test, the floor-prism / wall-function hypothesis is REJECTED
(drift persists without prisms). The cause is the **non-equilibrium measured
profile not self-sustaining under a high-Re RANS wall function — a known
RANS-ABL limitation, not a pipeline defect.**

**Resolution — honest normalization.** Normalise CFD by its own building-free
incident U(x) at the same height (exactly how the experiment normalised by the
maintained tunnel incident, Table 1):

| normalization | q | FAC2 | NMSE | FB | R |
|---------------|---|------|------|----|----|
| /2.935 (naive) | 0.533 | 0.867 | 0.114 | −0.256 | 0.850 |
| **/building-free incident(x)** | **0.700** | 0.883 | 0.087 | +0.088 | 0.849 |

**q = 0.70 on the building-free-incident (FALLBACK) normalization — passes the
0.66 threshold; FB ≈ 0.** This shows the building-induced perturbation field
matches the experiment. It is NOT the milestone pass: the Case A Level-1
milestone is q ≥ 0.66 on the DIRECT normalization by u_ref=2.935, which gives
q = 0.533 (does not pass) because the incident profile drifts +40%.

**Precursor attempt (to earn the direct-normalization pass) — known WIP, not
converged.** A streamwise-cyclic rough-channel precursor (meanVelocityForce,
same z0/model/wall-function) was built and tuned (Ubar=5.72) to a self-sustaining
profile with U(z/b=0.125)≈2.93 and healthy k≈0.31. It was then run on a
near-ground z-mesh IDENTICAL to the main domain (structured blockMesh nz=50,
grading 12, no adaptive box) to remove the earlier mesh-mismatch. Results
(criterion: incident ratio ≤ 1.05 at x/b=-0.75 on /2.935):
- matched-mesh main, precursor table inlet, force-free: ratio 1.086 (FAIL),
  rising to 1.46 downstream.
- + meanVelocityForce in the main domain: ratio 1.137 (FAIL).

Root cause (RANS physics, not a pipeline bug): the measured Meng & Hibi profile
is a NON-EQUILIBRIUM wind-tunnel BL (power-law U, varying k). In a force-free
RANS domain only the zero-pressure-gradient equilibrium self-sustains
(Richards & Hoxey: log U, k=u*^2/sqrt(Cmu) const, eps=u*^3/(kappa(z+z0))). The
measured profile is not that equilibrium, so its k decays -> nut->0 -> the
near-ground accelerates -> drift. The cyclic precursor's profile is balanced by
a body force; that balance does not transfer to the force-free building domain,
and importing the force distorts the building flow. Maintaining exactly the
measured profile on /2.935 in standard force-free RANS is therefore not
achievable; only an RH-type equilibrium self-sustains (different profile shape,
explicitly out of scope for Case A). 4 precursor runs spent; stopped per plan.

### y+ on the floor (first cell), with vs without prisms
Direct test of the wall-function hypothesis (yPlus function object, ground patch):

| floor y+ | median | min | p90 | max | regime |
|----------|--------|-----|-----|-----|--------|
| with prisms | 91 | 19 | 101 | 567 | in log layer (30–150) ✓ |
| no prisms | 435 | 75 | 486 | 3896 | above log layer ✗ |

The result is the *opposite* of the initial guess: prisms give y+≈91 (valid log
layer), removing them gives y+≈435 (too coarse). Yet the incident drift is the
same in both (1.25 vs 1.23). All three conditions for the wall-function
hypothesis fail (prisms y+ is NOT out of range; drift does NOT disappear without
prisms) → **hypothesis rejected**: the drift is independent of the y+ regime,
confirming the non-equilibrium-profile cause. Prisms are kept (better floor y+;
needed on the building for X_R/X_F).

## Status: primary validation passed; /2.935 milestone NOT met (best q_direct=0.650 via forced relaxation — engineering workaround); Case A CLOSED

**PROVEN.** The pipeline runs end-to-end and the building aerodynamics are
captured: pedestrian hit rate q = 0.70 on the (fallback) incident normalization
with FB ≈ 0 and R ≈ 0.85 — the building-induced perturbation field matches the
experiment; correct qualitative behaviour (no roof reattachment, wake
recirculation present). k-omega SST is the best-tested baseline (X_F/b = 1.00).

**OPEN — milestone NOT met (best q_direct = 0.650).** The Case A Level-1
milestone (q ≥ 0.66 on DIRECT normalization by u_ref = 2.935) was pursued to its
end. On the structured mesh + equilibrium atm inlet (canonical), q_direct = 0.467
(kEps) / 0.433 (kOmega) — the incident drifts because the ABL does not
self-sustain under high-Re RANS (precursor, σε=1.167, fixed top, const ground k
all failed; the near-ground k runs away in the cells above the first).

**Hargreaves–Wright + Parente attempts.** HW coefficient/BC consistency
(σε=1.167, fixed atm top, const ground k) reduced but did not stop the drift
(held to x/b=-2.5 at ratio 1.04, then 1.23 at the building). The final attempt
implemented **Parente (2011) source terms** as a forced relaxation of k and ε
(or ω) toward the RH equilibrium in the approach zone (x < -0.04) via a
codedFvModel. Building-free this maintains the profile exactly (k = 0.298 const,
incident ratio 1.009 at x/b=-0.75 ≤ 1.05). With the building, q_direct rose to
**0.650 (kEps)** / 0.533 (kOmega) — kEps is just under 0.66. Full kEps metrics
(incident norm): FAC2 0.883, NMSE 0.065, FB +0.001, R 0.855 — comparable/better
than the unforced structured run.

**Honest framing — this is an engineering workaround, not model
self-sustainment.** The profile is held by a *forced* source-relaxation in the
approach (a fringe/nudging zone), not by the turbulence model maintaining the
ABL. The forcing also alters the building physics: it imposes a lower-k inflow,
so X_F jumps (0.72 → 1.71 kEps; → 2.03 kOmega, which even gains a roof
reattachment X_R = 0.96) — these are consequences of the imposed low-k approach,
not pure model improvement. The residual gap (0.650 vs 0.66) is the far-wake
background drift: the relaxation is off behind the box, so the un-forced wake
(x/b = 2–3.25, mid-lateral) over-predicts by +0.3…+0.45 (e.g. pt 56: CFD 1.06
vs exp 0.62). Per the plan this was the final inflow attempt; **Case A is closed
here regardless of outcome.** Data: incident_fetch_parente.csv,
pedestrian_z0125_{kepsilon,komega}_parente.csv, summary_metrics_parente.csv.

Two documented model/methodology characteristics (not bugs): (a) wake X_F is
under-predicted by all OF13-Foundation RANS without a production limiter
(k-omega SST closest, X_F/b=1.00); (b) the non-equilibrium ABL is not maintained
under high-Re RANS — building-free incident normalization is a valid fallback for
reporting q, but the milestone is on direct /u_ref. Numbers above reproduce via
run_validation.py; raw cases regenerate from conditions.case_a_inputs.
