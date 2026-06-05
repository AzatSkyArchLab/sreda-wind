# AIJ Case B — validation spec for sreda-wind (v1)

Spec for `tests/aij/case_b/`. Read with repo-root `CLAUDE.md` and
`case_a/SPEC.md` (shared method). Conventions: English comments, no list
comprehensions, layer-by-layer commits, `pytest -q` green before commit.

Case B is the AIJ 4:4:1 **thin tall plate** in an atmospheric boundary layer.
Reference data: `validation_data/caseB_data.json` (copy of the AIJ xls). Read it
programmatically (`json.load`) — never hardcode. Integrity verified on disk:
pedestrian_section 115 points, vertical_section 109 points, inflow_profile 12
levels.

Carries forward the Case A closure lessons (see VALIDATION_RESULTS.md):
- domain is an explicit per-case tunnel geometry (no COST 732 sizing);
- the convergence protocol is mandatory: **equilibrium seed (generator-enforced)
  → monitor probe → take q ONLY after the probe freezes**; if a limit cycle,
  window-average + uncertainty band (`solver.convergence.window_stat`), never a
  single snapshot.

## 1. Goal and acceptance
Pedestrian wind-speed-ratio hit rate at z/b = 0.25 (z = 12.5 mm), 115 points:
q >= 0.66 (AIJ / COST 732). Report q, FAC2, NMSE, FB, R, both normalisations
(§8). For standard k-epsilon "success" = landing in the published family, not
beating experiment. Given Case A, expect std k-ε to be marginal and possibly
under-performing on this strongly separated bluff plate.

## 2. Scale and geometry — orientation RESOLVED from data
Model scale, b = 0.05 m (50 mm), H = 4b = 0.20 m (200 mm). Wind along +x.
The "4:4:1" plate is **broadside to the wind**: the wide 200 mm face is
across-wind.

Building footprint (centred on origin in plan, base at z = 0):
- across-wind width (y): 200 mm = 4b  -> y in [-0.10, +0.10] m
- along-wind depth  (x):  50 mm = 1b  -> x in [-0.025, +0.025] m
- height            (z): 200 mm = 4b  -> z in [0, 0.20] m

**Orientation evidence (programmatic, from caseB_data.json pedestrian section):**
the measurement grid skips the footprint, so the blocked region maps the body.

| x_mm | min |y| measured | interpretation |
|------|------------------|----------------|
| -75  | 0   | clear (y=0 measured, upstream recirc U=-0.98) |
| -25  | 110 | BLOCKED for \|y\|<110 -> body |
|  0   | 110 | BLOCKED -> body |
| +25  | 110 | BLOCKED -> body |
| +50  | 0   | clear (y=0 measured, wake U=-0.70) |

y=0 pedestrian points exist only at x = -75, 50, 100, 200, 300, 400, 550 —
never at x = -25/0/+25. So the body spans x in [-25, +25] (depth 1b) and, since
the nearest measured |y| at x=0 is 110 mm (just outside a 100 mm face), the
across-wind half-width is ~100 mm (width 4b). The alternative orientation
(50 mm across-wind / 200 mm along-wind) is REJECTED: x=-75 and x=+50 have y=0
points (so along-wind extent != 200 mm), and |y|<100 is unmeasured at x=0 (so
across-wind width != 50 mm). The vertical y=0 section confirms H: at x=+50 the
streamwise U reverses below z=200 mm (wake), free stream above.

Residual check (nice-to-have, not blocking): confirm against the AIJ schematic;
the data determination above is unambiguous.

bbox = 0.05 (x) x 0.20 (y) x 0.20 (z) m. Build via geometry.extrude_footprint +
write_binary, as Case A.

## 3. Reference velocity — RESOLVED: U_H = 5.133 m/s
The experimental `ratio_UH` column normalises by U_H = 5.133 m/s = the inflow U
at building height H = 200 mm (z/b = 4), read from inflow_profile (z=200 -> U=
5.133). This is the AIJ Case B convention. The pedestrian-level inflow U
(~3.114 m/s interpolated at z=12.5) is NOT the reference — recording it only
avoids the Case A 2.935-vs-2.75 ambiguity.

Note the reference height (z=200) is well ABOVE ground, unlike Case A's
near-ground z/b=0.125 reference; the incident-drift problem that forced Case A's
fallback normalisation is far weaker here. Still verify (below).

## 4. Normalisation — primary DIRECT /U_H; incident-local as a guarded fallback
- PRIMARY (milestone): q on DIRECT normalisation, ratio = sqrt(U^2+V^2) / U_H,
  U_H = 5.133 (CFD vs exp both /5.133). Horizontal speed (AIJ near-ground convention).
- GUARD (Case A lesson): from a building-free run, confirm the CFD maintains
  U(z=200) ~ 5.133 along the fetch. If it drifts > ~5%, also report the
  incident-local normalisation (CFD by its own building-free U at the reference).
  Expected to matter little (reference is high up), but must be checked, not assumed.

## 5. Domain — PROPOSED FULL-span tunnel box (OPEN: confirm vs AIJ schematic)
No COST 732 sizing. Built from the measurement span (x = -75..550,
y = -350..+350, z up to 1000 mm) + standard bluff-body margins. **FULL span in
y, NO symmetry plane** — see the caveat below.

Proposed extent [m]:
- x (streamwise): inlet -0.30 (-6b), outlet +1.00 (+20b). Measurements reach
  x/b=11 (0.55 m); the centreline wake reattaches near x≈0.40 (U->0 at point 90),
  so 20b leaves clear margin.
- y (cross-stream): FULL span y in [-0.50, +0.50] (±10b), both lateral patches
  symmetry/far-field. Measurements reach |y|/b = 7 (0.35 m).
- z (vertical): 0 to 1.00 (20b = 5H), the top of the measured inflow profile.

Blockage (full domain): frontal area = 0.20 (y) x 0.20 (z) = 0.04 m^2 over a
1.00 x 1.00 = 1.00 m^2 cross-section = **4.0%** (AIJ-acceptable).

WHY FULL SPAN (mandatory, not an optimisation): a y=0 symmetry plane would
forbid the anti-symmetric vortex shedding that a thin broadside plate produces.
That would FREEZE the monitor probe for a numerical (boundary) reason, not a
physical one — pre-deciding the convergence question that is the whole point of
Case B (§7). The 2x cell cost is required to let the wake shed if the physics
sheds. The body and the time-MEAN are symmetric, but the instantaneous /
limit-cycle field is not, and the steady solver must be free to express it.

OPEN QUESTION: confirm the exact AIJ Case B tunnel dimensions / blockage against
the source schematic; adjust inlet/outlet/lateral/top if the spec differs. The
domain is an explicit `core.box.Domain` parameter of the case (per Case A
closure), not a formula.

## 6. Boundary conditions and inlet
- Inlet: measured tabulated profile (AIJ 1/4 power law), inflow_profile 12 levels
  (z=5..1000 mm, U=2.865..7.84, k=0.376..0.106). Tabulated U(z), k(z);
  eps(z) = Cmu^(1/2) k dU/dz (as Case A `inlet.py`). This reproduces the AIJ
  Case B postановка. internalField SEED stays the generator's equilibrium k/ε
  (never an arbitrary high seed) — inlet profile and initial seed are separate.
- Floor: rough-wall log law. z0 = **3.1e-6 m (0.003 mm)** — DERIVED from the
  inflow (not an AIJ spec), and POORLY CONSTRAINED. The profile is power-law
  (U = U_H(z/z_H)^α, α = 0.19, R^2 = 0.96 over all 12 levels), NOT a log law, so a
  fitted log-z0 is window-dependent: z0 = 1e-6 (z<=20mm, R^2=0.99) / 3.1e-6
  (z<=50mm, R^2=0.96) / 1.9e-5 (z<=100mm, R^2=0.93). The inlet is TABULATED so z0
  does NOT set the inflow profile (that is imposed directly) — z0 only sets the
  floor wall shear, so the near-wall window (z<=50mm, the layer the wall function
  sees) is used: z0 = 3.1e-6 m, u* = 0.156. Flagged inflow-derived; revisit if
  the pedestrian q is biased. Recompute in conditions.py — do not hardcode.
- Side far walls (y = ±0.50) + top: symmetry/far-field. NO y=0 symmetry plane
  (§5). Building walls: smooth-wall log law.
- Outflow: zero-gradient (inletOutlet).

## 7. Numerics, model, convergence protocol (MANDATORY)
- Solver: foamRun -solver incompressibleFluid (OF13), steady RANS, 2nd-order
  bounded convection (linearUpwind), SIMPLE consistent.
- Turbulence (parameter): step 1 standard k-epsilon (physical equilibrium seed).
- CONVERGENCE GATE (baked in code): monitor probe(s) in the wake at pedestrian
  height; foamRun, then `RunResult.stationary` / `monitor_band` from
  `_monitor_stationarity`. Take q ONLY when the probe is FROZEN. If the probe
  oscillates (limit cycle), q = plateau-window average + band (`window_stat`),
  not a single snapshot.
- Expectation: a thin broadside plate sheds strongly. As in Case A, std k-ε may
  reach a fixed point by over-damping (then q is well defined); k-ω SST likely
  will NOT converge steady (URANS deferred to backlog). The full-span domain (no
  y=0 symmetry, §5) leaves the wake FREE to shed, so a frozen probe now means
  physics, not a boundary artefact — the honest convergence test.

## 8. Metrics
Reuse `tests/aij/metrics.py` (q, FAC2, NMSE, FB, R; D=0.25, W=0.06). Quantity =
horizontal speed ratio at the 115 pedestrian points. The 109-point y=0 vertical
section is a secondary qualitative check (separation height, wake), not the
headline q.

## 9. File-level tests (before any OF run)
Pure, no solver — exactly the checks that caught the COST 732 substitution and
the snappy mismatch in Case A:
- reference loader: `json.load(caseB_data.json)` returns 115 / 109 / 12; ratio_UH
  uses 5.133; geometry b=0.05, H=0.20.
- geometry: footprint bbox = 0.05 (x) x 0.20 (y) x 0.20 (z), centred; orientation
  (y-width 4b > x-depth 1b).
- domain: the `Domain` object equals the proposed extent.
- inlet: tabulated profile parses 12 levels; eps derived; monotone U(z).
- generated dicts (via the runner, mesh_type=structured): blockMeshDict extent +
  resolution; 0/ fields carry the tabulated inlet + symmetry planes; controlDict
  carries the monitor probes; manifest provenance.

## 10. Build order
1. reference.py loader + geometry.py + conditions.py (domain, inlet, settings) +
   tests — pure, green, commit (no OpenFOAM).
2. Runner RunConfig assembly; generate the case; SHOW blockMeshDict + 0/ fields +
   inlet BEFORE solving (operator review, as Case A).
3. First run: std k-ε, equilibrium seed; FIRST check probe freeze (do NOT read q
   until stationary). Show probe trajectory + residual level.
4. q + metrics only after confirmed stationarity (or window-average + band if a
   limit cycle). Compare to experiment on the normalisation fixed in §3-4.

## 11. Open questions tracker (resolve/flag before metrics)
- [RESOLVED] Plate orientation: wide 200 mm face across-wind (data, §2).
- [RESOLVED] Reference velocity: U_H = 5.133 at z=H (§3).
- [PRIMARY SET, VERIFY] Normalisation: direct /U_H; incident-local guard if the
  reference drifts (§4) — confirm from a building-free run.
- [RESOLVED-decision] Full-span Y domain, no y=0 symmetry, blockage 4.0% (§5).
- [OPEN] Exact domain extent vs AIJ Case B tunnel schematic (§5).
- [DERIVED from inflow, poorly constrained] Floor z0 = 3.1e-6 m (near-wall log
  fit z<=50mm, R^2=0.96); profile is power-law so z0 is window-dependent; inlet is
  tabulated so z0 only sets floor shear; not an AIJ value (§6).
