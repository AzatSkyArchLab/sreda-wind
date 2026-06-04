"""Convergence and stationarity decisions from a parsed solver log.

Pure: operates on a SolverLog (from logparse) and, optionally, a probe/quantity
series. Two questions, kept separate because AIJ 2.1.7 asks for both: did the
residuals meet the control target, and is a monitored quantity stationary (flat
to within a relative tolerance over the last window of iterations)?
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

DEFAULT_REL_TOL = 0.01    # window spread / |mean| for stationarity
DEFAULT_WINDOW = 20       # iterations in the stationarity window


def is_converged(log, residual_target, fields=None):
    """True if the run reached the residual control.

    Honours the explicit "solution converged" message; otherwise checks that
    every tracked field's last initial residual is finite and <= residual_target.
    A diverged or fatal run is never converged.
    """
    if log.fatal or log.diverged:
        return False
    if log.converged:
        return True
    if log.n_steps == 0:
        return False
    if fields is None:
        names = list(log.final_residuals.keys())
    else:
        names = fields
    if len(names) == 0:
        return False
    i = 0
    while i < len(names):
        r = log.final_residuals.get(names[i])
        if r is None:
            return False
        if r != r or r == float("inf"):   # nan / inf
            return False
        if r > residual_target:
            return False
        i += 1
    return True


def is_stationary(series, rel_tol=DEFAULT_REL_TOL, window=DEFAULT_WINDOW):
    """True if the last `window` values are flat to within rel_tol.

    Flatness = (max - min) over the window <= rel_tol * |mean of window|. For a
    near-zero mean the same bound is applied absolutely (rel_tol) to avoid a
    divide-by-zero blow-up. Returns False if there is less than `window` history.
    """
    if window < 2 or len(series) < window:
        return False
    w = series[len(series) - window:]
    smallest = w[0]
    largest = w[0]
    total = 0.0
    i = 0
    while i < len(w):
        v = w[i]
        if v != v or v == float("inf") or v == float("-inf"):
            return False
        if v < smallest:
            smallest = v
        if v > largest:
            largest = v
        total += v
        i += 1
    spread = largest - smallest
    mean = total / len(w)
    scale = abs(mean)
    if scale < 1.0e-12:
        return spread <= rel_tol
    return spread <= rel_tol * scale


@dataclass
class ConvergenceReport:
    """Combined verdict for one run."""
    status: str = "not_converged"   # converged | not_converged | diverged | failed
    converged: bool = False         # residual control reached
    stationary: bool = True         # probe series flat (True if no probe given)
    diverged: bool = False
    fatal: bool = False
    n_iterations: int = 0
    final_residuals: dict = field(default_factory=dict)
    max_final_residual: float = 0.0


def evaluate(log, residual_target, probe_series=None,
             rel_tol=DEFAULT_REL_TOL, window=DEFAULT_WINDOW, fields=None):
    """Fold a SolverLog (+ optional probe series) into a ConvergenceReport."""
    rep = ConvergenceReport()
    rep.fatal = log.fatal
    rep.diverged = log.diverged
    rep.n_iterations = log.n_steps
    rep.final_residuals = dict(log.final_residuals)

    worst = 0.0
    for name in log.final_residuals:
        r = log.final_residuals[name]
        if r == r and r != float("inf") and r > worst:   # ignore nan/inf here
            worst = r
    rep.max_final_residual = worst

    if log.fatal:
        rep.status = "failed"
        return rep
    if log.diverged:
        rep.status = "diverged"
        return rep

    rep.converged = is_converged(log, residual_target, fields)
    if probe_series is not None:
        rep.stationary = is_stationary(probe_series, rel_tol, window)
    if rep.converged and rep.stationary:
        rep.status = "converged"
    else:
        rep.status = "not_converged"
    return rep
