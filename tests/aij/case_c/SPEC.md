# AIJ Case C — validation spec for sreda-wind (v1)

Spec for `tests/aij/case_c/`. Read with repo-root `CLAUDE.md`, `case_a/SPEC.md`
and `case_b/SPEC.md` (shared method). Conventions: English, no list
comprehensions, layer-by-layer commits, `pytest -q` green before commit.

Case C is the AIJ **city-block group**: 8 cubes in a 3×3 ring around a centre
that varies by config. The first real urban test of the engine — canyon physics
(mutual sheltering between blocks), not one isolated bluff body. Reference:
`validation_data/caseC_data.json` (read programmatically). Normalisation is
INCIDENT (local/inflow at the same height) — GIVEN by the experiment, so the
reference-velocity ambiguity that dogged A and B does NOT arise here.

## 1. Goal and the question
Pedestrian wind-speed ratio at z = 0.02 m, 120 canyon points, per config × wind
direction. AIJ pass q ≥ 0.66 (incident ratio, D=0.25, W=0.06). The decisive
question: **does steady k-ε pass on urban blocks (canyon/sheltering physics —
many short recirculations between blocks), or does it repeat Case B's failure
(missed recirculation)?** This determines whether the engine is valid for the
product (urban) scenario.

## 2. Geometry — CONFIRMED from the data (layout cross-checked)
Cube D = 0.2 m, H = D = 0.2 m (confirmed, AIJ Case C / SimScale). 3×3 grid, pitch
0.4 m, so cube centres at x,y ∈ {−0.4, 0, +0.4}; each cube spans ±0.1 about its
centre; street/canyon gap = 0.4 − 0.2 = 0.2 m (= 1 D). The **8 surrounding cubes**
(always present, all H): four corners (±0.4,±0.4) + four edge-mids (±0.4,0),
(0,±0.4). The **centre (0,0)** varies by config:
- **0H** — centre EMPTY (ring only, open courtyard).
- **1H** — centre cube H = 0.2 (same as the ring).
- **2H** — centre cube 2H = 0.4 (twice the ring height).

Group plan extent: x,y ∈ [−0.5, +0.5] → **1.0 × 1.0 m = 5D × 5D**.

Cross-check (programmatic, from caseC_data 0deg grid −0.30..0.30 step 0.05, 169
nodes, 120 measured): the 49 missing nodes are exactly the cube footprints — 4
corner inner-corners (±0.3,±0.3), 4 edge-mid inner faces (5 nodes each at x=±0.3
y∈[−0.1,0.1] and y=±0.3 x∈[−0.1,0.1]), and the 25-node centre cube (|x|,|y|≤0.1).
49 = 4 + 20 + 25. Layout matches the schematic description. Wind +x; directions
0 / 22.5 / 45° relative to the grid.

## 3. Reference and normalisation — RESOLVED FROM THE EXPERIMENT (variant 1)
Decided from the public SimScale AIJ Case C methodology, NOT from convenience
(the A/B reference-discipline): the velocity ratio is **local / the FIXED upstream
inflow profile value at the same height** (a single reference profile imposed at
the inlet) — quote: "normalized by the inflow velocity at the measurement height
of 0.1D … uses the upstream velocity profile established at the inlet boundary,
NOT a local building-free measurement at each spatial location."
- **HEADLINE METRIC = variant 1:** ratio(point) = |U_local| / inflow(z), where
  inflow(z) is the measured 16-level inlet profile value (e.g. 2.434 at z=0.02,
  3.654 at z=H=0.2). This is what the experiment used; it does NOT hide the RANS
  near-ground drift.
- **REJECTED: building-free-local** (|U_local| / CFD-building-free(x,y,z)). Using
  it as the metric would mask the engine's +7.3 % near-ground ABL drift and flatter
  the result — the same temptation as the A forced-relaxation, rejected.
- **DIAGNOSTIC ONLY (not the metric):** also report building-free-local q to
  SEPARATE the contributions — (variant-1 q) reflects model + residual drift;
  (building-free-local q) removes the drift; the difference ≈ the drift's share of
  the bias. This is "disentangle the mechanisms" (B-lesson), clearly labelled.
- Canonical reference U_H = 3.654 m/s at z = H = 0.2 m (for reporting).

**Baseline incident drift (measured, building-free, z0 = 4.5e-4):** the imposed
inflow does not perfectly self-sustain (it is not a pure log law, R² = 0.855), so
the near-ground incident drifts **+7.3 % at z = 0.02 at the group (x=0)** (≈+7 %
across the measurement region, +10 % far downstream) — HALVED from +18.7 % when
the floor z0 was wrong (7.3e-5). The y-profile is exactly uniform (building-free,
±20H, centre vs wall = −0.0 %). So a low Case C q would be MOSTLY a model result
(urban flow) with a residual ~+7 % drift contribution to acknowledge — never 100 %
model (B-lesson). Record this number for honest q interpretation.

## 4. Domain and blockage — DECISION NEEDED (B's lateral lesson)
AIJ nominal (caseC_data domain_aij_spec, Tominaga–Mochida/Franke): longitudinal
20H, lateral 10H, vertical 4H, blockage 0.5 %, mesh H/10 background + H/40 octree.

**Blockage, transparent arithmetic (total frontal area of ALL cubes — B lesson).**
Frontal y-z projection at 0° = **0.12 m² (1H) / 0.16 m² (2H)** (three 0.2-wide
y-strips at y = −0.4/0/+0.4). Convention made explicit: "NH HALF" = NH from group
CENTRE to each wall (full width 2·NH); height = 4H above the building = 1.00 m.
blockage = frontal / (width × height):

| domain (HALF) | width y [m] | height [m] | cross [m²] | blockage 1H |
|---------------|-------------|------------|------------|-------------|
| 10H | 4.0 | 1.0 | 4.0 | 3.00 % |
| **20H** | **8.0** | 1.0 | 8.0 | **1.50 %** |
| 40H | 16.0 | 1.0 | 16.0 | 0.75 % |

AIJ-nominal 10H → ~3 % (NOT 0.5 %); true <0.5 % needs ~50H+ lateral. Uniform H/10
over such a width is infeasible (~1500 cells in y).

**Decision (operator-approved): ±20H HALF (≈1.5 %), adaptive mesh.** Use an
adaptive (snappy) mesh — coarse far-field + refinement region ≈H/10 around the
group + surface octree ≈H/40 on the cube faces (engine `mesh_type="box"`), NOT a
uniform H/10 background, so the wide low-blockage domain is affordable. Extent:
lateral ±20H (±4 m), longitudinal −5H inlet … +15H outlet, vertical 4H above the
tallest block.

**Building-free verification DONE (±20H, z0 = 4.5e-4):** the empty-domain incident
is exactly y-uniform (centre vs +y wall = −0.0 % at every height) → the side walls
do not distort the incident; the domain setup is clean. (Caveat: an empty domain
is trivially y-uniform; the DEFINITIVE width test — whether the cubes' wake reaches
the ±4 m walls — is the with-cubes 1H/0° run: sample the flow at the lateral
boundary; if disturbed vs inflow, widen.) The building-free run also fixes the
incident-drift baseline (§3) and provides the diagnostic reference.

## 5. Mesh and sampling
Adaptive: coarse background base ~H/2; refinement region (box around the group +
canyons) to ≈ H/10 = 0.02 m; surface (prism + octree) on the cube faces to ≈
H/40 = 0.005 m; a few prism layers on the cubes and the floor. z = 0.02 m
(pedestrian) must sit in resolved near-ground cells. checkMesh after snappy.

**Sampling height (precision matters):** the pedestrian plane z = 0.02 m sits on
a STEEP part of the profile (building-free: z=0.01 −11 %, z=0.02 +7 %). Sample the
CFD at EXACTLY z = 0.02 m (cellPoint interpolation to the precise height), never
the nearest-cell-centre — on this gradient a floating height accrues a spurious
bias. The inflow reference inflow(0.02) is likewise the interpolated 16-level
value (2.434), not a nearest level.

## 6. Numerics, model, convergence protocol (MANDATORY — same as A/B)
- foamRun -solver incompressibleFluid, steady RANS, 2nd-order bounded convection,
  SIMPLE consistent. Turbulence (parameter): step-1 std k-ε.
- Equilibrium turbulence seed (generator-enforced). Inlet: tabulated measured
  inflow (16 levels), eps = Cmu^0.5 k dU/dz; inlet TKE k ≈ σ_u² (only σ_u given).
- Floor rough-wall **z0 = 4.5e-4 m** — the PUBLISHED AIJ Case C value (SimScale
  doc), not an inflow fit. (My near-wall fit gave 7.3e-5, ×6 too smooth, and gave
  +18.7 % drift; the published 4.5e-4 halves it to +7.3 %. Use the published value.)
- Sides/top: symmetry (far-field). Cube + floor walls: log-law.
- **Convergence gate:** monitor probes in representative canyons (incl. off-axis
  to catch any unsteadiness); q ONLY after the probes FREEZE. If a limit cycle →
  window-average + band, never a snapshot.

## 7. First run — ONE config first (not all 9)
**1H, 0°, std k-ε.** Full protocol. Show the generated dicts (domain around the
GROUP, blockage, adaptive mesh) BEFORE solving — operator review as on A/B. Then
probe-freeze → q. Only after that, decide whether to run the rest
(0H/2H × 0/22.5/45°). The 9-cell sweep is Phase-2 of Case C, gated on the first
result.

## 8. File-level tests (before any OF run)
- reference loader: caseC_data.json → 120 points × 3 directions, each with
  ratio_0H/1H/2H; U_H = 3.654; configs/directions as specified.
- geometry: 8 surrounding cube footprints at the confirmed positions; centre per
  config (none/H/2H); group bbox = 1.0 × 1.0 × {0.2|0.4}.
- domain: the explicit Domain around the whole group; blockage helper < the
  chosen target.
- generated dicts (via the runner): blockMeshDict extent around the group,
  adaptive refinement region present, tabulated inlet, monitor probes, manifest.

## 9. Open questions tracker
- [RESOLVED] Geometry layout — confirmed from the data (§2).
- [RESOLVED] Normalisation = variant 1, local / fixed inflow(z) (SimScale
  methodology); building-free-local is a diagnostic, not the metric (§3). U_H=3.654.
- [RESOLVED] Floor z0 = 4.5e-4 m (published AIJ value, §6).
- [RESOLVED-decision] Domain ±20H HALF (~1.5 %), adaptive mesh; building-free
  confirms y-uniform/clean (§4).
- [VERIFY at run] Definitive lateral-width test needs the cubes: in the 1H/0° run,
  check the flow at the ±4 m walls = inflow; widen if the wake reaches them (§4).
- [RECORDED] Incident drift baseline +7.3 % near-ground — for honest q
  interpretation (§3).
