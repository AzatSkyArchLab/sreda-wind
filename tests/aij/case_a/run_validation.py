"""End-to-end AIJ Case A validation against a solved OpenFOAM case.

Given a solved case directory, this:
  1. writes a `sets` sampling dict (roof + wake lines for reattachment;
     the 60 pedestrian points for the hit rate),
  2. runs foamPostProcess to sample the latest time,
  3. extracts X_R / X_F and compares to AIJ Table 2-1-3,
  4. computes q / FAC2 / NMSE / FB / R of the pedestrian horizontal speed
     ratio vs the measured data, and prints PASS/FAIL.

Run manually (needs a solved case + OpenFOAM): it is not a pytest test. The
pure pieces it relies on (metrics, reattachment, sampling parsers) are tested.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from aij.metrics import compute_metrics
from aij.case_a import reference, reattachment
from sreda_wind.post import LineSample, PointSample, sets_dict, parse_raw, horizontal_speed

B = 0.08
ROOF_ORIGIN_X = -0.04
WAKE_ORIGIN_X = 0.04
PEDESTRIAN_Z = 0.01
ROOF_Z = 0.163          # just above the roof (z = 2b + a near-wall offset)
WAKE_Z = 0.002          # wall-adjacent above the floor (inside the prism layers)


def _write_sets(case_dir, ped_points):
    samples = [
        LineSample("roof", (ROOF_ORIGIN_X, 0.0, ROOF_Z), (0.04, 0.0, ROOF_Z), 200),
        LineSample("wake", (WAKE_ORIGIN_X, 0.0, WAKE_Z), (0.6, 0.0, WAKE_Z), 400),
        PointSample("pedestrian", tuple(ped_points)),
    ]
    text = sets_dict(samples, fields=("U",))
    path = os.path.join(case_dir, "system", "validationSets")
    with open(path, "w") as f:
        f.write(text)


def _latest_dir(case_dir):
    base = os.path.join(case_dir, "postProcessing", "validationSets")
    times = []
    for d in os.listdir(base):
        try:
            times.append((float(d), d))
        except ValueError:
            pass
    times.sort()
    return os.path.join(base, times[-1][1])


def _read(path, origin_x):
    """Read a line .xy (cols: x Ux Uy Uz) -> (distances_from_origin, Ux)."""
    rows = parse_raw(open(path).read())
    distances = []
    ux = []
    i = 0
    while i < len(rows):
        distances.append(rows[i][0] - origin_x)
        ux.append(rows[i][1])
        i += 1
    return distances, ux


def main(case_dir):
    data = reference.load_reference()
    ped = reference.pedestrian_ratios(data)
    ped_points = []
    i = 0
    while i < len(ped):
        p = ped[i]
        ped_points.append((p["x"], p["y"], PEDESTRIAN_Z))
        i += 1

    _write_sets(case_dir, ped_points)
    subprocess.run(["foamPostProcess", "-func", "validationSets", "-latestTime"],
                   cwd=case_dir, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = _latest_dir(case_dir)

    # --- reattachment ---
    roof_d, roof_u = _read(os.path.join(d, "roof.xy"), ROOF_ORIGIN_X)
    wake_d, wake_u = _read(os.path.join(d, "wake.xy"), WAKE_ORIGIN_X)
    xr = reattachment.reattachment_over_b(roof_d, roof_u, B)
    xf = reattachment.reattachment_over_b(wake_d, wake_u, B)
    t = reference.reattachment_targets(data)

    print("=== Reattachment vs AIJ Table 2-1-3 (standard k-epsilon) ===")
    print("                     X_R/b      X_F/b")
    print("  sreda-wind         {:<10} {}".format(
        "none" if xr is None else "{:.2f}".format(xr),
        "none" if xf is None else "{:.2f}".format(xf)))
    print("  experiment         {:<10} {}".format(
        t["experiment"]["XR_over_b"], t["experiment"]["XF_over_b"]))
    print("  std k-eps KE1-KE5  {:<10} {}".format("none", t["standard_keps_KE1_KE5"]["XF_over_b_range"]))

    # --- pedestrian hit rate ---
    rows = parse_raw(open(os.path.join(d, "pedestrian.xy")).read())
    u_ref = reference.u_ref(data, "pedestrian")
    observed = []
    predicted = []
    i = 0
    while i < len(ped) and i < len(rows):
        r = rows[i]
        # points set raw output: x y z Ux Uy Uz
        ux, uy = r[3], r[4]
        predicted.append(horizontal_speed(ux, uy) / u_ref)
        observed.append(ped[i]["ratio_horizontal"])
        i += 1

    m = compute_metrics(observed, predicted)
    print()
    print("=== Pedestrian hit rate (z/b=0.125, horizontal ratio, N={}) ===".format(m.n))
    print("  q    = {:.3f}   (AIJ target >= 0.66)".format(m.q))
    print("  FAC2 = {:.3f}".format(m.fac2))
    print("  NMSE = {:.3f}".format(m.nmse))
    print("  FB   = {:.3f}".format(m.fb))
    print("  R    = {:.3f}".format(m.r))
    print("  q PASS" if m.q >= 0.66 else "  q BELOW TARGET")


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "/tmp/caseA_floor"
    main(case)
