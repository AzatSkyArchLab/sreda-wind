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
- `incident_fetch.csv` — building-free run (caseA_empty), MEASURED Meng & Hibi
  inlet: near-ground U and k at z/b=0.125 along the fetch, showing the +40%
  incident drift (and the k runaway inside the refinement box). `ratio_vs_2935`
  = U/2.935.
- `incident_fetch_equilibrium.csv` — same mesh/domain as incident_fetch.csv (the
  adaptive box mesh), but with an EQUILIBRIUM Atmospheric-BL inlet
  (atmBoundaryLayerInletVelocity/K/Epsilon, Richards-Hoxey; Uref=2.935 @
  Zref=0.01, z0=1.8e-4). Result: it ALSO drifts to ~1.45 with the same k runaway
  -> on the box mesh the drift is caused by the MESH, not the inlet profile
  (measured and equilibrium behave identically). Fig-4 analog vs incident_fetch.
- `incident_fetch_equilibrium_cleanmesh.csv` — equilibrium Atmospheric-BL inlet
  on a CLEAN structured mesh (nz=50 grading 12, no adaptive box). Here k stays
  constant at 0.30 (self-sustaining, as RH intends) and U holds to ratio 1.02 at
  x/b=-2.5, but still creeps to ~1.10 at the building free column (x/b=-0.75) and
  runs up downstream. So the equilibrium inlet self-sustains FAR better than the
  measured profile, and the adaptive box mesh is the dominant drift cause; but a
  residual ~10% horizontal inhomogeneity remains (known RANS-ABL effect, needs
  Hargreaves-Wright wall-function consistency for <5%). The Step-1 criterion
  (ratio <= 1.05 at x/b=-0.75) is therefore NOT met; Step 2 (with-building, q on
  /2.935) was not run.
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

## Equilibrium-inlet with-building check (summary_metrics_equilibrium.csv)
Case A WITH building on a clean structured mesh (uniform near-ground z, no
adaptive box) + equilibrium Atmospheric-BL inlet, vs the box-mesh + measured-inlet
baseline. `incident_xb075` = incident ratio at the free column x/b=-0.75 (the
Step-1 criterion; <=1.05 means the profile is maintained).

Result: the structured mesh does NOT degrade the building flow (R, FAC2, X_F
comparable; NMSE and FB improved). But the incident still drifts to ~1.37 at the
building on the well-resolved mesh (the building-free 1.10 was a coarse-y,
under-resolved artefact). So the /2.935 milestone remains open: ABL
self-sustainment worsens with refinement and needs Hargreaves-Wright
wall-function consistency, not a mesh/inlet choice.
