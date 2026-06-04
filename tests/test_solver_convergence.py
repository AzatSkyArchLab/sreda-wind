"""Unit tests for solver convergence/stationarity (pure)."""
import pytest

from sreda_wind.solver import (
    parse_solver_log, is_converged, is_stationary, evaluate, window_stat,
)


def _log(steps):
    """Build a tiny foamRun log from (time, p_init, k_init) tuples."""
    out = []
    i = 0
    while i < len(steps):
        t, pp, kk = steps[i]
        out.append("Time = {}s\n".format(t))
        out.append("smoothSolver:  Solving for Ux, Initial residual = {}, Final residual = 1e-6, No Iterations 3\n".format(pp))
        out.append("GAMG:  Solving for p, Initial residual = {}, Final residual = 1e-6, No Iterations 4\n".format(pp))
        out.append("smoothSolver:  Solving for k, Initial residual = {}, Final residual = 1e-6, No Iterations 3\n".format(kk))
        i += 1
    return "".join(out)


# --- is_converged -----------------------------------------------------------

def test_is_converged_explicit_message():
    text = _log([(1, 0.5, 0.4), (2, 0.2, 0.1)]) + "\nSIMPLE solution converged in 2 iterations\n"
    log = parse_solver_log(text)
    assert is_converged(log, 1e-4) is True   # message wins regardless of target


def test_is_converged_by_residual_target():
    log = parse_solver_log(_log([(1, 0.5, 0.4), (2, 5e-5, 3e-5)]))
    assert is_converged(log, 1e-4) is True       # all last residuals < target
    assert is_converged(log, 1e-6) is False      # tighter target not met


def test_is_converged_false_when_diverged_or_empty():
    div = parse_solver_log(_log([(1, 0.1, 0.1)]) + "Floating point exception (core dumped)\n")
    assert div.diverged is True
    assert is_converged(div, 1.0) is False       # diverged is never converged
    assert is_converged(parse_solver_log(""), 1.0) is False


# --- is_stationary ----------------------------------------------------------

def _series(values):
    out = []
    i = 0
    while i < len(values):
        out.append(values[i])
        i += 1
    return out


def test_is_stationary_flat():
    # 30 points hovering at 1.20 +/- 0.005 -> spread 0.01, /mean ~0.008 < 0.01.
    vals = []
    i = 0
    while i < 30:
        vals.append(1.20 + (0.005 if i % 2 == 0 else -0.005))
        i += 1
    assert is_stationary(vals, rel_tol=0.01, window=20) is True


def test_is_stationary_trending_false():
    # Still developing: rising from 1.0 to 2.0 over the window.
    vals = []
    i = 0
    while i < 30:
        vals.append(1.0 + 0.05 * i)
        i += 1
    assert is_stationary(vals, rel_tol=0.01, window=20) is False


def test_is_stationary_too_short():
    assert is_stationary([1.0, 1.0, 1.0], rel_tol=0.01, window=20) is False


def test_is_stationary_near_zero_mean():
    # Mean ~0: absolute spread compared to rel_tol.
    vals = []
    i = 0
    while i < 25:
        vals.append(0.002 if i % 2 == 0 else -0.002)
        i += 1
    assert is_stationary(vals, rel_tol=0.01, window=20) is True


def test_is_stationary_on_real_probe_series():
    # Real |U| at a wake point (0.16,-0.05,0.01) over a Case A run (OF13). The
    # settled tail oscillates within ~0.8% over the last 20; a still-developing
    # earlier segment does not. Calibrates window/rel_tol on real numerics, not a
    # smooth synthetic curve.
    tail = [3.0118, 3.0104, 3.009, 3.0075, 3.0061, 3.0048, 3.0034, 3.002, 3.0006,
            2.9993, 2.9979, 2.9966, 2.9952, 2.9939, 2.9926, 2.9912, 2.9899, 2.9886,
            2.9873, 2.986, 2.9847, 2.9834, 2.9822, 2.9809]
    dev = [3.9194, 3.9256, 3.9302, 3.9306, 3.926, 3.9171, 3.9057, 3.8937, 3.8826,
           3.8733, 3.8661, 3.8604, 3.8556, 3.8509, 3.8457, 3.8397, 3.8329, 3.8255,
           3.8178, 3.8102, 3.8027, 3.7955, 3.7886, 3.7819]
    assert is_stationary(tail, rel_tol=0.01, window=20) is True
    assert is_stationary(dev, rel_tol=0.01, window=20) is False


# --- window_stat (plateau-window q for non-converging steady RANS) ---------

def test_window_stat_narrow_band():
    # A frozen/settled plateau: q identical across snapshots -> narrow, the mean
    # is trustworthy (this is the AIJ Case A equilibrium-seed outcome).
    vals = [0.6167, 0.6167, 0.6167, 0.6167, 0.6167]
    ws = window_stat(vals)
    assert ws.n == 5
    assert ws.mean == pytest.approx(0.6167)
    assert ws.half_band == pytest.approx(0.0)
    assert ws.narrow is True


def test_window_stat_wide_band_not_narrow():
    # Wide scatter (0.55-0.75): averaging hides the uncertainty -> not narrow,
    # the band must be reported (or move to URANS).
    vals = [0.55, 0.62, 0.75, 0.60, 0.71]
    ws = window_stat(vals, rel_tol=0.01)
    assert ws.minimum == pytest.approx(0.55)
    assert ws.maximum == pytest.approx(0.75)
    assert ws.half_band == pytest.approx(0.10)
    assert ws.narrow is False
    assert ws.std > 0.0


def test_window_stat_empty():
    ws = window_stat([])
    assert ws.n == 0 and ws.mean == 0.0


# --- evaluate (combined verdict) -------------------------------------------

def test_evaluate_converged_and_stationary():
    text = _log([(1, 0.5, 0.4), (2, 5e-5, 3e-5)])
    log = parse_solver_log(text)
    flat = []
    i = 0
    while i < 25:
        flat.append(3.0)
        i += 1
    rep = evaluate(log, 1e-4, probe_series=flat, window=20)
    assert rep.status == "converged"
    assert rep.converged is True and rep.stationary is True


def test_evaluate_diverged():
    log = parse_solver_log(_log([(1, 0.1, 0.1)]) + "Floating point exception (core dumped)\n")
    rep = evaluate(log, 1e-4)
    assert rep.status == "diverged" and rep.diverged is True


def test_evaluate_fatal():
    log = parse_solver_log("--> FOAM FATAL ERROR: \nbad\nFOAM exiting\n")
    rep = evaluate(log, 1e-4)
    assert rep.status == "failed" and rep.fatal is True


def test_evaluate_residual_ok_but_not_stationary():
    log = parse_solver_log(_log([(1, 5e-5, 3e-5)]))
    rising = []
    i = 0
    while i < 25:
        rising.append(1.0 + 0.1 * i)
        i += 1
    rep = evaluate(log, 1e-4, probe_series=rising, window=20)
    assert rep.converged is True
    assert rep.stationary is False
    assert rep.status == "not_converged"
