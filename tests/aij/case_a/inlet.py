"""Build the tabulated inflow profile for the Case A inlet.

Takes the measured (z, U, k) points and adds the dissipation rate using the
AIJ-sanctioned local-equilibrium form (Section 4):

    epsilon(z) = Cmu^(1/2) * k(z) * dU/dz

dU/dz is estimated by finite differences (central in the interior, one-sided at
the ends). The result is the ((z, u, k, eps), ...) tuple that case/ consumes via
generate_case(inlet_profile=...).
"""
from __future__ import annotations

import math

C_MU = 0.09
_SQRT_CMU = math.sqrt(C_MU)   # Cmu^(1/2) ~ 0.3
_MIN_EPS = 1e-6               # floor to keep epsilon strictly positive


def _du_dz(zs, us):
    """Finite-difference dU/dz at each node (central interior, one-sided ends)."""
    n = len(zs)
    grad = [0.0] * n
    if n == 1:
        return grad
    grad[0] = (us[1] - us[0]) / (zs[1] - zs[0])
    grad[n - 1] = (us[n - 1] - us[n - 2]) / (zs[n - 1] - zs[n - 2])
    i = 1
    while i < n - 1:
        grad[i] = (us[i + 1] - us[i - 1]) / (zs[i + 1] - zs[i - 1])
        i += 1
    return grad


def build_inlet_profile(points):
    """Return ((z, u, k, eps), ...) from a list of (z, u, k) tuples.

    points: iterable of (z, u, k), assumed sorted by z.
    """
    zs = []
    us = []
    ks = []
    i = 0
    seq = list(points)
    while i < len(seq):
        z, u, k = seq[i]
        zs.append(z)
        us.append(u)
        ks.append(k)
        i += 1

    grad = _du_dz(zs, us)
    out = []
    i = 0
    while i < len(zs):
        eps = _SQRT_CMU * ks[i] * abs(grad[i])
        if eps < _MIN_EPS:
            eps = _MIN_EPS
        out.append((zs[i], us[i], ks[i], eps))
        i += 1
    return tuple(out)
