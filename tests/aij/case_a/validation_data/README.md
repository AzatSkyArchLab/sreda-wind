# Case A validation data exports (for plotting)

Numeric exports from the converged OpenFOAM 13 runs (2000 it), for external
plotting. All values are real, sampled from the solved fields. Reproduced from
the cases regenerated via `conditions.case_a_inputs` (kEpsilon = base, kOmegaSST
= recommended baseline). Source experiment: Meng & Hibi (1998).

Sampling: `cellPoint` interpolation for the point/line comparisons (matches
`run_validation.py`), so q_direct/X_F here reproduce VALIDATION_RESULTS.md
(kEpsilon q_direct=0.533, X_F/b=0.76; kOmegaSST X_F/b=1.00). `incident_fetch`
uses cell-centre values (true field, avoids near-wall interpolation artefacts).

## Files
- `pedestrian_z0125_kepsilon.csv`, `pedestrian_z0125_komega.csv` — 60 pedestrian
  points (z/b=0.125). `ratio_direct` = speed_h_cfd/2.935 (milestone normalization);
  `ratio_incident` = speed_h_cfd/`incident_local`; `incident_local` = the CFD
  building-free-equivalent incident speed at that point's x, sampled at the far-
  lateral column y/b=-5 (undisturbed), z/b=0.125. `*_exp` columns are the
  measured Meng & Hibi values from reference_data.json.
- `incident_fetch.csv` — building-free run (caseA_empty): near-ground U and k at
  z/b=0.125 along the fetch, showing the +40% incident drift (and the k runaway
  inside the refinement box). `ratio_vs_2935` = U/2.935.
- `reattachment_floor.csv` — wall-adjacent (z=0.002) streamwise Ux along the
  centreline (y=0) behind the building, both models. X_F is the first
  negative->positive sign change (kEpsilon ~0.76 b, kOmegaSST ~1.00 b).
- `wake_profile_xb2.csv` — vertical streamwise-U profile at x/b=2, y=0, both
  models. `U_exp` is intentionally EMPTY: the experimental vertical plane
  (Table 2) has no per-id (x,z) coordinate mapping yet, so no honest exp value.
- `summary_metrics.csv` — per model: X_R, X_F, q_direct (/2.935), q_incident
  (/building-free incident), FAC2, NMSE, FB, R. FAC2/NMSE/FB/R are computed on
  the INCIDENT normalization (the physically meaningful comparison; R is
  scale-invariant so identical under either normalization).

Units: lengths normalised by b=0.08 m where `*_over_b`; velocities in m/s.
