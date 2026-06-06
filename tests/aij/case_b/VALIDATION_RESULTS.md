# AIJ Case B — validation results (sreda-wind, OpenFOAM 13)

Thin tall **broadside plate**, 4:4:1, b = 0.05 m, H = 4b = 0.20 m. Wide face
(200 mm = 4b) across-wind, depth 50 mm = 1b along-wind (orientation RESOLVED from
the measurement grid, see SPEC.md §2). Wind along +x. Reference data:
`validation_data/caseB_data.json` (115 pedestrian points at z/b=0.25, 109-point
y=0 vertical, 12-level 1/4-power inflow). Read programmatically.

Run with the validated engine: explicit AIJ domain (no COST 732), structured
mesh + measured tabulated inlet, std k-ε, **equilibrium seed (generator-enforced)
+ monitor-probe stationarity gate** (the Case A convergence protocol).

## Status: CLOSED — std k-ε converges (steady) but q = 0.28 < 0.66 (AIJ),
## because it FAILS TO REPRODUCE the upstream recirculation in front of the
## broadside plate (proven by the sign of streamwise U at bound points). A
## qualitative steady-k-ε limit, NOT cured by any k-ε variant (Phase-1 matrix).

## Result
| metric | value |
|--------|-------|
| q_direct (/U_H = 5.133), 115 pts | **0.278** (narrow domain 0.261) |
| q_incident (/building-free at z=200) | 0.278 (= q_direct; reference stable) |
| FAC2 / NMSE / FB / R | 0.765 / 0.168 / **−0.204** / **0.845** |

q far below the AIJ 0.66 target. The signature is a clean systematic positive
speed bias (FB < 0) at high R (0.845) — pattern correct, magnitudes shifted up.

## Convergence — a genuine steady fixed point (full domain, no symmetry)
The lateral domain is FULL span (±30b, no y=0 symmetry plane) precisely so the
wake is free to shed; a symmetry plane would force a false freeze. Even so, std
k-ε froze: monitor probes (incl. two off-centre ±0.05y to catch anti-symmetric
shedding) reach a fixed point with last-200 half-band ~2e-6 and abs fluctuation
~1e-6 (machine level, not 1e-3 incipient shedding). p residual plateaus ~5e-4
(local artefact); the field is steady. Over-damping, as in Case A.

## Diagnosis — model physics, NOT setup (single-variable elimination)
1. **Reference velocity confirmed from the DATA.** X = |Uh|_exp / ratio_UH_exp
   over all 115 points = 5.133 ± 0.0013 (constant). The experiment normalised by
   U_H = 5.133 (inflow at building height); so does the CFD. The +24% shift is
   NOT a wrong denominator.
2. **Incident is correct.** Building-free inlet U = 3.114 at z=12.5 / 5.126 at
   z=200 = the imposed values. Building-free far-lateral ratio = 0.657 = the
   experiment far-lateral 0.656. The pedestrian incident drifts +13.7% along the
   fetch (RANS-ABL non-equilibrium, weaker than Case A's +40% because the
   reference is high up), but the building-height reference is stable (<1% drift),
   so q_incident = q_direct.
3. **Lateral blockage REJECTED by experiment.** Widening the domain ×3 (±10b →
   ±30b, frontal blockage 4.0% → 1.33%) barely moved q (0.261 → 0.278) or the
   far-lateral bias (+0.216 → +0.206). The far-lateral over-acceleration is
   domain-width INDEPENDENT (+26% narrow vs building-free, +31% wide) — not
   confinement.
4. **Error localised to the front/sides, NOT the wake.** Bias (ratio_cfd −
   ratio_exp) by zone: far-lateral +0.206, upstream +0.142, side +0.099,
   near-wake +0.028, far-wake +0.021. The opposite of a "bad wake" signature.
5. **Mechanism — DIRECTLY PROVEN by the sign of streamwise U: a MISSED upstream
   recirculation.** Signed U(y) at x = −75 mm, z = 12.5 mm, sampled at the exact
   measured coordinates (binding verified), wind along +x so U < 0 = reverse
   flow:

   | pt no | (x,y) mm | exp U | std k-ε U | RNG U | sign exp/std/RNG |
   |-------|----------|-------|-----------|-------|------------------|
   | 1 | (−75, 0) | **−0.98** | +0.40 | **−0.44** | REV / fwd / REV |
   | 2 | (−75,−25) | **−0.87** | +0.46 | **−0.38** | REV / fwd / REV |
   | 3 | (−75,−50) | **−0.78** | +0.65 | **−0.18** | REV / fwd / REV |
   | 4 | (−75,−76) | **−0.49** | +1.04 | +0.24 | REV / fwd / fwd |
   | 5 | (−75,−100) | **−0.02** | +1.64 | +0.92 | REV / fwd / fwd |

   The experiment has a standing **upstream recirculation** (reverse flow, U < 0
   on points 1–5, to U = −0.98, with V converging inward — a horseshoe/standing
   vortex in front of the tall broadside plate). **std k-ε and realizable k-ε miss
   it entirely** (U > 0 at every point, attached diverging flow). **RNG recovers
   it only partially** (points 1–3). The "side jet" (Uh up to +22 % above the
   incident at y = −150…−250) is the **SYMPTOM** of this missed recirculation —
   the CFD sends the flow around the plate (attached, diverging) instead of into
   a front recirculation, so the side flow is too fast where the experiment is in
   a converging/recirculating zone.
6. **stagnation-k is elevated but is NOT the cause (yesterday's chain is
   RETRACTED).** Windward stagnation k IS over-produced (peak k ≈ 3.97 at
   z = 150 mm, ×6.7 the incident — a real fact). But the jet is **k_stag-
   INDEPENDENT**: RNG halves k_stag (×6.7 → ×3.0) yet the side-jet profile is
   unchanged (std peak 3.99 vs RNG 3.96, both +22 %, identical within ~2 % at
   every y). So the earlier causal chain "stagnation-k → jet → low q" is
   DISPROVEN — it mistook a correlation (high k_stag coincides with the jet) for
   causation. The driver is the missed recirculation (a separation/topology
   failure), which the stagnation-k suppression only *partly* relates to (lower
   k_stag in RNG → partial reverse-flow recovery, but insufficient).

## Conclusion
std k-ε on Case B is a genuine, reproducible STEADY solution that under-predicts
pedestrian comfort (q = 0.278), because it **fails to reproduce the upstream
recirculation** in front of the broadside plate — a **qualitative** error
(wrong sign of U, not a magnitude offset), proven at bound measurement points
(1–5). All setup causes were eliminated (reference X = 5.133 from data, incident
correct, lateral blockage rejected by ×3 widening, wake matches; §1–4).

**Not cured by switching k-ε variant** — the Phase-1 multi-model matrix
(PHASE1_MODEL_MATRIX.md) confirms: realizable k-ε q = 0.270, RNG k-ε q = 0.261,
k-ω SST 0.226 (snapshot). Lower k_stag did NOT raise q (it lowered it). A steady
RANS k-ε family cannot capture this front recirculation; the path is **URANS**
(the unsteady horseshoe/standing-vortex dynamics), deferred to backlog. (Note:
the SAME k-ε stagnation over-production is real on both cases, but Case A's q is
limited differently — see PHASE1_MODEL_MATRIX.md; do not over-generalise one
anomaly across geometries.)

Reproduce: domain Domain(-0.30,1.00,-1.50,1.50,0,1.00); structured base 0.01,
nz 50, grading 12, surface level 2, 4 building layers; measured tabulated inlet
(eps = Cmu^0.5 k dU/dz); z0 = 3.1e-6 (inflow near-wall fit, poorly constrained);
equilibrium seed; monitor probes; foamRun 4000; sample 115 pts at z=0.0125,
/5.133.
