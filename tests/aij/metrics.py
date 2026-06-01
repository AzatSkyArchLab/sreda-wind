"""Validation metrics for comparing CFD predictions against benchmark data.

All metrics follow the COST 732 / AIJ definitions. The headline metric is the
hit rate q (AIJ acceptance: q >= 0.66). Inputs are two equal-length sequences:
observed O (experiment / reference) and predicted P (CFD). Pure Python, stdlib
only, no list comprehensions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# AIJ hit-rate tolerances: D relative, W absolute (on the compared quantity).
DEFAULT_D = 0.25
DEFAULT_W = 0.06


@dataclass(frozen=True)
class ValidationMetrics:
    """Bundle of validation statistics for one comparison set."""
    n: int
    q: float        # hit rate
    fac2: float     # fraction within a factor of two
    nmse: float     # normalised mean square error
    fb: float       # fractional bias
    r: float        # Pearson correlation coefficient


def _check_pair(observed, predicted):
    """Validate the two sequences and return them as plain lists."""
    o = list(observed)
    p = list(predicted)
    if len(o) != len(p):
        raise ValueError("observed and predicted must have equal length")
    if len(o) == 0:
        raise ValueError("need at least one data point")
    return o, p


def _mean(values):
    total = 0.0
    i = 0
    while i < len(values):
        total += values[i]
        i += 1
    return total / len(values)


def hit_rate(observed, predicted, d=DEFAULT_D, w=DEFAULT_W):
    """AIJ hit rate q.

    A point counts as a hit if it is within the relative tolerance d OR the
    absolute tolerance w: |(P-O)/O| <= d  or  |P-O| <= w. When O == 0 only the
    absolute criterion applies (the relative one is undefined).
    """
    o, p = _check_pair(observed, predicted)
    hits = 0
    i = 0
    while i < len(o):
        oi = o[i]
        pi = p[i]
        abs_ok = abs(pi - oi) <= w
        rel_ok = False
        if oi != 0.0:
            rel_ok = abs((pi - oi) / oi) <= d
        if abs_ok or rel_ok:
            hits += 1
        i += 1
    return hits / len(o)


def fac2(observed, predicted):
    """Fraction of points with 0.5 <= P/O <= 2.

    When O == 0 a point counts only if P == 0 as well.
    """
    o, p = _check_pair(observed, predicted)
    good = 0
    i = 0
    while i < len(o):
        oi = o[i]
        pi = p[i]
        if oi == 0.0:
            if pi == 0.0:
                good += 1
        else:
            ratio = pi / oi
            if 0.5 <= ratio <= 2.0:
                good += 1
        i += 1
    return good / len(o)


def nmse(observed, predicted):
    """Normalised mean square error: mean((O-P)^2) / (mean(O) * mean(P))."""
    o, p = _check_pair(observed, predicted)
    se_total = 0.0
    i = 0
    while i < len(o):
        diff = o[i] - p[i]
        se_total += diff * diff
        i += 1
    mse = se_total / len(o)
    denom = _mean(o) * _mean(p)
    if denom == 0.0:
        return float("nan")
    return mse / denom


def fractional_bias(observed, predicted):
    """Fractional bias: (mean(O)-mean(P)) / (0.5*(mean(O)+mean(P)))."""
    o, p = _check_pair(observed, predicted)
    mo = _mean(o)
    mp = _mean(p)
    denom = 0.5 * (mo + mp)
    if denom == 0.0:
        return float("nan")
    return (mo - mp) / denom


def pearson_r(observed, predicted):
    """Pearson correlation coefficient; nan if either series is constant."""
    o, p = _check_pair(observed, predicted)
    mo = _mean(o)
    mp = _mean(p)
    cov = 0.0
    var_o = 0.0
    var_p = 0.0
    i = 0
    while i < len(o):
        do = o[i] - mo
        dp = p[i] - mp
        cov += do * dp
        var_o += do * do
        var_p += dp * dp
        i += 1
    if var_o == 0.0 or var_p == 0.0:
        return float("nan")
    return cov / math.sqrt(var_o * var_p)


def compute_metrics(observed, predicted, d=DEFAULT_D, w=DEFAULT_W):
    """Compute the full ValidationMetrics bundle for one comparison set."""
    o, p = _check_pair(observed, predicted)
    return ValidationMetrics(
        n=len(o),
        q=hit_rate(o, p, d=d, w=w),
        fac2=fac2(o, p),
        nmse=nmse(o, p),
        fb=fractional_bias(o, p),
        r=pearson_r(o, p),
    )
