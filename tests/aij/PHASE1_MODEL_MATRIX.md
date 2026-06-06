# Phase 1 — turbulence-model × AIJ-case characterization matrix

Honest, measured characterization of the OF13-Foundation RANS turbulence models
on the two closed AIJ cases (A: 1:1:2 cube; B: 4:4:1 broadside plate). Models
taken **AS-IS** (no coefficient tuning). Every cell is a real run under the same
protocol; nothing is filled by analogy. This file is the source for model briefs
in the UI — quote it, do not re-derive.

## Protocol (identical for every cell)
- Equilibrium turbulence seed (generator-enforced: k = u*²/√Cμ, ε/ω from it — an
  arbitrary high seed is impossible).
- Monitor probes (incl. two off-centre ±y to catch anti-symmetric shedding).
- q is read ONLY after the probe FREEZES (steady fixed point). If the probe is in
  a limit cycle, q would need a plateau-window average ± band — never a single
  snapshot (flagged where relevant below).
- Same structured mesh per case (base 0.01 m, nz 50, grading 12); same sampling.

## Matrix

| model | A converges? | A q | A k_stag | B converges? | B q | B k_stag |
|-------|--------------|-----|----------|--------------|-----|----------|
| **std kEpsilon** | YES, frozen (band 2e-6) | **0.617** | ×10.9 | YES, frozen (band 2e-6) | **0.278** | ×6.7 |
| **realizableKE** | YES, frozen (4e-6) | 0.617 | ×7.66 | YES, frozen (1e-6) | 0.270 | ×6.1 |
| **RNGkEpsilon** | YES (soft; ±y 1.3e-3→1.4e-4 over 2000→6000, q invariant) | **0.65** | ×4.42 | YES (frozen, band ×50 vs std) | 0.261 | ×3.0 |
| **kOmegaSST** | **NO** — limit cycle (probe ±125 %, p~0.10) | n/a | — | borderline (±y ~2e-2, p~4e-4; NOT like A) | 0.226 (snapshot) | ×2.34 |

- A q = q_incident (CFD normalised by its own building-free incident at the
  pedestrian plane, the Case A method). B q = q_direct = q_incident (= /U_H 5.133;
  the building-height reference is stable, <1 % drift). AIJ pass = q ≥ 0.66.
- k_stag = peak windward stagnation k / equilibrium incident k, on the SAME mesh,
  cellPoint, scanned a few mm upstream of the windward face (peak ~0.75 H). It is
  **mesh-sensitive** (finer mesh → sharper peak → higher ratio), so only the
  RELATIVE model ordering on one mesh is meaningful, not the absolute number. (An
  earlier "×100" for A was a different/finer mesh and is NOT comparable — discard.)

## Proven facts (measured, not assumed)

1. **k_stag does NOT control q.** Reducing the windward stagnation-k does not
   reliably improve the hit rate:
   - Case B: std ×6.7 → q 0.278; realizable ×6.1 → 0.270; RNG ×3.0 → 0.261;
     k-ω ×2.34 → 0.226. **Lower k_stag → WORSE q on B.**
   - Case A: RNG ×4.42 → q 0.65 (> std 0.617). **Lower k_stag → better q on A.**
   - A and B respond OPPOSITELY → the stagnation-k anomaly is a real fact but is
     NOT the single lever on pedestrian comfort. (This retracts the earlier Case B
     chain "stagnation-k → jet → low q", which confused correlation for causation.)

2. **Case B failure mechanism = a MISSED upstream recirculation (qualitative).**
   Proven by the SIGN of streamwise U at bound measurement points (x=−75 mm):
   experiment has reverse flow U < 0 on points 1–5 (to −0.98) — a standing
   horseshoe vortex in front of the broadside plate. std k-ε and realizable MISS
   it (U > 0 everywhere); RNG recovers it only partially (points 1–3). The "side
   jet" (+22 % over incident) is the SYMPTOM, and it is k_stag-INDEPENDENT (std
   peak 3.99 vs RNG 3.96 despite ×2 less k_stag). q = 0.278 is a qualitative
   steady-k-ε limit on a broadside body, not cured by any k-ε variant → URANS.

3. **Case A failure mechanism differs from B.** A's over-speed couples to k_stag
   (RNG's k_stag drop improved q 0.617 → 0.65). Do NOT over-generalise one
   anomaly across geometries — the cube and the plate fail for related but
   distinct reasons.

4. **RNG A q = 0.65 is REAL, not an under-convergence artefact.** Continued
   2000 → 6000: the probe ±y wobble tightened ×10 (1.3e-3 → 1.4e-4) while
   q_incident stayed exactly 0.65 (and q_direct 0.60). q was already converged at
   2000; tightening the field did not move it.

5. **k-ω SST does not give a usable steady answer here.** Case A: no convergence
   (sustained limit cycle, probe ±125 %, p residual ~0.10) — measured, not
   assumed. Case B: borderline (probe ±y ~2e-2, p~4e-4; did NOT blow up like A),
   q only as an unaveraged snapshot. k-ω resolves more of the real unsteadiness,
   so the STEADY solver cannot settle → the honest path for k-ω is URANS.

## AIJ pass status (q ≥ 0.66), this engine, steady RANS
- Case A: std/realizable 0.617 (fail), RNG 0.65 (near-miss), k-ω n/a.
- Case B: all variants 0.23–0.28 (fail).
- No steady OF13-Foundation k-ε/k-ω variant passes both as-is. The recurring
  limiters (stagnation-k over-production; missed front recirculation; genuine
  unsteadiness) point to URANS and/or a production-limited model
  (Kato–Launder / MMK / Durbin — absent in OF13 Foundation, implementable via a
  codedFvModel) as the next characterization phase. Backlog.

## Run directories (raw fields, this session)
- A: std /tmp/se_canon/canon · realizable /tmp/se_caseA_rke · RNG /tmp/se_caseA_rng (to 6000) · k-ω (earlier session)
- B: std /tmp/se_caseB_w · realizable /tmp/se_caseB_rke · RNG /tmp/se_caseB_rng · k-ω /tmp/se_caseB_kw · building-free /tmp/se_caseB_bf
