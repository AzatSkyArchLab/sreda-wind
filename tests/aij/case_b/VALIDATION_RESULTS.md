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
## driven by a DIRECTLY MEASURED windward stagnation-k over-production.

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
5. **Mechanism — a non-physical lateral jet.** Lateral profile at x=−75
   (upstream): CFD over-decelerates the windward centreline (Uh 0.40 vs exp 0.99)
   and forms a side JET peaking at Uh 3.97 = +22% ABOVE the incident (3.26) at
   y = −150…−250; the experiment shows NO jet (Uh stays ≤ incident everywhere).
6. **Root cause DIRECTLY MEASURED — windward stagnation-k over-production.** k in
   the cells just upstream of the front face (y=0) vs the equilibrium incident k
   at the same height:

   | z_mm | k_stagnation | k_incident | ratio |
   |------|--------------|------------|-------|
   | 12.5 | 1.0–1.4 | 0.33 | ×3–4 |
   | 50 | 1.8–2.3 | 0.51 | ×3.5–4.4 |
   | 100 | 2.4–3.1 | 0.58 | ×4–5.3 |
   | 150 | **3.97 (peak)** | 0.58 | **×6.9** |

   k is amplified ×3–7 (peak ×6.9 at the upper windward face) — the standard-k-ε
   stagnation-k over-production, the SAME anomaly as Case A (there ×~100 on the
   cube; milder here on the plate, same mechanism). Elevated k → elevated νt →
   over-deflection of the approach flow → the non-physical side jet → far-lateral
   over-speed → low q. The chain is closed end-to-end by measurement, not assumed.

## Conclusion
std k-ε on Case B is a genuine, reproducible STEADY solution that under-predicts
pedestrian comfort (q = 0.28), driven by a measured windward stagnation-k
over-production — not a domain/normalisation/inlet artefact (all eliminated).
Consistent with Case A (q = 0.617): std k-ε's stagnation anomaly is the limiter
on bluff-body pedestrian wind. A production-limited model (Kato–Launder / MMK /
Durbin — not in OF13 Foundation) or URANS is the remedy; deferred to backlog.

Reproduce: domain Domain(-0.30,1.00,-1.50,1.50,0,1.00); structured base 0.01,
nz 50, grading 12, surface level 2, 4 building layers; measured tabulated inlet
(eps = Cmu^0.5 k dU/dz); z0 = 3.1e-6 (inflow near-wall fit, poorly constrained);
equilibrium seed; monitor probes; foamRun 4000; sample 115 pts at z=0.0125,
/5.133.
