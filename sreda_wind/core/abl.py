"""Atmospheric boundary layer (ABL) inflow physics.

Richards & Hoxey (1993) equilibrium profiles for a neutral ABL. Pure functions:
given a reference wind speed and a roughness length they return the friction
velocity, turbulent kinetic energy and dissipation rate that drive the inlet.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

VON_KARMAN = 0.41   # kappa
C_MU = 0.09         # k-epsilon model constant


@dataclass(frozen=True)
class ABLParameters:
    """Equilibrium ABL inflow parameters at the reference height."""
    ustar: float       # friction velocity [m/s]
    k: float           # turbulent kinetic energy [m2/s2]
    epsilon: float     # turbulent dissipation rate [m2/s3]
    z0: float          # aerodynamic roughness length [m]
    z_ref: float       # reference height [m]
    u_ref: float       # wind speed at z_ref [m/s]


def friction_velocity(u_ref, z_ref, z0, kappa=VON_KARMAN):
    """u* from the log law: u* = U_ref * kappa / ln((z_ref + z0) / z0)."""
    if z0 <= 0.0:
        raise ValueError("z0 must be positive")
    return u_ref * kappa / math.log((z_ref + z0) / z0)


def abl_parameters(u_ref, z_ref, z0, kappa=VON_KARMAN, c_mu=C_MU):
    """Richards & Hoxey inflow parameters.

    k = u*^2 / sqrt(C_mu),  epsilon = u*^3 / (kappa * (z_ref + z0)).
    """
    ustar = friction_velocity(u_ref, z_ref, z0, kappa)
    k = ustar * ustar / math.sqrt(c_mu)
    epsilon = ustar ** 3 / (kappa * (z_ref + z0))
    return ABLParameters(ustar=ustar, k=k, epsilon=epsilon, z0=z0, z_ref=z_ref, u_ref=u_ref)


def velocity_at(z, ustar, z0, kappa=VON_KARMAN):
    """Mean wind speed at height z: U(z) = (u*/kappa) * ln((z + z0) / z0)."""
    z_eff = max(z, 0.0)
    return (ustar / kappa) * math.log((z_eff + z0) / z0)


def dissipation_at(z, ustar, z0, kappa=VON_KARMAN):
    """Dissipation at height z: epsilon(z) = u*^3 / (kappa * (z + z0))."""
    z_eff = max(z, 0.0)
    return ustar ** 3 / (kappa * (z_eff + z0))
