"""Wind direction convention and inflow velocity vectors.

Meteorological convention: the angle (degrees) is where the wind blows FROM,
clockwise from north (+y). 270 deg is a westerly wind blowing toward +x.
"""
from __future__ import annotations

import math


def flow_vector(direction_deg):
    """Unit horizontal flow direction (fx, fy) for wind coming FROM direction_deg.

    fx = -sin(theta), fy = -cos(theta).
    """
    rad = math.radians(direction_deg)
    return (-math.sin(rad), -math.cos(rad))


def inflow_velocity(direction_deg, speed):
    """Inflow velocity vector (ux, uy, uz) with uz = 0."""
    fx, fy = flow_vector(direction_deg)
    return (fx * speed, fy * speed, 0.0)
