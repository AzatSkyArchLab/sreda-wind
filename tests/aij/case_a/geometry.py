"""AIJ Case A geometry: the 1:1:2 isolated building at wind-tunnel scale.

A single rectangular block, b x b in plan and h = 2b tall, centred on the
origin in plan with its base at z = 0. At model scale b = 0.08 m, so the box is
0.08 x 0.08 x 0.16 m. The mesh is built with the generic geometry layer and
written as a binary STL for snappyHexMesh.
"""
from __future__ import annotations

from sreda_wind.geometry import extrude_footprint, write_binary

# Model-scale dimensions [m].
B = 0.08            # building width and depth (the AIJ length scale)
H = 2.0 * B         # building height (1:1:2 -> h = 2b = 0.16 m)


def footprint(b=B):
    """CCW square footprint centred on the origin, side length b."""
    half = b / 2.0
    return [
        (-half, -half),
        (half, -half),
        (half, half),
        (-half, half),
    ]


def build_mesh(b=B):
    """Return the watertight TriMesh of the Case A building."""
    return extrude_footprint(footprint(b), height=2.0 * b)


def write_stl(path, b=B):
    """Write the Case A building as a binary STL and return its TriMesh."""
    mesh = build_mesh(b)
    write_binary(mesh, path)
    return mesh
