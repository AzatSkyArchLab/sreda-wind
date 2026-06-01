"""Reattachment-length extraction from wall-adjacent streamwise velocity.

A separation bubble shows up as a stretch of reverse flow (negative streamwise
velocity) next to the wall, ending where the flow reattaches and the velocity
changes sign back to positive. The reattachment length is the distance from the
separation origin (the leading roof edge for X_R, the rear face for X_F) to that
first negative -> positive sign reversal, found by linear interpolation.

Standard k-epsilon famously predicts no roof separation, so X_R comes back as
None there -- which is the expected (correct) behaviour for KE1-KE5, not a bug.
"""
from __future__ import annotations


def reattachment_length(distances, u_wall):
    """Distance from the origin to the first reverse-to-forward reattachment.

    distances: increasing distances from the separation origin (>= 0).
    u_wall: wall-adjacent streamwise velocity (flow-aligned) at each distance.

    Returns the interpolated reattachment distance, or None if the flow never
    reverses (no separation bubble was captured).
    """
    if len(distances) != len(u_wall):
        raise ValueError("distances and u_wall must have equal length")
    if len(distances) < 2:
        return None

    saw_negative = False
    i = 0
    while i < len(u_wall) - 1:
        if u_wall[i] < 0.0:
            saw_negative = True
        if saw_negative and u_wall[i] < 0.0 <= u_wall[i + 1]:
            # Linear interpolation to the zero crossing between i and i+1.
            u0 = u_wall[i]
            u1 = u_wall[i + 1]
            t = (0.0 - u0) / (u1 - u0)
            return distances[i] + t * (distances[i + 1] - distances[i])
        i += 1
    return None


def reattachment_over_b(distances, u_wall, b):
    """Reattachment length normalised by b, or None if no reversal."""
    length = reattachment_length(distances, u_wall)
    if length is None:
        return None
    return length / b
