"""Reproduce the AIJ Case B pedestrian metrics from a solved case.

Given a converged case directory, samples the 115 pedestrian points (z=12.5 mm),
normalises the horizontal speed by U_H=5.133 and compares to the measured
ratio_UH -> q / FAC2 / NMSE / FB / R. Needs OpenFOAM (foamPostProcess); the pure
pieces (reference loader, metrics) are unit-tested. Run manually:

    python tests/aij/case_b/run_validation.py <solved_case_dir>
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from aij.metrics import compute_metrics
from aij.case_b import reference
from sreda_wind.post import PointSample, sets_dict, parse_raw, horizontal_speed


def pedestrian_metrics(case_dir, data=None):
    """Sample the 115 pedestrian points on a solved case and return the metrics."""
    if data is None:
        data = reference.load_reference()
    coords = reference.pedestrian_coords(data)
    observed = reference.observed_ratios(data)
    u_h = reference.reference_velocity(data)

    text = sets_dict([PointSample("ped", tuple(coords))], fields=("U",))
    with open(os.path.join(case_dir, "system", "caseBped"), "w") as f:
        f.write(text)
    subprocess.run(["foamPostProcess", "-func", "caseBped", "-latestTime"],
                   cwd=case_dir, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    base = os.path.join(case_dir, "postProcessing", "caseBped")
    times = []
    for d in os.listdir(base):
        try:
            times.append((float(d), d))
        except ValueError:
            pass
    times.sort()
    rows = parse_raw(open(os.path.join(base, times[-1][1], "ped.xy")).read())

    predicted = []
    i = 0
    while i < len(rows):
        ux, uy = rows[i][3], rows[i][4]
        predicted.append(horizontal_speed(ux, uy) / u_h)
        i += 1
    return compute_metrics(observed, predicted)


def main(case_dir):
    m = pedestrian_metrics(case_dir)
    print("=== AIJ Case B pedestrian metrics (/U_H=5.133, N={}) ===".format(m.n))
    print("  q    = {:.4f}   (AIJ target >= 0.66)".format(m.q))
    print("  FAC2 = {:.4f}".format(m.fac2))
    print("  NMSE = {:.4f}".format(m.nmse))
    print("  FB   = {:.4f}".format(m.fb))
    print("  R    = {:.4f}".format(m.r))
    print("  std k-epsilon: converges (steady), under-predicts comfort "
          "(stagnation-k anomaly, see VALIDATION_RESULTS.md)")


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "/tmp/se_caseB_w/caseBw"
    main(case)
