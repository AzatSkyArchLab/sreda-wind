"""AIJ Case B geometry: the 4:4:1 thin tall plate at wind-tunnel scale.

A broadside plate: the WIDE face (200 mm = 4b) is across-wind, the depth
(50 mm = 1b) is along-wind, height 200 mm = 4b. Orientation RESOLVED from the
measurement grid (SPEC.md §2): wind along +x, so the plate is wide in y, thin in
x. Centred on the origin in plan, base at z = 0.
"""
from __future__ import annotations

from sreda_wind.geometry import extrude_footprint, write_binary

# Model-scale dimensions [m].
B = 0.05               # length scale b (the thin along-wind depth)
H = 4.0 * B            # height = 4b = 0.20 m
WIDTH_CROSS = 4.0 * B  # across-wind width = 4b = 0.20 m (the wide broadside face)
DEPTH_ALONG = 1.0 * B  # along-wind depth = 1b = 0.05 m


def footprint():
    """CCW rectangle: thin in x (along-wind), wide in y (across-wind)."""
    hx = DEPTH_ALONG / 2.0   # 0.025
    hy = WIDTH_CROSS / 2.0   # 0.10
    return [
        (-hx, -hy),
        (hx, -hy),
        (hx, hy),
        (-hx, hy),
    ]


def build_mesh():
    """Return the watertight TriMesh of the Case B plate."""
    return extrude_footprint(footprint(), height=H)


def write_stl(path):
    """Write the Case B plate as a binary STL and return its TriMesh."""
    mesh = build_mesh()
    write_binary(mesh, path)
    return mesh
