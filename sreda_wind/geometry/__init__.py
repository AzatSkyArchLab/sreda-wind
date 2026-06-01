"""Geometry layer: triangulation, triangle mesh, STL I/O, polygon validation.

Pure geometry, no OpenFOAM. Building footprints (polygon + height) are extruded
into a watertight triangle mesh, which is written as STL for snappyHexMesh.
"""
from .mesh import TriMesh, merge
from .triangulate import (
    is_ccw, ensure_ccw, is_convex_polygon, triangulate_ear_clipping,
    extrude_footprint,
)
from .stl import write_ascii, write_binary, read_stl
from .validate import polygon_area, validate_polygon

__all__ = [
    "TriMesh", "merge",
    "is_ccw", "ensure_ccw", "is_convex_polygon", "triangulate_ear_clipping",
    "extrude_footprint",
    "write_ascii", "write_binary", "read_stl",
    "polygon_area", "validate_polygon",
]
